#!/usr/bin/env python3
"""P02 v5 = la v4 avec la 2e paire de correctifs de la liste (avis du 14/10 sur la v3) :

3. plaque avant : noire à caractères blancs « 1_ 67 », comme la plaque arrière de la 4L dans P01 v33
   (fond passé au noir de la plaque de P01, caractères étroits gris clair posés dans la perspective) ;
4. peinture et rouille de la 4L comme dans P01 v33 :
   - la peinture prend la teinte de la 4L de P01 (vert amande plus jaune et plus sourd ; la clarté est
     ramenée sur la plage ombre → lumière de la 4L de P01) ; ombres, reflets et traits gardés ;
   - la rouille existante passe à l'orangé-brun plus sombre de P01 ;
   - des taches et des points de rouille sont ajoutés sur les panneaux (bas des portes, aile, capot, face
     avant), quelques-uns avec une courte coulure, comme sur la 4L de P01.
   Les teintes de rouille sont prises parmi les tons rouille déjà présents dans l'image (critère du
   contrôle) et les plus proches de ceux de P01.

Sans IA. Tout le reste est identique à la v4 (Jeannot, Enji, lieux, volant, sol). Contrôle obligatoire :
  python3 tools/controle_retouche.py p02-v4-volant-couleurs.png p02-v5-plaque-rouille.png \\
      --zones "<voir ZONES>" --plan P02 --sortie p02-v5-controle.jpg

Usage : python3 tools/p02_v5.py [SORTIE]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v4-volant-couleurs.png"
POLICE = ROOT / "assets/fonts/DejaVuSans.ttf"     # trait fin, comme les caractères de P01

ZONE_4L = (1140, 320, 1920, 962)      # carrosserie de la 4L (x0, y0, x1, y1)
CLIGNOTANT = (1500, 826, 1570, 866)   # clignotant orange : ni peinture ni rouille
PARE_CHOCS_Y = 878                    # sous cette ligne (x > 1430) : pare-chocs, sa rouille reste telle quelle
# arrière de la 4L visible entre la jambe de Jeannot et la caisse (x < 1140) : la PEINTURE seule y est
# reprise (pas la rouille ni les taches : la main de Jeannot est là, et sa peau a une teinte « rouille »)
PEINTURE_EXTRA = (1080, 580, 1140, 880)
ZONES = [ZONE_4L, PEINTURE_EXTRA]     # zones autorisées pour le contrôle
# silhouette de la 4L (relevée 4 px au-dessus du trait du toit, du montant et du capot) : peinture, rouille et
# taches n'existent que dedans — les pierres verdâtres du mur derrière le toit ne sont pas de la peinture
# (à droite de x 1600, le fond au-dessus du toit et du capot est le mur crème, déjà exclu par la couleur :
# la silhouette y reste large pour ne pas couper le coin du toit ni le montant de pare-brise)
SILHOUETTE = [(1140, 430), (1190, 400), (1240, 383), (1280, 376), (1320, 372), (1440, 371), (1520, 376),
              (1560, 381), (1600, 384), (1920, 384), (1920, 880), (1140, 880)]

# --------------------------------------------------------------------------- 1. peinture
# mesures (Lab OpenCV, 128 = neutre) : 4L de P01 v33 p10/p50/p90 de L = 143/174/195, a = 117, b = 145 ;
# 4L de la v4 : L = 152/189/200, a = 115, b = 141
P01_L10, P01_L90, V4_L10, V4_L90 = 143.0, 195.0, 152.0, 200.0
D_A, D_B = 117.0 - 115.0, 145.0 - 141.0


def masque_peinture(L, A, B):
    """Appartenance (0..1) à la peinture vert menthe : 1 pour le menthe franc, partielle pour les reflets
    et les pixels de bord (mélange avec un trait), 0 pour le reste (mur crème, Jeannot, vitres, chromes)."""
    m = np.clip((-A - 2.0) / 4.0, 0, 1)
    m *= (B > -8) & (B < 30) & (L > 90)
    return m.astype(np.float32)


def peinture(lab):
    new = lab.copy()
    new[..., 0] = P01_L10 + (lab[..., 0] - V4_L10) * (P01_L90 - P01_L10) / (V4_L90 - V4_L10)
    new[..., 1] = lab[..., 1] + D_A
    new[..., 2] = lab[..., 2] + D_B
    return new


# --------------------------------------------------------------------------- 2. rouille existante
# rouille v4 : L médian 123, a +16, b +28 ; P01 : L 100, a +23, b +28 → plus sombre, à peine plus rouge
# (un rouge plus franc fait « éclaboussure » sur le vert) ; texture gardée
ROUILLE_DL, ROUILLE_DA = -15.0, 2.0


def masque_rouille(L, A, B, zone):
    fort = (A > 6) & (B > 14) & (L > 60) & (L < 175) & zone
    faible = (A > 1) & (B > 8) & (L > 50) & (L < 208) & zone
    n, lbl = cv2.connectedComponents(faible.astype(np.uint8), connectivity=8)
    garde = np.unique(lbl[fort])
    return np.isin(lbl, garde[garde > 0])


# --------------------------------------------------------------------------- 3. taches et points ajoutés
# tons rouille OCRE et BRUNS déjà présents dans l'image (cases de couleur de la v4), proches de la rouille de
# P01 : auréole ocre clair semi-transparente, brun ocre, cœur brun sombre — pas d'orangé-rouge (sur ce vert,
# il fait « éclaboussure »)
R_AUREOLE, R_MILIEU, R_COEUR = (168, 120, 88), (152, 104, 72), (112, 68, 42)
AUREOLE_ALPHA = 0.45
# régions (x0, y0, x1, y1) et nombre de taches, à la manière de la 4L de P01 (bas de caisse, bords, avant)
# (x0, y0, x1, y1), nombre, rayons possibles : grandes plaques en bas de caisse, petites taches en haut
REGIONS = [((1160, 600, 1262, 700), 1, (4.0, 5.0, 6.0)), ((1160, 760, 1262, 846), 2, (9.0, 11.0, 13.0)),
           ((1160, 700, 1262, 760), 1, (5.0, 6.0, 7.0)),                                   # portière arrière
           ((1276, 650, 1420, 738), 2, (4.0, 5.0, 6.0)), ((1276, 770, 1420, 852), 3, (8.0, 10.0, 12.0, 14.0)),
           ((1276, 738, 1420, 770), 1, (5.0, 6.0)),                                        # portière avant
           ((1430, 630, 1560, 720), 1, (4.0, 5.0)), ((1430, 720, 1560, 800), 2, (6.0, 8.0, 10.0)),  # aile avant
           ((1480, 570, 1900, 700), 2, (4.0, 5.0, 6.0)),                                   # capot (peu)
           ((1590, 790, 1920, 880), 3, (5.0, 7.0, 9.0))]                                   # face avant (hors plaque)
GRAINE = 20261014


def _blob(cx, cy, R, rng, n=24):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r = np.ones(n)
    for k, amp in ((2, 0.28), (3, 0.16), (4, 0.08), (5, 0.05)):   # ondulations lentes : plaque, pas éclaboussure
        r += rng.uniform(0.3, 1.0) * amp * np.sin(k * th + rng.uniform(0, 2 * np.pi))
    r = R * np.clip(r, 0.6, 1.4)
    ell = rng.uniform(0.5, 0.85)                       # taches plutôt allongées à l'horizontale
    rot = rng.uniform(-0.35, 0.35)
    x, y = r * np.cos(th), ell * r * np.sin(th)
    return np.stack([cx + x * np.cos(rot) - y * np.sin(rot), cy + x * np.sin(rot) + y * np.cos(rot)], 1)


def taches(shape, interieur, evite, rng):
    """Calque RGBA (flottant) des taches ajoutées, dessiné ×4 puis réduit (bords nets et lissés)."""
    x0, y0, x1, y1 = ZONE_4L
    S = 4
    W4, H4 = (x1 - x0) * S, (y1 - y0) * S
    col = Image.new("RGB", (W4, H4), (0, 0, 0))
    alp = Image.new("L", (W4, H4), 0)
    dc, da = ImageDraw.Draw(col), ImageDraw.Draw(alp)
    dist = cv2.distanceTransform(interieur.astype(np.uint8), cv2.DIST_L2, 5)
    occupe = evite.copy()
    poses = []
    for (rx0, ry0, rx1, ry1), nb, rayons in REGIONS:
        essais = 0
        while nb > 0 and essais < 600:
            essais += 1
            cx, cy = rng.uniform(rx0, rx1), rng.uniform(ry0, ry1)
            R = float(rng.choice(rayons))
            ix, iy = int(cx), int(cy)
            if dist[iy, ix] < R * 0.7 + 3 or occupe[max(0, iy - 22):iy + 22, max(0, ix - 22):ix + 22].any():
                continue
            poses.append((cx, cy, R))
            occupe[max(0, iy - 18):iy + 18, max(0, ix - 18):ix + 18] = True
            nb -= 1

    def poly(pts, couleur, opac=255):
        p = [((x - x0) * S, (y - y0) * S) for x, y in pts]
        dc.polygon(p, fill=couleur)
        da.polygon(p, fill=opac)

    for cx, cy, R in poses:
        formes = [_blob(cx, cy, R, rng)]
        if R >= 7 and rng.random() < 0.5:                  # tache double (deux plaques qui se rejoignent)
            formes.append(_blob(cx + rng.choice([-1, 1]) * R * rng.uniform(0.6, 1.0), cy + rng.uniform(-0.3, 0.3) * R,
                                R * rng.uniform(0.45, 0.7), rng))
        for b in formes:
            c0 = b.mean(0)
            poly(c0 + (b - c0) * 1.35, R_AUREOLE, int(255 * AUREOLE_ALPHA))       # auréole qui « mord » la peinture
        for b in formes:
            poly(b, R_MILIEU)
        for b in formes:                                   # cœur sombre décentré, de forme propre (pas une cible)
            c0 = b.mean(0)
            rb = float(np.sqrt(((b - c0) ** 2).sum(1)).mean())
            ang = rng.uniform(0, 2 * np.pi)
            dec = rng.uniform(0.15, 0.4) * rb
            poly(_blob(c0[0] + dec * np.cos(ang), c0[1] + dec * 0.6 * np.sin(ang), rb * rng.uniform(0.35, 0.55), rng),
                 R_COEUR)
        if R >= 6 and rng.random() < 0.4:                  # courte coulure sous la tache
            lg, lw = rng.uniform(5, 12), rng.uniform(1.5, 2.4)
            xd = cx + rng.uniform(-R * 0.4, R * 0.4)
            pts = [(xd - lw / 2, cy + R * 0.5), (xd + lw / 2, cy + R * 0.5), (xd + lw * 0.2, cy + R * 0.5 + lg),
                   (xd - lw * 0.2, cy + R * 0.5 + lg)]
            poly(pts, R_MILIEU)
        for _ in range(int(rng.integers(0, 4))):            # quelques points autour
            a, d = rng.uniform(0, 2 * np.pi), rng.uniform(R * 1.3 + 2, R * 1.3 + 10)
            px, py, pr = cx + d * np.cos(a), cy + d * np.sin(a) * 0.8, rng.uniform(0.9, 1.8)
            if 0 <= int(py) < shape[0] and 0 <= int(px) < shape[1] and dist[int(py), int(px)] >= pr + 2:
                poly([(px + pr * np.cos(t), py + pr * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 12, endpoint=False)],
                     R_MILIEU)
    w1, h1 = x1 - x0, y1 - y0
    a = np.asarray(alp.resize((w1, h1), Image.LANCZOS), np.float32) / 255.0
    # couleur « dé-prémultipliée » (le fond noir du calque ne doit pas assombrir les bords)
    cp = np.asarray(Image.fromarray(np.asarray(col)).resize((w1, h1), Image.LANCZOS), np.float32)
    acc = np.asarray(Image.fromarray((np.asarray(alp) > 0).astype(np.uint8) * 255).resize((w1, h1), Image.LANCZOS),
                     np.float32) / 255.0
    c = cp / np.maximum(acc[..., None], 1e-3)
    return np.clip(c, 0, 255), np.clip(a, 0, 1), len(poses)


# --------------------------------------------------------------------------- 4. plaque
# coins intérieurs de la plaque avant (dans le trait noir) : haut gauche, haut droit, bas droit, bas gauche
PLAQUE = np.array([(1677.0, 831.0), (1880.0, 823.5), (1880.0, 859.5), (1677.0, 869.5)], np.float32)
PLAQUE_FOND = (32, 38, 35)            # fond de la plaque arrière de P01
PLAQUE_TEXTE = (215, 218, 205)        # caractères gris clair


def plaque(img):
    H, W = img.shape[:2]
    S = 4
    bx0, by0 = int(PLAQUE[:, 0].min()) - 2, int(PLAQUE[:, 1].min()) - 2
    bx1, by1 = int(PLAQUE[:, 0].max()) + 3, int(PLAQUE[:, 1].max()) + 3
    bw, bh = bx1 - bx0, by1 - by0
    # masque de l'intérieur (lissé)
    m4 = Image.new("L", (bw * S, bh * S), 0)
    ImageDraw.Draw(m4).polygon([((x - bx0) * S, (y - by0) * S) for x, y in PLAQUE], fill=255)
    m = np.asarray(m4.resize((bw, bh), Image.LANCZOS), np.float32) / 255.0
    # fond : noir de P01, texture gardée
    sub = img[by0:by1, bx0:bx1].astype(np.float32)
    lab = cv2.cvtColor(img[by0:by1, bx0:bx1], cv2.COLOR_RGB2LAB).astype(np.float32)
    cible = cv2.cvtColor(np.array([[PLAQUE_FOND]], np.uint8), cv2.COLOR_RGB2LAB)[0, 0].astype(np.float32)
    sel = m > 0.9
    med = np.median(lab[sel], axis=0)
    new = lab.copy()
    new[..., 0] = lab[..., 0] * (cible[0] / med[0])
    new[..., 1] = cible[1] + (lab[..., 1] - med[1]) * 0.5
    new[..., 2] = cible[2] + (lab[..., 2] - med[2]) * 0.5
    fond = cv2.cvtColor(np.clip(new, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    out = sub * (1 - m[..., None]) + fond * m[..., None]
    # texte « 1_ 67 » à la manière de P01 : « 1 » à gauche, petit trait bas, « 67 » à droite ; 78 % de haut
    TH = 152                                           # rectangle du texte (×4) aux proportions de l'intérieur
    TW = int(TH * (203 - 4) / (37 - 4))                # de la plaque (199 × 33 px) : caractères non déformés
    t = Image.new("L", (TW, TH), 0)
    d = ImageDraw.Draw(t)
    haut = 0.78 * TH
    f = ImageFont.truetype(str(POLICE), int(round(haut / 0.729)))

    def glyphe(txt):
        g = Image.new("L", (int(haut * 2.2), int(haut * 1.6)), 0)
        ImageDraw.Draw(g).text((0, 0), txt, fill=255, font=f)
        bb = g.getbbox()
        g = g.crop(bb)
        return g.resize((max(1, int(g.width * 0.62)), int(haut)), Image.LANCZOS)

    y_haut = int((TH - haut) / 2)
    un = glyphe("1")
    x_un = int(0.07 * TW)
    t.paste(un, (x_un, y_haut), un)
    # petit trait bas après le « 1 » (comme sur la plaque de P01)
    tx0 = x_un + un.width + int(0.025 * TW)
    d.rectangle([tx0, y_haut + haut - 0.09 * TH, tx0 + 0.085 * TW, y_haut + haut], fill=255)
    sept = glyphe("67")
    t.paste(sept, (int(0.95 * TW) - sept.width, y_haut), sept)
    # pose dans la perspective de la plaque (rectangle intérieur rentré de 2 px)
    c = PLAQUE.mean(0)
    dst = (c + (PLAQUE - c) * np.array([(203 - 4) / 203, (37 - 4) / 37], np.float32) - [bx0, by0]) * S
    M = cv2.getPerspectiveTransform(np.float32([(0, 0), (TW, 0), (TW, TH), (0, TH)]), dst.astype(np.float32))
    big = cv2.warpPerspective(np.asarray(t), M, (bw * S, bh * S), flags=cv2.INTER_LINEAR)
    a = cv2.resize(big, (bw, bh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    a *= m
    out = out * (1 - a[..., None]) + np.array(PLAQUE_TEXTE, np.float32) * a[..., None]
    res = img.copy()
    res[by0:by1, bx0:bx1] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return res


# --------------------------------------------------------------------------- assemblage
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_path = Path(args[0]) if args else DOSSIER / "p02-v5-plaque-rouille.png"
    img = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = img.shape[:2]
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    x0, y0, x1, y1 = ZONE_4L
    zone = np.zeros((H, W), bool)
    zone[y0:y1, x0:x1] = True
    cx0, cy0, cx1, cy1 = CLIGNOTANT
    zone[cy0:cy1, cx0:cx1] = False
    zone[PARE_CHOCS_Y:, 1430:] = False
    sil = np.zeros((H, W), np.uint8)
    cv2.fillPoly(sil, [np.int32(SILHOUETTE)], 1)
    zone &= sil.astype(bool)
    ex0, ey0, ex1, ey1 = PEINTURE_EXTRA
    zone_p = zone.copy()
    zone_p[ey0:ey1, ex0:ex1] = True

    # 1. peinture : appartenance au menthe, limitée aux vrais morceaux de carrosserie (les pixels verdâtres
    # isolés des vitres et des murs sont écartés)
    ap = masque_peinture(L, A, B) * zone_p
    coeur = cv2.morphologyEx((ap >= 0.5).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(coeur, 8)
    gros = np.isin(lbl, [i for i in range(1, n) if st[i][4] >= 150])
    ap *= cv2.dilate(gros.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    # 2. rouille existante
    rou = masque_rouille(L, A, B, zone)
    ar = rou.astype(np.float32)
    ap[rou] = 0.0
    # mélange en RVB (pas en Lab) : là où les masques valent 0, les pixels restent STRICTEMENT ceux de la v4
    # (l'aller-retour RVB → Lab → RVB arrondi décalerait d'un ou deux niveaux toute la zone)
    def vers_rgb(l):
        return cv2.cvtColor(np.clip(np.rint(l), 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    rt = lab.copy()
    rt[..., 0] += ROUILLE_DL
    rt[..., 1] += ROUILLE_DA
    rgb = img.astype(np.float32)
    rgb = rgb * (1 - ap[..., None]) + vers_rgb(peinture(lab)) * ap[..., None]
    rgb = rgb * (1 - ar[..., None]) + vers_rgb(rt) * ar[..., None]

    # 3. taches et points : seulement dans la peinture franche, loin des traits et de la rouille existante
    franc = (masque_peinture(L, A, B) >= 0.99) & zone
    franc = cv2.erode(franc.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    pl = np.zeros((H, W), np.uint8)
    cv2.fillPoly(pl, [np.int32(PLAQUE)], 1)
    evite = rou | cv2.dilate(pl, np.ones((15, 15), np.uint8)).astype(bool)
    rng = np.random.default_rng(GRAINE)
    tc, ta, nb = taches((H, W), franc, evite, rng)
    ta = ta * np.clip(cv2.GaussianBlur(franc[y0:y1, x0:x1].astype(np.float32), (0, 0), 0.7) * 1.4, 0, 1)
    blk = rgb[y0:y1, x0:x1]
    rgb[y0:y1, x0:x1] = blk * (1 - ta[..., None]) + tc * ta[..., None]
    res = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)

    # 4. plaque
    res = plaque(res)

    # hors des zones de la 4L : pixels strictement ceux de la v4
    res[~zone_p] = img[~zone_p]
    Image.fromarray(res).save(out_path, optimize=True)
    print(f"ok {out_path} | peinture {int((ap > 0).sum())} px · rouille recolorée {int(rou.sum())} px · "
          f"taches ajoutées {nb} · plaque « 1_ 67 »")
    print("zones du contrôle :", ";".join(",".join(str(v) for v in z) for z in ZONES))


if __name__ == "__main__":
    main()
