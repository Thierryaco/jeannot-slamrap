"""P01 v21 — Henri quitte le milieu de l'escalier et monte sur le palier, en haut.

Deux temps (tout est local, aucune retouche du reste de l'image) :
  1) le trou laissé sur les marches est rebouché par l'édition du recadrage B
     (crop-v21-B-ed : l'escalier redessiné sans Henri) ;
  2) la silhouette d'Henri, découpée dans la v20 grâce à la différence avec cette
     édition, est recollée plus haut, les pieds sur le palier (repère du calque).

Usage : PYTHONPATH=tools python3 tools/p01_v21.py OUT.png   (depuis la racine du dépôt)
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import p01_v20 as V20

W = "assets/storyboards/a-valider/p01/work/"
ED_B = W + "crop-v21-B-ed.png"      # édition du recadrage (620,400)-(900,680) : escalier sans Henri
BX, BY, BW = 620, 400, 280          # origine et taille du recadrage B (px natifs)
PIEDS = (762, 370)                  # où poser les pieds d'Henri : le palier, côté rue (calque)


def build(pieds=PIEDS):
    a = np.array(V20.build()).astype(float)
    zone0 = a[BY:BY + BW, BX:BX + BW].copy()                      # v20 dans le recadrage
    brut = Image.open(ED_B).convert("RGB").resize((BW, BW), Image.LANCZOS)
    # l'édition générée est un peu plus douce que l'image : léger renfort de netteté avant collage
    ed = np.array(brut.filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=0))).astype(float)
    brut = np.array(brut).astype(float)

    # 1) ce que l'édition a changé = la silhouette d'Henri (plus d'éventuelles retouches)
    dif = np.abs(brut - zone0).mean(2) > 18
    dif = ndimage.binary_closing(ndimage.binary_opening(dif, np.ones((2, 2))), np.ones((5, 5)))
    dif = ndimage.binary_fill_holes(dif)
    lab, n = ndimage.label(dif)
    if n:                                                          # on ne garde que le plus gros morceau : Henri
        tailles = ndimage.sum(dif, lab, range(1, n + 1))
        dif = lab == (1 + int(np.argmax(tailles)))

    # 2) reboucher l'escalier avec l'édition (masque un peu élargi et adouci)
    trou = ndimage.binary_dilation(dif, iterations=2)
    trou = ndimage.gaussian_filter(trou.astype(float), 0.9)[..., None]
    a[BY:BY + BW, BX:BX + BW] = zone0 * (1 - trou) + ed * trou

    # 3) découper Henri dans la v20 et le recoller plus haut, les pieds sur le palier
    masque = ndimage.binary_erosion(dif, iterations=1)
    masque = ndimage.gaussian_filter(masque.astype(float), 0.7)[..., None]
    ys, xs = np.nonzero(dif)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2.0, float(y1)                            # pieds = bas de la silhouette
    dx, dy = int(round(pieds[0] - (BX + cx))), int(round(pieds[1] - (BY + cy)))

    henr = zone0 * masque                                          # Henri seul (fond à 0)
    fond = 1 - masque

    # harmonisation : Henri est éclairé pareil, mais le mur derrière le palier est un peu
    # plus clair que les marches ; on corrige le gain canal par canal, sans toucher au trait.
    def moy(img, m):
        return (img * m).sum(axis=(0, 1)) / max(m.sum(), 1e-6)

    zd = a[BY + dy:BY + dy + BW, BX + dx:BX + dx + BW]
    g = moy(zd, fond) / np.maximum(moy(henr, masque), 1e-6)
    g = np.clip(g, 0.80, 1.25)
    henr = henr * g[None, None, :]

    zd_new = zd * (1 - masque) + henr * masque
    a[BY + dy:BY + dy + BW, BX + dx:BX + dx + BW] = zd_new
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8")), (x0 + BX, y0 + BY, x1 + BX, y1 + BY, dx, dy)


if __name__ == "__main__":
    im, info = build()
    im.save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w/v21.png")
    print(f"silhouette v20 x {info[0]}..{info[2]}, y {info[1]}..{info[3]} -> déplacée de ({info[4]},{info[5]})")
