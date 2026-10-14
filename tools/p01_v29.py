"""P01 v29 — Henri quitte le milieu de son escalier (avis v19 : il doit être sur le palier).

Étape 1 (ce fichier, sans IA) : effacer Henri des marches à partir de la v28 et reconstituer ce qu'il
cachait, rangée par rangée, à partir de ce qui est visible juste à côté de lui :
  - le mur beige (interpolé entre gauche et droite), et sa ligne de soubassement inclinée, recopiée
    le long de sa pente ;
  - les marches : bandes horizontales recopiées sur la même rangée (les nez de marche se raccordent
    donc forcément), bouts de marche cachés redessinés dans la suite des bouts visibles
    (… 737, 731,5, 726, 720,5, 715 … : −5,5 px par marche) ;
  - la main courante sous ses chaussures : recopiée le long de sa pente (x recule de 0,53 px par rangée).

Étape 2 : poser Henri sur le palier, penché, les avant-bras sur le rebord du muret, en train de
fumer, le visage tourné vers la gauche (vers le bas de l'escalier et la 4L). Il a été dessiné par
retouche IA sur le recadrage (700, 270)–(900, 470) agrandi en 1024 px (work/crop-v29-1024.png →
work/crop-v29-ed6.png, avec work/henri-pose-v29.png comme modèle de pose, lui-même tiré d'un essai
d'après assets/art/henri-character-v2.png). L'IA a laissé le fond intact (écart médian 3) : on ne
recolle que la silhouette d'Henri et sa fumée, isolées par différence, avec un bord adouci.

Usage : python3 tools/p01_v29.py [OUT.png]   (depuis la racine du dépôt)
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter

P = "assets/storyboards/a-valider/p01/"
V28 = P + "p01-v28-trait.png"
W = P + "work/"
RECADRAGE = (700, 270, 900, 470)       # zone envoyée à l'IA (agrandie ×5,12 en 1024 px)
FUMEE = (690, 540, 770, 700)           # zone de la fumée dans le recadrage 1024 (x0, y0, x1, y1)

# emprise d'Henri sur la v28, rangée par rangée (y0, y1 inclus, x0, x1 inclus), avec 1 px de marge
EMPRISE = [(426, 427, 722, 741), (428, 430, 718, 742), (431, 452, 712, 744), (453, 470, 711, 736),
           (471, 477, 711, 735), (478, 487, 711, 737), (488, 495, 712, 735), (496, 504, 714, 733),
           (505, 537, 716, 731), (538, 548, 715, 737)]
# marches : (rangée du nez, x du bout gauche) ; 731,5 / 726 / 720,5 sont cachés par Henri
MARCHES = [(446, 752), (453.5, 747), (461, 742), (470, 737), (477.5, 731.5), (487, 726),
           (495, 720.5), (504.5, 715), (514, 709.5), (524, 703.5), (534, 697.5), (545.5, 691)]
BOUTS_CACHES = (731.5, 726, 720.5)


def bord_ext(y):
    """Trait extérieur (haut) de la main courante."""
    return 774 - 0.53 * (y - 458)


def bout_marche(y):
    x = None
    for yk, xk in MARCHES:
        if y >= yk:
            x = xk
    return x


def emprise(y):
    for y0, y1, x0, x1 in EMPRISE:
        if y0 <= y <= y1:
            return x0, x1
    return None


def _ligne(src, y, x):
    """Valeur interpolée en x (sous-pixel) sur la rangée y."""
    i = int(np.floor(x))
    f = x - i
    return src[y, i] * (1 - f) + src[y, i + 1] * f


def _colonne(src, x, y):
    """Valeur interpolée en y (sous-pixel) sur la colonne x."""
    i = int(np.floor(y))
    f = y - i
    return src[i, x] * (1 - f) + src[i + 1, x] * f


def retirer_henri(img):
    a = np.asarray(img.convert("RGB"), float).copy()
    src = a.copy()
    L = src.mean(2)
    h, w, _ = a.shape
    rng = np.random.default_rng(29)
    grain = gaussian_filter(rng.standard_normal((h, w)), 1.5)
    grain *= 2.0 / grain[420:560, 700:750].std()
    gr = lambda y, x: 1 + grain[y, x] / 170

    # ligne de soubassement : rangée la plus sombre des colonnes visibles, ajustée par une droite
    xs = [x for x in list(range(690, 712)) + list(range(745, 759))]
    ys = [418 + int(np.argmin(L[418:446, x])) for x in xs]
    pente, orig = np.polyfit(xs, ys, 1)
    soub = lambda x: pente * x + orig

    # teinte du cœur des bouts de marche visibles
    coeurs = [src[y, 715] for y in range(506, 513)] + [src[y, 737] for y in range(471, 477)]
    teinte_bout = np.median(np.array(coeurs), 0)

    # références de mur par rangée (à gauche / à droite d'Henri), lissées sur ±2 rangées
    mur_g, mur_d = {}, {}
    for y in range(426, 506):
        e = emprise(y)
        if not e:
            continue
        x0, x1 = e
        px = [src[y, x] for x in range(x0 - 4, x0) if L[y, x] > 150]
        if px:
            mur_g[y] = np.median(np.array(px), 0)
        xb = bout_marche(y)
        lim = (xb - 1.5) if xb is not None else x1 + 5
        px = [src[y, x] for x in range(x1 + 1, int(min(x1 + 5, lim))) if L[y, x] > 150]
        if px:
            mur_d[y] = np.median(np.array(px), 0)

    def lisse(dic, y):
        vals = [dic[t] for t in range(y - 2, y + 3) if t in dic]
        if vals:
            return np.mean(vals, 0)
        ks = sorted(dic, key=lambda t: abs(t - y))[:3]
        return np.mean([dic[t] for t in ks], 0)

    for y in range(426, 549):
        e = emprise(y)
        if not e:
            continue
        x0, x1 = e
        xb = bout_marche(y)
        xe = bord_ext(y)
        for x in range(x0, x1 + 1):
            # 1. la main courante (trait extérieur et dessus) : recopiée le long de sa pente, depuis
            #    la rangée 532 (au-dessus des chaussures) et la rangée 550 (en dessous), selon la distance
            if x >= xe - 2.5:
                tb = (y - 532) / (550 - 532)
                a[y, x] = (_ligne(src, 532, x + 0.53 * (y - 532)) * (1 - tb)
                           + _ligne(src, 550, x - 0.53 * (550 - y)) * tb)
                continue
            # 2. la marche (à droite de son bout gauche)
            if xb is not None and x > xb + 1:
                g = [src[y, t] for t in range(max(int(np.ceil(xb + 2)), x0 - 3), x0)]
                d = [src[y, t] for t in range(x1 + 1, int(min(x1 + 4, xe - 2.5)))]
                cg = np.median(np.array(g), 0) if g else None
                cd = np.median(np.array(d), 0) if d else None
                if cg is not None and cd is not None:
                    t = (x - (x0 - 1)) / ((x1 + 1) - (x0 - 1))
                    c = cg * (1 - t) + cd * t
                else:
                    c = cg if cg is not None else cd
                a[y, x] = c * gr(y, x)
                continue
            # 3. le mur (avec la ligne de soubassement dans le haut)
            if y <= 452:
                dy = y - soub(x)
                cg = np.mean([_colonne(src, t, soub(t) + dy) for t in range(x0 - 4, x0)], 0)
                cd = np.mean([_colonne(src, t, soub(t) + dy) for t in range(x1 + 1, x1 + 3)], 0)
                tt = (x - (x0 - 2.5)) / ((x1 + 2) - (x0 - 2.5))
                c = cg * (1 - tt) + cd * tt
            else:
                cg = lisse(mur_g, y)
                cd = lisse(mur_d, y) if (xb is not None and xb > x1 + 2 and mur_d) else None
                if cd is not None:
                    tt = (x - (x0 - 1)) / ((x1 + 1) - (x0 - 1))
                    c = cg * (1 - tt) + cd * tt
                else:
                    c = cg
            a[y, x] = c * gr(y, x)
        # 4. bout de marche caché : trait vertical sombre, anticrénelé
        if xb in BOUTS_CACHES:
            for x in range(int(xb) - 1, int(xb) + 3):
                cov = np.clip(1.3 / 2 + 0.5 - abs(x - xb), 0, 1)
                if cov > 0 and x0 <= x <= x1:
                    a[y, x] = a[y, x] * (1 - cov) + teinte_bout * cov
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8"))


def masque_henri():
    """Silhouette d'Henri (et de sa fumée) dans le recadrage 1024, en alpha 0..1."""
    avant = np.asarray(Image.open(W + "crop-v29-1024.png").convert("RGB"), float)
    apres = np.asarray(Image.open(W + "crop-v29-ed6.png").convert("RGB").resize((1024, 1024), Image.LANCZOS), float)
    d = np.abs(apres - avant).max(2)
    lab, _ = ndi.label(ndi.binary_opening(d > 20, iterations=1))
    tailles = np.bincount(lab.ravel())
    tailles[0] = 0
    corps = ndi.binary_fill_holes(ndi.binary_closing(lab == tailles.argmax(), iterations=3))
    x0, y0, x1, y1 = FUMEE
    fumee = np.zeros_like(corps)
    fumee[y0:y1, x0:x1] = d[y0:y1, x0:x1] > 8
    fumee = ndi.binary_opening(fumee, iterations=1)
    m = ndi.binary_dilation(corps | fumee, iterations=2)
    return gaussian_filter(m.astype(float), 1.2), apres


def poser_henri(img):
    a = np.asarray(img.convert("RGB"), float).copy()
    alpha, apres = masque_henri()
    x0, y0, x1, y1 = RECADRAGE
    w, h = x1 - x0, y1 - y0
    petit = np.asarray(Image.fromarray(np.clip(apres, 0, 255).astype("uint8")).resize((w, h), Image.LANCZOS), float)
    al = np.asarray(Image.fromarray((alpha * 255).astype("uint8")).resize((w, h), Image.BOX), float)[..., None] / 255
    a[y0:y1, x0:x1] = petit * al + a[y0:y1, x0:x1] * (1 - al)
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8"))


if __name__ == "__main__":
    im = poser_henri(retirer_henri(Image.open(V28)))
    if len(sys.argv) > 1:
        sortie = sys.argv[1]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v29.png")
    im.save(sortie)
    d = np.abs(np.asarray(im, float) - np.asarray(Image.open(V28).convert("RGB"), float)).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
