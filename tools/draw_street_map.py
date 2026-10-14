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
  python3 tools/draw_street_map.py decrire P01  -> description texte du plan
                                                   (sert de base aux prompts d'images)
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
def _police(nom):
    """Police DejaVu livrée avec le dépôt (assets/fonts) : même rendu sous Linux, Windows et macOS."""
    for p in (ROOT / "assets/fonts" / nom, Path("/usr/share/fonts/truetype/dejavu") / nom):
        if p.exists():
            return str(p)
    return nom  # dernier recours : Pillow la cherche parmi les polices du système


FONT = _police("DejaVuSans.ttf")
FONT_B = _police("DejaVuSans-Bold.ttf")
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
        self.ox = 0  # bord gauche de la vue (négatif si la rue est prolongée vers l'ouest)

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
    c.ox = min(0, L["rue"]["x0"] - 40)
    c.rect(c.ox, 0, W - c.ox, H, "#f4efe4", stroke=None, sw=0)
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
        if b.get("terrasse"):  # terrasse sur le toit
            c.rect(b["x"] + 6, b["y"] + 6, b["w"] - 12, b["h"] - 12, None, stroke="#8a7f6a", sw=1)
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
            n = 9
            vertical = d.get("montee", "est") in ("nord", "sud")
            for i in range(1, n):
                if vertical:
                    c.line(d["x"], d["y"] + i * d["h"] / n, d["x"] + d["w"], d["y"] + i * d["h"] / n, "#6e6658", 1)
                else:
                    c.line(d["x"] + i * d["w"] / n, d["y"], d["x"] + i * d["w"] / n, d["y"] + d["h"], "#6e6658", 1)
            if vertical:
                c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] / 2 - 2, "↑" if d["montee"] == "nord" else "↓", 16, "#3b352b", True)
                c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] / 2 + 13, "monte", 10, "#3b352b", True)
            else:
                c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] / 2 + 5, ("monte →" if d.get("montee", "est") == "est" else "← monte"), 11, "#3b352b", True)
            pa = d.get("palier")
            if pa:
                c.rect(pa["x"], pa["y"], pa["w"], pa["h"], "#d8cfbd", "#33404f", 2)
                c.text(pa["x"] + pa["w"] / 2, pa["y"] + pa["h"] / 2 + 4, "palier", 10, "#3b352b", True)
            if d.get("etiquette", "escalier d'Henri"):
                c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] + 15, d.get("etiquette", "escalier d'Henri"), 12, "#4a5566")
        elif d["type"] == "portail":  # portail (segment) en bas d'un escalier
            c.line(d["x"], d["y"], d["x"] + d.get("w", 0), d["y"] + d.get("h", 0), "#7a4b2a", 5)
            c.text(d["x"] + d.get("w", 0) / 2, d["y"] + d.get("h", 0) + 15, "portail", 10, "#5a3a20", True)
        elif d["type"] == "passage_niveau":
            x, y, w, h = d["x"], d["y"] - 120, d["w"], d["h"] + 240
            c.rect(x, y, w, h, "#b9ab95", stroke=None, sw=0)
            for yy in range(int(y) + 6, int(y + h), 14):
                c.line(x + 4, yy, x + w - 4, yy, "#7a5c3a", 4)
            c.line(x + 12, y, x + 12, y + h, "#4b4f55", 3)
            c.line(x + w - 12, y, x + w - 12, y + h, "#4b4f55", 3)
            for by in (r["chaussee_haut"] - 6, r["chaussee_bas"] + 6):
                c.line(x - 4, by, x - 4 - 34, by, "#d9363e", 6)
            c.text(1596, y - 24, "passage", 12, "#7a1d27", True, anchor="end")
            c.text(1596, y - 9, "à niveau", 12, "#7a1d27", True, anchor="end")
            c.text(1596, y + h + 16, "puis descente,", 11, "#4a5566", anchor="end")
            c.text(1596, y + h + 30, "collines au fond", 11, "#4a5566", anchor="end")
        elif d["type"] == "terre_plein":  # jardin surélevé, tenu par un mur
            c.rect(d["x"], d["y"], d["w"], d["h"], "#cfe3b4", stroke="#6f8a52", sw=2)
            c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] / 2 - 2, "jardin", 12, "#3f5a2a", True)
            c.text(d["x"] + d["w"] / 2, d["y"] + d["h"] / 2 + 13, "surélevé", 10, "#4a5566")
        elif d["type"] == "grillage":  # clôture grillagée (segment)
            c.line(d["x"], d["y"], d["x"] + d.get("w", 0), d["y"] + d["h"], "#3d4652", 3, dash=(7, 4))
            c.text(d["x"] + 6, mid - 34, "grillage (cul-de-sac)", 11, "#2b323b", True, anchor="start")
        elif d["type"] == "colline":  # colline boisée qui monte au-delà du bord ouest
            x0 = c.ox
            c.rect(x0, d["y"], d["x"] - x0, d["h"], "#7f9c66", stroke=None, sw=0)
            for i, yy in enumerate(range(int(d["y"]) + 14, int(d["y"] + d["h"]), 26)):
                c.circle((x0 + d["x"]) / 2 + (4 if i % 2 else -4), yy, 7, "#557a43", stroke="#3d5a2f", sw=1)
            c.text((x0 + d["x"]) / 2, d["y"] + 40, "forêt", 10, "#1f3316", True)
    c.text(r["x0"] - 30, mid + 5, "O", 20, "#4a5566", True)
    c.text(1592, 100, "E →", 16, "#4a5566", True, anchor="end")


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
            lab = pose_label(e)
            if lab:
                c.text(x, y + 30, lab, 11, "#1b2430", True)


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


