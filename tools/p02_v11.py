#!/usr/bin/env python3
"""P02 v11 = la v10 avec la 1re paire du correctif 9 de la liste (trait et textures comme P01, zone par zone — la
passe de style sur toute l'image a été refusée par l'utilisateur le 15/10) :

  a. la colline boisée : quelques grandes masses de feuillage en aplats doux, chacune cernée d'un contour net et
     foncé de largeur régulière (comme les arbres et buissons de P01), au lieu d'un trait noir autour de chaque
     sapin et d'un remplissage moucheté ; même crête ; verts ramenés à ceux de la v10 (lumière de plein jour) ;
  b. le haut mur de soutènement (ses deux parties et les marches du pied) : de grandes pierres régulières en aplats
     beiges doux, joints fins nets et foncés, contour net du mur (trait net et régulier de P01) au lieu d'un gros
     trait noir autour de chaque petite pierre irrégulière.

Méthode : retouches IA sur des recadrages de la v10 (p02/work/v11-ia-colline-2.png, v11-ia-mur-4.png) ; déjà
alignées ; collage par coupe de graphe (p02_v8.coupe_graphe) ; Jeannot, Enji, la 4L, la route et l'escalier qui
monte derrière Jeannot restent ceux de la v10 au pixel près.
Essais écartés : v11-ia-mur.png (avait recopié P01 entière) ; v11-ia-mur-2.png (ne couvrait pas la partie droite) ;
essai 1 = v11-ia-colline.png + v11-ia-mur-3.png (masses molles, joints clairs) : contrôle À REFAIRE sur la netteté
(×0,79 / ×0,65) — le style de P01 a des aplats doux mais des contours NETS ; rangé dans work/v11-essai1-*.

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
V9 = DOSSIER / "p02-v9-lumiere.png"   # silhouette de la 4L : calculée sur la v9 (mur crème au-dessus du toit) ; dans
                                      # la v10 le mur de pierre touche le toit et GrabCut l'englobait dans la 4L
SORTIE = DOSSIER / "p02-v11-style-colline-mur.png"

CC = (0, 0, 1067, 600)          # recadrage « colline »
CM = (560, 150, 1480, 668)      # recadrage « mur » (les deux parties du mur et les marches du pied)


# pied de la partie gauche du mur (trait foncé entre le mur et le trottoir), relevé sur un agrandissement ×4 de la v10
# (les dernières pierres, délavées et gris-bleu, sont juste au-dessus)
PIED_X = [660, 675, 700, 725, 750, 775, 800, 825, 850, 875, 900, 905]
PIED_Y = [456, 458, 462, 467, 473, 480, 487, 492, 497, 503, 508, 510]


def base_mur(x):
    """Pied de la partie gauche du mur (y image), interpolé entre les points mesurés."""
    return np.interp(np.asarray(x, np.float32), PIED_X, PIED_Y).astype(np.float32)


def graines_mur(H, W, jeannot, car):
    yy, xx = np.mgrid[0:H, 0:W]
    def boite(x0, y0, x1, y1):
        return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    pied = base_mur(xx)
    # partie gauche (du garage au pied de l'escalier), marches du pied, partie droite (au-dessus de la 4L)
    # jusqu'à 2 px sous le pied : la frontière passe dans le trottoir, identique dans la retouche et la v10
    # la partie gauche du mur continue derrière la tête et la main de Jeannot jusqu'à l'escalier (x ≈ 1060)
    ia = ((boite(676, 292, 905, H) & (yy < pied + 3)) | boite(905, 292, 1052, 420) | boite(905, 432, 1052, 568)
          | boite(1212, 282, 1468, 400)      # partie droite jusqu'au toit de la 4L (protégée) et au bout du mur
          | boite(1165, 330, 1212, 400))     # pied du pilier de gauche de la partie droite
    j = cv2.dilate(jeannot.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    garde = (j | car | boite(0, 0, 662, H) | boite(0, 0, 1066, 262) | boite(1066, 0, 1160, H)
             | boite(1160, 0, W, 250) | ((yy > pied + 12) & (xx < 905)) | boite(905, 576, 1045, H)
             | boite(1475, 0, W, H) | boite(0, 590, W, H))
    return ia & ~garde, garde


def charger(nom, rc):
    x0, y0, x1, y1 = rc
    return np.asarray(Image.open(TRAVAIL / nom).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v10 = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = v10.shape[:2]
    v9 = np.asarray(Image.open(V9).convert("RGB"))
    jeannot, car = p02_v10.silhouettes(v9)          # Jeannot et la 4L sont identiques au pixel près depuis la v6
    protege = jeannot | car
    res = v10.astype(np.float32)
    zones, infos, masques = [], [], []
    for nom, fichier, rc in (("colline", "v11-ia-colline-2.png", CC), ("mur", "v11-ia-mur-4.png", CM)):
        x0, y0, x1, y1 = rc
        ia = charger(fichier, rc)
        cur = np.clip(np.rint(res), 0, 255).astype(np.uint8)
        if nom == "colline":
            # le dessin change, pas la lumière : verts ramenés à ceux de la colline de la v10, ciel à celui de P01
            ia = p02_v10.couleurs_colline(ia, cur[y0:y1, x0:x1])
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
