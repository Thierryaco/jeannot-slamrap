#!/usr/bin/env python3
"""Carte de la rue (vue de dessus) — référence de cohérence des lieux.

Données :
  - assets/storyboards/a-valider/carte/lieux.json : rue, maisons, détails fixes,
    catalogue des personnages/véhicules et placement par défaut.
  - assets/storyboards/a-valider/carte/plans.json : placement par plan
    (caméra(s), personnages, véhicules, note), édité dans storyboard/carte.html.

Sorties (SVG + PNG identiques) :
  python3 tools/draw_street_map.py base v3      -> carte/carte-rue-v3.{svg,png}
  python3 tools/draw_street_map.py plan P01     -> carte/plans/p01.{svg,png}
  python3 tools/draw_street_map.py tous         -> toutes les cartes de plans
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CARTE = ROOT / "assets/storyboards/a-valider/carte"
LIEUX = CARTE / "lieux.json"
PLANS = CARTE / "plans.json"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CAM_COLORS = ["#e04f5f", "#2f7fd8"]


def load_lieux():
    return json.loads(LIEUX.read_text(encoding="utf-8"))


def load_plans():
    if PLANS.exists():
        return json.loads(PLANS.read_text(encoding="utf-8"))
    return {}


# --------------------------------------------------------------------------- formes
class Canvas:
    def __init__(self, w, h):
        self.w, self.h, self.shapes = w, h, []

    def rect(self, x, y, w, h, fill, stroke="#33404f", sw=2, rx=0, dash=None, rot=None):
        self.shapes.append(("rect", dict(x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, rx=rx, dash=dash, rot=rot)))

    def circle(self, cx, cy, r, fill, stroke="#1b2430", sw=2):
        self.shapes.append(("circle", dict(cx=cx, cy=cy, r=r, fill=fill, stroke=stroke, sw=sw)))

    def poly(self, pts, fill, opacity=1.0, clip=None):
        self.shapes.append(("poly", dict(pts=pts, fill=fill, opacity=opacity, clip=clip)))

    def line(self, x1, y1, x2, y2, stroke, sw=2, dash=None):
        self.shapes.append(("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, sw=sw, dash=dash)))

    def text(self, x, y, s, size=16, fill="#1b2430", bold=False, anchor="middle"):
        self.shapes.append(("text", dict(x=x, y=y, s=s, size=size, fill=fill, bold=bold, anchor=anchor)))


def rot_pts(cx, cy, pts, ang):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + px * ca - py * sa, cy + px * sa + py * ca) for px, py in pts]


# --------------------------------------------------------------------------- dessin
def draw_base(c, L):
    r = L["rue"]
    W, H = L["taille"]
    c.rect(0, 0, W, H, "#f4efe4", stroke=None, sw=0)
    c.rect(r["x0"], r["nord_trottoir"], r["x1"] - r["x0"], r["chaussee_haut"] - r["nord_trottoir"], "#d9d4ca", sw=1)
    c.rect(r["x0"], r["chaussee_haut"], r["x1"] - r["x0"], r["chaussee_bas"] - r["chaussee_haut"], "#8e939a", sw=1)
    c.rect(r["x0"], r["chaussee_bas"], r["x1"] - r["x0"], r["sud_trottoir"] - r["chaussee_bas"], "#d9d4ca", sw=1)
    mid = (r["chaussee_haut"] + r["chaussee_bas"]) / 2
    c.line(r["x0"] + 20, mid, r["x1"] - 20, mid, "#e8e8e8", 2, dash=(18, 16))
    c.text(820, mid + 30, "RUE (une seule rue pour tout le clip)", 15, "#f1f1f1", True)
    for p in L["parcelles"]:
        c.rect(p["x"], p["y"], p["w"], p["h"], "#e9f0dc", stroke="#9aa58a", sw=1)
    for b in L["batiments"]:
        c.rect(b["x"], b["y"], b["w"], b["h"], b["couleur"])
        cy = b["y"] + b["h"] / 2
        if b.get("ouverture") == "sud":
            c.line(b["x"] + 10, b["y"] + b["h"], b["x"] + b["w"] - 10, b["y"] + b["h"], b["couleur"], 6)
            c.line(b["x"], b["y"] + b["h"], b["x"] + b["w"], b["y"] + b["h"], "#e04f5f", 3, dash=(10, 6))
            cy = b["y"] + 28
        c.text(b["x"] + b["w"] / 2, cy, b["nom"], 17 if b["w"] > 150 else 14, bold=True)
        if b.get("sous"):
            c.text(b["x"] + b["w"] / 2, cy + 22, b["sous"], 13, "#4a5566")
    for d in L["details"]:
        if d["type"] == "tourelle":
            c.circle(d["x"], d["y"], d["r"], "#c9b6e8")
            c.text(d["x"] + 22, d["y"] - d["r"] - 8, "tourelle", 12, "#5b3f8c", anchor="start")
        elif d["type"] == "escalier":
            c.rect(d["x"], d["y"], d["w"], d["h"], "#bfb7a8")
            for i in range(1, 6):
                c.line(d["x"] + i * d["w"] / 6, d["y"], d["x"] + i * d["w"] / 6, d["y"] + d["h"], "#6e6658", 1)
            c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] + 16, "escalier ext.", 12, "#4a5566")
    c.text(r["x0"] - 30, mid + 5, "O", 20, "#4a5566", True)
    c.text(r["x1"] + 30, mid + 5, "E", 20, "#4a5566", True)


def draw_elements(c, L, placement):
    cat = {e["id"]: e for e in L["catalogue"]}
    els = placement.get("elements", {})
    # véhicules d'abord, personnages au-dessus
    order = sorted(els.items(), key=lambda kv: 0 if cat.get(kv[0], {}).get("type") == "vehicule" else 1)
    for eid, e in order:
        if not e.get("visible", True) or eid not in cat:
            continue
        k = cat[eid]
        x, y, a = e["x"], e["y"], e.get("angle", 0)
        if k["type"] == "vehicule":
            w, h = k["w"], k["h"]
            c.poly(rot_pts(x, y, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], a), k["contour"])
            c.poly(rot_pts(x, y, [(-w / 2 + 3, -h / 2 + 3), (w / 2 - 3, -h / 2 + 3), (w / 2 - 3, h / 2 - 3), (-w / 2 + 3, h / 2 - 3)], a), k["couleur"])
            c.poly(rot_pts(x, y, [(w / 2 - 2, -h / 2 + 8), (w / 2 + 16, 0), (w / 2 - 2, h / 2 - 8)], a), k["contour"])
            c.text(x, y + 5, k["lettre"], 14, "#111", True)
        else:
            c.poly(rot_pts(x, y, [(10, -8), (26, 0), (10, 8)], a), "#1b2430")
            c.circle(x, y, 13, k["couleur"])
            c.text(x, y + 5, k["lettre"], 14, "#fff" if k["lettre"] == "S" else "#111", True)


def cone(cam):
    x, y, ang, fov, reach = cam["x"], cam["y"], cam["angle"], cam["fov"], cam["portee"]
    a1, a2 = math.radians(ang - fov / 2), math.radians(ang + fov / 2)
    return [(x, y), (x + reach * math.cos(a1), y + reach * math.sin(a1)), (x + reach * math.cos(a2), y + reach * math.sin(a2))]


def clip_seg(x0, y0, x1, y1, box=(0, 90, 1600, 870)):
    """Raccourcit le segment (x0,y0)->(x1,y1) à l'intérieur de la zone de carte."""
    t = 1.0
    bx0, by0, bx1, by1 = box
    for v0, v1, lo, hi in ((x0, x1, bx0, bx1), (y0, y1, by0, by1)):
        if v1 != v0:
            for lim in (lo, hi):
                tt = (lim - v0) / (v1 - v0)
                if 0 < tt < t and not (lo <= v1 <= hi):
                    t = tt
    return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t


