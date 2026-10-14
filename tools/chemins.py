"""Chemins communs aux scripts, valables sous Linux, Windows et macOS.

- ROOT : racine du dépôt, quel que soit le dossier d'où l'on lance un script.
- sortie_par_defaut(nom) : fichier dans `_sorties/` (dossier ignoré par git), utilisé quand un
  script de retouche est lancé sans chemin de sortie (par exemple avec le bouton ▷ de VS Code).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SORTIES = ROOT / "_sorties"


def sortie_par_defaut(nom):
    SORTIES.mkdir(exist_ok=True)
    chemin = SORTIES / nom
    print(f"Sortie : {chemin}", flush=True)
    return str(chemin)