def pose_label(e, court=True):
    """Pose (si autre que « debout ») et action d'un personnage."""
    pose = e.get("pose", "")
    action = e.get("action", "")
    parts = [pose] if pose and (pose != "debout" or not court) else []
    if action:
        parts.append(action[:28] + ("…" if court and len(action) > 28 else "") if court else action)
    return " · ".join(parts)


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
        box = (c.ox, 90, W, 870)
        c.poly(pts, col, opacity=0.14, clip=box)
        c.line(*pts[0], *clip_seg(*pts[0], *pts[1], box), col, 2, dash=(6, 5))
        c.line(*pts[0], *clip_seg(*pts[0], *pts[2], box), col, 2, dash=(6, 5))
    if len(cams) == 2:
        c.line(cams[0]["x"], cams[0]["y"], cams[1]["x"], cams[1]["y"], "#2f7fd8", 3, dash=(4, 4))
    for i, cam in enumerate(cams):
        col = CAM_COLORS[i % 2]
        x, y, a = cam["x"], cam["y"], cam["angle"]
        c.poly(rot_pts(x, y, [(-16, -11), (10, -11), (10, 11), (-16, 11)], a), col)
        c.poly(rot_pts(x, y, [(10, -6), (21, -12), (21, 12), (10, 6)], a), "#1b2430")
        c.text(x, y + 34, ("début" if i == 0 else "fin") if len(cams) == 2 else label, 13, col, True)


def dans_le_champ(L, placement, cam_index=0):
    """Liste ce que voit la caméra : [(distance, côté, nom, au_dela_de_la_portee)]."""
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
            if dist < 1:
                continue
            diff = (math.degrees(math.atan2(dy, dx)) - cam["angle"] + 540) % 360 - 180
            if abs(diff) <= cam["fov"] / 2 and (best is None or dist < best[0]):
                side = "au centre" if abs(diff) <= cam["fov"] / 8 else ("à gauche" if diff < 0 else "à droite")
                fwd = dx * math.cos(math.radians(cam["angle"])) + dy * math.sin(math.radians(cam["angle"]))
                best = (dist, side, nom, fwd > portee_px(cam))
        if best:
            out.append(best)
    return sorted(out)


def portee_px(cam):
    """Portée = longueur du cône : net jusqu'au bord du fond du cône (profondeur devant la caméra, en px de carte)."""
    return cam.get("portee", 1300) * math.cos(math.radians(cam["fov"] / 2))


def sur_escalier(L, x, y):
    """(texte, hauteur en m) si le point est sur un escalier extérieur ou son palier, sinon None."""
    for d in L["details"]:
        if d["type"] == "tourelle" and d.get("balcon") and (x - d["x"]) ** 2 + (y - d["y"]) ** 2 <= (d["r"] + 4) ** 2:
            return f"au balcon de la {d['nom']} (à {d['balcon']:.1f} m du sol)".replace(".", ",", 1), float(d["balcon"])
        if d["type"] != "escalier":
            continue
        hmax = d.get("hauteur", 2.8)
        pa = d.get("palier")
        if pa and pa["x"] - 3 <= x <= pa["x"] + pa["w"] + 3 and pa["y"] - 3 <= y <= pa["y"] + pa["h"] + 3:
            return f"sur le palier en haut de l'{d['nom']} (à {hmax:.1f} m du sol, devant la porte du 1er étage)".replace(".", ",", 1), hmax
        mo = d.get("montee", "est")
        if mo in ("nord", "sud"):
            dedans = d["x"] - 3 <= x <= d["x"] + d["w"] + 3 and d["y"] <= y <= d["y"] + d["h"]
            f = ((d["y"] + d["h"] - y) if mo == "nord" else (y - d["y"])) / d["h"]
        else:
            dedans = d["x"] <= x <= d["x"] + d["w"] and d["y"] - 3 <= y <= d["y"] + d["h"] + 3
            f = (x - d["x"]) / d["w"] if mo == "est" else (d["x"] + d["w"] - x) / d["w"]
        if dedans:
            quand = "en bas de" if f < 0.25 else ("presque en haut de" if f > 0.75 else "au milieu de")
            return f"{quand} l'{d['nom']} (à {f * hmax:.1f} m du sol)".replace(".", ",", 1), f * hmax
    return None


