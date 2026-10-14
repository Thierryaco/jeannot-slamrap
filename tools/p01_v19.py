"""P01 v19 — retouches locales sur la v18 (même chaîne que p01_v18.py, depuis la v17).
Avis v18 : sorcière floue / pas définie -> la sorcière et sa fenêtre restent nettes ;
façade de la tourelle « plus propre que le reste de la maison » -> teinte et patine de la tour ronde ;
logo Renault de l'Estafette invisible / pas de la bonne couleur -> losange chromé comme sur la 4L.
Usage : python3 tools/p01_v19.py OUT.png"""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import p01_v18 as V

TOUR_RONDE = (84, 110, 165, 330)          # aplat éclairé de la tour ronde (x0, x1, y0, y1) : teinte + patine de référence


def patine_tourelle(a):
    x0, x1, y0, y1 = TOUR_RONDE
    ref = a[y0:y1, x0:x1].copy()
    cible = np.median(ref.reshape(-1, 3), 0)
    det = ref - ndimage.gaussian_filter(ref, (4, 4, 0))            # taches / marbrures du crépi
    det -= det.mean(0, keepdims=True); det -= det.mean(1, keepdims=True)   # pas de rayures au tuilage
    det = np.clip(det, -10, 10)                                     # pas de tache isolée trop marquée
    det = np.concatenate([det, det[:, ::-1]], 1)                   # tuilage en miroir (pas de couture)
    det = np.concatenate([det, det[::-1]], 0)
    X0, X1, Y0, Y1 = 300, 466, 150, 472
    h, w = Y1 - Y0, X1 - X0
    det = np.tile(det, (h // det.shape[0] + 1, w // det.shape[1] + 1, 1))[:h, :w]
    reg = a[Y0:Y1, X0:X1]
    lum = reg.mean(2)
    mur = (reg[..., 0] > reg[..., 2] + 12) & (lum > 120) & (lum < 235)
    Y, X = np.mgrid[Y0:Y1, X0:X1]
    mur &= ((Y >= 183) & (X >= 340) & (X <= 457)) | ((Y < 183) & (lum > 150))   # fût, ou crème de la corniche
    arc = ((X >= 384) & (X <= 457) & (Y >= 210) & (Y <= 294)) | ((Y < 210) & (((X - 420.5) / 37.5) ** 2 + ((Y - 210) / 25.0) ** 2 <= 1))
    arc |= (X >= 380) & (X <= 460) & (Y >= 278) & (Y <= 296)       # appui de fenêtre
    mur &= ~arc                                                    # fenêtre + sorcière
    mur = ndimage.binary_opening(mur, np.ones((3, 3)))
    mf = ndimage.gaussian_filter(mur.astype(float), 1.0)[..., None]
    eclaire = np.median(reg[mur & (X > 395) & (Y > 300)], 0)      # partie éclairée du fût
    gain = cible / eclaire
    nouv = reg * gain + det * 0.9
    a[Y0:Y1, X0:X1] = reg * (1 - mf) + nouv * mf
    return a, gain


def logo_estafette(a, cx=1064.6, cy=532.0, w=7.0, h=9.0):
    """Losange Renault chromé comme sur la 4L : contour sombre, facettes argent claires, trait sombre au centre."""
    k = 10
    W, H = int(w * k) + 2 * k, int(h * k) + 2 * k
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = (W / 2, H / 2)
    pts = [(c[0], c[1] - h * k / 2), (c[0] + w * k / 2, c[1]), (c[0], c[1] + h * k / 2), (c[0] - w * k / 2, c[1])]
    d.polygon(pts, fill=(38, 38, 42, 255))
    s = 0.72
    inn = [(c[0] + (x - c[0]) * s, c[1] + (y - c[1]) * s) for x, y in pts]
    d.polygon(inn, fill=(228, 232, 228, 255))
    d.polygon([inn[1], inn[2], (c[0], c[1])], fill=(168, 172, 170, 255))     # facette ombrée
    d.polygon([inn[2], inn[3], (c[0], c[1])], fill=(198, 202, 198, 255))
    d.line([(c[0], c[1] - h * k * 0.18), (c[0], c[1] + h * k * 0.18)], fill=(45, 45, 50, 255), width=int(k * 0.9))
    sm = im.resize((W // k, H // k), Image.LANCZOS)
    sa = np.asarray(sm).astype(float)
    ox, oy = int(round(cx - sm.width / 2)), int(round(cy - sm.height / 2))
    al = sa[..., 3:] / 255
    reg = a[oy:oy + sm.height, ox:ox + sm.width]
    a[oy:oy + sm.height, ox:ox + sm.width] = reg * (1 - al) + sa[..., :3] * al
    return a


def build():
    a = np.array(Image.open(V.V17).convert("RGB")).astype(float)
    o = np.array(Image.open(V.V13).convert("RGB")).astype(float)
    a = V.corrige_toit(a, o)
    a = V.estafette(a)
    a = V.tourelle(a, flou=1.2, flou_sorciere=0.35)
    a, g = patine_tourelle(a)
    print('gain teinte tourelle', np.round(g, 3))
    a = logo_estafette(a)
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


if __name__ == "__main__":
    from chemins import sortie_par_defaut
    build().save(sys.argv[1] if len(sys.argv) > 1 else sortie_par_defaut("v19.png"))
