"""P02 v19 — escalier droit (avis #3).

Avis : « escalier depuis (835, 500), tout droit, même largeur, sans dépasser sur le trottoir ».

Base : assets/storyboards/a-valider/p02/p02-v18-maison-droite.png (v18 « façade droite »).
Une seule zone touchée : x 833–909, y 255–518 (l'escalier du mur de pierre).

Réalisation (aucune IA, dessin procédural) :
  - la volée part du point demandé (835, 500), monte DROIT (contremarches horizontales, on monte vers le
    fond), de LARGEUR CONSTANTE (x 835 → 907) ;
  - sa ligne de base suit le pied du mur de pierre (y = 502 → 514) : la volée est posée sur le mur,
    rien ne descend sur le trottoir ;
  - elle arrive sur l'herbe du jardin (ligne de l'herbe : y = 262 → 265) : 15 marches ;
  - deux joues de 6 px (pierre claire) encadrent la volée, avec les traits de coupe ;
  - palette prise dans l'image : contremarche (186,168,140), ombre (170,152,128), marche (203,191,172),
    nez/traits (36,29,23), joue (196,183,163). Arêtes nettes, aucun flou.

Usage : python3 tools/p02_v19.py [SORTIE]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
SRC = RACINE / "assets/storyboards/a-valider/p02/p02-v18-maison-droite.png"
SORTIE = RACINE / "assets/storyboards/a-valider/p02/p02-v19-escalier-droit.png"

# géométrie (px image 1920×1080)
X0, X1 = 835, 907                     # emprise totale (largeur constante)
JOUES = 6                             # largeur des joues latérales
Y_BASE0, PENTE_BASE = 502.0, 0.166    # pied du mur : (835, 502) → (907, 514)
Y_HAUT0, PENTE_HAUT = 262.0, 0.04     # herbe du jardin : (835, 262) → (907, 265)
N_MARCHES = 15
HAUTEUR_MARCHE = 3                    # dessus visible de la marche
EPAIS_NEZ = 2                         # trait du nez de marche

# palette (bins déjà présents dans la référence)
CONTREMARCHE = np.array([186, 168, 140], float)
CONTREM_OMBRE = np.array([170, 152, 128], float)
MARCHE = np.array([203, 191, 172], float)
TRAIT = np.array([36, 29, 23], float)
JOUE = np.array([196, 183, 163], float)
JOUE_OMBRE = np.array([163, 146, 124], float)


def lignes(x):
    """(y_base, y_haut) de la volée pour la colonne x."""
    xf = x - X0
    return Y_BASE0 + PENTE_BASE * xf, Y_HAUT0 + PENTE_HAUT * xf


def melange(c, k):
    return np.clip(c * k, 0, 255).astype(int)


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    img = np.asarray(Image.open(SRC).convert("RGB")).astype(int)
    out = img.copy()

    for x in range(X0, X1 + 1):
        yb, yh = lignes(x)
        yb, yh = int(round(yb)), int(round(yh))
        total = max(yb - yh, 1)
        h = total / N_MARCHES
        joue_g = x < X0 + JOUES
        joue_d = x > X1 - JOUES

        for y in range(yh, yb + 1):
            prof = 0.955 + 0.045 * (yb - y) / total          # léger modèle vertical
            lx = (x - X0) / (X1 - X0)
            prof *= 1.0 - 0.03 * lx                          # lumière venant de la gauche
            pos = (yb - y) % h
            i = int((yb - y) // h)            # n° de la marche (0 = bas)
            hm = 4 if i < 5 else (3 if i < 10 else 2)   # dessus plus fin en montant

            if joue_g or joue_d:
                c = JOUE
                bord_ext = (x <= X0 + 1) or (x >= X1 - 1)
                bord_int = (x == X0 + JOUES - 1) if joue_g else (x == X1 - JOUES + 1)
                if bord_ext or bord_int:
                    c = TRAIT if bord_ext else JOUE_OMBRE
            elif pos < EPAIS_NEZ:
                c = TRAIT
            elif pos >= h - hm:
                c = MARCHE
            else:
                c = CONTREM_OMBRE if pos < h - hm - 2 else CONTREMARCHE

            out[y, x] = melange(c, prof)

        out[yb, x] = TRAIT                    # ligne de base, posée sur le pied du mur
        out[yb - 1, x] = TRAIT
        out[yh, x] = TRAIT                    # arête haute, sous l'herbe

    diff = np.abs(out - img).sum(2) > 0
    ys, xs = np.where(diff)
    Image.fromarray(out.astype("uint8")).save(sortie)
    print(f"{sortie} | {int(diff.sum())} px changés "
          f"(x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()})")


if __name__ == "__main__":
    main()
