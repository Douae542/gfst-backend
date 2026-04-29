from pydantic import BaseModel
from typing import Optional

class DemandeCreate(BaseModel):
    reference: str
    type_demande: str
    description: Optional[str] = ""

class DemandeUpdate(BaseModel):
    statut: Optional[str] = None
    description: Optional[str] = None

class DemandeResponse(BaseModel):
    id: int
    reference: str
    type_demande: str
    statut: str
    description: Optional[str]
    created_by: int

    class Config:
        from_attributes = True