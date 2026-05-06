import pandas as pd
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from database import SessionLocal, engine
from models.fiche import Fiche
from models.user import User  # ← force la création de la table users
from database import Base

# Créer TOUTES les tables avant l'import
Base.metadata.create_all(bind=engine)

def import_fiches(fichier):
    print("Import:", fichier)
    df = pd.read_excel(fichier, sheet_name="Table APOQUA files", header=1)
    df.columns = df.columns.str.strip().str.lower()
    print("Lignes trouvees:", len(df))

    db = SessionLocal()
    imported = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            ref = str(row.get("reference", "")).strip()
            if not ref or ref == "nan":
                continue

            existing = db.query(Fiche).filter(Fiche.reference == ref).first()
            if existing:
                skipped += 1
                continue

            fiche = Fiche(
                reference=ref,
                designation_fr=str(row.get("apoqua designation (français)", "") or ""),
                designation_en=str(row.get("apoqua designation (english)", "") or ""),
                vehicle_area=str(row.get("vehicle area", "") or ""),
                psa_dec=str(row.get("psa dec", "") or ""),
                lot=str(row.get("lot", "") or ""),
                status=str(row.get("status", "To be updated") or "To be updated"),
                in_poro=str(row.get("in file poro", "NO") or "NO"),
                in_pfr=str(row.get("in pfr for lionel", "NO") or "NO"),
                creation_date=str(row.get("creation date", "") or ""),
                last_modification=str(row.get("last modification", "") or ""),
                created_by=None,  # ← FIX clé étrangère
            )
            db.add(fiche)
            imported += 1

            if imported % 50 == 0:
                db.commit()
                print("Importees:", imported)

        except Exception as e:
            db.rollback()  # ← FIX rollback
            print("Erreur ligne ignoree:", e)

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