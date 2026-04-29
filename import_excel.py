import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from init_db import Fiche
import os
import sys

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def import_fiches(fichier):
    print("Import:", fichier)
    df = pd.read_excel(fichier, sheet_name="Table APOQUA files", header=1)
    df.columns = df.columns.str.strip()
    print("Lignes trouvees:", len(df))

    db = SessionLocal()
    imported = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            ref = str(row.get("Reference", "")).strip()
            if not ref or ref == "nan":
                continue

            existing = db.query(Fiche).filter(Fiche.reference == ref).first()
            if existing:
                skipped += 1
                continue

            fiche = Fiche(
                reference=ref,
                designation_fr=str(row.get("APOQUA designation (Français)", "") or ""),
                designation_en=str(row.get("APOQUA designation (English)", "") or ""),
                vehicle_area=str(row.get("Vehicle area", "") or ""),
                psa_dec=str(row.get("PSA DEC", "") or ""),
                lot=str(row.get("Lot", "") or ""),
                status=str(row.get("Status", "To be updated") or "To be updated"),
                in_poro=str(row.get("In file PORO", "NO") or "NO"),
                in_pfr=str(row.get("In pfe Lionel", "NO") or "NO"),
                creation_date=str(row.get("Creation date", "") or ""),
                last_modification=str(row.get("Last modification", "") or ""),
            )
            db.add(fiche)
            imported += 1

            if imported % 50 == 0:
                db.commit()
                print("Importees:", imported)

        except Exception as e:
            print("Erreur:", e)

    db.commit()
    print("Import termine!")
    print("Importees:", imported)
    print("Ignorees:", skipped)
    db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fichier = sys.argv[1]
    else:
        fichier = input("Chemin du fichier Excel: ").strip()
    
    if not os.path.exists(fichier):
        print("Fichier introuvable:", fichier)
    else:
        import_fiches(fichier)