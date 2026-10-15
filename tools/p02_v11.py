#!/usr/bin/env python3
"""P02 v11 = la v10 avec la 1re paire du correctif 9 de la liste (trait et textures comme P01, zone par zone — la
passe de style sur toute l'image a été refusée par l'utilisateur le 15/10) :

  a. la colline boisée : des masses de feuillage douces et peintes, peu de traits (comme la végétation de P01) au
     lieu d'un trait noir autour de chaque sapin et d'un remplissage moucheté ; même crête, mêmes verts ;
  b. le haut mur de soutènement : de grandes pierres taillées à joints fins et clairs, ombre peinte douce (comme
     les murs de P01) au lieu d'un gros trait noir autour de chaque pierre ; même forme, même beige.

Méthode : retouches IA sur des recadrages de la v10 (p02/work/v11-ia-colline.png ; v11-ia-mur-2.png — le 1er essai
du mur, v11-ia-mur.png, avait recopié P01 entière : écarté) ; déjà alignées (décalage < 0,25 px) ; collage par coupe
de graphe (p02_v8.coupe_graphe) ; Jeannot, Enji, la 4L, la route et les marches du pied du mur restent ceux de la
v10 au pixel près.

Contrôle obligatoire :
  python3 tools/controle_retouche.py p02-v10-colline-jardin.png p02-v11-style-colline-mur.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v11-controle.jpg

Usage : python3 tools/p02_v11.py [SORTIE] [--coupes IMG]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v8  # noqa: E402  (coupe de graphe, zones sûres du ciel, collage protégé)
import p02_v10  # noqa: E402  (silhouettes de Jeannot et de la 4L)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v10-colline-jardin.png"
SORTIE = DOSSIER / "p02-v11-style-colline-mur.png"

CC = (0, 0, 1067, 600)          # recadrage « colline »
CM = (500, 170, 1300, 620)      # recadrage « mur »


def base_mur(x):
    """Pied du mur (y image) dans sa partie gauche, mesuré sur la v10 : (670, 460) → (900, 505)."""
    return 460 + 0.196 * (np.asarray(x, np.float32) - 670)


def graines_mur(H, W, jeannot, car):
    yy, xx = np.mgrid[0:H, 0:W]
    def boite(x0, y0, x1, y1):
        return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    pied = base_mur(xx)
    ia = (boite(578, 238, 878, H) & (yy < pied - 8)) | boite(1012, 226, 1200, 372)
    j = cv2.dilate(jeannot.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    garde = (j | car | boite(0, 0, 560, H) | boite(0, 0, W, 206) | ((yy > pied + 6) & (xx < 890))
             | boite(885, 425, 1012, H) | boite(1205, 0, W, H) | boite(0, 575, W, H))
    return ia & ~garde, garde


def charger(nom, rc):
    x0, y0, x1, y1 = rc
    return np.asarray(Image.open(TRAVAIL / nom).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v10 = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = v10.shape[:2]
    jeannot, car = p02_v10.silhouettes(v10)
    protege = jeannot | car
    res = v10.astype(np.float32)
    zones, infos, masques = [], [], []
    for nom, fichier, rc in (("colline", "v11-ia-colline.png", CC), ("mur", "v11-ia-mur-2.png", CM)):
        x0, y0, x1, y1 = rc
        ia = charger(fichier, rc)
        cur = np.clip(np.rint(res), 0, 255).astype(np.uint8)
        gi, gg = p02_v8.graines_ciel(H, W) if nom == "colline" else graines_mur(H, W, jeannot, car)
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
