"""P01 v24 / v25 — on repart de la v20 (décision du 14/10 : v21, v22, v23 supprimées).

Avis v20 (14/10) : « retire moi le portail avec la clôture qu'il y a sous l'escalier d'henri ».
Avis v19 (13/10) : « ... rajoute plutôt une porte directement sur la maison, c'est plus logique ».

Le portail = deux piliers carrés + portillon en bois + petit morceau de clôture à barreaux sur muret,
au pied de l'escalier d'Henri, entre le muret de l'escalier et le garage (image x 772–850, y 497–615).
(La zone x 706–782 / y 317–425 notée autrefois dans REPRISE est la porte d'entrée de l'étage : intacte.)

Méthode : recadrage 320×320 en (651, 396) → édition (work/crop-v24-{A,B}-ed.png, 1024×1024) → on ne
recolle QUE les pixels réellement changés (composantes connexes qui touchent la zone du portail),
avec un fondu de 1,5 px. Tout le reste de l'image est la v20 au pixel près.

  v24 (option A) : portail et clôture retirés, mur sous l'escalier prolongé jusqu'au sol.
  v25 (option B) : v24 + une porte dans le mur de la maison (seule la porte vient de l'édition B).

Usage : python3 tools/p01_v24.py A|B [OUT.png]   (depuis la racine du dépôt)
"""
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

P = "assets/storyboards/a-valider/p01/"
W = P + "work/"
V20 = P + "p01-v20-nette.png"
BOX = (651, 396, 971, 716)        # recadrage de travail (320×320)
PORTAIL = (772, 497, 850, 615)    # zone du portail dans l'image 1920×1080
PORTE = (794, 494, 838, 616)      # option B : zone de la porte (cadre + seuil) dans l'image
SEUIL = 22                        # écart moyen RVB à partir duquel un pixel est « changé »


def edition(nom):
    """Édition ramenée à la taille du recadrage, et l'écart avec la v20 (en 320×320)."""
    v20 = Image.open(V20).convert("RGB")
    o = np.asarray(v20.crop(BOX), float)
    e = Image.open(W + nom).convert("RGB").resize((BOX[2] - BOX[0], BOX[3] - BOX[1]), Image.LANCZOS)
    e = np.asarray(e, float)
    return v20, o, e, np.abs(e - o).mean(2)


def masque_portail(d):
    """Pixels changés reliés à la zone du portail (on écarte les petites variations ailleurs)."""
    m = d > SEUIL
    m = ndimage.binary_closing(m, iterations=2)
    lab, n = ndimage.label(m)
    x0, y0, x1, y1 = (PORTAIL[0] - BOX[0], PORTAIL[1] - BOX[1], PORTAIL[2] - BOX[0], PORTAIL[3] - BOX[1])
    garde = set(np.unique(lab[y0:y1, x0:x1])) - {0}
    m = np.isin(lab, list(garde))
    m = ndimage.binary_fill_holes(m)
    return ndimage.binary_dilation(m, iterations=2)


def coller(fond, e, m, flou=1.5):
    a = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(flou))
    a = np.asarray(a, float)[..., None] / 255.0
    return fond * (1 - a) + e * a, a[..., 0]


def build(option="A"):
    v20, o, eA, dA = edition("crop-v24-A-ed.png")
    mA = masque_portail(dA)
    c, alpha = coller(o, eA, mA)
    if option == "B":
        # seulement la porte (vantail, encadrement, seuil) : pixels où l'édition B diffère de la v24,
        # dans le rectangle de la porte — le mur de l'édition B (plus clair) n'est pas recollé
        _, _, eB, _ = edition("crop-v24-B-ed.png")
        dB = np.abs(eB - c).mean(2)
        r = np.zeros(mA.shape, bool)
        r[PORTE[1] - BOX[1]:PORTE[3] - BOX[1], PORTE[0] - BOX[0]:PORTE[2] - BOX[0]] = True
        mB = ndimage.binary_closing((dB > SEUIL) & r, iterations=2)
        lab, n = ndimage.label(mB)
        if n:
            tailles = ndimage.sum(mB, lab, range(1, n + 1))
            mB = lab == (1 + int(np.argmax(tailles)))
        mB = ndimage.binary_dilation(ndimage.binary_fill_holes(mB), iterations=1) & r
        c, aB = coller(c, eB, mB, flou=1.0)
        alpha = np.maximum(alpha, aB)
    img = np.asarray(v20, float).copy()
    img[BOX[1]:BOX[3], BOX[0]:BOX[2]] = c
    return Image.fromarray(np.clip(img, 0, 255).astype("uint8")), alpha


def zone_controle(alpha, marge=3):
    ys, xs = np.nonzero(alpha > 0.01)
    return (BOX[0] + xs.min() - marge, BOX[1] + ys.min() - marge,
            BOX[0] + xs.max() + 1 + marge, BOX[1] + ys.max() + 1 + marge)


if __name__ == "__main__":
    opt = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
    im, alpha = build(opt)
    if len(sys.argv) > 2:
        sortie = sys.argv[2]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut(f"v24-{opt}.png")
    im.save(sortie)
    print("zone modifiée (pour le contrôle) : %d,%d,%d,%d" % zone_controle(alpha))
