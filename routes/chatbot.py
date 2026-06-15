from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models.fiche import Fiche
from models.demande import Demande
from models.user import User
from routes.auth import get_current_user
from openai import OpenAI
import os
import httpx 
router = APIRouter()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    http_client=httpx.Client(verify=False)
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    historique: Optional[List[Message]] = []

def build_system_prompt(db: Session, user: User) -> str:
    total_fiches = db.query(Fiche).count()
    approved = db.query(Fiche).filter(Fiche.status == "Approved").count()
    to_update = db.query(Fiche).filter(Fiche.status == "To be updated").count()
    cancelled = db.query(Fiche).filter(Fiche.status == "Cancelled").count()
    total_demandes = db.query(Demande).count()

    return f"""
Tu es l'assistant intelligent de la plateforme GFST (Global FaSteners Team) de Stellantis.
Tu aides les ingénieurs, concepteurs et opérateurs à gérer les gammes de fixations automobiles.

IDENTITÉ :
- Tu t'appelles "Assistant GFST"
- Tu es expert en fixations automobiles (vis, boulons, clips, inserts)
- Tu réponds en français par défaut, en anglais si l'utilisateur écrit en anglais
- Tu es professionnel, précis et concis

UTILISATEUR CONNECTÉ :
- Nom : {user.prenom} {user.nom}
- Rôle : {user.role.value}
- Site : {user.site or "Non renseigné"}

ÉTAT DE LA BASE DE DONNÉES :
- Total fiches GFST : {total_fiches}
- Approuvées : {approved}
- À mettre à jour : {to_update}
- Annulées : {cancelled}
- Total demandes : {total_demandes}

FONCTIONNALITÉS DE LA PLATEFORME :
1. /parametres — Liste complète des fiches avec filtres
2. /ajouter-fiche — Créer une nouvelle gamme
3. /modifie-fiche — Modifier une fiche existante
4. Demandes — Suivi des créations et modifications

STATUTS DES FICHES :
- Approved : Validée et applicable en production
- Applicable : Applicable sans approbation formelle
- To be updated : À mettre à jour
- Cancelled : Annulée, ne pas utiliser
- Current Update : Mise à jour en cours

RÈGLES :
- Si on te demande une fiche, guide vers la recherche dans /parametres
- Si on te demande de créer, guide vers /ajouter-fiche
- Si on te demande de modifier, guide vers /modifie-fiche
- Ne jamais inventer de références ou données techniques
- Toujours rester factuel et basé sur les vraies données
"""

def search_fiches_context(db: Session, query: str) -> str:
    if not query or len(query) < 3:
        return ""
    fiches = db.query(Fiche).filter(
        Fiche.reference.ilike(f"%{query}%") |
        Fiche.designation_fr.ilike(f"%{query}%") |
        Fiche.designation_en.ilike(f"%{query}%") |
        Fiche.vehicle_area.ilike(f"%{query}%")
    ).limit(5).all()

    if not fiches:
        return f"\nAucune fiche trouvée pour '{query}'."

    result = f"\nFiches trouvées pour '{query}' :\n"
    for f in fiches:
        result += f"- {f.reference} | {f.designation_fr} | {f.vehicle_area} | Statut: {f.status}\n"
    return result

@router.post("/")
async def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        system_prompt = build_system_prompt(db, current_user)

        keywords = ["fiche", "référence", "fixation", "gamme", "cherche", "trouve", "search", "find"]
        if any(kw in body.message.lower() for kw in keywords):
            fiche_context = search_fiches_context(db, body.message)
            if fiche_context:
                system_prompt += f"\n═══ RECHERCHE EN BASE ═══{fiche_context}"

        messages = [{"role": "system", "content": system_prompt}]
        for msg in body.historique[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": body.message})

        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "GFST Platform",
            },
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )

        return {
            "reponse": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens if response.usage else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur IA: {str(e)}")

@router.get("/search")
def search_fiches(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fiches = db.query(Fiche).filter(
        Fiche.reference.ilike(f"%{q}%") |
        Fiche.designation_fr.ilike(f"%{q}%") |
        Fiche.designation_en.ilike(f"%{q}%")
    ).limit(10).all()

    return {
        "data": [{
            "reference": f.reference,
            "designation_fr": f.designation_fr,
            "designation_en": f.designation_en,
            "vehicle_area": f.vehicle_area,
            "status": f.status,
            "lot": f.lot
        } for f in fiches]
    }