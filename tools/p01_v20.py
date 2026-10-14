"""P01 v20 — même contenu que la v19, reconstruit SANS adoucissement des ajouts (avis : Diego et la caisse
à outils flous au zoom ; le flou venait de l'ancien critère « grain » du contrôle, retiré).
Chaîne : v16 -> (v17 : Diego net) -> (v18 : toit, Estafette nette, tourelle nette) -> (v19 : patine, logo)
-> v20 : zone d'Henri (à venir).
Usage : python3 tools/p01_v20.py OUT.png   (depuis la racine du dépôt)"""
import sys
import numpy as np
from PIL import Image
import p01_v17 as V17
import p01_v18 as V18
import p01_v19 as V19


def build():
    a = np.array(V17.build(flou_diego=0)).astype(float)
    o = np.array(Image.open(V18.V13).convert("RGB")).astype(float)
    a = V18.corrige_toit(a, o)
    a = V18.estafette(a, flou=0)
    a = V18.tourelle(a, flou=0.35, flou_sorciere=0.35)
    a, _ = V19.patine_tourelle(a)
    a = V19.logo_estafette(a)
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


if __name__ == "__main__":
    from chemins import sortie_par_defaut
    build().save(sys.argv[1] if len(sys.argv) > 1 else sortie_par_defaut("v20.png"))
