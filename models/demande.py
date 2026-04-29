from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Demande(Base):
    __tablename__ = "demandes"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(100), nullable=False)
    type_demande = Column(String(100))
    statut = Column(String(100), default="En attente")
    description = Column(String(1000))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())