def _ou(L, x, y):
    """Décrit un point de la carte en mots."""
    esc = sur_escalier(L, x, y)
    if esc:
        return esc[0]
    r = L["rue"]
    if y < r["nord_trottoir"] or y > r["sud_trottoir"]:
        cote = "côté Jeannot" if y < r["nord_trottoir"] else "côté narrateur"
        for b in L["batiments"]:
            if b["x"] - 12 <= x <= b["x"] + b["w"] + 12 and ((y < 495) == (b["y"] < 495)):
                nom = nom_lieu(b["nom"], b["y"] + b["h"] / 2)
                if b["y"] <= y <= b["y"] + b["h"]:
                    return f"dans/contre {nom} ({cote})"
                return f"devant {nom}, dans la cour/le jardin ({cote})"
        return f"parcelle {cote}"
    if y < r["chaussee_haut"]:
        zone = "sur le trottoir côté Jeannot"
    elif y > r["chaussee_bas"]:
        zone = "sur le trottoir côté narrateur"
    elif y < r["chaussee_haut"] + 40:
        zone = "sur la chaussée contre le trottoir côté Jeannot"
    elif y > r["chaussee_bas"] - 40:
        zone = "sur la chaussée contre le trottoir côté narrateur"
    else:
        zone = "au milieu de la chaussée"
    if x < L["batiments"][0]["x"] + 40:
        return f"{zone}, tout au bout ouest de la rue (bout de Jeannot)"
    if x > r["x1"] - 40:
        return f"{zone}, tout au bout est de la rue (vers le passage à niveau)"
    north = [b for b in L["batiments"] if b["y"] < 495]
    near = min(north, key=lambda b: abs(b["x"] + b["w"] / 2 - x))
    return f"{zone}, à hauteur de {nom_lieu(near['nom'], near['y'] + near['h'] / 2)}"


def _vu(cam, x, y, ang, vehicule):
    """Comment la caméra voit un élément orienté (de face, de dos, de profil)."""
    to = math.degrees(math.atan2(y - cam["y"], x - cam["x"]))
    diff = (ang - to + 540) % 360 - 180
    if abs(diff) <= 45:
        return "vue de derrière" if vehicule else "de dos"
    if abs(diff) >= 135:
        return "vue de face (l'avant vers la caméra)" if vehicule else "de face"
    side = "droite" if diff > 0 else "gauche"
    return f"vue de profil, l'avant vers la {side} de l'image" if vehicule else f"de profil, tourné vers la {side} de l'image"


def decrire(L, placement):
    cat = {e["id"]: e for e in L["catalogue"]}
    cams = placement.get("cameras", [])
    lines = []
    dirs = {0: "l'est (vers le bout de Diego)", 90: "le sud (vers le côté narrateur)", 180: "l'ouest (vers le bout de Jeannot)", -90: "le nord (vers le côté Jeannot)"}
    for i, cam in enumerate(cams):
        nom = ("Caméra de début" if i == 0 else "Caméra de fin") if len(cams) == 2 else "Caméra"
        a = (cam["angle"] + 180) % 360 - 180
        best = min(dirs, key=lambda k: abs((a - k + 540) % 360 - 180))
        ecart = (a - best + 540) % 360 - 180
        prec = "" if abs(ecart) < 8 else f" (décalée de {abs(round(ecart))}° vers le {'sud' if ecart > 0 else 'nord'})" if best in (0, 180) else f" (décalée de {abs(round(ecart))}°)"
        lines.append(f"{nom} : {_ou(L, cam['x'], cam['y'])} ; regarde vers {dirs[best]}{prec} ; angle de vue {cam['fov']:.0f}° ; {cam.get('hauteur', '')}.")
        champ = dans_le_champ(L, placement, i)
        import calque  # noqa: E402  (import tardif : calque importe ce module)
        occ = calque.occultations(L, placement, i)
        for titre, lo, hi in (("Premier plan", 0, 300), ("Plan moyen", 300, 800), ("Fond", 800, 99999)):
            items = [f"{n} ({sd})" for dist, sd, n, loin in champ if lo <= dist < hi and not loin]
            lines.append(f"  {titre} : {', '.join(items) if items else '—'}")
        loins = [f"{n} ({sd})" for dist, sd, n, loin in champ if loin]
        if loins:
            lines.append(f"  Au-delà de la portée ({portee_px(cam) * 0.037:.0f} m) — flou, dans la brume : {', '.join(loins)}")
        for eid, e in placement.get("elements", {}).items():
            if not e.get("visible", True) or eid not in cat:
                continue
            if any(n == cat[eid]["nom"] for _, _, n, _ in champ):
                k = cat[eid]
                loin = any(n == k["nom"] and lo for _, _, n, lo in champ)
                lines.append(f"  - {k['nom']} : {_ou(L, e['x'], e['y'])} ; {_vu(cam, e['x'], e['y'], e.get('angle', 0), k['type'] == 'vehicule')}"
                             + (f" ; pose : {e['pose']}" if e.get("pose") else "")
                             + (f" ; action : {e['action']}" if e.get("action") else "")
                             + (" ; flou (au-delà de la portée)" if loin else "")
                             + (f" ; ⚠ {'CACHÉ' if occ[eid][0] >= 0.7 else 'en partie caché'} par {occ[eid][1]} (≈ {occ[eid][0] * 100:.0f} %)" if eid in occ else "") + ".")
    hors = [cat[eid]["nom"] for eid, e in placement.get("elements", {}).items()
            if e.get("visible", True) and eid in cat and not any(n == cat[eid]["nom"] for c in range(len(cams)) for _, _, n, _ in dans_le_champ(L, placement, c))]
    if hors:
        lines.append("Présents dans la scène mais hors champ : " + ", ".join(hors) + ".")
    for d in L["details"]:
        if d.get("apres") and any(n == d["nom"] for c in range(len(cams)) for _, _, n, _ in dans_le_champ(L, placement, c)):
            etat = f" — {d['etat']}" if d.get("etat") else ""
            lines.append(f"Au bout de la rue : {d['nom']}{etat} ; {d['apres']}.")
    if placement.get("note"):
        lines.append("Note de l'utilisateur : " + placement["note"])
    lines.append(f"(carte du plan rév. {placement.get('rev', '?')}, lieux rév. {L.get('rev', 1)})")
    return "\n".join(lines)


