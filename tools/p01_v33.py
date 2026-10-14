"""P01 v33 — la v32 sans les restes de flou de l'ancien contrôle autour de Diego (avis v32, 14/10).

Avis de l'utilisateur sur la v32 (pointage (866, 445) (860, 622) (1119, 625) (1112, 442)) :
« vérifie la zone intérieur des points 1 2 3 et 4 il y a des reste de flou de l'ancien controle ».

Cause : à l'époque de la v16 et de la v17, le contrôle avait un critère « grain » (retiré depuis), et
les collages étaient volontairement adoucis pour s'y conformer :
  - p01_v16.py : capot ouvert + compartiment moteur, et outils au sol, collés avec un flou de 0,7 ;
  - p01_v17.py (repris par la v20) : Diego et sa caisse nets, mais tout le fond autour d'eux
    (clôture, piliers, haie) collé « doux comme v16 », avec un flou de 1,1.
La v20 a rendu nets Diego, la caisse, l'Estafette et la tourelle, mais pas ces deux collages-là.

Méthode, sans IA et sans rien redessiner : on refait la même chaîne (p01_v16 → Diego de p01_v17 →
Estafette de p01_v18 → logo de p01_v19), avec les mêmes images d'origine, deux fois :
  - avec les anciens flous : elle redonne la v20, donc la v32, à 1 niveau près dans la zone ;
  - sans flou.
Seuls les pixels qui diffèrent entre les deux sont remplacés dans la v32 : partout ailleurs, l'image
est exactement la v32.

Usage : python3 tools/p01_v33.py [OUT.png]   (depuis la racine du dépôt)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p01_v16  # noqa: E402
import p01_v18 as V18  # noqa: E402
import p01_v19 as V19  # noqa: E402

P = "assets/storyboards/a-valider/p01/"
V32 = P + "p01-v32-ed5.png"
ZONE = (863, 430, 1140, 640)       # zone pointée par l'utilisateur, avec marge (x0, y0, x1, y1)
FLOU_V16 = 0.7                      # p01_v16.FLOU d'origine
FLOU_FOND_DIEGO = 1.1               # flou du fond autour de Diego dans p01_v17 (v20)


def diego(a, flou_fond):
    """Étape 4 de p01_v17.build(flou_diego=0) : Diego et sa caisse nets ; fond de l'édition flouté de
    `flou_fond` (1,1 dans la v20 ; 0 = net)."""
    ed = Image.open(P + "work/crop-v17-diego-ed.png").convert("RGB").resize((180, 180), Image.LANCZOS)
    md = Image.new("L", (180, 180), 0)
    ImageDraw.Draw(md).polygon([(40, 140), (72, 140), (72, 56), (108, 56), (108, 85), (128, 85), (128, 172),
                                (40, 172)], fill=255)
    md = np.array(md.filter(ImageFilter.GaussianBlur(1.2)))[..., None] / 255.0
    z = a[440:620, 900:1080]
    ea = np.array(ed).astype(float)
    dif = np.abs(ea - z).mean(2) > 22
    dif |= (ea[..., 0] > ea[..., 1] + 60) & (ea[..., 0] > 110)          # la caisse à outils rouge
    dif = ndimage.binary_closing(ndimage.binary_opening(dif, np.ones((2, 2))), np.ones((5, 5)))
    dif = ndimage.binary_fill_holes(dif)
    lab, n = ndimage.label(dif)
    if n:
        tailles = ndimage.sum(dif, lab, range(1, n + 1))
        dif = np.isin(lab, 1 + np.nonzero(tailles >= 150)[0])
    dif = ndimage.binary_dilation(dif, iterations=2)
    nette = ndimage.gaussian_filter(dif.astype(float), 0.8)[..., None]
    douce = np.array(ed.filter(ImageFilter.GaussianBlur(flou_fond)) if flou_fond else ed).astype(float)
    ed2 = np.clip(douce * (1 - nette) + ea * nette, 0, 255).astype("uint8").astype(float)
    a[440:620, 900:1080] = z * (1 - md) + ed2 * md
    return a


def chaine(flou_v16, flou_fond):
    p01_v16.FLOU = flou_v16
    try:
        a = np.array(p01_v16.build()).astype(float)
    finally:
        p01_v16.FLOU = FLOU_V16
    a = diego(a, flou_fond)
    a = V18.estafette(a, flou=0)
    a = V19.logo_estafette(a)
    return np.clip(a, 0, 255).astype("uint8")


def build():
    x0, y0, x1, y1 = ZONE
    ancien = chaine(FLOU_V16, FLOU_FOND_DIEGO)[y0:y1, x0:x1]
    net = chaine(0, 0)[y0:y1, x0:x1]
    v32 = np.array(Image.open(V32).convert("RGB"))
    ecart = np.abs(ancien.astype(int) - v32[y0:y1, x0:x1].astype(int)).max()
    if ecart > 2:
        raise SystemExit("la chaîne ne redonne plus la v32 dans la zone (écart %d) : à vérifier" % ecart)
    change = (net != ancien).any(2)
    out = v32.copy()
    out[y0:y1, x0:x1][change] = net[change]
    return Image.fromarray(out)


if __name__ == "__main__":
    im = build()
    if len(sys.argv) > 1:
        sortie = sys.argv[1]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v33.png")
    im.save(sortie)
    d = np.abs(np.asarray(im, int) - np.asarray(Image.open(V32).convert("RGB"), int)).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée depuis la v32 : %d,%d,%d,%d (%d pixels)" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, len(xs)))