def nom_lieu(nom, y):
    if nom.lower().startswith("voisin"):
        return f"{nom} ({'côté Jeannot' if y < 495 else 'côté narrateur'})"
    return nom.lower() if nom.isupper() else nom


def draw_cameras(c, L, placement, label="P"):
    W, H = L["taille"]
    cams = placement.get("cameras", [])
    for i, cam in enumerate(cams):
        col = CAM_COLORS[i % 2]
        pts = cone(cam)
        c.poly(pts, col, opacity=0.14, clip=(0, 90, W, 870))
        c.line(*pts[0], *clip_seg(*pts[0], *pts[1]), col, 2, dash=(6, 5))
        c.line(*pts[0], *clip_seg(*pts[0], *pts[2]), col, 2, dash=(6, 5))
    if len(cams) == 2:
        c.line(cams[0]["x"], cams[0]["y"], cams[1]["x"], cams[1]["y"], "#2f7fd8", 3, dash=(4, 4))
    for i, cam in enumerate(cams):
        col = CAM_COLORS[i % 2]
        x, y, a = cam["x"], cam["y"], cam["angle"]
        c.poly(rot_pts(x, y, [(-16, -11), (10, -11), (10, 11), (-16, 11)], a), col)
        c.poly(rot_pts(x, y, [(10, -6), (21, -12), (21, 12), (10, 6)], a), "#1b2430")
        c.text(x, y + 34, ("début" if i == 0 else "fin") if len(cams) == 2 else label, 13, col, True)


