#!/usr/bin/env python3
"""P02 v10 = la v9 avec les deux rectifications demandées le 15/10 après la v8 (écartée) :

  « la colline était beaucoup trop basse il va falloir rectifier — le jardin qui fait colline alors qu'il est au
    même niveau que la terrasse juste un poil plus bas »

1. colline : nettement plus haute que dans la v8 (la crête part du bord gauche vers le tiers supérieur et sort par
   le haut de l'image au-dessus de la terrasse) ; il reste un coin de ciel bleu en haut à gauche ;
2. jardin : PLAT, au niveau de la terrasse du garage (juste un peu plus bas), tenu par un haut mur de soutènement
   en pierre le long du trottoir ; l'escalier part du trottoir, monte tout droit jusqu'à la porte de la maison et
   coupe le jardin en deux moitiés (pelouse et arbustes).

Méthode : retouches IA sur des recadrages de la v9 (p02/work/v10-ia-colline.png ; v10-ia-jardin-2.png, faite avec
la disposition de l'escalier de la v8 comme modèle — v10-ia-jardin.png, 1er essai écarté : escalier en biais tout à
droite, jardin pas coupé en deux) ; le jardin est recalé sur la v9 (ECC, agrandissement de 0,9 %) ; collage par
coupe de graphe (p02_v8.coupe_graphe) ; Jeannot et la 4L de la v9 restent au pixel près.

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
    j = cv2.dilate(jeannot.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    garde = (j | car | boite(0, 0, 968, 232) | boite(0, 0, 655, H)
             | (boite(968, 0, 1310, 176) & ~porte) | boite(1310, 0, 1488, 95) | boite(1488, 0, W, H)
             | boite(0, 496, W, H) | boite(0, 472, 958, H))
    return ia & ~garde, garde


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
    col = charger("v10-ia-colline.png", CC)
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
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    for a in (a1, a2):
        ys, xs = np.nonzero(a > 0)
        zones.append((max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1), min(W, int(xs.max()) + 2), min(H, int(ys.max()) + 2)))
    print(f"ok {sortie} | colline {int(m1.sum())} px · jardin {int(m2.sum())} px (recalage cc {cc:.4f}, "
          f"échelle {w[0, 0]:.4f}, décalage {w[0, 2]:+.2f} {w[1, 2]:+.2f})")
    print("zones du contrôle : " + ";".join(",".join(map(str, z)) for z in zones))
    if "--coupes" in sys.argv:
        vis = out.copy()
        for m, c in zip((m1, m2), ([255, 0, 255], [0, 255, 255])):
            e = m ^ cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            vis[e] = c
        Image.fromarray(vis).save(sys.argv[sys.argv.index("--coupes") + 1])


if __name__ == "__main__":
    main()
