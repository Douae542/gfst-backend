from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.demande import Demande
from models.user import User, RoleEnum
from schemas.demande import DemandeCreate, DemandeUpdate, DemandeResponse
from routes.auth import get_current_user, require_role

router = APIRouter()

@router.get("/")
def get_demandes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role in [RoleEnum.super_admin, RoleEnum.admin]:
        demandes = db.query(Demande).all()
    else:
        demandes = db.query(Demande).filter(
            Demande.created_by == current_user.id
        ).all()
    return {"data": demandes, "total": len(demandes)}

@router.post("/")
def create_demande(
    data: DemandeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    demande = Demande(**data.dict(), created_by=current_user.id)
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return demande

@router.put("/{demande_id}")
def update_demande(
    demande_id: int,
    data: DemandeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.super_admin, RoleEnum.admin))
):
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    for key, value in data.dict(exclude_none=True).items():
        setattr(demande, key, value)
    db.commit()
    db.refresh(demande)
    return demande

@router.delete("/{demande_id}")
def delete_demande(
    demande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.super_admin))
):
    demande = db.query(Demande).filter(Demande.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    db.delete(demande)
    db.commit()
    return {"message": "Demande supprimée"}