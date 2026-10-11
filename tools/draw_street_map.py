#!/usr/bin/env python3
"""Carte de la rue (vue de dessus) — référence de cohérence des lieux.

Une seule description des formes produit deux fichiers identiques :
  - assets/storyboards/a-valider/carte/carte-rue-vN.svg (net, modifiable)
  - assets/storyboards/a-valider/carte/carte-rue-vN.png (pour la génération d'images)

Les positions des caméras par plan sont dans CAMERAS : on en ajoute une à
chaque plan validé, pour que tous les plans partagent la même géographie.

Usage : python3 tools/draw_street_map.py [version]   (défaut : v1)
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/storyboards/a-valider/carte"
W, H = 1600, 1000
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Géométrie de la rue (ouest = bout Jeannot, est = bout Diego)
X0, X1 = 70, 1530
N_LOT, N_PAVE, ROAD_T, ROAD_B, S_PAVE, S_LOT = 110, 385, 425, 565, 605, 860

# Caméras : plan -> (x, y, direction en degrés [0 = vers l'est, 90 = vers le sud], ouverture, portée, note)
CAMERAS = {
    "P01": (X0 + 22, 495, -2, 30, 1250, "bout Jeannot → vers Diego : 4L vue de derrière"),
}

shapes = []  # (type, params)


def rect(x, y, w, h, fill, stroke="#33404f", sw=2, rx=0, dash=None):
    shapes.append(("rect", dict(x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, rx=rx, dash=dash)))


def circle(cx, cy, r, fill, stroke="#1b2430", sw=2):
    shapes.append(("circle", dict(cx=cx, cy=cy, r=r, fill=fill, stroke=stroke, sw=sw)))


def poly(pts, fill, stroke=None, sw=0, opacity=1.0):
    shapes.append(("poly", dict(pts=pts, fill=fill, stroke=stroke, sw=sw, opacity=opacity)))


def line(x1, y1, x2, y2, stroke, sw=2, dash=None):
    shapes.append(("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, sw=sw, dash=dash)))


def text(x, y, s, size=16, fill="#1b2430", bold=False, anchor="middle"):
    shapes.append(("text", dict(x=x, y=y, s=s, size=size, fill=fill, bold=bold, anchor=anchor)))


def build():
    rect(0, 0, W, H, "#f4efe4", stroke=None, sw=0)
    text(W / 2, 42, "Carte de la rue — vue de dessus (référence des lieux)", 26, bold=True)
    text(W / 2, 72, "Ouest = bout de Jeannot  ·  Est = bout de Diego  ·  côté nord = côté Jeannot  ·  côté sud = côté narrateur", 15, "#4a5566")

    # Chaussée et trottoirs
    rect(X0, N_PAVE, X1 - X0, ROAD_T - N_PAVE, "#d9d4ca", sw=1)
    rect(X0, ROAD_T, X1 - X0, ROAD_B - ROAD_T, "#8e939a", sw=1)
    rect(X0, ROAD_B, X1 - X0, S_PAVE - ROAD_B, "#d9d4ca", sw=1)
    line(X0 + 20, (ROAD_T + ROAD_B) / 2, X1 - 20, (ROAD_T + ROAD_B) / 2, "#e8e8e8", 2, dash=(18, 16))
    text(820, (ROAD_T + ROAD_B) / 2 + 30, "RUE (une seule rue pour tout le clip)", 15, "#f1f1f1", True)

    # Côté nord (côté Jeannot)
    lots_n = [
        (X0 + 10, 250, "#f7d9a8", "Maison de JEANNOT", "+ la sorcière + Enji"),
        (X0 + 270, 230, "#e7e0f5", "Maison d'HENRI", "juste à côté"),
        (X0 + 510, 250, "#ebe7df", "voisin", ""),
        (X0 + 770, 250, "#ebe7df", "voisin", ""),
    ]
    for x, w, col, t1, t2 in lots_n:
        rect(x, N_LOT, w, N_PAVE - N_LOT - 8, "#e9f0dc", stroke="#9aa58a", sw=1)  # jardin
        rect(x + 20, N_LOT + 55, w - 40, 175, col)
        text(x + w / 2, N_LOT + 140, t1, 17, bold=True)
        if t2:
            text(x + w / 2, N_LOT + 164, t2, 14, "#4a5566")
    # Tourelle de la sorcière, sur la maison de Jeannot (angle côté rue, ouest)
    circle(X0 + 58, N_LOT + 222, 30, "#c9b6e8")
    text(X0 + 150, N_LOT + 40, "tourelle de la sorcière ↓", 13, "#5b3f8c", anchor="middle")
    # Escalier extérieur d'Henri (façade côté rue, monte vers la porte du 1er)
    sx, sy = X0 + 430, N_LOT + 232
    rect(sx, sy, 50, 40, "#bfb7a8")
    for i in range(1, 6):
        line(sx + i * 8.3, sy, sx + i * 8.3, sy + 40, "#6e6658", 1)
    text(sx + 25, sy + 58, "escalier ext.", 12, "#4a5566")
    # Diego : garage/atelier OUVERT côté ouest (vue dégagée depuis la rue), maison à l'est
    dx = X0 + 1030
    rect(dx, N_LOT, X1 - dx - 10, N_PAVE - N_LOT - 8, "#e9f0dc", stroke="#9aa58a", sw=1)
    gx = dx + 15
    rect(gx, N_LOT + 40, 200, 205, "#d7d2c8")
    line(gx + 8, N_LOT + 245, gx + 192, N_LOT + 245, "#d7d2c8", 6)  # façade ouverte sur la rue
    line(gx, N_LOT + 245, gx + 200, N_LOT + 245, "#e04f5f", 3, dash=(10, 6))
    text(gx + 100, N_LOT + 68, "garage / atelier", 14, bold=True)
    text(gx + 100, N_LOT + 262, "porte ouverte ↓ vue dégagée", 12, "#7a1d27", True)
    rect(gx + 52, N_LOT + 120, 96, 52, "#f08a2c", rx=20)
    for px, py in ((gx + 48, N_LOT + 112), (gx + 134, N_LOT + 112), (gx + 48, N_LOT + 166), (gx + 134, N_LOT + 166)):
        rect(px, py, 18, 14, "#9b9b9b", sw=1)
    text(gx + 100, N_LOT + 200, "Coccinelle orange", 13, bold=True)
    text(gx + 100, N_LOT + 218, "sur parpaings (Diego + Marco)", 12, "#4a5566")
    hx = dx + 235
    rect(hx, N_LOT + 55, 180, 175, "#cfe0f2")
    text(hx + 90, N_LOT + 140, "Maison de DIEGO", 17, bold=True)

    # Côté sud (côté narrateur)
    lots_s = [
        (X0 + 10, 250, "#d8ecf7", "NARRATEUR", "en face de Jeannot"),
        (X0 + 270, 240, "#ebe7df", "voisin", ""),
        (X0 + 520, 250, "#ebe7df", "voisin", ""),
        (X0 + 780, 250, "#ebe7df", "voisin", ""),
        (X0 + 1040, 410, "#ebe7df", "voisins", "en face de Diego"),
    ]
    for x, w, col, t1, t2 in lots_s:
        rect(x, S_PAVE + 8, w, S_LOT - S_PAVE - 8, "#e9f0dc", stroke="#9aa58a", sw=1)
        rect(x + 20, S_PAVE + 30, w - 40, 165, col)
        text(x + w / 2, S_PAVE + 110, t1, 17, bold=True)
        if t2:
            text(x + w / 2, S_PAVE + 134, t2, 14, "#4a5566")

    # Voitures (échelle : 4L ≈ 3,7 m = 100 px)
    cx4, cy4 = X0 + 110, ROAD_T + 6
    rect(cx4, cy4, 100, 42, "#a8dcc0", stroke="#2c5f47", sw=2, rx=6)
    poly([(cx4 + 100, cy4 + 8), (cx4 + 116, cy4 + 21), (cx4 + 100, cy4 + 34)], "#2c5f47")
    text(cx4 + 50, cy4 + 27, "4L", 16, "#173b2b", True)
    text(cx4 + 8, cy4 + 64, "l'unique 4L, très rouillée — nez vers l'est", 12, "#173b2b", anchor="start")
    ex, ey = hx + 30, ROAD_T + 6
    rect(ex, ey, 118, 46, "#8fa3b8", stroke="#33475c", sw=2, rx=5)
    poly([(ex, ey + 9), (ex - 15, ey + 23), (ex, ey + 37)], "#33475c")
    text(ex + 59, ey + 29, "Estafette", 14, "#16222f", True)
    text(ex + 59, ey + 66, "devant la maison de Diego", 12, "#16222f")

    # Personnages (repères habituels)
    chars = [
        (X0 + 230, N_PAVE + 4, "#f2bf44", "J", "Jeannot"),
        (X0 + 262, N_PAVE + 8, "#b08a5a", "E", "Enji"),
        (X0 + 58, N_LOT + 222, None, "S", ""),
        (sx + 25, sy - 18, "#c9b6e8", "H", "Henri"),
        (gx + 100, N_PAVE + 4, "#5d8fd6", "D", "Diego"),
        (X0 + 135, S_PAVE + 4, "#9fd1ee", "N", "narrateur"),
    ]
    for x, y, col, letter, _ in chars:
        if col:
            circle(x, y, 13, col)
            text(x, y + 5, letter, 14, "#111", True)
    # S dans la tourelle
    circle(X0 + 58, N_LOT + 222, 12, "#7d5cc0")
    text(X0 + 58, N_LOT + 227, "S", 13, "#fff", True)

    # Caméras
    for plan, (x, y, ang, fov, reach, note) in CAMERAS.items():
        a1, a2 = math.radians(ang - fov / 2), math.radians(ang + fov / 2)
        pts = [(x, y), (x + reach * math.cos(a1), y + reach * math.sin(a1)), (x + reach * math.cos(a2), y + reach * math.sin(a2))]
        shapes.append(("poly", dict(pts=pts, fill="#e04f5f", stroke=None, sw=0, opacity=0.13, clip=True)))
        rect(x - 16, y - 11, 26, 22, "#e04f5f", stroke="#7a1d27", rx=3)
        poly([(x + 10, y - 6), (x + 20, y - 11), (x + 20, y + 11), (x + 10, y + 6)], "#7a1d27")
        text(x - 3, y + 38, plan, 15, "#7a1d27", True)

    # Boussole
    text(X0 - 30, (ROAD_T + ROAD_B) / 2 + 5, "O", 20, "#4a5566", True)
    text(X1 + 30, (ROAD_T + ROAD_B) / 2 + 5, "E", 20, "#4a5566", True)

    # Légende
    ly = 895
    text(X0, ly, "Légende :", 16, bold=True, anchor="start")
    items = [("#f2bf44", "J  Jeannot"), ("#7d5cc0", "S  la sorcière (tourelle)"), ("#c9b6e8", "H  Henri"),
             ("#5d8fd6", "D  Diego"), ("#b08a5a", "E  Enji"), ("#9fd1ee", "N  narrateur")]
    for i, (col, lab) in enumerate(items):
        x = X0 + 110 + i * 205
        circle(x, ly - 6, 10, col)
        text(x + 18, ly, lab, 14, anchor="start")
    rect(X0 + 10, ly + 22, 26, 20, "#e04f5f", stroke="#7a1d27", rx=3)
    cams = " · ".join(f"{p} : {c[5]}" for p, c in CAMERAS.items())
    text(X0 + 48, ly + 38, f"Caméra + champ de vision.  {cams}", 14, anchor="start")
    text(X0 + 10, ly + 72, "Règle : les lieux et les voitures ne bougent jamais d'un plan à l'autre ; seule la caméra change de place ou d'axe.",
         14, "#7a1d27", True, anchor="start")


def to_svg():
    def col(c):
        return c if c else "none"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="DejaVu Sans, Arial, sans-serif">',
           f'<defs><clipPath id="zone"><rect x="{X0}" y="{N_LOT}" width="{X1 - X0}" height="{S_LOT - N_LOT}"/></clipPath></defs>']
    for kind, p in shapes:
        if kind == "rect":
            dash = f' stroke-dasharray="{p["dash"][0]} {p["dash"][1]}"' if p["dash"] else ""
            out.append(f'<rect x="{p["x"]:.1f}" y="{p["y"]:.1f}" width="{p["w"]:.1f}" height="{p["h"]:.1f}" rx="{p["rx"]}" '
                       f'fill="{col(p["fill"])}" stroke="{col(p["stroke"])}" stroke-width="{p["sw"]}"{dash}/>')
        elif kind == "circle":
            out.append(f'<circle cx="{p["cx"]:.1f}" cy="{p["cy"]:.1f}" r="{p["r"]}" fill="{col(p["fill"])}" '
                       f'stroke="{col(p["stroke"])}" stroke-width="{p["sw"]}"/>')
        elif kind == "poly":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in p["pts"])
            clip = ' clip-path="url(#zone)"' if p.get("clip") else ""
            out.append(f'<polygon points="{pts}" fill="{col(p["fill"])}" fill-opacity="{p["opacity"]}" '
                       f'stroke="{col(p["stroke"])}" stroke-width="{p["sw"]}"{clip}/>')
        elif kind == "line":
            dash = f' stroke-dasharray="{p["dash"][0]} {p["dash"][1]}"' if p["dash"] else ""
            out.append(f'<line x1="{p["x1"]:.1f}" y1="{p["y1"]:.1f}" x2="{p["x2"]:.1f}" y2="{p["y2"]:.1f}" '
                       f'stroke="{p["stroke"]}" stroke-width="{p["sw"]}"{dash}/>')
        elif kind == "text":
            anchor = {"middle": "middle", "start": "start", "end": "end"}[p["anchor"]]
            s = p["s"].replace("&", "&amp;").replace("<", "&lt;")
            weight = ' font-weight="bold"' if p["bold"] else ""
            out.append(f'<text x="{p["x"]:.1f}" y="{p["y"]:.1f}" font-size="{p["size"]}" fill="{p["fill"]}" '
                       f'text-anchor="{anchor}"{weight}>{s}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def hexrgb(c, a=255):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def to_png(path, scale=2):
    img = Image.new("RGBA", (W * scale, H * scale), (255, 255, 255, 255))
    s = scale
    for kind, p in shapes:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if kind == "rect":
            box = [p["x"] * s, p["y"] * s, (p["x"] + p["w"]) * s, (p["y"] + p["h"]) * s]
            d.rounded_rectangle(box, radius=p["rx"] * s, fill=hexrgb(p["fill"]) if p["fill"] else None,
                                outline=hexrgb(p["stroke"]) if p["stroke"] and not p["dash"] else None,
                                width=int(p["sw"] * s))
            if p["dash"] and p["stroke"]:
                x0, y0, x1, y1 = box
                for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
                    _dashed(d, ax, ay, bx, by, hexrgb(p["stroke"]), int(p["sw"] * s), [v * s for v in p["dash"]])
        elif kind == "circle":
            r = p["r"] * s
            d.ellipse([p["cx"] * s - r, p["cy"] * s - r, p["cx"] * s + r, p["cy"] * s + r],
                      fill=hexrgb(p["fill"]) if p["fill"] else None, outline=hexrgb(p["stroke"]), width=int(p["sw"] * s))
        elif kind == "poly":
            d.polygon([(x * s, y * s) for x, y in p["pts"]], fill=hexrgb(p["fill"], int(255 * p["opacity"])))
            if p.get("clip"):
                mask = Image.new("L", img.size, 0)
                ImageDraw.Draw(mask).rectangle([X0 * s, N_LOT * s, X1 * s, S_LOT * s], fill=255)
                layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", img.size, 0), mask))
        elif kind == "line":
            args = (p["x1"] * s, p["y1"] * s, p["x2"] * s, p["y2"] * s)
            if p["dash"]:
                _dashed(d, *args, hexrgb(p["stroke"]), int(p["sw"] * s), [v * s for v in p["dash"]])
            else:
                d.line(args, fill=hexrgb(p["stroke"]), width=int(p["sw"] * s))
        elif kind == "text":
            f = ImageFont.truetype(FONT_B if p["bold"] else FONT, int(p["size"] * s))
            anchor = {"middle": "ms", "start": "ls", "end": "rs"}[p["anchor"]]
            d.text((p["x"] * s, p["y"] * s), p["s"], font=f, fill=hexrgb(p["fill"]), anchor=anchor)
        img = Image.alpha_composite(img, layer)
    img.convert("RGB").save(path, optimize=True)


def _dashed(d, x1, y1, x2, y2, fill, width, dash):
    length = math.hypot(x2 - x1, y2 - y1)
    if not length:
        return
    on, off = dash
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    t = 0.0
    while t < length:
        e = min(t + on, length)
        d.line((x1 + ux * t, y1 + uy * t, x1 + ux * e, y1 + uy * e), fill=fill, width=width)
        t += on + off


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v1"
    OUT.mkdir(parents=True, exist_ok=True)
    build()
    (OUT / f"carte-rue-{version}.svg").write_text(to_svg(), encoding="utf-8")
    to_png(OUT / f"carte-rue-{version}.png")
    print("ok", OUT / f"carte-rue-{version}.svg", OUT / f"carte-rue-{version}.png")
