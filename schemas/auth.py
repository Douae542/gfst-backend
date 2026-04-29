from pydantic import BaseModel, EmailStr
from typing import Optional
from models.user import RoleEnum

class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    password: str
    role: Optional[RoleEnum] = RoleEnum.operateur
    site: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: RoleEnum
    site: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse