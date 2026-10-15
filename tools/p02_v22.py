#!/usr/bin/env python3
"""P02 v22 = la v14, avec l'extrémité ouest de la maison déplacée (avis du 15/10 au soir, après la v21).

Avis sur la v21 : « j'ai dit une maison du style de la v13 mais pour le reste j'attends toujours une maison qui
s'arrête avant la terrasse et commence attenante à la façade ouest de la maison de Jeannot mais toujours en
retrait. la porte d'entrée est côté sud donc face à la rue et les escaliers coupent toujours le jardin en 2 de
la rue à la maison. »

Conséquences :
  - la maison de la **v13** ne suffit pas (elle est trop petite) : c'est la **v14** qui a la bonne étendue — elle
    part de la façade ouest de la maison de Jeannot (x ≈ 1470) et sa porte d'entrée est face à la rue, au sud,
    avec les escaliers qui coupent le jardin en deux depuis la rue (tout cela ne change pas ici) ;
  - son seul défaut était son **extrémité ouest** : le pignon et sa rive de toit dépassaient devant la terrasse
    (mur à x 975, rive jusqu'à x 955). L'avis de 15:47 disait déjà « la maison doit être droite… elle ne va pas
    devant la terrasse, elle s'arrête avant ».
  - ici, **l'IA déplace cette extrémité** (work/v22-ia-ouest-decale.png, recadrage x 840-1200 / y 0-260) : le
    pignon, sa rive et l'égout commencent maintenant à **x ≈ 1007**, juste après le dernier poteau de la grille de
    la terrasse, et la forêt remplit l'espace libéré à gauche. Le reste de la maison (façade, fenêtres, porte),
    le toit, le jardin, les escaliers, le mur de pierre et le trottoir sont **recopiés au pixel de la v14**.

Le collage ne touche que l'extrémité ouest (différence + fondu de 5 px), le ton est recalé ligne par ligne sur la
v14, la grille de la terrasse et le jardin restent ceux de la v14, Jeannot et la 4L sont protégés.

Contrôle obligatoire (par rapport à la v14) :
  python3 tools/controle_retouche.py assets/storyboards/a-valider/p02/p02-v14-maison-escalier.png \\
      assets/storyboards/a-valider/p02/p02-v22-maison-ouest-decalee.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie assets/storyboards/a-valider/p02/p02-v22-controle.jpg

Usage : python3 tools/p02_v22.py [SORTIE] [--essai]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v10  # noqa: E402  (silhouettes de Jeannot et de la 4L)

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v14-maison-escalier.png"
SORTIE = DOSSIER / "p02-v22-maison-ouest-decalee.png"

OUEST = dict(fichier="v22-ia-ouest-decale.png", recadrage=(840, 0, 1200, 260), seuil=14,
             zone=(952, 0, 1216, 212),
             # témoins de ton : la forêt (à gauche) et la façade (à droite), communs aux deux images
             temoins=((852, 886), (1148, 1192)),
             # bornes du collage : on ne touche ni la grille de la terrasse, ni le jardin, ni le bas du mur
             gauche_haute=958,        # à partir de cette colonne au-dessus de la grille
             gauche_basse=996,        # et à partir de celle-ci en dessous (la grille de la terrasse est à x < 990)
             y_bas=204)               # on s'arrête au-dessus de la pelouse du jardin

FEATHER = 5
ZONES = [f"{OUEST['zone'][0]},{OUEST['zone'][1]},{OUEST['zone'][2]},{OUEST['zone'][3]}"]


def boite(x0, y0, x1, y1, H, W):
    m = np.zeros((H, W), bool)
    m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    return m


def retouche_ia(src, p, protege, H, W):
    x0, y0, x1, y1 = p["recadrage"]
    ia = np.asarray(Image.open(TRAVAIL / p["fichier"]).convert("RGB")
                    .resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
    ref = src[y0:y1, x0:x1]
    for i in range(y1 - y0):                       # ton de la retouche recalé ligne par ligne sur la v14
        refi, iai = ref[i], ia[i]
        g = np.zeros(refi.shape[0], bool)
        for a, b in p["temoins"]:
            g[a - x0:b - x0] = True
        g &= np.abs(refi - iai).max(1) < 60        # témoins identiques dans les deux images
        if g.sum() > 10:
            ia[i] = np.clip(iai + np.median(refi[g] - iai[g], axis=0), 0, 255)
    plein = np.zeros((H, W, 3), np.float32)
    plein[y0:y1, x0:x1] = ia
    d = np.abs(ia - ref).max(2)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = d > p["seuil"]
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    zx0, zy0, zx1, zy1 = p["zone"]
    m &= boite(zx0, zy0, zx1, zy1, H, W)
    m[p["y_bas"]:, :] = False                      # on s'arrête au-dessus de la pelouse du jardin
    m &= ~boite(0, 130, p["gauche_basse"], H, H, W)   # la grille de la terrasse (et à gauche) reste celle de la v14
    m &= ~boite(0, 0, p["gauche_haute"], 130, H, W)
    m &= ~protege
    return plein, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie", nargs="?", default=str(SORTIE))
    ap.add_argument("--essai", action="store_true", help="écrit une planche de relecture dans /tmp/p02")
    a = ap.parse_args()

    src = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    H, W, _ = src.shape
    jeannot, car = p02_v10.silhouettes(src.astype(np.uint8))
    protege = cv2.dilate((jeannot | car).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) | car

    plein, m = retouche_ia(src, OUEST, protege, H, W)
    alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), FEATHER / 2)[:, :, None]
    alpha[m] = 1.0
    out = np.clip(src * (1 - alpha) + plein * alpha, 0, 255).astype(np.uint8)
    print(f"  extrémité ouest déplacée : {int(m.sum())} px")
    Image.fromarray(out).save(a.sortie)
    print(f"écrit : {a.sortie}")
    print("zones du contrôle : " + ";".join(ZONES))

    if a.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        zx0, zy0, zx1, zy1 = OUEST["zone"]
        p0 = (max(zx0 - 40, 0), max(zy0 - 5, 0))
        p1 = (min(zx1 + 40, W), min(zy1 + 60, H))
        Image.fromarray(out[p0[1]:p1[1], p0[0]:p1[0]]).resize(
            ((p1[0] - p0[0]) * 3, (p1[1] - p0[1]) * 3), Image.NEAREST).save("/tmp/p02/v22-ouest.png")
        print("planche : /tmp/p02/v22-ouest.png")


if __name__ == "__main__":
    main()
