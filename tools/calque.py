#!/usr/bin/env python3
"""Calque de perspective : projette la carte d'un plan dans l'image 16:9 vue par sa caméra.

Sert à vérifier/forcer la corrélation entre la carte (vue de dessus) et l'image générée :
le calque montre où doit se trouver chaque élément (position, taille, sens) dans l'image.

  python3 tools/calque.py P01                     -> carte/plans/p01-calque.png (transparent)
  python3 tools/calque.py P01 --sur image.png out.png   -> calque superposé sur une image
  python3 tools/calque.py P01 --texte              -> positions attendues dans l'image (pour les prompts)

Conventions : 1 px de carte = 0,037 m (100 px ≈ 3,7 m) ; image 1920x1080 ; caméra à la position,
direction et angle de vue (horizontal) de la carte ; hauteur selon le réglage « Hauteur ».
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw_street_map as dsm  # noqa: E402

M = 0.037          # mètres par px de carte
W, H = 1920, 1080
NEAR = 0.6         # m
FONT = dsm.FONT
FONT_B = dsm.FONT_B

# hauteur de l'œil (m) et inclinaison (degrés, + vers le haut) selon le réglage de la carte
HAUTEURS = {
    "à hauteur d'yeux": (1.6, 0.0),
    "plongée (vue d'en haut)": (4.5, -14.0),
    "contre-plongée (vue d'en bas)": (0.6, 12.0),
    "vue aérienne / drone": (18.0, -38.0),
    "au ras du sol": (0.3, 2.0),
}
# hauteurs des bâtiments (m)
H_BAT = {"garage-diego": 3.3}
H_MAISON = 6.8
# véhicules : hauteur (m)
H_VEH = {"4l": 1.55, "estafette": 1.95, "coccinelle": 1.7}
# personnages : hauteur debout (m) et facteur selon la pose
H_PERSO = 1.75
H_CHIEN = 0.62
POSE_F = {"debout": 1, "marche": 1, "court": .95, "assis": .72, "accroupi": .6, "couché": .3,
          "appuyé": 1, "penché": .85, "tombe": .6, "saute": 1.1, "renifle": .75, "aboie": 1, "dort": .45}
POSE_CHIEN = {"assis": 1.15, "couché": .55, "dort": .5, "renifle": .8}


class Cam:
    def __init__(self, c):
        self.x, self.y = c["x"], c["y"]
        a = math.radians(c.get("angle", 0))
        self.fx, self.fy = math.cos(a), math.sin(a)        # vers l'avant (carte)
        self.rx, self.ry = -math.sin(a), math.cos(a)       # vers la droite de l'image
        self.eye, pitch = HAUTEURS.get(c.get("hauteur", ""), (1.6, 0.0))
        if c.get("oeil") is not None:  # hauteur d'œil précise (m), prioritaire sur le préréglage
            self.eye = float(c["oeil"])
        if c.get("inclinaison") is not None:  # inclinaison précise (°, négatif = vers le bas)
            pitch = float(c["inclinaison"])
        self.p = math.radians(pitch)
        self.F = (W / 2) / math.tan(math.radians(c.get("fov", 60)) / 2)

    def cam(self, mx, my, h):
        dx, dy = (mx - self.x) * M, (my - self.y) * M
        f = dx * self.fx + dy * self.fy
        r = dx * self.rx + dy * self.ry
        u = h - self.eye
        z = f * math.cos(self.p) + u * math.sin(self.p)
        y = -f * math.sin(self.p) + u * math.cos(self.p)
        return r, y, z

    def proj_c(self, r, y, z):
        return (W / 2 + self.F * r / z, H / 2 - self.F * y / z)

    def proj(self, mx, my, h=0.0):
        r, y, z = self.cam(mx, my, h)
        return self.proj_c(r, y, z) if z > NEAR else None

    def seg(self, a, b):
        """Segment 3D (carte) -> segment image, coupé au plan proche."""
        A, B = self.cam(*a), self.cam(*b)
        if A[2] < NEAR and B[2] < NEAR:
            return None
        if A[2] < NEAR or B[2] < NEAR:
            t = (NEAR - A[2]) / (B[2] - A[2])
            P = tuple(A[i] + t * (B[i] - A[i]) for i in range(3))
            if A[2] < NEAR:
                A = P
            else:
                B = P
        return self.proj_c(*A), self.proj_c(*B)


def box_edges(cx, cy, w, h, ang, z0, z1):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(cx + ca * u - sa * v, cy + sa * u + ca * v) for u, v in ((w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, -h / 2))]
    bot = [(x, y, z0) for x, y in pts]
    top = [(x, y, z1) for x, y in pts]
    e = [(bot[i], bot[(i + 1) % 4]) for i in range(4)] + [(top[i], top[(i + 1) % 4]) for i in range(4)] + [(bot[i], top[i]) for i in range(4)]
    front = [bot[0], bot[1], top[1], top[0]]  # face avant (côté +w/2)
    return e, front


def stairs_elev(L, x, y):
    e = dsm.sur_escalier(L, x, y)
    return e[1] if e else 0.0


def occultations(L, placement, cam_i=0):
    """{id: (fraction cachée 0..1, nom de ce qui cache)} pour les éléments masqués par un véhicule
    ou un personnage plus proche (approximation par rectangles projetés)."""
    els = elements_attendus(L, placement, cam_i)  # du plus loin au plus près
    out = {}
    for i, (eid, nom, typ, bb, dist) in enumerate(els):
        area = max(1.0, (bb[2] - bb[0]) * (bb[3] - bb[1]))
        best = (0.0, "")
        for oid, onom, otyp, ob, od in els[i + 1:]:
            if od >= dist - 0.3:
                continue
            ix = max(0, min(bb[2], ob[2]) - max(bb[0], ob[0]))
            iy = max(0, min(bb[3], ob[3]) - max(bb[1], ob[1]))
            f = ix * iy / area
            if f > best[0]:
                best = (f, onom)
        if best[0] >= 0.25:
            out[eid] = best
    return out


def elements_attendus(L, placement, cam_i=0):
    """[(id, nom, type, bbox image (x0,y0,x1,y1), distance m)] pour les éléments visibles."""
    cam = Cam(placement["cameras"][cam_i])
    cat = {k["id"]: k for k in L["catalogue"]}
    out = []
    for eid, e in placement.get("elements", {}).items():
        if not e.get("visible", True) or eid not in cat:
            continue
        k = cat[eid]
        pts = []
        if k["type"] == "vehicule":
            edges, _ = box_edges(e["x"], e["y"], k["w"], k["h"], e.get("angle", 0), 0, H_VEH.get(eid, 1.6))
            for a, b in edges:
                for p in (a, b):
                    q = cam.proj(*p)
                    if q:
                        pts.append(q)
        else:
            z0 = stairs_elev(L, e["x"], e["y"])
            hh = perso_h(k, e)
            for dx, dy in ((-7, 0), (7, 0), (0, -7), (0, 7)):
                for z in (z0, z0 + hh):
                    q = cam.proj(e["x"] + dx, e["y"] + dy, z)
                    if q:
                        pts.append(q)
        if not pts:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        bb = (min(xs), min(ys), max(xs), max(ys))
        if bb[2] < 0 or bb[0] > W or bb[3] < 0 or bb[1] > H:
            continue
        r, _, z = cam.cam(e["x"], e["y"], 0)
        out.append((eid, k["nom"], k["type"], bb, math.hypot(r, z)))
    return sorted(out, key=lambda t: -t[4])


def perso_h(k, e):
    pose = e.get("pose", "debout")
    if k.get("espece") == "chien":
        return H_CHIEN * POSE_CHIEN.get(pose, 1)
    return H_PERSO * POSE_F.get(pose, 1)


def calque(plan_id, cam_i=0):
    L = dsm.load_lieux()
    placement = dsm.load_plans()[plan_id]
    cam = Cam(placement["cameras"][cam_i])
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f_s = ImageFont.truetype(FONT, 20)
    f_b = ImageFont.truetype(FONT_B, 24)

    def line(a, b, col, w=2):
        s = cam.seg(a, b)
        if s:
            d.line(s, fill=col, width=w)

    def label(p, txt, col, font=f_s):
        if p and -50 < p[0] < W + 50 and -50 < p[1] < H + 50:
            d.text(p, txt, font=font, fill=col, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 200))

    R = L["rue"]
    x1 = 1600
    # sol : bords de chaussée et limites de trottoir
    for y, col in ((R["chaussee_haut"], (255, 255, 255, 230)), (R["chaussee_bas"], (255, 255, 255, 230)),
                   (R["nord_trottoir"], (200, 200, 200, 170)), (R["sud_trottoir"], (200, 200, 200, 170))):
        line((R["x0"], y, 0), (1530, y, 0), col, 2)
    # repères de distance tous les 10 m sur l'axe de la chaussée
    ymid = (R["chaussee_haut"] + R["chaussee_bas"]) / 2
    for dist in range(10, 70, 10):
        x = cam.x + dist / M * cam.fx
        line((x, R["chaussee_haut"], 0), (x, R["chaussee_bas"], 0), (255, 255, 255, 90), 1)
        label(cam.proj(x, ymid, 0), f"{dist} m", (255, 255, 255, 160))
    # portée (= longueur du cône) : au-delà, flou / brume
    lim = dsm.portee_px(placement["cameras"][cam_i])
    pa_c = (cam.x + lim * cam.fx, cam.y + lim * cam.fy)
    line((pa_c[0] - 3000 * cam.fy, pa_c[1] + 3000 * cam.fx, 0), (pa_c[0] + 3000 * cam.fy, pa_c[1] - 3000 * cam.fx, 0), (224, 79, 95, 230), 3)
    pm = cam.proj(pa_c[0], pa_c[1], 0)
    if pm:
        label((pm[0], pm[1] + 22), f"portée {lim * M:.0f} m — au-delà : flou", (255, 180, 180, 230))
    # bâtiments
    for b in L["batiments"]:
        hb = H_BAT.get(b["id"], H_MAISON)
        edges, _ = box_edges(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, b["w"], b["h"], 0, 0, hb)
        for a, c in edges:
            line(a, c, (255, 230, 120, 150), 2)
        face_y = b["y"] + b["h"] if b["y"] < 495 else b["y"]
        label(cam.proj(b["x"] + b["w"] / 2, face_y, hb + 0.6), b["nom"].replace("Maison d'", "").replace("Maison de ", ""), (255, 230, 120, 230))
        if b.get("ouverture") == "sud":
            cx, y = b["x"] + b["w"] / 2, b["y"] + b["h"]
            dw = 3.0 / M / 2
            for a, c in (((cx - dw, y, 0), (cx - dw, y, 2.4)), ((cx + dw, y, 0), (cx + dw, y, 2.4)), ((cx - dw, y, 2.4), (cx + dw, y, 2.4))):
                line(a, c, (255, 140, 40, 255), 4)
            label(cam.proj(cx, y, 2.8), "porte du garage", (255, 160, 60, 255))
    # détails
    for dt in L["details"]:
        if dt["type"] == "escalier":
            x0, y0, w, h, hm = dt["x"], dt["y"], dt["w"], dt["h"], dt.get("hauteur", 2.8)
            for yy in (y0, y0 + h):
                line((x0, yy, 0), (x0 + w, yy, hm), (200, 255, 200, 230), 3)
            pa = dt.get("palier")
            if pa:
                for a, b in box_edges(pa["x"] + pa["w"] / 2, pa["y"] + pa["h"] / 2, pa["w"], pa["h"], 0, hm, hm)[0][:4]:
                    line(a, b, (200, 255, 200, 230), 3)
                label(cam.proj(pa["x"] + pa["w"] / 2, pa["y"] + pa["h"], hm + 0.5), "palier", (200, 255, 200, 230))
        elif dt["type"] == "tourelle":
            for dx in (-dt["r"], dt["r"]):
                line((dt["x"] + dx, dt["y"], 0), (dt["x"] + dx, dt["y"], 9.5), (210, 180, 255, 200), 2)
        elif dt["type"] == "passage_niveau":
            xr = dt["x"]
            for dx in (-7, 7):  # rails
                line((xr + dx, dt["y"], 0), (xr + dx, dt["y"] + dt["h"], 0), (255, 80, 80, 255), 3)
            for yb in (R["chaussee_haut"] - 6, R["chaussee_bas"] + 6):  # barrières levées
                line((xr - 20, yb, 0), (xr - 20, yb, 1.1), (255, 255, 255, 255), 4)
                line((xr - 20, yb, 1.1), (xr - 20, yb, 5.0), (255, 60, 60, 255), 3)
            label(cam.proj(xr, ymid, 0.0), "rails", (255, 120, 120, 255))
            label(cam.proj(xr + 40, ymid, 0.0), "↓ la route plonge", (255, 200, 200, 230))
    # éléments (du plus loin au plus près)
    cat = {k["id"]: k for k in L["catalogue"]}
    els = [(eid, e) for eid, e in placement.get("elements", {}).items() if e.get("visible", True) and eid in cat]
    els.sort(key=lambda t: -cam.cam(t[1]["x"], t[1]["y"], 0)[2])
    for eid, e in els:
        k = cat[eid]
        col = dsm.hexrgb(k.get("couleur", "#ffffff"))[:3]
        loin = cam.cam(e["x"], e["y"], 0)[2] > lim * M
        if loin:  # au-delà de la portée : couleurs atténuées + « (flou) »
            col = tuple(int(v * 0.55 + 200 * 0.45) for v in col)
        if k["type"] == "vehicule":
            hv = H_VEH.get(eid, 1.6)
            edges, front = box_edges(e["x"], e["y"], k["w"], k["h"], e.get("angle", 0), 0, hv)
            fp = [cam.proj(*p) for p in front]
            if all(fp):
                d.polygon(fp, fill=col + (110,))
            for a, b in edges:
                line(a, b, col + (255,), 3)
            label(cam.proj(e["x"], e["y"], hv + 0.5), k["nom"].replace(" (sur parpaings)", "") + (" (flou)" if loin else ""), col + (255,), f_b)
        else:
            z0 = stairs_elev(L, e["x"], e["y"])
            hh = perso_h(k, e)
            pb, pt = cam.proj(e["x"], e["y"], z0), cam.proj(e["x"], e["y"], z0 + hh)
            if not pb or not pt:
                continue
            hp = pb[1] - pt[1]
            wp = hp * (0.55 if k.get("espece") == "chien" and e.get("pose") not in ("assis",) else 0.28)
            d.rounded_rectangle([pb[0] - wp / 2, pt[1], pb[0] + wp / 2, pb[1]], radius=max(2, wp / 3), outline=col + (255,), width=3, fill=col + (70,))
            # sens du regard
            a = math.radians(e.get("angle", 0))
            tip = cam.proj(e["x"] + 22 * math.cos(a), e["y"] + 22 * math.sin(a), z0)
            if tip:
                d.line([pb, tip], fill=col + (255,), width=3)
            label((pb[0], pt[1] - 16), k["nom"] + (" (flou)" if loin else ""), col + (255,), f_b)
    return img


def texte(plan_id, cam_i=0):
    L = dsm.load_lieux()
    placement = dsm.load_plans()[plan_id]
    lines = [f"Cadrage calculé depuis la carte {plan_id} (image 16:9, 0 % = bord gauche/haut) :"]
    lim_m = dsm.portee_px(placement["cameras"][cam_i]) * M
    for eid, nom, typ, (x0, y0, x1, y1), dist in elements_attendus(L, placement, cam_i):
        cx = max(0, min(100, (x0 + x1) / 2 / W * 100))
        if dist > lim_m:
            nom += " (flou, au-delà de la portée)"
        lines.append(f"  - {nom} : centre à {cx:.0f} % de la largeur, de {max(0, y0) / H * 100:.0f} % à {min(H, y1) / H * 100:.0f} % de la hauteur"
                     f" (hauteur ≈ {(min(H, y1) - max(0, y0)) / H * 100:.0f} % de l'image), à {dist:.0f} m.")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    plan = argv[1].upper()
    if "--texte" in argv:
        print(texte(plan))
        return 0
    img = calque(plan)
    out = dsm.CARTE / "plans" / f"{plan.lower()}-calque.png"
    if "--sur" in argv:
        i = argv.index("--sur")
        base = Image.open(argv[i + 1]).convert("RGBA").resize((W, H))
        out = Path(argv[i + 2]) if len(argv) > i + 2 else out.with_name(f"{plan.lower()}-calque-sur.png")
        Image.alpha_composite(base, img).convert("RGB").save(out, quality=90)
    else:
        img.save(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
