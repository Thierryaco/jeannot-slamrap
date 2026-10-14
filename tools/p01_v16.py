"""P01 v16 = v13 + retouches locales uniquement (aucune recomposition) :
- tourelle d'ardoise surélevée (~0,55 m), balcon retiré, sorcière à la fenêtre de la tourelle (p01_v16_tourelle.py) ;
- capot avant de la Coccinelle ouvert + outils au sol (édition d'un recadrage, collage masqué du capot et des outils seuls).
Usage : python3 tools/p01_v16.py SORTIE.png"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, "tools")
import p01_v16_tourelle

ED = "assets/storyboards/a-valider/p01/work/crop-v16-cox-ed.png"
BOX = (830, 430, 1010, 610)            # recadrage envoyé à l'édition (180 x 180 dans l'image 1920)
# zones collées (coordonnées du recadrage 180 px) : capot ouvert + compartiment, outils au sol

FLOU = 0.7          # adoucissement du collage pour égaler la douceur de v13 à cette distance
ZONES = [[(64, 74), (146, 72), (146, 92), (142, 134), (66, 134)],
         [(52, 148), (146, 150), (146, 180), (52, 180)]]


def build():
    im = p01_v16_tourelle.build()
    a = np.array(im).astype(float)
    w, h = BOX[2] - BOX[0], BOX[3] - BOX[1]
    ed = np.array(Image.open(ED).convert("RGB").resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(FLOU))).astype(float)
    m = Image.new("L", (w, h), 0)
    for z in ZONES:
        ImageDraw.Draw(m).polygon(z, fill=255)
    mk = np.array(m.filter(ImageFilter.GaussianBlur(1.2)))[..., None] / 255.0
    reg = a[BOX[1]:BOX[3], BOX[0]:BOX[2]]
    a[BOX[1]:BOX[3], BOX[0]:BOX[2]] = reg * (1 - mk) + ed * mk
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


if __name__ == "__main__":
    from chemins import sortie_par_defaut
    build().save(sys.argv[1] if len(sys.argv) > 1 else sortie_par_defaut("v16.png"))
