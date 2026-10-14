"""P01 v26 — part de la v24 (portail retiré). Avis du 14/10 :
  « tu donneras à la partie main courante (la rampe en béton couleur blanche) la même couleur et
    texture que la façade du garage. tu remplaceras le trait noir du bas en forme d'escalier par une
    ligne rectiligne »

1. Trait en escalier (dents de scie sous la rampe, de (812, 449) à la jonction (765, 552)) : effacé
   et remplacé par une droite au même endroit, même épaisseur et même teinte de trait.
2. Rampe (bande de la main courante, face latérale, bande étroite, muret du palier, poteau du bas) :
   ses surfaces claires prennent la couleur et le grain de la façade du garage (statistiques Lab
   mesurées sur le jambage et le dessus de la porte du garage). Les traits noirs ne changent pas.

Tout le reste de l'image est la v24 au pixel près.
Usage : python3 tools/p01_v26.py [OUT.png]   (depuis la racine du dépôt)
"""
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

P = "assets/storyboards/a-valider/p01/"
V24 = P + "p01-v24-sans-portail.png"

# Tracés mesurés sur la v24 (pixels de l'image 1920×1080)
HAUT, BAS = (813.0, 449.0), (765.0, 552.0)       # nouvelle droite (à la place des dents de scie),
                                                 # part du coin où la bande étroite tourne sous le palier
EPAIS = (818.0, 452.0), (771.0, 548.0)           # trait épais du bas, déjà droit (conservé)

# Contour de la rampe : trait extérieur de la main courante (haut-gauche), poteau du bas, seuil,
# trait unique du bas, trait épais, dessous et bord droit du muret du palier.
RAMPE = [(722, 603), (722, 548), (726, 548), (733, 536), (739, 524), (746, 512), (752, 500),
         (758, 488), (765, 476), (771, 464), (774, 458), (781, 446), (787, 434), (794, 422),
         (801, 410), (804, 404), (808, 398), (812, 395), (821, 397), (842, 406), (842, 452),
         (834, 451.5), (818, 452), (815, 458), (809.5, 470), (803.5, 482), (798.5, 494),
         (793.5, 506), (787, 518), (781, 530), (774, 542), (771, 548), (766, 552), (764, 554),
         (760, 560), (757, 566), (754, 572), (751, 578), (748, 584), (744.5, 590), (741, 596),
         (738, 602)]

# Façade du garage : zones d'échantillonnage (pixels clairs seulement)
FACADE = [(855, 462, 865, 596), (872, 424, 960, 447), (853, 412, 870, 450)]


def _x_sur(seg, y):
    (x0, y0), (x1, y1) = seg
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)


def _masque_poly(poly, shape, k=4):
    """Polygone rasterisé avec bords adoucis (suréchantillonnage ×k)."""
    h, w = shape
    im = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(im).polygon([(x * k, y * k) for x, y in poly], fill=255)
    return np.asarray(im.resize((w, h), Image.BOX), float) / 255.0


