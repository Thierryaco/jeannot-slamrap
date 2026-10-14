#!/usr/bin/env python3
"""P02 v8 = la v7 avec les correctifs 11 et 12 de la liste (avis du 14/10 sur la v3) :

11. plus de ciel bleu comme dans P01 : la colline boisée est abaissée (toujours raide et boisée), un grand ciel
    bleu clair à nuages légers apparaît au-dessus (la carte suivra) ;
12. l'escalier de la maison du fond monte tout droit depuis le portail jusqu'à la porte de la maison et coupe le
    jardin surélevé en deux moitiés (au lieu de monter en biais le long d'un haut mur de pierre).

Méthode (retouches IA brutes dans p02/work/) :
  - ciel : v8-ia-ciel.png (recadrage x 0–1067, y 0–600 ×1,5, modèle du ciel : ref-p01-ciel.png) ;
  - escalier : v8-ia-escalier.png (recadrage x 620–1508, y 0–500 ×1,5) ;
  - les deux sont déjà alignées (décalage < 0,15 px) ; chacune est collée sur la v7 par une COUPE DE GRAPHE
    (PyMaxflow) : des zones sûres côté IA (ciel et colline au-dessus des structures ; escalier, jardin, porte) et
    côté v7 (grillage, garage, rambarde, maison, muret, portail, Jeannot, 4L), et entre les deux la frontière
    passe là où les deux images sont identiques (sur les contours eux-mêmes) — pas de liseré ;
  - la 4L et Jeannot restent strictement ceux de la v7 (lissage du bord remis à zéro sur eux).
  Tout le reste est identique à la v7.

Contrôle obligatoire (le bleu du ciel de P01 n'existe pas dans la v7 : --palette P01, demandé « comme P01 ») :
  python3 tools/controle_retouche.py p02-v7-maison-route.png p02-v8-ciel-escalier.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v8-controle.jpg \\
      --palette assets/storyboards/a-valider/p01/p01-v33-net.png

Usage : python3 tools/p02_v8.py [SORTIE] [--coupes IMG]
"""
import sys
from pathlib import Path

import cv2
import maxflow
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v6  # noqa: E402  (silhouette de Jeannot)
import p02_v7  # noqa: E402  (silhouette de la 4L)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v7-maison-route.png"
V5 = DOSSIER / "p02-v5-plaque-rouille.png"
SORTIE = DOSSIER / "p02-v8-ciel-escalier.png"

CC = (0, 0, 1067, 600)          # recadrage « ciel »
CE = (620, 0, 1508, 500)        # recadrage « escalier »


def ligne_toits(x):
    """Haut des structures devant la colline (y image) : grillage de gauche, grillage du fond, puis haut de la
    dalle de la terrasse (la rambarde ajourée vient de l'IA, identique et alignée : entre ses barreaux on voit la
    nouvelle colline, pas l'ancienne)."""
    x = np.asarray(x, np.float32)
    return np.where(x < 150, 222 + 61 * x / 150, np.where(x < 549, 284.0, 198.0))


def bord_maison(y):
    """Bord gauche de la maison du fond (x image, mesuré sur la v7) : pente gauche du toit (x 994 → 962),
    avant-toit (x 961), puis façade (x 976)."""
    y = np.asarray(y, np.float32)
    return np.where(y < 78, 994 - 0.42 * y, np.where(y < 92, 961.0, 976.0))


def graines_ciel(H, W):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    toit, maison = ligne_toits(xx), bord_maison(yy)
    ia = (yy < toit - 12) & (xx < maison - 8)
    garde = (yy > toit + 10) | (xx > maison + 4) | (yy > 300)
    return ia, garde


def silhouettes_persos(v7):
    """Jeannot (silhouette de p02_v6) et la 4L (p02_v7) dans l'image entière."""
    v5 = np.asarray(Image.open(V5).convert("RGB"))
    jeannot = np.zeros(v7.shape[:2], bool)
    for nom, fichier, rc, retournee, boite in p02_v6.PERSOS:
        if nom != "jeannot":
            continue
        x0, y0, x1, y1 = rc
        _, nouvelle = p02_v6.masque(v5[y0:y1, x0:x1], p02_v6.charger(fichier, rc, retournee), boite)
        jeannot[y0:y1, x0:x1] = nouvelle
    car = p02_v7.silhouette_4l(v7)
    return jeannot, car


