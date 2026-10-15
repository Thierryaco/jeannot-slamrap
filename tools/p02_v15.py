#!/usr/bin/env python3
"""P02 v15 = la v13 + le point 1 de l'avis du 15/10 après la v14 (pointé sur la v13 : (164, 439) et (186, 425),
« il faut prolonger aussi le grillage ») : le grillage de gauche et son muret continuent le long du trottoir
redressé jusqu'au grillage du fond.

Sans IA (une retouche IA, p02/work/v15-ia-grillage.png, a repoussé le grillage du fond au loin et allongé la
rue : écartée). Le dernier panneau du grillage (entre les poteaux x 146 et 156, muret compris) est recopié vers
la droite en panneaux de plus en plus étroits (poteaux x 165, 173, 180, 186, poteau d'about x 192, au coin du
grillage du fond), chaque copie suivant les lignes du haut et du pied du grillage (perspective). Tout le reste
est identique à la v13.

Contrôle obligatoire (par rapport à la v13) :
  python3 tools/controle_retouche.py p02-v13-rue-droite.png p02-v15-grillage-prolonge.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v15-controle.jpg

Usage : python3 tools/p02_v15.py SORTIE
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v13-rue-droite.png"
SORTIE = DOSSIER / "p02-v15-grillage-prolonge.png"

SOURCE = (146.0, 156.0)                     # dernier panneau de la v13 (poteau à poteau)
POTEAUX = [156.0, 165.0, 173.0, 180.0, 186.0, 192.0]   # nouveaux panneaux ; 192 = poteau d'about
ABOUT = 2.5                                 # demi-largeur du poteau d'about (copie du poteau x 156)
MARGE_HAUT = 2                              # lignes copiées au-dessus de la lisse haute
MURET = 0.20                                # hauteur du muret / hauteur du grillage


def haut(x):
    return 227 + 0.39 * x


def pied(x):
    return 505 - 0.47 * x


def bas(x):
    return pied(x) + MURET * (pied(x) - haut(x))


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    v13 = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    H, W = v13.shape[:2]
    mapx = np.full((H, W), -1, np.float32)
    mapy = np.full((H, W), -1, np.float32)
    zone = np.zeros((H, W), bool)
    x_fin = int(np.ceil(POTEAUX[-1] + ABOUT))
    for xd in range(int(POTEAUX[0]) + 1, x_fin + 1):
        if xd >= POTEAUX[-1] - ABOUT:                       # poteau d'about : copie du poteau x 156
            xs = SOURCE[1] + (xd - POTEAUX[-1])
        else:
            k = max(i for i in range(len(POTEAUX) - 1) if POTEAUX[i] <= xd)
            u = (xd - POTEAUX[k]) / (POTEAUX[k + 1] - POTEAUX[k])
            xs = SOURCE[0] + u * (SOURCE[1] - SOURCE[0])
        hd, pd = haut(xd), pied(xd)
        hs, ps = haut(xs), pied(xs)
        y0, y1 = int(np.floor(hd - MARGE_HAUT)), int(np.ceil(bas(xd)))
        for y in range(y0, y1 + 1):
            t = (y - hd) / (pd - hd)
            mapx[y, xd] = xs
            mapy[y, xd] = hs + t * (ps - hs)
            zone[y, xd] = True
    copie = cv2.remap(v13, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = v13.copy()
    out[zone] = copie[zone]
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    ys, xs = np.nonzero(zone)
    z = (int(xs.min()) - 1, int(ys.min()) - 1, int(xs.max()) + 2, int(ys.max()) + 2)
    print(f"ok {sortie} | grillage prolongé de x {int(POTEAUX[0])} à {x_fin} ({int(zone.sum())} px)")
    print("zones du contrôle : " + ",".join(map(str, z)))


if __name__ == "__main__":
    main()
