#!/usr/bin/env python3
"""P02 v16 = la v15 + l'avis du 15/10 sur la v15 : « il faut faire un angle propre et en profiter pour remplacer celui
du fond pour qu'il ait le même aspect avec le petit muret et la même hauteur ».

Sans IA. Mesures sur la v15 (profils de luminosité) :
  - grillage de gauche au coin (x ≈ 190) : lisse haute ≈ y 300, lisse basse ≈ y 418–422, face du muret y 424–435,
    pied du muret ≈ y 436 ;
  - grillage du fond : lisse haute y 287–295 (plus haute : elle dépassait au-dessus du grillage de gauche), maille
    jusqu'à y 416, lisse basse y 417–423 (déjà à la bonne hauteur), socle rayé y 424–437, pas de muret.
Le grillage du fond prend donc la hauteur et l'aspect de celui de gauche :
  1. sa lisse haute descend de 9 px (y 296–304) ; la bande libérée au-dessus — et la lisse du fond qui dépassait
     au-dessus du grillage de gauche prolongé — est remplie par la colline (bande y 250–286 étirée, sans répétition) ;
  2. maille et lisse basse inchangées ;
  3. le socle rayé devient un muret comme celui de gauche (face claire de la couleur relevée sur le muret de gauche,
     trait foncé à son pied), jusqu'au garage.
Tout le reste est identique à la v15.

Contrôle obligatoire (par rapport à la v15) :
  python3 tools/controle_retouche.py p02-v15-grillage-prolonge.png p02-v16-grillage-fond.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v16-controle.jpg

Usage : python3 tools/p02_v16.py SORTIE
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v15-grillage-prolonge.png"
SORTIE = DOSSIER / "p02-v16-grillage-fond.png"

X_COIN = 158            # début du grillage de gauche prolongé (v15)
X_FOND = 196            # le grillage du fond commence à droite du poteau d'about
X_FIN = 558             # fin du grillage du fond (contre le garage)
COLLINE = (250, 286)    # bande de colline au-dessus de l'ancienne lisse haute
LISSE_HAUTE = (287, 296)
DECALAGE = 9            # la lisse haute descend de 9 px
MURET = (424, 437)      # face du muret (y 424–435) et trait du pied (y 436)


def haut_gauche(x):
    """Lisse haute du grillage de gauche (prolongé), relevée sur la v15."""
    return 227 + 0.39 * x


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    v15 = np.asarray(Image.open(SRC).convert("RGB"))
    out = v15.copy()
    H, W = v15.shape[:2]
    c0, c1 = COLLINE
    # couleur de la face du muret de gauche, relevée dans le prolongement (x 176–188, y 425–434)
    face = np.median(v15[425:435, 176:189].reshape(-1, 3), axis=0)
    trait = np.median(v15[436:438, 176:189].reshape(-1, 3), axis=0)
    for x in range(X_COIN, X_FIN + 1):
        # 1. nouvelle limite haute du grillage : lisse du grillage de gauche avant le coin, sinon nouvelle lisse du fond
        t = int(np.floor(haut_gauche(x))) - 2 if x < X_FOND else LISSE_HAUTE[0] + DECALAGE
        # colline étirée de [c0, c1) vers [c0, t)
        ys = np.arange(c0, t)
        src = c0 + (ys - c0) * (c1 - c0) / max(1, (t - c0))
        s0 = np.floor(src).astype(int); f = (src - s0)[:, None]
        out[c0:t, x] = np.clip(v15[s0, x] * (1 - f) + v15[np.minimum(s0 + 1, c1 - 1), x] * f, 0, 255).astype(np.uint8)
        if x < X_FOND:
            continue
        # 2. lisse haute recopiée 9 px plus bas
        l0, l1 = LISSE_HAUTE
        out[l0 + DECALAGE:l1 + DECALAGE, x] = v15[l0:l1, x]
        # 3. muret : face claire avec la texture douce du socle, trait foncé au pied
        m0, m1 = MURET
        grain = v15[m0:m1 - 1, x].astype(np.float32)
        g = (grain - grain.mean(axis=0)) * 0.15
        out[m0:m1 - 1, x] = np.clip(face + g, 0, 255).astype(np.uint8)
        out[m1 - 1:m1 + 1, x] = trait.astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    ch = np.abs(out.astype(int) - v15.astype(int)).max(axis=2) > 0
    ys, xs = np.nonzero(ch)
    print(f"ok {sortie} | {int(ch.sum())} px changés (x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()})")
    print("zones du contrôle : " + ",".join(map(str, (int(xs.min()) - 1, int(ys.min()) - 1, int(xs.max()) + 2, int(ys.max()) + 2))))


if __name__ == "__main__":
    main()
