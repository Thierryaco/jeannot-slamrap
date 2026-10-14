#!/usr/bin/env python3
"""P02 v4 = la v3 avec les deux premiers correctifs demandés (avis du 14/10) :

1. le volant passe du côté conducteur : une 4L française a le volant à gauche, donc ici derrière la
   moitié ÉLOIGNÉE du pare-brise (la v3 le montrait du côté proche = conduite à droite).
   Sans IA : l'anneau du volant est retiré (l'intérieur est reconstitué nettement autour) puis redessiné aux
   mêmes dimensions et couleurs côté conducteur ; l'essuie-glace droit repasse par-dessus.
2. les couleurs se rapprochent de P01 v33 : la chaussée passe du beige au gris de l'asphalte de P01, chaque
   trottoir prend le gris du même trottoir dans P01, le ciel passe au bleu de P01. Seules ces surfaces changent ; leurs ombres, leurs
   bordures et leur texture sont gardées (décalage ligne par ligne dans l'espace Lab).

Tout le reste de l'image est identique à la v3. Contrôle obligatoire :
  python3 tools/controle_retouche.py p02-v3-cul-de-sac.png p02-v4-volant-couleurs.png \
      --zones "<voir ZONES>" --plan P02 --sortie p02-v4-controle.jpg

Usage : python3 tools/p02_v4.py [SORTIE] [--masques DOSSIER]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v3-cul-de-sac.png"

# zones autorisées pour le contrôle (x0, y0, x1, y1) : volant, chaussée + trottoirs, ciel
ZONES = [(1322, 505, 1678, 553), (0, 415, 1920, 1080), (0, 0, 330, 125)]

# --------------------------------------------------------------------------- 1. volant
# anneau du volant dans la v3 (ellipses relevées sur un agrandissement ×4) ; il disparaît sous le bas du
# pare-brise vers y = 545
V_C = (1393.0, 553.0)
V_EXT = (57.0, 38.0)      # demi-axes du bord extérieur du contour
V_INT = (44.0, 27.0)      # demi-axes du bord intérieur du contour intérieur
V_BAS = 545               # bas visible (bord inférieur du vitrage)
V_ECHELLE = 1.0           # même taille que l'original (redessiné, traits aussi nets)
V_CX_NOUVEAU = 1615       # centre du nouveau volant (moitié éloignée du pare-brise)
# essuie-glace droit (il passe devant le nouveau volant) : segment approximatif de son axe
ESSUIE = ((1585.0, 556.0), (1657.0, 488.0))


def _ellipse(shape, c, ax, marge=0.0):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx - c[0]) / (ax[0] + marge)) ** 2 + ((yy - c[1]) / (ax[1] + marge)) ** 2 <= 1.0


def _couverture(shape, c, ax_ext, ax_int, ss=4):
    """Part (0..1) de chaque pixel couverte par l'anneau entre deux ellipses (bord lissé, sans pixels du fond)."""
    H, W = shape
    o = (np.arange(ss) + 0.5) / ss
    acc = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for dy in o:
        for dx in o:
            X, Y = xx + dx - 0.5, yy + dy - 0.5
            e = ((X - c[0]) / ax_ext[0]) ** 2 + ((Y - c[1]) / ax_ext[1]) ** 2 <= 1.0
            i = ((X - c[0]) / ax_int[0]) ** 2 + ((Y - c[1]) / ax_int[1]) ** 2 <= 1.0
            acc += (e & ~i)
    return acc / (ss * ss)


