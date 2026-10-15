#!/usr/bin/env python3
"""P02 v23 = la v22 avec la maison redessinée VUE DE FACE par l'IA (avis du 15/10 au soir, après la v22).

Avis : « la maison et une partie de l'escalier reste encore à 45° c'est pas ce que j'ai dit pourtant… tu fais en
sorte qu'elle respecte toujours sa limite par rapport à la terrasse ».

Ce qui n'allait pas dans la v22 : la partie ouest de la façade (entre le pignon et la porte, x 1000-1155) était
dessinée comme un **pan de mur en biais** — la maison semblait pivotée à 45°. Ici l'IA redessine la maison **vue
bien de face** (`work/v23-ia-maison-face.png`, recadrage x 900-1560 / y 0-260) :
  - la façade (mur crème, porte, fenêtres) est **parallèle au bas de l'image sur toute sa longueur** ;
  - l'extrémité ouest est un **angle droit vertical à x ≈ 995** avec un mince retour de pignon et sa rive presque
    verticale : **la limite par rapport à la terrasse est conservée** (la grille finit à x 985) ;
  - même hauteur, même avant-toit horizontal, même toit de tuiles, même gouttière ; la **porte reste au même
    endroit** (x 1150-1200, face à la rue) ; l'extrémité est reste contre la maison de Jeannot.

Le collage ne touche que la maison (différence + fondu de 5 px, borné à x 990-1490 / y ≤ 205) : le jardin, les
escaliers, la grille de la terrasse, la forêt, le mur de pierre et le mur du voisin restent ceux de la v22. Le ton
est recalé ligne par ligne sur la v22.

Les escaliers (encore à 45° eux aussi) sont traités dans une version suivante.

Contrôle obligatoire (par rapport à la v22) :
  python3 tools/controle_retouche.py assets/storyboards/a-valider/p02/p02-v22-maison-ouest-decalee.png \\
      assets/storyboards/a-valider/p02/p02-v23-maison-de-face.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie assets/storyboards/a-valider/p02/p02-v23-controle.jpg

Usage : python3 tools/p02_v23.py [SORTIE] [--essai]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v10  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v22-maison-ouest-decalee.png"
SORTIE = DOSSIER / "p02-v23-maison-de-face.png"

FACE = dict(fichier="v23-ia-maison-face.png", recadrage=(900, 0, 1560, 260), seuil=14,
            zone=(988, 0, 1492, 206),
            temoins=((905, 930), (1528, 1554)),      # la forêt à gauche, le mur du voisin à droite
            limite=(990, 0, 1490, 205))

FEATHER = 5
ZONES = [f"{FACE['zone'][0]},{FACE['zone'][1]},{FACE['zone'][2]},{FACE['zone'][3]}"]


def boite(x0, y0, x1, y1, H, W):
    m = np.zeros((H, W), bool)
    m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie", nargs="?", default=str(SORTIE))
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()

    src = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    H, W, _ = src.shape
    p = FACE
    x0, y0, x1, y1 = p["recadrage"]
    ia = np.asarray(Image.open(TRAVAIL / p["fichier"]).convert("RGB")
                    .resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
    ref = src[y0:y1, x0:x1]
    for i in range(y1 - y0):                          # ton recalé ligne par ligne sur la v22
        refi, iai = ref[i], ia[i]
        g = np.zeros(refi.shape[0], bool)
        for aa, bb in p["temoins"]:
            g[aa - x0:bb - x0] = True
        g &= np.abs(refi - iai).max(1) < 60
        if g.sum() > 10:
            ia[i] = np.clip(iai + np.median(refi[g] - iai[g], axis=0), 0, 255)
    plein = src.copy()                     # hors du recadrage, « plein » = l'image : le fondu ne peut rien tacher
    plein[y0:y1, x0:x1] = ia
    d = np.abs(ia - ref).max(2)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = d > p["seuil"]
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m &= boite(*p["limite"], H, W)

    jeannot, car = p02_v10.silhouettes(src.astype(np.uint8))
    protege = cv2.dilate((jeannot | car).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) | car
    m &= ~protege

    alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), FEATHER / 2)[:, :, None]
    alpha[m] = 1.0
    out = np.clip(src * (1 - alpha) + plein * alpha, 0, 255).astype(np.uint8)
    print(f"  maison redessinée de face : {int(m.sum())} px")
    Image.fromarray(out).save(a.sortie)
    print(f"écrit : {a.sortie}")
    print("zones du contrôle : " + ";".join(ZONES))

    if a.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        Image.fromarray(out[0:240, 940:1540]).resize((600 * 3, 240 * 3), Image.NEAREST).save("/tmp/p02/v23-maison.png")
        print("planche : /tmp/p02/v23-maison.png")


if __name__ == "__main__":
    main()