def build(L, placement, titre, sous_titre="", legend_extra="", label="P"):
    W, H = L["taille"]
    c = Canvas(W, H)
    draw_base(c, L)
    draw_elements(c, L, placement)
    draw_cameras(c, L, placement, label)
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
        info = f"Caméra : {cam.get('hauteur', '')}, angle de vue {cam.get('fov', 0):.0f}°. " + info
    c.text(70, ly + 36, info[:170], 14, anchor="start")
    c.text(70, ly + 70, "Règle : les lieux ne bougent jamais ; véhicules et personnages restent en place sauf action prévue dans le plan.",
           14, "#7a1d27", True, anchor="start")
    return c


# --------------------------------------------------------------------------- export
def to_svg(c):
    def col(v):
        return v if v else "none"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{c.w - c.ox}" height="{c.h}" viewBox="{c.ox} 0 {c.w - c.ox} {c.h}" '
           f'font-family="DejaVu Sans, Arial, sans-serif">', f'<defs><clipPath id="zone"><rect x="{c.ox}" y="90" width="{c.w - c.ox}" height="780"/></clipPath></defs>']
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


def _decale(c):
    """Formes décalées de -ox en x (rue prolongée vers l'ouest : x négatifs)."""
    ox = getattr(c, "ox", 0)
    if not ox:
        return c.w, c.shapes
    out = []
    for kind, p in c.shapes:
        q = dict(p)
        for k in ("x", "cx", "x1", "x2"):
            if k in q:
                q[k] = q[k] - ox
        if "pts" in q:
            q["pts"] = [(x - ox, y) for x, y in q["pts"]]
        if q.get("clip"):
            x0, y0, x1, y1 = q["clip"]
            q["clip"] = (x0 - ox, y0, x1 - ox, y1)
        out.append((kind, q))
    return c.w - ox, out


def to_png(c, path, s=2):
    cw, shapes = _decale(c)
    img = Image.new("RGBA", (int(cw * s), c.h * s), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    for kind, p in shapes:
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
    vu = ", ".join(f"{n} ({s}{', flou' if lo else ''})" for _, s, n, lo in champ[:8])
    titre = f"Plan {plan_id}" + (f" — {meta['temps']}" if meta else "") + f"  (rév. {placement.get('rev', 1)})"
    sous = meta["paroles"] if meta else ""
    c = build(L, placement, titre, sous, legend_extra=("Dans le champ : " + vu) if vu else "", label=plan_id)
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
    elif args[0] == "decrire":
        plans = load_plans()
        for pid in [a.upper() for a in args[1:]]:
            print(f"== {pid}")
            print(decrire(L, plans[pid]))
    elif args[0] in ("plan", "tous"):
        plans, meta = load_plans(), plan_meta()
        ids = list(plans) if args[0] == "tous" else [a.upper() for a in args[1:]]
        for pid in ids:
            print("ok", render_plan(pid, L, plans, meta.get(pid)))