def dans_le_champ(L, placement, cam_index=0):
    """Liste ce que voit la caméra : [(distance, côté, nom)]."""
    cams = placement.get("cameras", [])
    if len(cams) <= cam_index:
        return []
    cam = cams[cam_index]
    cat = {e["id"]: e for e in L["catalogue"]}
    pts = []  # (nom, [points échantillons])
    for b in L["batiments"]:
        x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
        samples = [((x0 + x1) / 2, (y0 + y1) / 2)] + [(x0 + (x1 - x0) * f, yy) for yy in (y0, y1) for f in (0, .25, .5, .75, 1)]
        pts.append((nom_lieu(b["nom"], (y0 + y1) / 2), samples))
    for d in L["details"]:
        pts.append((d["nom"], [(d["x"] + d.get("w", 0) / 2, d["y"] + d.get("h", 0) / 2)]))
    for eid, e in placement.get("elements", {}).items():
        if e.get("visible", True) and eid in cat:
            pts.append((cat[eid]["nom"], [(e["x"], e["y"])]))
    out = []
    for nom, samples in pts:
        best = None
        for px, py in samples:
            dx, dy = px - cam["x"], py - cam["y"]
            dist = math.hypot(dx, dy)
            if dist < 1 or dist > cam["portee"]:
                continue
            diff = (math.degrees(math.atan2(dy, dx)) - cam["angle"] + 540) % 360 - 180
            if abs(diff) <= cam["fov"] / 2 and (best is None or dist < best[0]):
                side = "au centre" if abs(diff) <= cam["fov"] / 8 else ("à gauche" if diff < 0 else "à droite")
                best = (dist, side, nom)
        if best:
            out.append(best)
    return sorted(out)


def build(L, placement, titre, sous_titre="", legend_extra=""):
    W, H = L["taille"]
    c = Canvas(W, H)
    draw_base(c, L)
    draw_elements(c, L, placement)
    draw_cameras(c, L, placement)
    c.text(W / 2, 42, titre, 26, bold=True)
    c.text(W / 2, 72, sous_titre or "Ouest = bout de Jeannot  ·  Est = bout de Diego  ·  nord = côté Jeannot  ·  sud = côté narrateur", 15, "#4a5566")
    ly = 895
    cat = [e for e in L["catalogue"] if e["type"] == "perso"]
    c.text(70, ly, "Légende :", 16, bold=True, anchor="start")
    for i, k in enumerate(cat):
        x = 180 + i * 190
        c.circle(x, ly - 6, 10, k["couleur"])
        c.text(x + 17, ly, f"{k['lettre']}  {k['nom']}", 14, anchor="start")
    cam = placement.get("cameras", [{}])[0]
    info = legend_extra
    if cam:
        info = f"Caméra : {cam.get('hauteur', '')}, angle de vue {cam.get('fov', '?')}°. " + info
    c.text(70, ly + 36, info[:170], 14, anchor="start")
    c.text(70, ly + 70, "Règle : les lieux ne bougent jamais ; véhicules et personnages restent en place sauf action prévue dans le plan.",
           14, "#7a1d27", True, anchor="start")
    return c


