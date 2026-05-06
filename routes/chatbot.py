# routes/chatbot.py

import os
from groq import Groq
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models.fiche import Fiche
from models.demande import Demande
from models.user import User
from routes.auth import get_current_user
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL        = "llama3-8b-8192"

groq_client = Groq(api_key=GROQ_API_KEY)

router = APIRouter(
    prefix="/api/chatbot",
    tags=["chatbot"],
    redirect_slashes=False
)

# ─── Schémas ─────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    historique: Optional[List[Message]] = []

# ─── Appel Groq SDK ──────────────────────────────────────────────────
def call_groq(messages: list) -> str:
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        print(f"✅ GROQ OK : {response.choices[0].message.content[:100]}")
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ GROQ ERREUR : {str(e)}")
        raise ValueError(f"Groq SDK erreur : {str(e)}")

# ─── Prompt système ──────────────────────────────────────────────────
def build_system_prompt(db: Session, user: User) -> str:
    try:
        total_fiches   = db.query(Fiche).count()
        approved       = db.query(Fiche).filter(Fiche.statut == "Approuvé").count()
        to_update      = db.query(Fiche).filter(Fiche.statut == "À mettre à jour").count()
        cancelled      = db.query(Fiche).filter(Fiche.statut == "Annulé").count()
        total_demandes = db.query(Demande).count()
    except:
        total_fiches = approved = to_update = cancelled = total_demandes = 0

    return f"""
Tu es l'assistant intelligent de la plateforme GFST (Global FaSteners Team) de Stellantis.
Tu aides les ingénieurs et opérateurs à gérer les gammes de fixations automobiles.

IDENTITÉ :
- Tu t'appelles "Assistant GFST"
- Tu es expert en fixations automobiles (vis, boulons, clips, inserts)
- Tu réponds en français par défaut, en anglais si l'utilisateur écrit en anglais
- Tu es professionnel, précis et concis

UTILISATEUR CONNECTÉ :
- Nom  : {user.prenom} {user.nom}
- Rôle : {user.role}
- Site : {getattr(user, 'site', 'Non renseigné')}

ÉTAT DE LA BASE DE DONNÉES :
- Total fiches GFST : {total_fiches}
- Approuvées        : {approved}
- À mettre à jour   : {to_update}
- Annulées          : {cancelled}
- Total demandes    : {total_demandes}

FONCTIONNALITÉS :
1. /parametres    — Liste complète des fiches avec filtres
2. /ajouter-fiche — Créer une nouvelle gamme
3. /modifie-fiche — Modifier une fiche existante
4. Demandes       — Suivi des créations et modifications

STATUTS DES FICHES :
- Approuvé             : Validée et applicable en production
- Applicable           : Applicable sans approbation formelle
- À mettre à jour      : Doit être mise à jour
- Annulé               : Ne pas utiliser
- Mise à jour actuelle : Mise à jour en cours

RÈGLES :
- Si on demande une fiche   → guide vers /parametres
- Si on demande de créer    → guide vers /ajouter-fiche
- Si on demande de modifier → guide vers /modifie-fiche
- Ne jamais inventer de références ou données techniques
- Toujours rester factuel et concis
"""

# ─── Recherche fiches ────────────────────────────────────────────────
def search_fiches_context(db: Session, query: str) -> str:
    if not query or len(query) < 3:
        return ""
    try:
        fiches = db.query(Fiche).filter(
            Fiche.reference.ilike(f"%{query}%") |
            Fiche.designation_fr.ilike(f"%{query}%") |
            Fiche.vehicle_area.ilike(f"%{query}%")
        ).limit(5).all()

        if not fiches:
            return f"\nAucune fiche trouvée pour '{query}'."

        result = f"\nFiches trouvées pour '{query}' :\n"
        for f in fiches:
            result += f"- {f.reference} | {f.designation_fr} | Statut : {f.statut}\n"
        return result
    except:
        return ""

# ─── POST /api/chatbot/ ──────────────────────────────────────────────
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

        reponse = call_groq(messages)
        return {"reponse": reponse}

    except Exception as e:
        print(f"❌ ERREUR CHATBOT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur IA : {str(e)}")

# ─── GET /api/chatbot/search ─────────────────────────────────────────
@router.get("/search")
def search_fiches(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        fiches = db.query(Fiche).filter(
            Fiche.reference.ilike(f"%{q}%") |
            Fiche.designation_fr.ilike(f"%{q}%")
        ).limit(10).all()

        return {
            "data": [{
                "reference":      f.reference,
                "designation_fr": f.designation_fr,
                "vehicle_area":   f.vehicle_area,
                "statut":         f.statut,
                "lot":            getattr(f, 'lot', '')
            } for f in fiches]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── GET /api/chatbot/health ─────────────────────────────────────────
@router.get("/health")
def health():
    return {"status": "ok", "model": MODEL, "provider": "Groq SDK"}