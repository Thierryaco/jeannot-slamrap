#!/usr/bin/env python3
"""P02 v14 = la v13 avec les points C et D de l'avis du 15/10 sur la v12 (faits ensemble : la porte de la maison
doit être dans l'axe de l'escalier, et l'escalier monter jusqu'à cette porte) :

  C. la maison du fond devient une seule maison large, qui va jusqu'au mur crème de Jeannot (presque collée) ; le
     bout de bâtiment pointé à droite de l'escalier (x 1307–1506, y 0–260) est supprimé ; porte d'entrée en haut
     de l'escalier, fenêtres de part et d'autre (retouche p02/work/v14-ia-maison-escalier.png, faite d'après le
     croquis v14-croquis.png ; recalée sur la v13 par ECC) ;
  D. (étape suivante, v15) l'escalier part du pied du mur à (835, 500), même largeur, entaillé dans le mur, et
     monte tout droit jusqu'à la porte (x 1144–1194, bas y ≈ 209). Deux retouches IA (v14-ia-maison-escalier.png,
     v14-ia-escalier.png sur l'entrée peinte v14-entree-escalier-peint.png) ont gardé l'ancien escalier : à
     dessiner sans IA.

Jeannot, Enji et la 4L restent ceux de la v13 au pixel près.

Contrôle obligatoire (par rapport à la v13) :
  python3 tools/controle_retouche.py p02-v13-rue-droite.png p02-v14-maison-escalier.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v14-controle.jpg

Usage : python3 tools/p02_v14.py SORTIE [--maison-seule] [--coupes IMG]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v8  # noqa: E402  (coupe de graphe, collage protégé)
import p02_v10  # noqa: E402  (silhouettes de Jeannot et de la 4L, recalage ECC)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v13-rue-droite.png"
V9 = DOSSIER / "p02-v9-lumiere.png"
SORTIE = DOSSIER / "p02-v14-maison-escalier.png"   # (point C seul)

CM = (600, 0, 1520, 518)       # recadrage « maison + escalier »


def boites(H, W):
    yy, xx = np.mgrid[0:H, 0:W]
    def boite(x0, y0, x1, y1):
        return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    return xx, yy, boite


def graines_maison(H, W, jeannot, car):
    """C. façade, toit, bas de la porte et pelouse à la place du bâtiment supprimé (côté IA) ; forêt, garage,
    mur, escalier actuel sous y 205 (refait à l'étape D), Jeannot, 4L, mur de Jeannot (côté v13)."""
    xx, yy, boite = boites(H, W)
    ia = boite(960, 0, 1484, 200) | boite(1300, 196, 1484, 262)
    garde = (xx < 945) | (yy > 280) | jeannot | car | (xx >= 1492) | boite(1040, 205, 1215, 300)
    return ia & ~garde, garde


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--") and not a.endswith(".jpg")]
    sortie = Path(args[0]) if args else SORTIE
    v13 = np.asarray(Image.open(SRC).convert("RGB"))
    v9 = np.asarray(Image.open(V9).convert("RGB"))
    H, W = v13.shape[:2]
    jeannot, car = p02_v10.silhouettes(v9)
    protege = jeannot | car
    x0, y0, x1, y1 = CM
    ia = np.asarray(Image.open(TRAVAIL / "v14-ia-maison-escalier.png").convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))
    ia, w, cc = p02_v10.recaler(v13[y0:y1, x0:x1], ia, [(0, 150, 300, 518), (380, 300, 560, 518)])
    gi, gg = graines_maison(H, W, jeannot, car)
    lab = p02_v8.coupe_graphe(v13[y0:y1, x0:x1], ia, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
    m1 = np.zeros((H, W), bool); m1[y0:y1, x0:x1] = lab
    full = v13.copy(); full[y0:y1, x0:x1] = ia
    res, a1 = p02_v8.coller(v13.astype(np.float32), full, m1, protege)
    alphas, masques = [a1], [m1]
    infos = [f"maison {int(m1.sum())} px (recalage cc {cc:.4f}, échelle {w[0, 0]:.4f})"]
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    zones = []
    for a in alphas:
        ys, xs = np.nonzero(a > 0)
        zones.append((max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1), min(W, int(xs.max()) + 2), min(H, int(ys.max()) + 2)))
    print(f"ok {sortie} | " + " · ".join(infos))
    print("zones du contrôle : " + ";".join(",".join(map(str, z)) for z in zones))
    if "--coupes" in sys.argv:
        vis = out.copy()
        for m, c in zip(masques, ([255, 0, 255], [0, 255, 255])):
            e = m ^ cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            vis[e] = c
        Image.fromarray(vis).save(sys.argv[sys.argv.index("--coupes") + 1])


if __name__ == "__main__":
    main()