# --------------------------------------------------------------------------- export
def to_svg(c):
    def col(v):
        return v if v else "none"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{c.w}" height="{c.h}" viewBox="0 0 {c.w} {c.h}" '
           f'font-family="DejaVu Sans, Arial, sans-serif">', '<defs><clipPath id="zone"><rect x="0" y="90" width="1600" height="780"/></clipPath></defs>']
    for kind, p in c.shapes:
        if kind == "rect":
            dash = f' stroke-dasharray="{p["dash"][0]} {p["dash"][1]}"' if p["dash"] else ""
            out.append(f'<rect x="{p["x"]:.1f}" y="{p["y"]:.1f}" width="{p["w"]:.1f}" height="{p["h"]:.1f}" rx="{p["rx"]}" '
                       f'fill="{col(p["fill"])}" stroke="{col(p["stroke"])}" stroke-width="{p["sw"]}"{dash}/>')
        elif kind == "circle":
            out.append(f'<circle cx="{p["cx"]:.1f}" cy="{p["cy"]:.1f}" r="{p["r"]}" fill="{col(p["fill"])}" '
                       f'stroke="{col(p["stroke"])}" stroke-width="{p["sw"]}"/>')
        elif kind == "poly":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in p["pts"])
            clip = ' clip-path="url(#zone)"' if p["clip"] else ""
            out.append(f'<polygon points="{pts}" fill="{p["fill"]}" fill-opacity="{p["opacity"]}"{clip}/>')
        elif kind == "line":
            dash = f' stroke-dasharray="{p["dash"][0]} {p["dash"][1]}"' if p["dash"] else ""
            out.append(f'<line x1="{p["x1"]:.1f}" y1="{p["y1"]:.1f}" x2="{p["x2"]:.1f}" y2="{p["y2"]:.1f}" '
                       f'stroke="{p["stroke"]}" stroke-width="{p["sw"]}"{dash}/>')
        elif kind == "text":
            s = p["s"].replace("&", "&amp;").replace("<", "&lt;")
            weight = ' font-weight="bold"' if p["bold"] else ""
            out.append(f'<text x="{p["x"]:.1f}" y="{p["y"]:.1f}" font-size="{p["size"]}" fill="{p["fill"]}" '
                       f'text-anchor="{p["anchor"]}"{weight}>{s}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def hexrgb(v, a=255):
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


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


def to_png(c, path, s=2):
    img = Image.new("RGBA", (c.w * s, c.h * s), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    for kind, p in c.shapes:
        if kind == "poly" and p["opacity"] < 1:
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).polygon([(x * s, y * s) for x, y in p["pts"]], fill=hexrgb(p["fill"], int(255 * p["opacity"])))
            if p["clip"]:
                x0, y0, x1, y1 = p["clip"]
                mask = Image.new("L", img.size, 0)
                ImageDraw.Draw(mask).rectangle([x0 * s, y0 * s, x1 * s, y1 * s], fill=255)
                layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", img.size, 0), mask))
            img = Image.alpha_composite(img, layer)
            d = ImageDraw.Draw(img)
        elif kind == "poly":
            d.polygon([(x * s, y * s) for x, y in p["pts"]], fill=hexrgb(p["fill"]))
        elif kind == "rect":
            box = [p["x"] * s, p["y"] * s, (p["x"] + p["w"]) * s, (p["y"] + p["h"]) * s]
            d.rounded_rectangle(box, radius=p["rx"] * s, fill=hexrgb(p["fill"]) if p["fill"] else None,
                                outline=hexrgb(p["stroke"]) if p["stroke"] and not p["dash"] else None, width=int(p["sw"] * s))
        elif kind == "circle":
            r = p["r"] * s
            d.ellipse([p["cx"] * s - r, p["cy"] * s - r, p["cx"] * s + r, p["cy"] * s + r],
                      fill=hexrgb(p["fill"]) if p["fill"] else None, outline=hexrgb(p["stroke"]), width=int(p["sw"] * s))
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
    img.convert("RGB").save(path, optimize=True)


def render_plan(plan_id, L=None, plans=None, meta=None):
    L = L or load_lieux()
    plans = plans if plans is not None else load_plans()
    placement = plans[plan_id]
    out = CARTE / "plans"
    out.mkdir(parents=True, exist_ok=True)
    champ = dans_le_champ(L, placement)
    vu = ", ".join(f"{n} ({s})" for _, s, n in champ[:8])
    titre = f"Plan {plan_id}" + (f" — {meta['temps']}" if meta else "")
    sous = meta["paroles"] if meta else ""
    c = build(L, placement, titre, sous, legend_extra=("Dans le champ : " + vu) if vu else "")
    (out / f"{plan_id.lower()}.svg").write_text(to_svg(c), encoding="utf-8")
    to_png(c, out / f"{plan_id.lower()}.png")
    return out / f"{plan_id.lower()}.png"


def plan_meta():
    man = json.loads((ROOT / "assets/storyboards/a-valider/options.json").read_text(encoding="utf-8"))
    return {p["plan"]: p for p in man["plans"]}


if __name__ == "__main__":
    args = sys.argv[1:] or ["base", "v3"]
    L = load_lieux()
    if args[0] == "base":
        version = args[1] if len(args) > 1 else "v3"
        c = build(L, L["defaut"], "Carte de la rue — vue de dessus (référence des lieux)")
        (CARTE / f"carte-rue-{version}.svg").write_text(to_svg(c), encoding="utf-8")
        to_png(c, CARTE / f"carte-rue-{version}.png")
        print("ok", CARTE / f"carte-rue-{version}.png")
    elif args[0] in ("plan", "tous"):
        plans, meta = load_plans(), plan_meta()
        ids = list(plans) if args[0] == "tous" else [a.upper() for a in args[1:]]
        for pid in ids:
            print("ok", render_plan(pid, L, plans, meta.get(pid)))
