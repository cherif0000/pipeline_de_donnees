"""Rattrapage : charge les N derniers jours dans l'entrepôt."""
import sys
from datetime import date, timedelta

from src.extract import extract
from src.load import run


def backfill(days=30):
    for n in range(days, 0, -1):
        day = date.today() - timedelta(days=n)
        try:
            extract(day)
            run(day)
        except SystemExit as exc:          # contrôle qualité échoué : on passe au jour suivant
            print(f"{day} ignoré : {exc}")
        except Exception as exc:
            print(f"{day} erreur : {exc}")


if __name__ == "__main__":
    backfill(int(sys.argv[1]) if len(sys.argv) > 1 else 30)