def graines_escalier(H, W, jeannot, car):
    yy, xx = np.mgrid[0:H, 0:W]
    def boite(x0, y0, x1, y1):
        return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    porte = boite(1125, 65, 1188, 192)
    ia = boite(1105, 195, 1480, 355) | porte | boite(850, 215, 1100, 330)
    j = cv2.dilate(jeannot.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    garde = (j | car | boite(0, 0, 935, 232) | boite(0, 0, 840, 380)
             | (boite(935, 0, 1310, 168) & ~porte) | boite(1310, 0, 1488, 95) | boite(1488, 0, W, H)
             | boite(0, 378, 990, H) | boite(0, 470, W, H))
    ia &= ~garde
    return ia, garde


def coupe_graphe(a, b, ia, garde):
    """Étiquette chaque pixel : True = image b (IA), False = image a (v7). Coût d'une frontière entre p et q :
    |a−b|(p) + |a−b|(q) (+1) — elle passe là où les deux images sont identiques."""
    d = np.abs(a.astype(np.float32) - b.astype(np.float32)).sum(axis=2)
    d = cv2.GaussianBlur(d, (0, 0), 1.0) + 1.0
    H, W = d.shape
    g = maxflow.Graph[float]()
    ids = g.add_grid_nodes((H, W))
    wr = np.zeros((H, W), np.float32); wr[:, :-1] = d[:, :-1] + d[:, 1:]
    wd = np.zeros((H, W), np.float32); wd[:-1, :] = d[:-1, :] + d[1:, :]
    g.add_grid_edges(ids, weights=wr, structure=np.array([[0, 0, 0], [0, 0, 1], [0, 0, 0]]), symmetric=True)
    g.add_grid_edges(ids, weights=wd, structure=np.array([[0, 0, 0], [0, 0, 0], [0, 1, 0]]), symmetric=True)
    inf = 1e12
    g.add_grid_tedges(ids, np.where(ia, inf, 0.0), np.where(garde, inf, 0.0))
    g.maxflow()
    return ~g.get_grid_segments(ids)       # segment « source » = IA


def coller(res, src, m, protege):
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.6)   # bord anti-crénelé côté décor
    a[a < 0.02] = 0.0
    a[protege] = 0.0
    return res * (1 - a[..., None]) + src.astype(np.float32) * a[..., None], a


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v7 = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = v7.shape[:2]
    jeannot, car = silhouettes_persos(v7)
    protege = jeannot | car
    res = v7.astype(np.float32)
    zones, infos, masques = [], [], []
    for nom, rc in (("ciel", CC), ("escalier", CE)):
        x0, y0, x1, y1 = rc
        ia_img = np.asarray(Image.open(TRAVAIL / f"v8-ia-{nom}.png").convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))
        a = v7[y0:y1, x0:x1]
        if nom == "ciel":
            gi, gg = graines_ciel(H, W)
        else:
            gi, gg = graines_escalier(H, W, jeannot, car)
        lab = coupe_graphe(a, ia_img, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
        m = np.zeros((H, W), bool); m[y0:y1, x0:x1] = lab
        full = v7.copy(); full[y0:y1, x0:x1] = ia_img
        res, al = coller(res, full, m, protege)
        ys, xs = np.nonzero(al > 0)
        zones.append((max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1), min(W, int(xs.max()) + 2), min(H, int(ys.max()) + 2)))
        infos.append(f"{nom} {int(m.sum())} px")
        masques.append(m)
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    print(f"ok {sortie} | " + " · ".join(infos))
    print("zones du contrôle : " + ";".join(",".join(map(str, z)) for z in zones))
    if "--coupes" in sys.argv:
        vis = out.copy()
        for m, col in zip(masques, ([255, 0, 255], [0, 255, 255])):
            e = m ^ cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            vis[e] = col
        Image.fromarray(vis).save(sys.argv[sys.argv.index("--coupes") + 1])


if __name__ == "__main__":
    main()
