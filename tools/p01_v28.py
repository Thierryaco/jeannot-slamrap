"""P01 v28 — v27 avec UN SEUL trait sous la rampe (avis du 14/10 : « je préfère un seul trait »).

Dans la v26/v27, le dessous de la rampe était un double trait : la droite fine (813, 449)→(765, 552)
qui remplaçait les dents de scie, la bande claire, puis le trait épais (818, 452)→(771, 548) et le trait
du bas (764, 554)→(738, 602). Sous le palier, la même bande continuait à l'horizontale entre un trait
supérieur incliné (814,5, 440)→(841, 448) et le trait inférieur (y ≈ 450–452).

Ici : trait fin, trait épais, trait du bas, trait supérieur du palier et bande claire sont effacés
(couleur de la rampe / du palier / du mur voisin, ligne par ligne, avec leur grain) ; le trait
inférieur du palier est gardé ; un seul trait droit de 2 px va du coin (818,3, 450,8) au pied de
l'escalier (738, 602).

Usage : python3 tools/p01_v28.py [OUT.png]   (depuis la racine du dépôt)
"""
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P = "assets/storyboards/a-valider/p01/"
V27 = P + "p01-v27-porte.png"
FIN = (813.0, 449.0), (765.0, 552.0)       # droite fine de la v26 (effacée)
EPAIS = (818.0, 452.0), (771.0, 548.0)     # trait épais de la v24 (effacé)
BAS = (764.0, 554.0), (738.0, 602.0)       # trait du bas (effacé, redessiné par le trait unique)
TRAIT = (818.3, 450.8), (738.0, 602.0)     # le trait unique
LARGEUR = 2.0
PORTE_X = 798.5                            # bord gauche de l'encadrement de la porte (v27)
HAUT_PALIER = (814.5, 440.0), (841.0, 448.0)   # trait supérieur du palier (effacé)


def _x(seg, y):
    (x0, y0), (x1, y1) = seg
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)


def _y(seg, x):
    (x0, y0), (x1, y1) = seg
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _bornes(y):
    """Zone à repeindre sur la ligne y (bord gauche, bord droit) autour des anciens traits."""
    if y <= 548:
        g, d = _x(FIN, y) - 3, _x(EPAIS, y) + 4
    elif y <= 557:
        g, d = min(_x(FIN, min(y, 552)), _x(BAS, y)) - 3, _x(EPAIS, 548) + 4
    else:
        g, d = _x(BAS, y) - 3, _x(BAS, y) + 3.5
    if y >= 492:
        d = min(d, PORTE_X)
    if y < 456:
        d = min(d, 819)      # sous le palier, à droite du coin : traité à l'étape 2b
    return g, d