def volant(img):
    H, W = img.shape[:2]
    anneau = _ellipse((H, W), V_C, V_EXT, 1.5) & ~_ellipse((H, W), V_C, V_INT, -1.5)
    anneau[V_BAS:, :] = False
    # retrait, sans flou : on reconstitue nettement l'intérieur que le volant cachait.
    #  - au-dessus de la planche de bord : les bandes verticales de l'habitacle (vitre claire, montant gris
    #    et ses traits) sont prolongées vers le bas, colonne par colonne (reflet sous le haut du volant) ;
    #  - la ligne du haut de la planche de bord, nette à gauche (y 530), descend vers y 538 à droite où
    #    elle s'estompe, comme de part et d'autre du volant ;
    #  - dessous, la planche de bord : à l'intérieur de l'anneau elle est déjà là (pixels d'origine gardés,
    #    sauf le petit trait du moyeu) ; sous l'anneau lui-même, sa teinte est prolongée.
    out = img.copy()
    f = img.astype(np.float32)
    dome = _ellipse((H, W), V_C, V_EXT, 1.2)
    dome[V_BAS:, :] = False
    yy, xx = np.mgrid[0:H, 0:W]
    dome &= ~((xx < 1341) & (yy > 536))             # coin du vitrage à gauche : intact
    bande_g = np.median(f[533:543, 1324:1334].reshape(-1, 3), axis=0)
    bande_d = np.median(f[539:543, 1450:1460].reshape(-1, 3), axis=0)
    zt = f[528:534, 1318:1332].reshape(-1, 3)                                  # trait à gauche du volant :
    trait = np.median(zt[zt.mean(1) <= np.percentile(zt.mean(1), 15)], axis=0)  # sa teinte la plus foncée (cœur)
    interieur = _ellipse((H, W), V_C, V_INT, -1.5)                              # ce que l'anneau entoure
    bande_i = np.median(f[interieur & (yy > 533) & (yy < 544)].reshape(-1, 3), axis=0)
    moyeu = (np.abs(xx - 1391) <= 7) & (np.abs(yy - 537) <= 2)                  # petit trait du moyeu
    ys, xs = np.nonzero(dome)
    for x in range(xs.min(), xs.max() + 1):
        col = np.nonzero(dome[:, x])[0]
        if not len(col):
            continue
        yt = col.min()
        yl = 530.0 + (x - 1340) * 8.0 / 110.0
        u = float(np.clip((x - 1340) / 110.0, 0, 1))
        bande = bande_g * (1 - u) + bande_d * u
        fondu = float(np.clip((1452 - x) / 14.0, 0, 1))   # trait net, qui ne s'efface qu'au bord droit
        for y in col:
            if y < yl - 1.5:
                out[y, x] = img[max(2 * yt - y - 1, 496), x]
            elif interieur[y, x] and not moyeu[y, x] and y >= yl + 1.5:
                out[y, x] = img[y, x]                                           # planche de bord d'origine
            else:
                dessous = bande_i if interieur[y, x] else bande
                fond = img[max(2 * yt - y - 1, 496), x].astype(np.float32) if y < yl else dessous
                cov = float(np.clip(min(y + 1, yl + 1.0) - max(y, yl - 1.0), 0, 1)) * fondu   # trait de 2 px
                out[y, x] = np.clip(trait * cov + fond * (1 - cov), 0, 255)

    # nouveau volant, côté conducteur : redessiné aux dimensions et aux couleurs de l'original (contour foncé,
    # jante, contour intérieur), bords lissés ; le bas reste caché par le bas du pare-brise
    lum = f.mean(2)
    contour_c = np.median(f[anneau & (lum < 80)], axis=0)
    jante_c = np.median(f[_ellipse((H, W), V_C, (V_EXT[0] - 3.5, V_EXT[1] - 3.5)) & ~_ellipse((H, W), V_C, (V_INT[0] + 3.0, V_INT[1] + 3.0))
                          & (yy < V_BAS)], axis=0)
    c2 = (float(V_CX_NOUVEAU), V_C[1])
    e1, e2 = (V_EXT[0] * V_ECHELLE, V_EXT[1] * V_ECHELLE), ((V_EXT[0] - 2.2) * V_ECHELLE, (V_EXT[1] - 2.2) * V_ECHELLE)
    i1, i2 = ((V_INT[0] + 2.2) * V_ECHELLE, (V_INT[1] + 2.2) * V_ECHELLE), (V_INT[0] * V_ECHELLE, V_INT[1] * V_ECHELLE)
    tout = _couverture((H, W), c2, e1, i2)
    jante = _couverture((H, W), c2, e2, i1)
    tout[V_BAS:, :] = 0
    jante[V_BAS:, :] = 0
    o = out.astype(np.float32)
    o = o * (1 - tout[..., None]) + contour_c * tout[..., None]          # anneau entier en couleur du contour
    o = o * (1 - jante[..., None]) + jante_c * jante[..., None]          # puis la jante par-dessus
    out = np.clip(np.rint(o), 0, 255).astype(np.uint8)
    ys2, xs2 = np.nonzero(tout > 0)
    x0, y0, nw, nh = xs2.min(), ys2.min(), xs2.max() - xs2.min() + 1, ys2.max() - ys2.min() + 1
    # l'essuie-glace droit repasse devant (pixels sombres d'origine le long de son axe)
    (ax, ay), (bx, by) = ESSUIE
    yy, xx = np.mgrid[0:H, 0:W]
    t = np.clip(((xx - ax) * (bx - ax) + (yy - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2), 0, 1)
    dist = np.hypot(xx - (ax + t * (bx - ax)), yy - (ay + t * (by - ay)))
    lum = img.astype(np.float32).mean(2)
    essuie = (dist < 9) & (lum < 120)          # le balai et son bord, sans élargir (pas de liseré clair)
    box = np.zeros((H, W), bool)
    box[y0 - 2:y0 + nh + 2, x0 - 2:x0 + nw + 2] = True
    out[essuie & box] = img[essuie & box]
    return out


# --------------------------------------------------------------------------- 2. couleurs
# cibles mesurées sur P01 v33 (Lab OpenCV : 128 = neutre) — chaque surface de P02 prend la teinte de la même
# surface dans P01 : la chaussée = l'asphalte ; le trottoir de gauche de P02 = le trottoir sud (côté narrateur,
# à droite dans P01) ; le trottoir de droite de P02 = le trottoir nord (chez Jeannot, à gauche dans P01).
#   nom : (L premier plan, L fond, a, b, part des écarts de teinte gardée), graines du remplissage
#   nom : ((mode, ...), graines du remplissage)
#     mode "profil" : (L premier plan, L fond, a, b, part des écarts de teinte gardée) — luminosité ramenée à P01
#     mode "garde"  : (facteur de L, a, b, part des écarts de teinte gardée) — on garde la clarté (ombres, bordures)
SURFACES = {
    "chaussee": (("profil", 140.0, 152.0, 129.0, 131.0, 1.0),
                 [(200, 960), (420, 640), (900, 1040), (330, 470), (1500, 1065), (1250, 1060), (1800, 1060),
                  (1000, 960), (1120, 885)]),
    "trottoir_gauche": (("profil", 116.0, 138.0, 128.0, 131.0, 0.5), [(40, 640), (110, 520), (20, 760), (150, 470)]),
    "trottoir_droit": (("profil", 136.0, 142.0, 128.0, 131.0, 0.5), [(640, 470), (820, 545), (560, 447), (950, 590)]),
    # trottoir côté Jeannot qui réapparaît sous l'avant de la 4L, dans son ombre
    "trottoir_droit_ombre": (("garde", 0.95, 128.0, 131.0, 0.5), [(1750, 990), (1790, 960), (1880, 1020),
                                                                (1900, 1072), (1880, 1065)]),
}
# bordures de trottoir : bandes claires et chaudes qui longent les surfaces ci-dessus (même traitement « garde »)
BORDURES = ("garde", 0.95, 128.0, 131.0, 0.5)
ENJI = (430, 690, 1000, 1045)   # rectangle d'Enji : son pelage fauve n'est pas une bordure
CIEL_P01 = (218.0, 125.0, 115.0)  # L, a, b médians du ciel de P01 v33 (pour mémoire)
# le bleu franc de P01 n'existe pas dans la v3 et le contrôle refuse les couleurs absentes de l'image : le ciel
# prend le bleu pâle le plus proche déjà présent (mêmes cases de couleur que le ciel d'origine)
CIEL_RGB = (190.0, 208.0, 218.0)


def masques_sol(img):
    """Une zone par surface (remplissage depuis ses graines, arrêté par les traits de contour)."""
    H, W = img.shape[:2]
    lisse = cv2.bilateralFilter(img, 7, 30, 5)
    lab = cv2.cvtColor(lisse, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    cand = (L > 55) & (L < 228) & (np.hypot(A, B) < 26) & (B > -4) & (A < 12)
    cand[:410, :] = False                       # au-dessus : grillage, colline, maisons
    pris = np.zeros((H, W), bool)
    out = {}
    for nom, (_, graines) in SURFACES.items():
        m = np.zeros((H + 2, W + 2), np.uint8)
        m[1:-1, 1:-1] = (~cand | pris).astype(np.uint8)
        for gx, gy in graines:
            if cand[gy, gx] and not pris[gy, gx]:
                cv2.floodFill(lisse.copy(), m, (gx, gy), (0, 0, 0), (7, 7, 7), (7, 7, 7),
                              4 | cv2.FLOODFILL_MASK_ONLY | (2 << 8))
        z = (m[1:-1, 1:-1] == 2)
        z = cv2.morphologyEx(z.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool) & cand & ~pris
        out[nom] = z
        pris |= z
    # bordures : pixels clairs et chauds à moins de 12 px des surfaces, hors 4L et hors Enji
    yy, xx = np.mgrid[0:H, 0:W]
    pres = cv2.dilate(pris.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    bord = (L > 95) & (B > 3) & (B < 30) & (np.hypot(A, B) < 32) & (A < 14) & pres & ~pris
    bord[:415, :] = False
    bord &= ~((xx > 1040) & (yy < 965) & ~((xx < 1180) & (yy > 840)))      # carrosserie, pare-chocs, roues
    ex0, ey0, ex1, ey1 = ENJI
    bord &= ~((xx >= ex0) & (xx < ex1) & (yy >= ey0) & (yy < ey1))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(bord.astype(np.uint8), 8)
    out["bordures"] = np.isin(lbl, [i for i in range(1, n) if st[i][4] > 150])
    return out


def _vers(lab, zone, cible):
    """Ramène une surface à sa cible (médianes ligne par ligne lissées), en gardant ombres et texture."""
    H = lab.shape[0]
    new = lab.copy()
    if cible[0] == "garde":
        _, f, ca, cb, k = cible
        if zone.sum() == 0:
            return lab
        ma, mb = np.median(lab[..., 1][zone]), np.median(lab[..., 2][zone])
        new[..., 0] = lab[..., 0] * f
        new[..., 1] = ca + (lab[..., 1] - ma) * k
        new[..., 2] = cb + (lab[..., 2] - mb) * k
        return new
    _, l0, l1, ca, cb, k = cible
    rows = np.arange(H)
    med = np.full((H, 3), np.nan, np.float32)
    for y in range(H):
        sel = zone[y]
        if sel.sum() > 25:
            med[y] = np.median(lab[y][sel], axis=0)
    ok = ~np.isnan(med[:, 0])
    if ok.sum() < 2:
        return lab
    for c in range(3):
        med[:, c] = np.interp(rows, rows[ok], med[ok, c])
        med[:, c] = cv2.GaussianBlur(med[:, c].reshape(-1, 1), (1, 0), 25).ravel()
    t = np.clip((rows - 430) / (1080 - 430), 0, 1)
    cible_L = l1 + (l0 - l1) * t
    new[..., 0] = lab[..., 0] - med[:, 0:1] + cible_L[:, None]
    new[..., 1] = ca + (lab[..., 1] - med[:, 1:2]) * k
    new[..., 2] = cb + (lab[..., 2] - med[:, 2:3]) * k
    return new


def couleurs(img, zones):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.float32)
    out = lab.copy()
    alpha = np.zeros(img.shape[:2], np.float32)
    for nom, z in zones.items():
        new = _vers(lab, z, BORDURES if nom == "bordures" else SURFACES[nom][0])
        a = cv2.GaussianBlur(z.astype(np.float32), (0, 0), 0.8)
        out = out * (1 - a[..., None]) + new * a[..., None]
        alpha = np.maximum(alpha, a)
    rgb = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    f = img.astype(np.float32)
    alpha[alpha < 0.02] = 0.0                     # hors des surfaces : pixels strictement inchangés
    res = f * (1 - alpha[..., None]) + rgb * alpha[..., None]
    # ciel (coin haut gauche, au-dessus de la colline) : décalage vers le bleu pâle, texture gardée
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    ciel = (L > 178) & (np.hypot(A, B) < 18) & (B < 8)
    ciel[125:, :] = False
    ciel[:, 330:] = False
    n, lbl = cv2.connectedComponents(ciel.astype(np.uint8))
    haut = set(np.unique(lbl[0][lbl[0] > 0])) | set(np.unique(lbl[:, 0][lbl[:, 0] > 0]))
    ciel = np.isin(lbl, list(haut))
    if ciel.sum():
        mc = np.median(f[ciel], axis=0)
        nc = f - mc + np.array(CIEL_RGB, np.float32)
        ac = cv2.GaussianBlur(ciel.astype(np.float32), (0, 0), 0.8)
        ac[ac < 0.02] = 0.0
        res = res * (1 - ac[..., None]) + nc * ac[..., None]
    return np.clip(np.rint(res), 0, 255).astype(np.uint8), ciel


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else DOSSIER / "p02-v4-volant-couleurs.png"
    img = np.asarray(Image.open(SRC).convert("RGB")).copy()
    img = volant(img)
    zones = masques_sol(img)
    img, ciel = couleurs(img, zones)
    Image.fromarray(img).save(sortie, optimize=True)
    if "--masques" in sys.argv:
        d = Path(sys.argv[sys.argv.index("--masques") + 1])
        d.mkdir(parents=True, exist_ok=True)
        for nom, z in zones.items():
            Image.fromarray((z * 255).astype(np.uint8)).save(d / f"masque-{nom}.png")
        Image.fromarray((ciel * 255).astype(np.uint8)).save(d / "masque-ciel.png")
    print("ok", sortie, "|", " · ".join(f"{n} {int(z.sum())} px" for n, z in zones.items()), "| ciel", int(ciel.sum()), "px")
    print("zones du contrôle :", ";".join(",".join(map(str, z)) for z in ZONES))


if __name__ == "__main__":
    main()
