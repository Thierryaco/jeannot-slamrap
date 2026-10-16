#!/usr/bin/env python3
"""P02 v26 = la v25 avec le toit et la maison remis « parallèles à la route » (avis du 16/10).

Avis : « la maison est toujours mal orientée, c'est-à-dire à 45° par rapport à la route ; il faut qu'elle soit
parallèle à la route ».

Ce qui causait la lecture « à 45° » (mesuré sur la v25) :
  1. au **bord ouest du toit** (x 1000-1090), les rangées de tuiles montent en biais à ~45° (reste d'un pignon) :
     le toit se lit comme un pan tourné. → ici cette bande est **remplacée par les tuiles du toit principal**
     (copie de la bande x 1090-1180, décalée de 2 px pour que les rangées s'alignent), et le toit se termine à
     l'ouest par une **coupe verticale** avec un liseré d'about ;
  2. la **pente de la maison** est celle de la **v13** (la référence validée par l'utilisateur) : bas du mur
     **+3,2°** et gouttière **+0,2°** (v13 mesurée : +3,17° et +0,21°), alors que la v25 était à −0,5° et −1,25°.
     La correction est un **cisaillement vertical par colonne** (les verticales restent verticales, seules les
     horizontales prennent la pente voulue — c'est le style « projection cavalière » des maisons de l'image),
     ancré sur la porte : le bas du mur et la gouttière ne bougent pas au niveau de la porte (x 1155).

Rien d'autre ne change : ni la porte, ni les fenêtres, ni la terrasse, ni le jardin, ni les escaliers, ni la rue,
ni Jeannot, Enji et la 4L (hors de la zone modifiée).

Contrôle obligatoire (par rapport à la v25) :
  python3 tools/controle_retouche.py assets/storyboards/a-valider/p02/p02-v25-maison-rue.png \\
      assets/storyboards/a-valider/p02/p02-v26-maison-parallele.png \\
      --zones "996,0,1478,240" --plan P02 --sortie assets/storyboards/a-valider/p02/p02-v26-controle.jpg

Usage : python3 tools/p02_v26.py [SORTIE] [--essai]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v25-maison-rue.png"
SORTIE = DOSSIER / "p02-v26-maison-parallele.png"

# ---- 1. le toit : on remplace la bande ouest (tuiles en biais) par le toit principal
TOIT = dict(x_dst=(1000, 1090), x_src=(1090, 1180), y=(0, 165), decalage=-2)
# ---- 2. la pente de la maison, mesurée sur la v13 (référence) et sur la v25
PENTE_V13 = dict(mur=0.0553, gouttiere=0.0036)      # bas du mur / ligne de gouttière
LIGNE_V25 = dict(mur=(0.0092, 199.0, 1000.0),       # y = m x + b, mesuré sur la v25 (m ∈ image, y vers le bas)
                 gouttiere=(-0.0219, 81.0, 1000.0))
X_ANCRE = 1155.0                                    # la porte : rien ne bouge là
ZONE = (996, 0, 1478, 215)
MARGE_BAS = 6                                       # la ligne rigide est prise 6 px sous le bas du mur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie", nargs="?", default=str(SORTIE))
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()

    img = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    out = img.copy()

    # ---- 1. toit d'un seul tenant ----
    xd0, xd1 = TOIT["x_dst"]
    xs0, xs1 = TOIT["x_src"]
    y0, y1 = TOIT["y"]
    bande = img[y0:y1, xs0:xs1].copy()
    bande = np.roll(bande, TOIT["decalage"], axis=0)
    out[y0:y1, xd0:xd1] = bande
    # fondu de 20 px au raccord est (x 1070-1090) : plus aucune couture verticale
    for i in range(20):
        w = (i + 1) / 20.0
        x = xd1 - 20 + i
        out[y0:y1, x] = out[y0:y1, x] * w + img[y0:y1, x] * (1 - w)
    # about du toit à l'ouest : trait vertical net à la limite de la maison
    out[y0:100, xd0] = (58, 50, 48)
    out[y0:100, xd0 + 1] = (120, 110, 104)
    print(f"  toit : bande ouest x {xd0}-{xd1} remplacée par le toit principal (x {xs0}-{xs1})")

    # ---- 2. cisaillement vertical : la maison prend la pente de la v13 ----
    def ligne(cfg, x):
        m, b, x0 = cfg
        return m * (x - x0) + b

    m_mur_25, b_mur_25, x0_mur = LIGNE_V25["mur"]
    m_gout_25, b_gout_25, x0_gout = LIGNE_V25["gouttiere"]

    def y_mur_25(x):
        return m_mur_25 * (x - x0_mur) + b_mur_25

    def y_gout_25(x):
        return m_gout_25 * (x - x0_gout) + b_gout_25

    # cibles : même pente que la v13, ancrées sur la porte (x = X_ANCRE)
    def y_mur_cible(x):
        return PENTE_V13["mur"] * (x - X_ANCRE) + y_mur_25(X_ANCRE)

    def y_gout_cible(x):
        return PENTE_V13["gouttiere"] * (x - X_ANCRE) + y_gout_25(X_ANCRE)

    H, W, _ = img.shape
    for x in range(ZONE[0], ZONE[2]):
        src_col = img[:, x]
        # points de contrôle : haut fixe, gouttière → cible, bas du mur → cible, bas fixe
        # points de contrôle : en haut fixe, gouttière et bas du mur reciblés, puis identité en bas
        # ligne rigide sous le bas du mur APRÈS correction (la pente fait descendre le mur vers la droite)
        y_fixe = max(y_mur_25(x), y_mur_cible(x)) + MARGE_BAS
        yc = np.array([0.0, y_gout_25(x), y_mur_25(x), y_fixe, float(H)])
        yt = np.array([0.0, y_gout_cible(x), y_mur_cible(x), y_fixe, float(H)])
        # monotone (au cas où) et rééchantillonnage de toute la colonne
        yc = np.maximum.accumulate(yc)
        yt = np.maximum.accumulate(yt)
        ys = np.arange(H, dtype=np.float32)
        new_y = np.interp(ys, yt, yc)                     # pour chaque ligne cible, la ligne source
        deplace = np.abs(new_y - ys) > 0.02          # lignes vraiment déplacées
        col = src_col.copy()
        if deplace.any():                             # seule la maison est rééchantillonnée : le reste au pixel
            col[deplace] = np.stack([np.interp(new_y[deplace], np.arange(H), src_col[:, c])
                                     for c in range(3)], axis=1)
        out[:, x] = col
    print(f"  maison remise à la pente de la v13 (bas du mur {100 * PENTE_V13['mur']:.1f} %, "
          f"gouttière {100 * PENTE_V13['gouttiere']:.1f} %), ancrée sur la porte x {X_ANCRE:.0f}")

    # le cisaillement rééchantillonne : on rend au mur la netteté du trait (léger surcroît de netteté)
    xd0, xd1 = ZONE[0], ZONE[2]
    yd1 = int(max(max(y_mur_25(x), y_mur_cible(x)) for x in range(xd0, xd1))) + MARGE_BAS
    sub = out[0:yd1, xd0:xd1]
    flou = np.stack([cv2.GaussianBlur(sub[:, :, c], (0, 0), 0.8) for c in range(3)], axis=2)
    out[0:yd1, xd0:xd1] = np.clip(sub + 0.40 * (sub - flou), 0, 255)

    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(a.sortie)
    print(f"écrit : {a.sortie}")
    print(f"zones du contrôle : {ZONE[0]},{ZONE[1]},{ZONE[2]},240")

    if a.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        Image.fromarray(out[0:230, 940:1520]).resize((580 * 2, 230 * 2), Image.LANCZOS).save(
            "/tmp/p02/v26-maison.png")
        Image.fromarray(out[0:130, 960:1220]).resize((260 * 5, 130 * 5), Image.NEAREST).save(
            "/tmp/p02/v26-toit-ouest.png")
        print("planches : /tmp/p02/v26-{maison,toit-ouest}.png")


if __name__ == "__main__":
    main()
