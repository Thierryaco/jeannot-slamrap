"""P01 v17 = v16 + retouches locales uniquement (on ne refait que ce qui ne va pas) :
- sorcière plus grande, fenêtre de tourelle plus grande, la sorcière fume (une seule volute) ;
- Diego à genoux devant sa caisse à outils.
Méthode : recadrage de v16 → édition → on ne colle que la zone utile (masque), à l'échelle de v16.
Usage : python3 tools/p01_v17.py SORTIE.png"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W = "assets/storyboards/a-valider/p01/work/"
V16 = "assets/storyboards/a-valider/p01/p01-v16-retouche-v13.png"
ED_S = W + "crop-v17-sorciere-ed.png"   # édition du recadrage (330,150)-(510,330) de v16
ED_D = W + "crop-v17-diego-ed.png"      # édition du recadrage (900,440)-(1080,620) de v16

# tourelle de v16 (image 1920) : corps x 384–452 ; corniche ≈ y 200
TX0, TX1 = 384, 452
# correspondance édition (repère 400 px) -> v16 : bord gauche du corps de tourelle 25 -> 384, bas de corniche 50 -> 200
K = (TX1 - TX0) / 245.0                 # 245 = largeur du corps de tourelle dans l'édition (repère 400)
REG = (60, 75, 300, 365)                # fenêtre + sorcière + main à la cigarette (repère 400)
FLOU = 0.6                              # douceur de v13 à cette distance


def ed400(path):
    return Image.open(path).convert("RGB").resize((400, 400), Image.LANCZOS)


def to16(x, y):
    return TX0 + (x - 25) * K, 200 + (y - 50) * K


def build(flou_diego=1.1):
    a = np.array(Image.open(V16).convert("RGB")).astype(float)

    # 1) l'ancienne petite fenêtre disparaît : corps de tourelle de v16 (rangée sans fenêtre) prolongé
    row = a[338:344, TX0 + 1:TX1 - 3].mean(0)
    a[240:324, TX0 + 1:TX1 - 3] = row[None]
    a[240:324, TX1 - 3:TX1] = [52, 50, 52]          # contour droit de la tourelle

    # 2) fenêtre agrandie + sorcière (à l'échelle de la tourelle de v16)
    e = ed400(ED_S)
    x0, y0, x1, y1 = REG
    reg = e.crop(REG)
    (X0, Y0), (X1, Y1) = to16(x0, y0), to16(x1, y1)
    X0, Y0 = round(X0), round(Y0)
    w, h = round(X1) - X0, round(Y1) - Y0
    reg = reg.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(FLOU))
    r = np.array(reg).astype(float)
    # masque : partie située sur le corps de la tourelle + cheveux noirs qui dépassent du bord
    xs = np.linspace(x0, x1, w)[None, :].repeat(h, 0)
    ys = np.linspace(y0, y1, h)[:, None].repeat(w, 1)
    # masque : seulement la fenêtre ronde (cadre compris), l'appui, le bras/la main et les cheveux noirs
    # (le mur de l'édition, plus clair, n'est PAS collé : le mur de v16 reste autour)
    fen = ((xs - 160) / 99.0) ** 2 + ((ys - 205) / 127.0) ** 2 <= 1.0
    appui = (xs >= 88) & (xs <= 262) & (ys >= 312) & (ys <= 344)
    main = (xs >= 200) & (xs <= 258) & (ys >= 296) & (ys <= 365) & (r.mean(2) < 200)
    cheveux = (r.mean(2) < 70) & (ys < 300)
    m = (fen | appui | main | cheveux).astype("uint8") * 255
    m = np.array(Image.fromarray(m).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    # adoucir le haut/bas du collage dans le mur de la tourelle
    zone = a[Y0:Y0 + h, X0:X0 + w]
    a[Y0:Y0 + h, X0:X0 + w] = zone * (1 - m[..., None]) + r * m[..., None]

    # 3) une seule volute de fumée qui part de la cigarette
    cx, cy = to16(248, 350)
    sm = Image.new("L", (a.shape[1], a.shape[0]), 0)
    d = ImageDraw.Draw(sm)
    pts = [(cx + 3 * np.sin(t / 7.0) + t * 0.10, cy - t) for t in range(0, 75)]
    d.line(pts, fill=230, width=3)
    sm = np.array(sm.filter(ImageFilter.GaussianBlur(1.0))) / 255.0
    sm *= np.clip(np.linspace(1.4, 0.3, sm.shape[0])[:, None] * 0 + 1, 0, 1)
    a = a * (1 - sm[..., None]) + np.array([232, 232, 230]) * sm[..., None]

    # 4) Diego à genoux devant sa caisse à outils (repère du recadrage 180 px, origine 900,440)
    ed = Image.open(ED_D).convert("RGB").resize((180, 180), Image.LANCZOS)
    if flou_diego:
        ed = ed.filter(ImageFilter.GaussianBlur(flou_diego))
    md = Image.new("L", (180, 180), 0)
    ImageDraw.Draw(md).polygon([(40, 140), (72, 140), (72, 56), (108, 56), (108, 85), (128, 85), (128, 172), (40, 172)], fill=255)
    md = np.array(md.filter(ImageFilter.GaussianBlur(1.2)))[..., None] / 255.0
    z = a[440:620, 900:1080]
    if not flou_diego:   # v20 : ne coller que Diego et la caisse (pas le feuillage net de l'édition autour)
        from scipy import ndimage
        dif = np.abs(np.array(ed).astype(float) - z).mean(2) > 22
        ea = np.array(ed).astype(float)
        dif |= (ea[..., 0] > ea[..., 1] + 60) & (ea[..., 0] > 110)          # la caisse à outils rouge
        dif = ndimage.binary_closing(ndimage.binary_opening(dif, np.ones((2, 2))), np.ones((5, 5)))
        dif = ndimage.binary_fill_holes(dif)
        lab, n = ndimage.label(dif)
        if n:
            tailles = ndimage.sum(dif, lab, range(1, n + 1))
            dif = np.isin(lab, 1 + np.nonzero(tailles >= 150)[0])
        dif = ndimage.binary_dilation(dif, iterations=2)
        nette = ndimage.gaussian_filter(dif.astype(float), 0.8)[..., None]
        douce = np.array(ed.filter(ImageFilter.GaussianBlur(1.1))).astype(float)   # fond de l'édition : doux comme v16
        ed = Image.fromarray(np.clip(douce * (1 - nette) + np.array(ed).astype(float) * nette, 0, 255).astype("uint8"))
    a[440:620, 900:1080] = z * (1 - md) + np.array(ed).astype(float) * md
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


ZONES = "380,195,475,330;936,494,1030,614"   # zones autorisées pour tools/controle_retouche.py

if __name__ == "__main__":
    build().save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w/v17.png")
