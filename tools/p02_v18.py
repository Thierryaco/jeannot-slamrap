#!/usr/bin/env python3
"""P02 v18 = la v17 + l'avis (point 2, la maison du fond) : « elle doit commencer à 950 et finir à 1337 // en
haut » et « surtout la façade doit être droite comme la v14 ».

Dans la v17, la maison du fond commence par un pignon dont le pan de toit descend en biais à ~45° : son arête
gauche part de (985, 0) et descend jusqu'à (962, 85), puis le mur a une arête verticale à x 977. L'avis demande
de supprimer ce pan de toit en biais et de finir par un angle droit : le mur est prolongé vers la gauche (à la
place du pan et derrière le garde-corps de la terrasse) jusqu'à une arête **verticale à x = 950** — en haut de
l'image la maison va donc de 950 à 1337 (la tuile), sans aucun biais.

Ce qui ne change pas : les deux fenêtres de côté du pignon (petite 1020-1042, grande 1007-1057), le garde-corps
de la terrasse (il passe devant le mur), le toit de tuiles, la porte, l'escalier, tout le reste de la v17.

Méthode (sans IA) : la bande de mur crème propre (x 1060-1090, y 20-144) est recopiée en tuile horizontale dans
la zone (x 950-1001, y 0-144), avec le ton recalé sur le mur juste à droite de la zone (x 1002-1005, y 55-80)
pour que la jointure ne se voie pas ; les 20 premières lignes sont le miroir du haut de la bande (mur plat) ; on
redessine l'arête verticale gauche à x 949-950 au ton de contour de la maison (40, 29, 15).

Usage : python3 tools/p02_v18.py [SORTIE]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v17-grillage-fond.png"
SORTIE = DOSSIER / "p02-v18-maison-droite.png"

ZONE = (950, 1058, 0, 145)      # x0, x1, y0, y1 (exclusifs) : le pignon biaisé à remplacer par le mur
BANDE = (1060, 1090, 36, 144)   # bande de mur crème propre (sous les tuiles), recopiée en tuile horizontale
TON = (1002, 1006, 55, 80)      # mur juste à droite de la zone : sert à recaler le ton
ARETE = (949, 951, 0, 145)      # nouvelle arête gauche, verticale (angle droit)


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    v17 = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    out = v17.copy()
    x0, x1, y0, y1 = ZONE
    bx0, bx1, by0, by1 = BANDE
    bande = v17[by0:by1, bx0:bx1]                               # 108 lignes de mur plat (y 36-143)
    med = np.median(bande, axis=1)                              # une couleur de mur par ligne (mur plat, sans motif)
    manque = (y1 - y0) - med.shape[0]
    bloc = np.vstack([med[:manque][::-1], med])                 # 145 lignes : y 0 -> 144, sans raccord visible
    tx0, tx1, ty0, ty1 = TON                                    # ton du mur juste à droite de la zone
    delta = (np.median(v17[ty0:ty1, tx0:tx1].reshape(-1, 3), axis=0) - bloc[ty0 - y0:ty1 - y0].mean(0))
    rng = np.random.default_rng(7)
    grain = rng.normal(0.0, 1.2, (bloc.shape[0], x1 - x0, 1))  # grain léger, comme le muret de la v17
    bloc = np.clip(bloc[:, None, :] + delta + grain, 0, 255)
    # limites mesurées : on remplace du bord gauche jusqu'au bord de chaque fenêtre de côté
    for y in range(y0, y1):
        lim = 1017 if y < 82 else 1006
        out[y, x0:lim] = bloc[y - y0, :lim - x0]
    # arête verticale gauche (angle droit), au ton de contour de la maison
    ax0, ax1, ay0, ay1 = ARETE
    out[ay0:ay1, ax0] = (79, 75, 66)      # liseré clair extérieur, comme sur l'arête existante
    out[ay0:ay1, ax0 + 1] = (40, 29, 15)  # trait de contour
    Image.fromarray(out.astype(np.uint8)).save(sortie, optimize=True)
    ch = np.abs(out - v17).max(axis=2) > 0
    ys, xs = np.nonzero(ch)
    print(f"ok {sortie} | {int(ch.sum())} px changés (x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()})")
    print("zones du contrôle : " + ",".join(map(str, (int(xs.min()) - 1, int(ys.min()) - 1,
                                                      int(xs.max()) + 2, int(ys.max()) + 2))))


if __name__ == "__main__":
    main()