def droite(a):
    """Efface les dents de scie et trace la droite HAUT→BAS (anti-crénelée)."""
    a = a.copy()
    L = a.mean(2)
    y0, y1 = int(HAUT[1]) + 3, int(BAS[1])
    # teinte du trait : cœur sombre des dents de scie
    coeur = []
    for y in range(y0, y1):
        xn = _x_sur((HAUT, BAS), y)
        for x in range(int(xn) - 6, int(xn) + 6):
            if L[y, x] < 105:
                coeur.append(a[y, x])
    teinte = np.median(np.array(coeur), 0)
    # couleurs de fond par ligne : face latérale (à gauche) et bande étroite (à droite, la plus claire)
    gauche, droite_ = {}, {}
    for y in range(y0 - 4, y1 + 5):
        xn, xe = _x_sur((HAUT, BAS), y), _x_sur(EPAIS, y)
        gauche[y] = np.median(a[y, int(xn) - 15:int(xn) - 9], 0)
        bande = a[y, int(xn) + 1:max(int(xn) + 2, int(xe) - 1)]
        droite_[y] = bande[np.argsort(bande.mean(1))[-max(1, len(bande) // 3):]].mean(0)
    lisse = lambda d, y: np.mean([d[t] for t in range(y - 4, y + 5)], 0)
    for y in range(y0, y1):
        xn, xe = _x_sur((HAUT, BAS), y), _x_sur(EPAIS, y)
        cg, cd = lisse(gauche, y), lisse(droite_, y)
        for x in range(int(xn) - 8, int(np.floor(xe - 1.5)) + 1):
            a[y, x] = cg if x + 0.5 < xn else cd
    # première marche (tiret horizontal sous le palier, à gauche du coin x 813) : effacée
    for y in range(444, y0):
        cg = np.median(a[y, 797:804], 0)
        for x in range(804, 813):
            if L[y, x] < cg.mean() - 12:
                a[y, x] = cg
    # droite anti-crénelée, épaisseur 1,7 px, distance au segment
    yy, xx = np.mgrid[int(HAUT[1]) - 3:int(BAS[1]) + 4, int(BAS[0]) - 4:int(HAUT[0]) + 5]
    (xa, ya), (xb, yb) = HAUT, BAS
    dx, dy = xb - xa, yb - ya
    t = np.clip(((xx + 0.5 - xa) * dx + (yy + 0.5 - ya) * dy) / (dx * dx + dy * dy), 0, 1)
    d = np.hypot(xx + 0.5 - (xa + t * dx), yy + 0.5 - (ya + t * dy))
    cov = np.clip(1.7 / 2 + 0.5 - d, 0, 1)[..., None]
    zone = a[yy, xx]
    a[yy, xx] = zone * (1 - cov) + teinte * cov
    return a


def recolore(a, ref):
    """Surfaces claires de la rampe -> couleur et grain de la façade du garage."""
    h, w, _ = a.shape
    lab = cv2.cvtColor((a / 255).astype(np.float32), cv2.COLOR_RGB2LAB)
    lab_ref = cv2.cvtColor((ref / 255).astype(np.float32), cv2.COLOR_RGB2LAB)
    L8 = a.mean(2)
    poly = _masque_poly(RAMPE, (h, w))
    clair = np.clip((L8 - 140) / 40, 0, 1)
    clair = clair * clair * (3 - 2 * clair)                     # transition douce (lissage)
    poids = poly * clair
    # statistiques : rampe (pixels clairs dans le polygone) et façade du garage
    m_r = (poly > 0.99) & (L8 > 150)
    m_f = np.zeros((h, w), bool)
    for x0, y0, x1, y1 in FACADE:
        m_f[y0:y1, x0:x1] = True
    m_f &= ref.mean(2) > 150
    mu_r, mu_f = lab[m_r].mean(0), lab_ref[m_f].mean(0)
    # grain de la façade : petites taches douces (deux échelles), graine fixe
    rng = np.random.default_rng(26)
    g1 = gaussian_filter(rng.standard_normal((h, w)), 2.5)
    g2 = gaussian_filter(rng.standard_normal((h, w)), 10)
    grain = g1 / g1[m_r].std() * 1.6 + g2 / g2[m_r].std() * 1.2
    new = lab.copy()
    new[..., 0] = mu_f[0] + (lab[..., 0] - mu_r[0]) * 0.6 + grain
    new[..., 1] = mu_f[1] + (lab[..., 1] - mu_r[1])
    new[..., 2] = mu_f[2] + (lab[..., 2] - mu_r[2]) * 0.7
    rgb = cv2.cvtColor(new.astype(np.float32), cv2.COLOR_LAB2RGB).astype(float) * 255
    p = poids[..., None]
    return a * (1 - p) + rgb * p, (mu_r, mu_f)


def build():
    v24 = np.asarray(Image.open(V24).convert("RGB"), float)
    a = droite(v24)
    a, stats = recolore(a, v24)
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8")), stats


if __name__ == "__main__":
    im, (mu_r, mu_f) = build()
    print("Lab moyen rampe avant :", mu_r.round(1), "| façade du garage :", mu_f.round(1))
    if len(sys.argv) > 1:
        sortie = sys.argv[1]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v26.png")
    im.save(sortie)
    d = np.abs(np.asarray(im, float) - np.asarray(Image.open(V24).convert("RGB"), float)).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
