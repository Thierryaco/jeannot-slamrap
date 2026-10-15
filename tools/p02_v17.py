#!/usr/bin/env python3
"""P02 v17 = la v16 avec le muret *refait proprement*.

La v16 avait la bonne géométrie (lisse haute du grillage du fond à la même hauteur que celui de gauche, colline
au-dessus), mais son muret était raté : un aplat gris, translucide, qui laissait voir la bordure du trottoir et se
terminait par un redan. On garde donc la v16 telle quelle et on ne refait que le muret.

Le muret du fond est la copie *opaque* du muret de gauche :
  - on relève le profil vertical exact du muret de gauche (v15, colonnes 182–195, lignes 424–441 : face claire
    (126,123,115) qui s'assombrit doucement jusqu'à (121,118,112)) et on le recopie pour chaque colonne du fond ;
  - on y ajoute une texture propre (basse fréquence ±2,5 + grain fin ±1,1), jamais le contenu du dessous : la
    bordure du trottoir ne peut plus apparaître au travers ;
  - face y 424 → 441 (18 px, exactement la hauteur du muret de gauche au coin), puis un trait de pied sombre
    (2 px) pris sur le ton du bas de la face, puis le contenu existant (pavement, route) reprend ;
  - le muret court du poteau d'angle (x 196) jusqu'au pied du garage (x 564) et se ferme par un trait vertical
    de 1 px au ton sombre relevé sur place (arête du garage) : fin propre, sans redan.

Usage : python3 tools/p02_v17.py SORTIE
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v15-grillage-prolonge.png"
SORTIE = DOSSIER / "p02-v17-grillage-fond.png"

# --- étapes 1 et 2 : identiques à la v16 (hauteur du grillage du fond) ---
X_COIN = 158            # début du grillage de gauche prolongé (v15)
X_FOND = 196            # début du grillage du fond (à droite du poteau d'angle)
X_LISSE = 558           # fin de la zone où l'on remonte la lisse / la colline
COLLINE = (250, 286)    # bande de colline au-dessus de l'ancienne lisse haute
LISSE_HAUTE = (287, 296)
DECALAGE = 9            # la lisse haute du fond descend de 9 px

# --- étape 3 : le muret refait ---
REF = (182, 196)        # colonnes du muret de gauche servant de référence
Y_FACE = 424            # première ligne de la face du muret
HAUTEUR = 18            # lignes de face (424 → 441) = hauteur du muret de gauche au coin
FIN_MURET = 564         # dernier pixel du muret (pied du garage)


def haut_gauche(x):
    """Lisse haute du grillage de gauche (prolongé), relevée sur la v15."""
    return 227 + 0.39 * x


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    v15 = np.asarray(Image.open(SRC).convert("RGB"))
    out = v15.copy()
    c0, c1 = COLLINE

    # 1 et 2. grillage du fond à la hauteur de celui de gauche (comme la v16)
    for x in range(X_COIN, X_LISSE + 1):
        t = int(np.floor(haut_gauche(x))) - 2 if x < X_FOND else LISSE_HAUTE[0] + DECALAGE
        ys = np.arange(c0, t)
        src = c0 + (ys - c0) * (c1 - c0) / max(1, (t - c0))
        s0 = np.floor(src).astype(int)
        f = (src - s0)[:, None]
        out[c0:t, x] = np.clip(v15[s0, x] * (1 - f) + v15[np.minimum(s0 + 1, c1 - 1), x] * f,
                               0, 255).astype(np.uint8)
        if x < X_FOND:
            continue
        l0, l1 = LISSE_HAUTE
        out[l0 + DECALAGE:l1 + DECALAGE, x] = v15[l0:l1, x]

    # 3. muret opaque, copie du muret de gauche
    y0 = Y_FACE
    y1 = y0 + HAUTEUR                                   # exclu : dernière ligne de face = 441
    r0, r1 = REF
    profil = np.median(v15[y0:y1, r0:r1].astype(np.float32), axis=1)   # (hauteur, 3)
    n = FIN_MURET - X_FOND + 1
    rng = np.random.default_rng(7)
    basse = gaussian_filter1d(rng.normal(0.0, 1.0, size=n), sigma=18.0)
    basse = basse / max(1e-6, np.abs(basse).max()) * 2.5
    grain = rng.normal(0.0, 1.1, size=(n, 1))
    texture = (basse[:, None] + grain)[:, :, None] * np.array([1.0, 0.97, 0.9])
    pied = np.clip(profil[-1] * 0.62, 0, 255).astype(np.uint8)
    for x in range(X_FOND, FIN_MURET + 1):
        out[y0:y1, x] = np.clip(profil + texture[x - X_FOND], 0, 255).astype(np.uint8)
        out[y1:y1 + 2, x] = pied
    # fermeture : trait vertical au ton sombre relevé sur l'arête du garage
    fermeture = np.median(v15[425:430, 566:572].reshape(-1, 3), axis=0).astype(np.uint8)
    out[y0 - 1:y1 + 2, FIN_MURET + 1] = fermeture
    Image.fromarray(out).save(sortie, optimize=True)

    ch = np.abs(out.astype(int) - v15.astype(int)).max(axis=2) > 0
    ys, xs = np.nonzero(ch)
    print(f"ok {sortie} | face y {y0}–{y1 - 1} ({HAUTEUR} px) | muret x {X_FOND}–{FIN_MURET} | "
          f"{int(ch.sum())} px changés (x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()})")
    print("zones du contrôle : " + ",".join(map(str, (int(xs.min()) - 1, int(ys.min()) - 1,
                                                       int(xs.max()) + 2, int(ys.max()) + 2))))


if __name__ == "__main__":
    main()
