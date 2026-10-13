"""P01 v18 = v17 + retouches locales uniquement :
1) toit autour de la tourelle : restes de la surélévation (v16) corrigés avec le toit/ciel d'origine de v13 ;
2) (étapes suivantes) Estafette plus fidèle + logo Renault ; tourelle et sorcière un peu plus grandes, tête plus sortie.
Usage : python3 tools/p01_v18.py SORTIE.png"""
import os
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


BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'storyboards', 'a-valider', 'p01')


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


def estafette(a):
    """Estafette refaite (avis v17) : vraie Renault Estafette de face + losange Renault, d'après P02 v2 / P03.
    Crop-edit work/v18-estafette-edit.png, détourée (work/v18-estafette-masque.png), mise à la largeur de
    l'ancienne (97 px, x 1020-1117), roues au même endroit (y 588)."""
    from scipy import ndimage
    from PIL import ImageFilter
    W = os.path.join(BASE, 'work')
    e = Image.open(os.path.join(W, 'v18-estafette-edit.png')).convert('RGB')
    m = np.asarray(Image.open(os.path.join(W, 'v18-estafette-masque.png'))) > 0
    ea = np.asarray(e).astype(float)
    Y, X = np.mgrid[:m.shape[0], :m.shape[1]]
    m &= ~((X > 730) & (Y < 272) & (ea.mean(2) < 140))          # moignons de la barrière
    s = 97 / 480.0
    w, h = round(e.width * s), round(e.height * s)
    es = np.asarray(e.resize((w, h), Image.LANCZOS)).astype(float)
    ms = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
    ms = np.asarray(ms.filter(ImageFilter.GaussianBlur(0.6))).astype(float) / 255
    ms = np.clip((ms - 0.15) / 0.7, 0, 1)
    es = np.asarray(Image.fromarray(es.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))).astype(float)
    es = es * np.array([0.80, 0.76, 0.81])                       # ramène au bleu-gris passé de l'ancienne (médianes carrosserie)
    ox = round(1068.5 - 618 * s); oy = round(588 - 771 * s)
    reg = a[oy:oy + h, ox:ox + w]
    a[oy:oy + h, ox:ox + w] = reg * (1 - ms[..., None]) + es * ms[..., None]
    return a


def tourelle(a, flou=1.2, flou_sorciere=None):
    """Avis v17 : tourelle et sorcière légèrement plus grandes, tête plus sortie ; + vérif. « à côté » :
    double débord de toit / marche / plaque pâle à gauche (traînés par le décalage v16) remplacés par un seul débord.
    Crop-edit work/v18-tourelle-edit2.png (crop v18 x 250-610, y 0-360, x3). Le cône et l'antenne restent ceux de v18.
    Le fût élargi (bord gauche x 343) est prolongé jusqu'au haut du mur (y ~470)."""
    from scipy import ndimage
    W = os.path.join(BASE, 'work')
    X0, Y0, S = 250, 0, 360
    e0 = Image.open(os.path.join(W, 'v18-tourelle-edit2.png')).convert('RGB').resize((S, S), Image.LANCZOS)
    e = np.asarray(e0.filter(ImageFilter.GaussianBlur(flou))).astype(float)
    if flou_sorciere is not None:   # v19 : sorcière + fenêtre restent nettes (avis v18 « floue, pas définie »)
        es = np.asarray(e0.filter(ImageFilter.GaussianBlur(flou_sorciere))).astype(float)
        ws = np.zeros((S, S)); ws[184 - Y0:304 - Y0, 382 - X0:508 - X0] = 1
        ws = ndimage.gaussian_filter(ws, 2.5)[..., None]
        e = e * (1 - ws) + es * ws
    v = a[Y0:Y0 + S, X0:X0 + S]
    d = np.abs(ndimage.gaussian_filter(e, (2, 2, 0)) - ndimage.gaussian_filter(v, (2, 2, 0))).mean(2)
    diff = ndimage.binary_closing(ndimage.binary_opening(d > 14, np.ones((3, 3))), np.ones((9, 9)))
    m = np.zeros((S, S), bool)
    def r(x0, x1, y0, y1): m[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = True
    r(340, 456, 172, 358)          # fût + fenêtre + sorcière
    r(300, 466, 145, 190)          # corniche (raccord fût)
    r(262, 345, 150, 262)          # débord de toit à gauche (un seul)
    zone = np.zeros_like(m); zone[190:305, 440 - X0:505 - X0] = True
    m |= diff & zone               # cheveux, main, fumée qui dépassent à droite
    mf = ndimage.gaussian_filter(m.astype(float), 1.5)[..., None]
    a[Y0:Y0 + S, X0:X0 + S] = v * (1 - mf) + e * mf
    # prolongement du fût jusqu'au mur
    prof = np.median(e[322:332, 340 - X0:453 - X0], axis=0)
    prof = ndimage.uniform_filter1d(prof, 3, axis=0)
    for i, x in enumerate(range(340, 453)):
        for y in range(326, 472):
            px = a[y, x]
            if y >= 466 and px.mean() > 185:
                break
            t = min(1.0, (y - 326) / 22.0)
            a[y, x] = a[y, x] * (1 - t) + prof[i] * t
    return a


def build():
    a = np.array(Image.open(V17).convert("RGB")).astype(float)
    o = np.array(Image.open(V13).convert("RGB")).astype(float)
    a = corrige_toit(a, o)
    a = estafette(a)
    a = tourelle(a)
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


if __name__ == "__main__":
    build().save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w/v18.png")
