"""Montage P01 v14/v15 : plaque de fond + éléments placés aux boîtes exactes du calque de la carte.

python3 tools/compose_p01.py A|B sortie.png
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import calque  # noqa: E402
import draw_street_map as dsm  # noqa: E402

WK = Path(__file__).resolve().parents[1] / "assets/storyboards/a-valider/p01/work"
GRASS = (141, 153, 119)
LILAC = (214, 201, 220)


def placement(cam):
    P = dsm.load_plans()["P01"]
    if cam == "B":
        P = json.loads(json.dumps(P))
        P["cameras"][0].update(y=535, angle=-6, portee=2000)
    return P


def proj(P, x, y, h=0.0):
    return calque.Cam(P["cameras"][0]).proj(x, y, h)


def turret_box(P):
    us, vb = [], []
    import math
    for k in range(72):
        a = math.radians(k * 5)
        q = proj(P, 280 + 30 * math.cos(a), 332 + 30 * math.sin(a), 0)
        if q:
            us.append(q[0]); vb.append(q[1])
    return min(us), max(us), max(vb)


def sidewalk_edge(x):  # bord herbe/trottoir de la plaque (côté Jeannot), mesuré sur plate2
    return 915 - x * (225 / 580)


def tourelle_et_mur(img, P, plate):
    """Replace la tourelle à sa position calculée, et peint le mur latéral d'Henri dans l'espace libéré."""
    u0, u1, vb = turret_box(P)
    W, H = img.size
    d = ImageDraw.Draw(img)
    corner = 487  # coin avant-gauche de la façade d'Henri dans la plaque
    top_side = 151
    # ciel au-dessus du mur latéral (colonne de ciel de la plaque)
    sky = plate.crop((820, 0, 821, H)).resize((corner - int(u1) + 40, H))
    img.paste(sky.crop((0, 0, sky.width, top_side)), (int(u1) - 40, 0))
    # mur latéral (pignon vu de face : rectangle)
    side = tuple(int(c * 0.9) for c in LILAC)
    d.rectangle([int(u1) - 40, top_side, corner, 690], fill=side)
    d.rectangle([int(u1) - 40, top_side - 9, corner + 2, top_side], fill=(120, 84, 70), outline=(40, 34, 38), width=2)
    d.line([(corner, top_side), (corner, 690)], fill=(40, 34, 38), width=3)
    # sol : herbe entre les maisons, et sous la tourelle
    for x in range(0, corner + 1):
        y1 = int(sidewalk_edge(x))
        d.line([(x, 688 if x > u1 - 40 else 640), (x, y1 - 2)], fill=GRASS)
    # tourelle : corps de la tourelle de la plaque, mis à l'échelle
    sx0, sx1, sy0, sy1 = 279, 486, 175, 742
    src = plate.crop((sx0, sy0, sx1, sy1)).convert("RGBA")
    m = Image.new("L", src.size, 0)
    curve = [(278, 728), (330, 734), (380, 737), (430, 727), (478, 702), (490, 690)]
    ImageDraw.Draw(m).polygon([(x - sx0, y - sy0) for x, y in [(sx0, sy0), (sx1, sy0)] + curve[::-1]], fill=255)
    src.putalpha(m)
    s = (u1 - u0) / (sx1 - sx0)
    tw, th = int(src.width * s), int(src.height * s)
    src = src.resize((tw, th), Image.LANCZOS)
    oy = int(vb - (737 - sy0) * s)
    img.alpha_composite(src, (int(u0), oy))
    return (u0, u1, vb)


def shadow(img, cx, y, w, h=None, alpha=90):
    h = h or max(6, w * 0.16)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([cx - w / 2, y - h / 2, cx + w / 2, y + h / 2], fill=(30, 30, 40, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(2, w / 18))))


def put(img, sprite, box, fit="h", anchor_x=None, foot=None, scale=None):
    """Colle un sprite : hauteur (fit=h) ou largeur (fit=w) de la boîte, pieds en bas de la boîte."""
    sp = Image.open(WK / sprite if isinstance(sprite, str) else sprite) if not isinstance(sprite, Image.Image) else sprite
    x0, y0, x1, y1 = box
    s = scale or ((y1 - y0) / sp.height if fit == "h" else (x1 - x0) / sp.width)
    sp = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.LANCZOS)
    cx = anchor_x if anchor_x is not None else (x0 + x1) / 2
    yb = foot if foot is not None else y1
    img.alpha_composite(sp, (int(round(cx - sp.width / 2)), int(round(yb - sp.height))))
    return sp.size


def boxes(P):
    L = dsm.load_lieux()
    return {t[0]: [round(v) for v in t[3]] for t in calque.elements_attendus(L, P, 0)}


def compose(cam, plate_path, out):
    P = placement(cam)
    plate = Image.open(plate_path).convert("RGBA")
    img = plate.copy()
    tourelle_et_mur(img, P, plate)
    bx = boxes(P)
    # Henri sur le palier (sprite de profil vers la droite)
    x0, y0, x1, y1 = bx["henri"]
    put(img, Image.open(Path(__file__).resolve().parents[1] / "assets/art/sprites/henri-profil-droite.png"), bx["henri"])
    # 4L : face arrière = de rearL à rearR, pieds au bas de la boîte
    e = P["elements"]["4l"]
    rl, rr = proj(P, e["x"] - 50, e["y"] - 21, 0), proj(P, e["x"] - 50, e["y"] + 21, 0)
    sp = Image.open(WK / "sprite-4l.png")
    s = (rr[0] - rl[0]) / (sp.width * 0.78)   # la face arrière occupe ~78 % de la largeur du sprite
    ylow = max(rl[1], rr[1])
    shadow(img, (rl[0] + rr[0]) / 2 + 15, ylow - 4, (rr[0] - rl[0]) * 1.15, 26, 110)
    put(img, "sprite-4l.png", bx["4l"], scale=s, anchor_x=rl[0] + sp.width * s / 2 - sp.width * s * 0.025, foot=ylow + 2)
    # Jeannot
    x0, y0, x1, y1 = bx["jeannot"]
    shadow(img, (x0 + x1) / 2, y1 - 2, (x1 - x0) * 1.2, 14, 90)
    put(img, "sprite-jeannot.png", bx["jeannot"])
    # Enji
    x0, y0, x1, y1 = bx["enji"]
    shadow(img, (x0 + x1) / 2, y1 - 3, (y1 - y0) * 1.1, 14, 90)
    put(img, "sprite-enji.png", bx["enji"])
    img.convert("RGB").save(out, quality=92)
    return bx


if __name__ == "__main__":
    cam, out = sys.argv[1], sys.argv[2]
    plate = sys.argv[3] if len(sys.argv) > 3 else WK / "plate2-sans-figurant.png"
    print(compose(cam, plate, out))
