"""P01 v16 : retouches locales sur v13 (aucune recomposition).
1) tourelle d'ardoise surélevée d'environ 0,55 m (24 px) ;
2) balcon retiré : mur et corps de tourelle reconstitués avec des morceaux de v13 elle-même ;
3) sorcière à la fenêtre de la tourelle, à l'échelle de la fenêtre."""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

V13 = "assets/storyboards/a-valider/p01/p01-v13-montage-rev5.png"
GEN = "assets/storyboards/a-valider/p01/work/gen-v16-tourelle.png"


def feather(box_or_poly, size, r=1.5):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    (d.rectangle if len(box_or_poly) == 4 and not isinstance(box_or_poly[0], tuple) else d.polygon)(box_or_poly, fill=255)
    return np.array(m.filter(ImageFilter.GaussianBlur(r))) / 255.0


def paste(out, src, mk):
    return out * (1 - mk[..., None]) + src * mk[..., None]


def build():
    im = Image.open(V13).convert("RGB")
    a = np.array(im).astype(float)
    H, W = a.shape[:2]
    # 1) surélévation de la tourelle
    S = 24
    mk = feather([(383, 0), (300, 182), (306, 200), (472, 200), (474, 182)], im.size, 1.2)
    mk = np.maximum(mk, feather((316, 195, 460, 232), im.size, 1.2))
    src = np.zeros_like(a); src[:-S] = a[S:]
    msh = np.zeros_like(mk); msh[:-S] = mk[S:]
    out = paste(a, src, msh)
    for x0, x1, xs in ((296, 318, 292), (458, 480, 484)):
        for y in range(182 - S, 206):
            k = msh[y, x0:x1]
            out[y, x0:x1] = out[y, x0:x1] * k[:, None] + a[y, xs] * (1 - k[:, None])
    r = out.copy()
    # 2a) mur derrière le balcon (x 199–384, y 280–405) : crépi de v13 en mosaïque + dégradé ombre → clair
    def median_filter(v, size, mode=None):  # médiane glissante le long des colonnes
        k = size[0] // 2
        pad = np.pad(v, ((k, k), (0, 0)), mode="edge")
        return np.stack([np.median(pad[i:i + 2 * k + 1], 0) for i in range(len(v))])
    hh, X0, X1 = 143, 199, 385
    wallcols = np.r_[0:38, 77:99, 133:186]  # colonnes de mur nu (sans fenêtre ni porte)
    def interp(rows):
        m = np.median(r[rows, X0:X1], 0)
        xs = np.arange(X1 - X0)
        return np.stack([np.interp(xs, wallcols, m[wallcols, c]) for c in range(3)], 1)
    topc = median_filter(interp(slice(266, 278)), size=(15, 1))
    botc = median_filter(interp(slice(414, 424)), size=(15, 1))
    t = np.linspace(0, 1, hh)[:, None, None]
    rng = np.random.default_rng(16)
    grain = np.array(Image.fromarray((rng.normal(128, 40, (hh, X1 - X0))).clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2))).astype(float) - 128
    fill = topc[None] * (1 - t) + botc[None] * t + grain[..., None] * 0.12
    wall = r.copy(); wall[270:270 + hh, 199:385] = fill
    # fenêtre et porte d'origine prolongées jusqu'à un appui
    for x0, x1 in ((240, 274), (300, 330)):
        band = r[258:270, x0:x1]
        wall[270:298, x0:x1] = np.tile(band, (3, 1, 1))[:28]
        ys = 298
        wall[ys:ys + 5, x0 - 3:x1 + 3] = [196, 190, 178]
        wall[ys + 5:ys + 7, x0 - 3:x1 + 3] = [60, 58, 56]
        wall[ys - 1:ys, x0 - 3:x1 + 3] = [60, 58, 56]
    out = paste(r, wall, feather((199, 275, 385, 412), im.size, 2.5))
    # 2b) corps de tourelle prolongé jusqu'au mur du jardin
    band = r[186:216, 384:452]
    col = np.tile(band.mean(0, keepdims=True), (140, 1, 1))
    col[:, -3:] = [52, 50, 52]  # contour droit de la tourelle (trait sombre de v13)
    col[:, :2] = col[:, :2] * 0.75
    col = col + grain[:140, :68, None] * 0.12
    tur = out.copy(); tur[298:438, 384:452] = col
    out2 = paste(out, tur, feather((384, 298, 452, 438), im.size, 0.8))
    # à droite de la tourelle : restes de balcon remplacés par le feuillage voisin
    bg = out2.copy(); bg[276:440, 452:470] = r[276:440, 470:488]
    out2 = paste(out2, bg, feather((453, 276, 470, 440), im.size, 1.0))
    # fumée de Jeannot conservée par-dessus
    box = (slice(392, 438), slice(355, 432))
    lum_o = a[box].mean(2); lum_n = out2[box].mean(2)
    k = np.clip((lum_o - lum_n - 25) / 40, 0, 0.85)[..., None]
    out2[box] = out2[box] * (1 - k) + a[box] * k
    # 3) sorcière à la fenêtre (patch de la génération, à l'échelle de la fenêtre)
    g = Image.open(GEN).convert("RGB").resize((440, 440), Image.LANCZOS).crop((206, 160, 302, 280))
    g = g.resize((54, 62), Image.LANCZOS)
    wm = Image.new("L", g.size, 0); ImageDraw.Draw(wm).rounded_rectangle((1, 1, g.size[0] - 2, g.size[1] - 2), 3, fill=255)
    wm = np.array(wm.filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    x0, y0 = 413 - g.size[0] // 2, 244
    reg = out2[y0:y0 + g.size[1], x0:x0 + g.size[0]]
    out2[y0:y0 + g.size[1], x0:x0 + g.size[0]] = reg * (1 - wm[..., None]) + np.array(g) * wm[..., None]
    return Image.fromarray(np.clip(out2, 0, 255).astype("uint8"))


if __name__ == "__main__":
    build().save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w/v16b.png")
