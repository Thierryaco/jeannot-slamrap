"""P01 v18 = v17 + retouches locales uniquement :
1) toit autour de la tourelle : restes de la surélévation (v16) corrigés avec le toit/ciel d'origine de v13 ;
2) (étapes suivantes) Estafette plus fidèle + logo Renault ; tourelle et sorcière un peu plus grandes, tête plus sortie.
Usage : python3 tools/p01_v18.py SORTIE.png"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

P = "assets/storyboards/a-valider/p01/"
V13 = P + "p01-v13-montage-rev5.png"
V17 = P + "p01-v17-retouche-v16.png"
S = 24  # surélévation de la tourelle faite en v16 (px)


def _masque_tourelle_v16(size):
    """Cône surélevé + corniche + corps de la tourelle tels qu'ils sont dans v16/v17."""
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.polygon([(383, 0), (300, 182 - S), (306, 200 - S), (472, 200 - S), (474, 182 - S)], fill=255)
    d.rectangle((316, 195 - S, 460, 232 - S), fill=255)
    d.rectangle((384, 200 - S, 452, 540), fill=255)
    return np.array(m.filter(ImageFilter.MaxFilter(5))) > 0


def corrige_toit(a, o):
    """Restes du toit remonté avec la tourelle (v16), au-dessus des faîtages d'origine : bloc rouge ET son contour.
    Tout ce qui n'est ni le cône d'ardoise (forme pleine, traits fins exclus) ni du ciel est remplacé par le ciel
    de la même rangée."""
    from scipy import ndimage
    R, B = a[..., 0], a[..., 2]
    lum = a.mean(2)
    ardoise = ((B - R) > -8) & (lum < 160)
    cone = ndimage.binary_opening(ardoise, structure=np.ones((5, 5)))      # forme pleine du cône (sans traits fins)
    lab, _ = ndimage.label(cone)
    cone = lab == lab[100, 400]                                            # seule la composante du vrai cône
    cone = ndimage.binary_dilation(cone, iterations=2)                     # + son contour noir
    ciel_px = (lum > 175) & (B > R)
    for x0, x1, y0, y1, c0, c1 in ((318, 372, 40, 94, 255, 292),           # à gauche du cône (faîtage v13 ≈ y 95)
                                   (462, 484, 140, 177, 486, 530),
                                   (452, 462, 140, 158, 486, 530)):        # à droite de la corniche, jusqu'à l'antenne (v13 y est juste)
        z = np.zeros(R.shape, bool); z[y0:y1, x0:x1] = True
        m = z & ~cone & ~ciel_px
        m = ndimage.binary_dilation(m, iterations=1) & z & ~cone
        z_tout = z & ~cone                                     # toute la zone hors cône est reprise (raccord propre)
        o_ciel = ((o.mean(2) > 175) & (o[..., 2] > o[..., 0])) | (o.mean(2) < 110)   # v13 : ciel ou antenne
        for y in range(y0, y1):
            row = a[y, c0:c1]; ok = (row.mean(1) > 175) & (row[:, 2] > row[:, 0])
            c = np.median(row[ok], 0) if ok.any() else np.median(row, 0)
            for x in np.nonzero(z_tout[y])[0]:
                if o_ciel[y, x] and (x < 463 or y0 < 100 or True):
                    a[y, x] = o[y, x] if (m[y, x] or abs(a[y, x] - o[y, x]).mean() > 6) else a[y, x]
                else:
                    a[y, x] = c
    return a


def build():
    a = np.array(Image.open(V17).convert("RGB")).astype(float)
    o = np.array(Image.open(V13).convert("RGB")).astype(float)
    a = corrige_toit(a, o)
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


if __name__ == "__main__":
    build().save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w/v18.png")
