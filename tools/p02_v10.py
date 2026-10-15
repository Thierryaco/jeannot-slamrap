#!/usr/bin/env python3
"""P02 v10 = la v9 avec les deux rectifications demandées le 15/10 après la v8 (écartée) :

  « la colline était beaucoup trop basse il va falloir rectifier — le jardin qui fait colline alors qu'il est au
    même niveau que la terrasse juste un poil plus bas »

1. colline : nettement plus haute que dans la v8 (la crête part du bord gauche vers le tiers supérieur et sort par
   le haut de l'image au-dessus de la terrasse) ; il reste un coin de ciel bleu en haut à gauche — le bleu de la
   retouche (trop saturé, cyan) est ramené à celui du ciel de P01, son vert à celui de la colline de la v9 ;
2. jardin : PLAT, au niveau de la terrasse du garage (juste un peu plus bas), tenu par un haut mur de soutènement
   en pierre le long du trottoir ; l'escalier part du trottoir, monte tout droit jusqu'à la porte de la maison et
   coupe le jardin en deux moitiés (pelouse et arbustes).

Méthode : retouches IA sur des recadrages de la v9 (p02/work/v10-ia-colline-2.png — v10-ia-colline.png, 1er essai
écarté : crête encore trop basse à gauche, jusqu'au grillage ; v10-ia-jardin-2.png, faite avec la disposition de
l'escalier de la v8 comme modèle — v10-ia-jardin.png, 1er essai écarté : escalier en biais tout à droite, jardin pas
coupé en deux) ; le jardin est recalé sur la v9 (ECC, agrandissement de 0,9 %) ; collage par
coupe de graphe (p02_v8.coupe_graphe) ; Jeannot et la 4L de la v9 restent au pixel près.
3. pied du mur : sous le nouveau mur restaient l'ancien pilier, la grille de l'ancien portail et des marches de la v9
   (x ≈ 880–1010, y ≈ 400–565, à gauche de Jeannot) ; retouche IA v10-ia-pied.png (recadrage x 620–1260,
   y 330–690 ×2 de la composition 1+2) : le mur descend jusqu'au trottoir et les premières marches de l'escalier
   partent du trottoir ; seule cette zone est collée (coupe de graphe), après recalage et accord des couleurs sur
   le mur actuel (ses pierres sortaient plus jaunes).

Contrôle obligatoire (bleu du ciel de P01 : --palette P01) :
  python3 tools/controle_retouche.py p02-v9-lumiere.png p02-v10-colline-jardin.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v10-controle.jpg \\
      --palette assets/storyboards/a-valider/p01/p01-v33-net.png

Usage : python3 tools/p02_v10.py [SORTIE] [--coupes IMG]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v6  # noqa: E402  (silhouette de Jeannot)
import p02_v7  # noqa: E402  (silhouette de la 4L)
import p02_v8  # noqa: E402  (coupe de graphe, zones sûres du ciel)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v9-lumiere.png"
V5 = DOSSIER / "p02-v5-plaque-rouille.png"
SORTIE = DOSSIER / "p02-v10-colline-jardin.png"

CC = (0, 0, 1067, 600)          # recadrage « colline »
CJ = (620, 0, 1508, 500)        # recadrage « jardin »
PORTE = (1112, 62, 1172, 194)   # porte de la maison au haut de l'escalier (nouvelle)
CP = (620, 330, 1260, 690)      # recadrage « pied du mur »
P01 = ROOT / "assets/storyboards/a-valider/p01/p01-v33-net.png"
P01_CIEL = (880, 0, 1920, 330)  # ciel de P01 v33 (modèle du bleu)
PIERRES = (680, 360, 870, 462)  # pierres du mur, identiques en dessin dans la composition et la retouche du pied
TROTTOIR = (700, 515, 880, 560) # trottoir au pied du mur, identique dans les deux


def charger(nom, rc):
    x0, y0, x1, y1 = rc
    return np.asarray(Image.open(TRAVAIL / nom).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS))


def recaler(ref, mov, garder):
    """Recalage affine (ECC) de mov sur ref, sur les parties inchangées ; renvoie mov recalé."""
    g1 = cv2.GaussianBlur(cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY), (0, 0), 1.5).astype(np.float32)
    g2 = cv2.GaussianBlur(cv2.cvtColor(mov, cv2.COLOR_RGB2GRAY), (0, 0), 1.5).astype(np.float32)
    m = np.zeros(g1.shape, np.uint8)
    for x0, y0, x1, y1 in garder:
        m[y0:y1, x0:x1] = 255
    w = np.eye(2, 3, dtype=np.float32)
    cc, w = cv2.findTransformECC(g1, g2, w, cv2.MOTION_AFFINE,
                                 (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), m, 5)
    al = cv2.warpAffine(mov, w, (ref.shape[1], ref.shape[0]), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                        borderMode=cv2.BORDER_REPLICATE)
    return al, w, cc


def silhouettes(v9):
    v5 = np.asarray(Image.open(V5).convert("RGB"))
    jeannot = np.zeros(v9.shape[:2], bool)
    for nom, fichier, rc, ret, boite in p02_v6.PERSOS:
        if nom == "jeannot":
            x0, y0, x1, y1 = rc
            _, nouvelle = p02_v6.masque(v5[y0:y1, x0:x1], p02_v6.charger(fichier, rc, ret), boite)
            jeannot[y0:y1, x0:x1] = nouvelle
    return jeannot, p02_v7.silhouette_4l(v9)


def graines_jardin(H, W, jeannot, car):
    yy, xx = np.mgrid[0:H, 0:W]
    def boite(x0, y0, x1, y1):
        return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    porte = boite(*PORTE)
    ia = boite(660, 238, 1485, 468) | porte
    # marge de 1 px seulement autour de Jeannot : le nouveau mur vient jusqu'à son contour (pas de halo de l'ancien
    # escalier clair autour du bob et des épaules)
    j = cv2.dilate(jeannot.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    garde = (j | car | boite(0, 0, 968, 232) | boite(0, 0, 655, H)
             | (boite(968, 0, 1240, 150) & ~porte) | boite(1240, 0, 1488, 95) | boite(1488, 0, W, H)
             | boite(0, 496, W, H) | boite(0, 472, 958, H))
    return ia & ~garde, garde


def couleurs_colline(col, v9c):
    """Le ciel de la retouche (bleu plus saturé, tirant sur le cyan) prend le bleu du ciel de P01 ; sa végétation
    prend celle de la colline de la v9 (lumière de plein jour) — moyenne et écart-type Lab, poids progressifs."""
    p01 = np.asarray(Image.open(P01).convert("RGB"))
    x0, y0, x1, y1 = P01_CIEL
    l1 = cv2.cvtColor(p01[y0:y1, x0:x1], cv2.COLOR_RGB2LAB).astype(np.float32)
    lc = cv2.cvtColor(col, cv2.COLOR_RGB2LAB).astype(np.float32)
    l9 = cv2.cvtColor(v9c, cv2.COLOR_RGB2LAB).astype(np.float32)
    def ciel(l):
        return np.clip((-(l[..., 2] - 128) - 2) / 4, 0, 1) * np.clip((l[..., 0] - 130) / 20, 0, 1)
    def veg(l):
        return np.clip((-(l[..., 1] - 128) - 2) / 4, 0, 1) * np.clip(((l[..., 2] - 128) + 6) / 4, 0, 1)
    out = lc.copy()
    poids = np.zeros(lc.shape[:2], np.float32)
    for wc, wr, ref in ((ciel(lc), ciel(l1), l1), (veg(lc), veg(l9), l9)):
        a, b = lc[wc > 0.5], ref[wr > 0.5]
        k = np.clip(b.std(0) / (a.std(0) + 1e-3), 0.6, 1.6)
        cible = (lc - a.mean(0)) * k + b.mean(0)
        out = out * (1 - wc[..., None]) + cible * wc[..., None]
        poids = np.maximum(poids, wc)
    rgb = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    res = col.astype(np.float32) * (1 - poids[..., None]) + rgb * poids[..., None]
    return np.clip(np.rint(res), 0, 255).astype(np.uint8)


def graines_pied(H, W, jeannot, car):
    yy, xx = np.mgrid[0:H, 0:W]
    def boite(x0, y0, x1, y1):
        return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    j = cv2.dilate(jeannot.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ia = boite(892, 425, 1000, 548)
    garde = j | car | boite(0, 0, 862, H) | boite(0, 0, W, 395) | boite(0, 578, W, H) | boite(1012, 0, W, H)
    return ia & ~garde, garde


def _transfert(ls, lr, zone):
    x0, y0, x1, y1 = zone
    a, b = ls[y0:y1, x0:x1].reshape(-1, 3), lr[y0:y1, x0:x1].reshape(-1, 3)
    k = np.clip(b.std(0) / (a.std(0) + 1e-3), 0.6, 1.6)
    out = (ls - a.mean(0)) * k + b.mean(0)
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32), k


def accorder(src, ref, zone_pierres, zone_trottoir):
    """Accorde les couleurs de src sur ref : les tons pierre (beiges) sur les pierres du mur, les gris sur le
    trottoir (moyenne et écart-type Lab mesurés sur des zones identiques dans les deux images)."""
    ls = cv2.cvtColor(src, cv2.COLOR_RGB2LAB).astype(np.float32)
    lr = cv2.cvtColor(ref, cv2.COLOR_RGB2LAB).astype(np.float32)
    pierre, k = _transfert(ls, lr, zone_pierres)
    gris, _ = _transfert(ls, lr, zone_trottoir)
    B, L = ls[..., 2] - 128, ls[..., 0]
    w = (np.clip((B - 4) / 6, 0, 1) * np.clip((L - 80) / 20, 0, 1))[..., None]
    res = gris * (1 - w) + pierre * w
    return np.clip(np.rint(res), 0, 255).astype(np.uint8), k


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v9 = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = v9.shape[:2]
    jeannot, car = silhouettes(v9)
    protege = jeannot | car
    res = v9.astype(np.float32)
    zones, infos, masques = [], [], []
    # 1. colline (déjà alignée)
    x0, y0, x1, y1 = CC
    col = charger("v10-ia-colline-2.png", CC)
    col = couleurs_colline(col, v9[y0:y1, x0:x1])
    gi, gg = p02_v8.graines_ciel(H, W)
    lab = p02_v8.coupe_graphe(v9[y0:y1, x0:x1], col, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
    m1 = np.zeros((H, W), bool); m1[y0:y1, x0:x1] = lab
    full = v9.copy(); full[y0:y1, x0:x1] = col
    res, a1 = p02_v8.coller(res, full, m1, protege)
    # 2. jardin (recalé sur la v9 : garage, haut de la façade, Jeannot, 4L)
    x0, y0, x1, y1 = CJ
    jar = charger("v10-ia-jardin-2.png", CJ)
    jar, w, cc = recaler(v9[y0:y1, x0:x1], jar, [(0, 120, 30, 500), (330, 0, 600, 60), (360, 250, 580, 500), (580, 380, 888, 500)])
    gi, gg = graines_jardin(H, W, jeannot, car)
    cur = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    lab = p02_v8.coupe_graphe(cur[y0:y1, x0:x1], jar, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
    m2 = np.zeros((H, W), bool); m2[y0:y1, x0:x1] = lab
    full = cur.copy(); full[y0:y1, x0:x1] = jar
    res, a2 = p02_v8.coller(res, full, m2, protege)
    # 3. pied du mur (recalé sur la route, Jeannot et la 4L ; couleurs accordées sur les pierres du mur actuel)
    x0, y0, x1, y1 = CP
    cur = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    pied = charger("v10-ia-pied.png", CP)
    pied, w3, cc3 = recaler(cur[y0:y1, x0:x1], pied, [(0, 250, 640, 360), (400, 0, 560, 360), (600, 150, 640, 360)])
    px0, py0, px1, py1 = PIERRES
    tx0, ty0, tx1, ty1 = TROTTOIR
    pied, k3 = accorder(pied, cur[y0:y1, x0:x1], (px0 - x0, py0 - y0, px1 - x0, py1 - y0),
                        (tx0 - x0, ty0 - y0, tx1 - x0, ty1 - y0))
    gi, gg = graines_pied(H, W, jeannot, car)
    lab = p02_v8.coupe_graphe(cur[y0:y1, x0:x1], pied, gi[y0:y1, x0:x1], gg[y0:y1, x0:x1])
    m3 = np.zeros((H, W), bool); m3[y0:y1, x0:x1] = lab
    full = cur.copy(); full[y0:y1, x0:x1] = pied
    res, a3 = p02_v8.coller(res, full, m3, protege)
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    for a in (a1, a2, a3):
        ys, xs = np.nonzero(a > 0)
        zones.append((max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1), min(W, int(xs.max()) + 2), min(H, int(ys.max()) + 2)))
    print(f"ok {sortie} | colline {int(m1.sum())} px · jardin {int(m2.sum())} px (recalage cc {cc:.4f}, "
          f"échelle {w[0, 0]:.4f}, décalage {w[0, 2]:+.2f} {w[1, 2]:+.2f}) · pied {int(m3.sum())} px (recalage cc "
          f"{cc3:.4f}, décalage {w3[0, 2]:+.2f} {w3[1, 2]:+.2f})")
    print("zones du contrôle : " + ";".join(",".join(map(str, z)) for z in zones))
    if "--coupes" in sys.argv:
        vis = out.copy()
        for m, c in zip((m1, m2, m3), ([255, 0, 255], [0, 255, 255], [255, 255, 0])):
            e = m ^ cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            vis[e] = c
        Image.fromarray(vis).save(sys.argv[sys.argv.index("--coupes") + 1])


if __name__ == "__main__":
    main()
