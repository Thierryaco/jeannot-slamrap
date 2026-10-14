"""P01 v27 — v26 + une porte directement dans le mur de la maison, sous l'escalier d'Henri.
Avis v19 : « rajoute plutôt une porte directement sur la maison, c'est plus logique ».
(Remplace la v25, dont la porte laissait un liseré clair et débordait sur le pan gris.)

La porte a été dessinée sur la v26 (work/crop-v27-ed.png, recadrage 320×320 en (651, 396)) ; on ne
recolle QUE la porte, au ras de son contour noir (encadrement + marche). Pour lui faire place, comme
dans l'édition, le bord du pan gris (côté garage) passe de x 819 à x 830 : au-dessus de la porte, la
bande x 819–829 / y 453–493 devient du mur beige (teinte prise sur le mur voisin de la v26) et le
trait du bord est redessiné à x 830.

Usage : python3 tools/p01_v27.py [OUT.png]   (depuis la racine du dépôt)
"""
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

P = "assets/storyboards/a-valider/p01/"
V26 = P + "p01-v26-rampe.png"
ED = P + "work/crop-v27-ed.png"
BOX = (651, 396, 971, 716)
PORTE = [(799.0, 492.5), (832.0, 492.5), (832.0, 583.0), (836.5, 583.0), (836.5, 592.5),
         (805.5, 592.5), (805.5, 591.5), (799.0, 591.5)]       # encadrement + marche
BORD_X = 830.0                       # nouveau bord du pan gris
MUR_Y = (454, 494)                   # bande prolongée au-dessus de la porte (y)
MUR_X = (817, 830)                   # (x, BORD_X exclu)
EPAIS = (818.0, 452.0), (771.0, 548.0)   # trait épais (dessous de l'escalier), cf. p01_v26


def _masque_poly(poly, shape, k=4):
    h, w = shape
    im = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(im).polygon([(x * k, y * k) for x, y in poly], fill=255)
    return np.asarray(im.resize((w, h), Image.BOX), float) / 255.0


def build():
    a = np.asarray(Image.open(V26).convert("RGB"), float).copy()
    h, w, _ = a.shape
    # 1. mur prolongé au-dessus de la porte : à chaque hauteur, la teinte moyenne du coin de mur
    #    voisin de la v26 (entre le trait épais et l'ancien bord) ; l'ancien bord (x 818–819) et son
    #    liseré clair (x 817) disparaissent. Le coin du trait épais et le dessous du palier restent.
    (x0, y0), (x1, y1) = EPAIS
    xt = lambda y: x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    ref = {}
    for y in range(455, 520):
        px = a[y, int(np.ceil(xt(y) + 3)):817]
        if len(px) >= 2:
            ref[y] = px.mean(0)
    ys = np.array(sorted(ref))
    cols = np.array([ref[y] for y in ys])
    rng = np.random.default_rng(27)
    grain = gaussian_filter(rng.standard_normal((h, w)), 1.5)
    grain *= 2.0 / grain[MUR_Y[0]:MUR_Y[1], MUR_X[0]:MUR_X[1]].std()
    for y in range(*MUR_Y):
        sel = np.abs(ys - y) <= 3
        c = cols[sel].mean(0) if sel.any() else cols[0]      # sous le palier : relevé le plus haut
        # lignes 454–456 : le trait épais occupe x 815–817 ; l'ancien bord (x 818–819) est effacé
        debut = 818 if y < 457 else max(817, int(np.ceil(xt(y) + 2.5)))
        for x in range(debut, MUR_X[1]):
            a[y, x] = c * (1 + grain[y, x] / 160)
    # 2. trait du bord du pan gris à x 830 (même teinte que l'ancien bord à x 819)
    teinte = np.median([a[y, 817:822][np.argmin(a[y, 817:822].mean(1))] for y in range(500, 580)], 0)
    yy, xx = np.mgrid[MUR_Y[0] - 1:MUR_Y[1] + 1, int(BORD_X) - 2:int(BORD_X) + 3]
    cov = np.clip(1.6 / 2 + 0.5 - np.abs(xx + 0.5 - BORD_X), 0, 1)[..., None]
    a[yy, xx] = a[yy, xx] * (1 - cov) + teinte * cov
    # 3. la porte de l'édition, au ras de son contour
    e = np.asarray(Image.open(ED).convert("RGB").resize((BOX[2] - BOX[0], BOX[3] - BOX[1]),
                                                        Image.LANCZOS), float)
    full = a.copy()
    full[BOX[1]:BOX[3], BOX[0]:BOX[2]] = e
    m = _masque_poly(PORTE, (h, w))[..., None]
    a = a * (1 - m) + full * m
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8"))


if __name__ == "__main__":
    im = build()
    if len(sys.argv) > 1:
        sortie = sys.argv[1]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v27.png")
    im.save(sortie)
    d = np.abs(np.asarray(im, float) - np.asarray(Image.open(V26).convert("RGB"), float)).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
