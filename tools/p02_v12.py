#!/usr/bin/env python3
"""P02 v12 = la v11 avec la 2e paire du correctif 9 de la liste (trait et textures comme P01, zone par zone) :

  a. le grillage de gauche (sur le muret du trottoir de gauche) : ses panneaux étaient remplis de gribouillis
     (hachures irrégulières) ; ils prennent les mêmes mailles en losange, nettes et régulières, que le grillage
     du fond ;
  b. le mur de jardin de Jeannot (à droite, derrière la 4L) : aplat crème vide → comme le même mur dans P01 :
     crépi crème, joints verticaux fins et foncés entre de larges panneaux, chaperon le long du haut.

Méthode : retouches IA sur des recadrages de la v11 (p02/work/v12-ia-grillage.png, x 0–569, y 150–470 ×2,25 ;
v12-ia-mur-jeannot.png, x 1400–1920, y 0–520 ×2, modèle : ref-p01-mur-jeannot.png, mur de P01 sans personnage) ;
collage par coupe de graphe (p02_v8.coupe_graphe) ; Jeannot, Enji et la 4L restent ceux de la v11 au pixel près.

Contrôle obligatoire :
  python3 tools/controle_retouche.py p02-v11-style-colline-mur.png p02-v12-grillage-mur.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v12-controle.jpg

Usage : python3 tools/p02_v12.py [SORTIE] [--coupes IMG]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v8  # noqa: E402  (coupe de graphe, collage protégé)
import p02_v10  # noqa: E402  (silhouettes de Jeannot et de la 4L)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v11-style-colline-mur.png"
V9 = DOSSIER / "p02-v9-lumiere.png"     # silhouettes calculées sur la v9 (Jeannot et la 4L inchangés depuis la v6)
SORTIE = DOSSIER / "p02-v12-grillage-mur.png"

CG = (0, 150, 569, 470)        # recadrage « grillage »
CW = (1400, 0, 1920, 520)      # recadrage « mur de Jeannot »


def haut_grillage(x):
    """Lisse haute du grillage de gauche (relevée sur la v11) : (0, 227) → (150, 285)."""
    return 227 + 0.39 * x


def pied_grillage(x):
    """Pied du grillage de gauche sur le muret : (0, 505) → (150, 435)."""
    return 505 - 0.47 * x


def chaperon(x):
    """Haut du mur de Jeannot (chaperon) : (1500, 115) → (1880, 15)."""
    return 115 - 0.263 * (x - 1500)


def graines(H, W, car):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # grillage de gauche
    hg, pg = haut_grillage(xx), pied_grillage(xx)
    ia_g = (xx >= 4) & (xx <= 150) & (yy > hg + 6) & (yy < pg - 6)
    garde_g = (yy < hg - 8) | (xx > 162) | (yy > pg + 8)
    # mur de Jeannot (chaperon compris)
    ch = chaperon(xx)
    ia_w = (xx >= 1508) & (xx <= 1915) & (yy > ch - 2) & (yy < 470) & ~car
    garde_w = (yy < ch - 16) | (xx < 1494) | car
    return (ia_g, garde_g), (ia_w, garde_w)


def charger(nom, rc):
    x0, y0, x1, y1 = rc
    return np.asarray(Image.open(TRAVAIL / nom).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v11 = np.asarray(Image.open(SRC).convert("RGB"))
    v9 = np.asarray(Image.open(V9).convert("RGB"))
    H, W = v11.shape[:2]
    jeannot, car = p02_v10.silhouettes(v9)
    protege = jeannot | car
    (gi_g, gg_g), (gi_w, gg_w) = graines(H, W, car)
    res = v11.astype(np.float32)
    zones, infos, masques = [], [], []
    for nom, fichier, rc, gi, gg in (("grillage", "v12-ia-grillage.png", CG, gi_g, gg_g),
                                     ("mur", "v12-ia-mur-jeannot.png", CW, gi_w, gg_w)):
        x0, y0, x1, y1 = rc
        ia = charger(fichier, rc)
        cur = np.clip(np.rint(res), 0, 255).astype(np.uint8)
        lab = p02_v8.coupe_graphe(cur[y0:y1, x0:x1], ia, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
        m = np.zeros((H, W), bool); m[y0:y1, x0:x1] = lab
        full = cur.copy(); full[y0:y1, x0:x1] = ia
        res, a = p02_v8.coller(res, full, m, protege)
        ys, xs = np.nonzero(a > 0)
        zones.append((max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1), min(W, int(xs.max()) + 2), min(H, int(ys.max()) + 2)))
        infos.append(f"{nom} {int(m.sum())} px")
        masques.append(m)
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
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
