"""P01 v21 — Henri quitte le milieu de l'escalier et monte sur le palier, en haut.

Quatre temps (tout est local, aucune retouche du reste de l'image) :
  1) le trou laissé sur les marches est rebouché par l'édition du recadrage B
     (crop-v21-B-ed : l'escalier redessiné sans Henri) ;
  2) la silhouette d'Henri, découpée dans la v20 grâce à la différence avec cette
     édition, est retournée (le visage vers la 4L, donc vers la gauche) ;
  3) elle est recollée plus haut, les pieds sur le palier (repère du calque),
     légèrement penchée vers le muret du palier (côté rue, à droite) ;
  4) une cigarette au coin des lèvres et un seul filet de fumée.

Usage : PYTHONPATH=tools python3 tools/p01_v21.py OUT.png   (depuis la racine du dépôt)
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import p01_v20 as V20

W = "assets/storyboards/a-valider/p01/work/"
ED_B = W + "crop-v21-B-ed.png"      # édition du recadrage (620,400)-(900,680) : escalier sans Henri
BX, BY, BW = 620, 400, 280          # origine et taille du recadrage B (px natifs)
PIEDS = (762, 370)                  # où poser les pieds d'Henri : le palier, côté rue (calque)
PENCHE = 10.0                       # degrés vers la droite (le muret du palier est à x≈814-827)
VISAGE = (0.69, 0.12)               # position de la bouche dans la silhouette (fraction de la boîte)
FUMEE = 44                          # longueur du filet de fumée (px)


def build(pieds=PIEDS, pencer=PENCHE, retourner=False, fumer=True):
    """pieds=None : Henri ne bouge pas (on ajoute seulement la cigarette et la fumée)."""
    deplacer = pieds is not None
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

    # 3) découper Henri, le retourner, le pencher
    masque = ndimage.binary_erosion(dif, iterations=1)
    masque = ndimage.gaussian_filter(masque.astype(float), 0.7)
    ys, xs = np.nonzero(dif)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2.0, float(y1)                            # pieds = bas de la silhouette
    bouche = np.array([x0 + VISAGE[0] * (x1 - x0), y0 + VISAGE[1] * (y1 - y0)])

    if not deplacer:                                               # Henri reste où il est dans la v20
        bouche = bouche + np.array([BX, BY])
        bx, by = float(bouche[0]), float(bouche[1])
        sens = 1                                                   # il regarde vers la droite (la rue)
        im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
        d = ImageDraw.Draw(im)
        d.line([(bx, by), (bx + 7 * sens, by - 1)], fill=(238, 236, 230), width=2)
        d.ellipse((bx + 5 * sens, by - 3, bx + 9 * sens, by + 1), fill=(250, 150, 55))
        sm = Image.new("L", im.size, 0)
        ImageDraw.Draw(sm).line(
            [(bx + 8 * sens + 2.2 * np.sin(k / 9.0) * sens + k * 0.045 * sens, by - 2 - k) for k in range(FUMEE)],
            fill=200, width=2)
        sm = np.array(sm.filter(ImageFilter.GaussianBlur(1.0)))[..., None] / 255.0
        a = np.array(im).astype(float) * (1 - sm) + np.array([206, 205, 202]) * sm
        return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))

    img = Image.fromarray(np.clip(zone0, 0, 255).astype("uint8"))
    img.putalpha(Image.fromarray((np.clip(masque, 0, 1) * 255).astype("uint8")))
    sens = -1 if retourner else 1
    if retourner:                                                  # miroir autour de l'axe de l'image
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        cx, bouche[0] = (BW - 1) - cx, (BW - 1) - bouche[0]
    t = np.radians(pencer)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])   # sens horaire : le haut part vers la droite
    bouche = R @ (bouche - np.array([cx, cy])) + np.array([cx, cy])
    if pencer:
        img = img.rotate(-pencer, resample=Image.BICUBIC, center=(cx, cy), expand=False)

    zone1 = np.array(img.convert("RGB")).astype(float)
    zone1 = np.array(Image.fromarray(np.clip(zone1, 0, 255).astype("uint8"))
                     .filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=0))).astype(float)
    m = (np.array(img.getchannel("A")).astype(float) / 255.0)[..., None]

    dx, dy = int(round(pieds[0] - (BX + cx))), int(round(pieds[1] - (BY + cy)))

    # harmonisation : le mur derrière le palier est un peu plus clair que les marches
    def moy(im_, mm):
        return (im_ * mm).sum(axis=(0, 1)) / max(mm.sum(), 1e-6)

    zd = a[BY + dy:BY + dy + BW, BX + dx:BX + dx + BW]
    g = moy(zd, 1 - m) / np.maximum(moy(zone1 * m, m), 1e-6)
    henr = zone1 * np.clip(g, 0.80, 1.25)[None, None, :]
    a[BY + dy:BY + dy + BW, BX + dx:BX + dx + BW] = zd * (1 - m) + henr * m

    if fumer:                                                       # 4) cigarette + un seul filet de fumée
        bx, by = bouche[0] + BX + dx, bouche[1] + BY + dy
        im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
        d = ImageDraw.Draw(im)
        d.line([(bx, by), (bx + 7 * sens, by - 1)], fill=(238, 236, 230), width=2)
        d.ellipse((bx + 5 * sens, by - 3, bx + 9 * sens, by + 1), fill=(250, 150, 55))
        sm = Image.new("L", im.size, 0)
        ds = ImageDraw.Draw(sm)
        pts = [(bx + 8 * sens + (2.2 * np.sin(k / 9.0) + k * 0.045) * sens, by - 2 - k) for k in range(FUMEE)]
        ds.line(pts[:FUMEE // 2], fill=235, width=3)               # plus dense près de la cigarette
        ds.line(pts[FUMEE // 2 - 1:], fill=150, width=2)           # s'étire et s'efface en montant
        sm = np.array(sm.filter(ImageFilter.GaussianBlur(1.0)))[..., None] / 255.0
        a = np.array(im).astype(float) * (1 - sm) + np.array([206, 205, 202]) * sm

    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


if __name__ == "__main__":
    build().save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w/v21.png")
    print("ok")
