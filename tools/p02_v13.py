#!/usr/bin/env python3
"""P02 v13 = retour à la v10 (avis du 15/10 sur la v12 : « tous les changements après la v10 ne vont pas sauf le
grillage de gauche ; la forêt et le mur étaient très bien sur la v10 ») + les points de cet avis, un par un :

  A. base = v10 + le grillage de gauche de la v12 (mailles nettes, retouche p02/work/v12-ia-grillage.png, recollée
     directement sur la v10 par coupe de graphe — pas de reste de la colline de la v11 au bord du grillage) ;
  B. la rue « tourne à gauche » au fond (pointé : (226, 460), (164, 442)) : la bordure et le trottoir de gauche
     filent tout droit jusqu'au grillage du fond (retouche p02/work/v13-ia-rue.png sur le recadrage x 0–480,
     y 360–630 ×2,67 de la base A).

Jeannot, Enji et la 4L restent ceux de la v10 au pixel près.

Contrôle obligatoire (par rapport à la v10) :
  python3 tools/controle_retouche.py p02-v10-colline-jardin.png p02-v13-rue-droite.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v13-controle.jpg

Usage : python3 tools/p02_v13.py [SORTIE] [--base-seule] [--coupes IMG]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v8  # noqa: E402  (coupe de graphe, collage protégé)
import p02_v10  # noqa: E402  (silhouettes de Jeannot et de la 4L)
import p02_v12  # noqa: E402  (zones sûres du grillage de gauche)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v10-colline-jardin.png"
V9 = DOSSIER / "p02-v9-lumiere.png"
SORTIE = DOSSIER / "p02-v13-rue-droite.png"

CR = (0, 360, 480, 630)        # recadrage « fond de la rue, à gauche »


def charger(nom, rc):
    x0, y0, x1, y1 = rc
    return np.asarray(Image.open(TRAVAIL / nom).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))


def base_a(v10, protege, car):
    """A. v10 + grillage de gauche de la v12 (coupe de graphe entre la v10 et la retouche du grillage)."""
    H, W = v10.shape[:2]
    (gi, gg), _ = p02_v12.graines(H, W, car)
    x0, y0, x1, y1 = p02_v12.CG
    ia = charger("v12-ia-grillage.png", p02_v12.CG)
    lab = p02_v8.coupe_graphe(v10[y0:y1, x0:x1], ia, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
    m = np.zeros((H, W), bool); m[y0:y1, x0:x1] = lab
    full = v10.copy(); full[y0:y1, x0:x1] = ia
    res, a = p02_v8.coller(v10.astype(np.float32), full, m, protege)
    return res, a, m


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v10 = np.asarray(Image.open(SRC).convert("RGB"))
    v9 = np.asarray(Image.open(V9).convert("RGB"))
    H, W = v10.shape[:2]
    jeannot, car = p02_v10.silhouettes(v9)
    protege = jeannot | car
    res, a1, m1 = base_a(v10, protege, car)
    zones, masques, infos = [], [m1], [f"grillage {int(m1.sum())} px"]
    alphas = [a1]
    if "--base-seule" not in sys.argv:
        pass   # B. rue droite : ajouté quand la retouche v13-ia-rue.png existe
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
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