def build():
    a = np.asarray(Image.open(V27).convert("RGB"), float).copy()
    src = a.copy()
    h, w, _ = a.shape
    L = src.mean(2)
    rng = np.random.default_rng(28)
    grain = gaussian_filter(rng.standard_normal((h, w)), 1.5)
    grain *= 2.2 / grain[440:600, 760:842].std()
    gr = lambda y, x: 1 + grain[y, x] / 160

    # teinte du trait : cœur du trait épais d'origine
    coeurs = []
    for y in range(462, 540):
        x0 = int(_x(EPAIS, y)) - 2
        coeurs.append(src[y, x0 + int(np.argmin(L[y, x0:x0 + 5]))])
    teinte = np.median(np.array(coeurs), 0)

    # couleurs de référence par ligne : face de la rampe (à gauche), mur (à droite)
    face, mur = {}, {}
    for y in range(445, 602):
        g, d = _bornes(y)
        px = [src[y, x] for x in range(int(g) - 6, int(g) - 1) if L[y, x] > 140]
        if len(px) >= 2:
            face[y] = np.median(np.array(px), 0)
        lim = PORTE_X if y >= 492 else 817
        px = [src[y, x] for x in range(int(np.ceil(d)) + 1, int(min(np.ceil(d) + 7, lim))) if L[y, x] > 110]
        if len(px) >= 2:
            mur[y] = np.median(np.array(px), 0)
    yf, ym = np.array(sorted(face)), np.array(sorted(mur))
    proche = lambda dic, ys, y: np.mean([dic[t] for t in ys[np.argsort(np.abs(ys - y))[:5]]], 0)

    # 1. sous la rampe : tout l'ancien double trait -> face (à gauche du trait unique) / mur (à droite)
    for y in range(449, 600):
        xt = _x(TRAIT, y)
        g, d = _bornes(y)
        cf, cm = proche(face, yf, y), proche(mur, ym, y)
        for x in range(int(np.floor(g)), int(np.ceil(d))):
            a[y, x] = (cf if x + 0.5 < xt else cm) * gr(y, x)

    # 1b. l'ombre douce que le dessous de l'escalier porte sur le mur (bande plus sombre le long de
    #     l'ancien trait épais) suit le nouveau trait : profil du mur décalé de l'écart entre les deux
    for y in range(452, 549):
        x0 = int(round(_x(EPAIS, y)))
        coeur = x0 - 3 + int(np.argmin(L[y, x0 - 3:x0 + 4]))     # cœur réel de l'ancien trait épais
        bord_nouveau = _x(TRAIT, y) + LARGEUR / 2
        s = (coeur + 1.5) - bord_nouveau
        lim = PORTE_X - 0.5 if y >= 492 else 828.5                # porte / bord du pan gris
        for x in range(int(np.ceil(bord_nouveau)), int(coeur + 1.5 + 9)):
            xs = x + s
            if xs + 1 >= lim:
                break
            i = int(np.floor(xs))
            f = xs - i
            a[y, x] = src[y, i] * (1 - f) + src[y, i + 1] * f

    # 2. sous le palier : trait supérieur (et son liseré clair), coin et bande -> face du palier ;
    #    le trait inférieur est gardé (on s'arrête au-dessus de son bord haut)
    for x in range(811, 841):
        yh = _y(HAUT_PALIER, max(x, 814.5))
        cf = np.median(src[int(yh) - 11:int(yh) - 5, x], 0)
        haut_inf = next((r for r in range(int(round(yh)) + 2, 457) if L[r, x] < 130), 452)
        y_fin = haut_inf - 1 if x >= 819 else 452
        for y in range(int(np.floor(yh)) - 3, y_fin):
            if x >= 819 or y < 450 or x + 0.5 < _x(TRAIT, y):
                a[y, x] = cf * gr(y, x)

    # 2b. juste sous le trait inférieur du palier, le dessin d'origine avait un second trait horizontal
    #     (y ≈ 453, prolongement du haut de l'ancien trait épais) et un mince triangle clair entre les
    #     deux : on les remplace par ce qu'il y a dessous -> bande de mur (x 819–828), bord du pan gris
    #     prolongé jusqu'au trait (x 829–830), pan gris (x 831–840). Le bord droit du palier est gardé.
    for x in range(819, 841):
        r0 = int(round(449 + (x - 819) * 0.2)) - 1
        coeur = r0 + int(np.argmin(L[r0:r0 + 3, x]))          # cœur du trait inférieur du palier
        if x <= 828:
            cm = np.median(src[456:461, x], 0)
        elif x <= 830:
            cm = src[457, x]
        else:
            cm = np.median(src[456:461, x], 0)
        y = coeur + 1                                          # rangée d'anticrénelage : la plus sombre
        a[y, x] = src[y, x] if src[y, x].mean() < cm.mean() else cm * gr(y, x)
        for y in range(coeur + 2, 457):
            a[y, x] = cm * gr(y, x)

    # 3. le trait unique, anti-crénelé, du coin jusqu'au pied de l'escalier
    (xa, ya), (xb, yb) = TRAIT
    yy, xx = np.mgrid[448:602, 732:822]
    dx, dy = xb - xa, yb - ya
    t = np.clip(((xx + 0.5 - xa) * dx + (yy + 0.5 - ya) * dy) / (dx * dx + dy * dy), 0, 1)
    dist = np.hypot(xx + 0.5 - (xa + t * dx), yy + 0.5 - (ya + t * dy))
    cov = np.clip(LARGEUR / 2 + 0.5 - dist, 0, 1)
    cov[yy + 0.5 < ya] = 0
    cov = cov[..., None]
    a[yy, xx] = a[yy, xx] * (1 - cov) + teinte * cov
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8"))


if __name__ == "__main__":
    im = build()
    if len(sys.argv) > 1:
        sortie = sys.argv[1]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v28.png")
    im.save(sortie)
    d = np.abs(np.asarray(im, float) - np.asarray(Image.open(V27).convert("RGB"), float)).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
