from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from models import user, fiche, demande
from routes import auth, fiches, demandes, chatbot
from routes.kpi import router as kpi_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GFST API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(fiches.router,   prefix="/api/fiches",   tags=["Fiches"])
app.include_router(demandes.router, prefix="/api/demandes", tags=["Demandes"])
app.include_router(chatbot.router,  prefix="/api/chatbot",  tags=["Chatbot"])
app.include_router(kpi_router, tags=["KPI"])

@app.get("/")
def root():
    return {"message": "GFST API OK"}



