#!/usr/bin/env python3
"""P02 v24 = la v23 avec les DEUX ESCALIERS REDRESSÉS À 90° par l'IA (avis du 15/10 au soir).

Avis : « la maison et une partie de l'escalier reste encore à 45°… ». La v23 a redressé la maison (vue de face) ;
ici, les deux volées sont redessinées **perpendiculaires à la rue** (donc tout droit dans l'image), avec des
**marches horizontales** et des **côtés verticaux** :
  - l'escalier du jardin, devant la porte (retouche IA `work/v23-ia-escalier-jardin-droit.png`, recadrage
    x 1030-1330 / y 130-300) : la volée monte droit dans l'axe de la porte, encadrée par ses deux murets droits ;
  - les marches du trottoir (retouche IA `work/v23-ia-escalier-bas-droit.png`, recadrage x 800-1080 / y 370-600) :
    la volée monte droit vers le mur de pierre, marches horizontales, sans déborder sur le trottoir.

Ton recalé ligne par ligne sur la v23, seuls les pixels qui changent sont collés (fondu 5 px), la porte et le mur
de la maison ne sont jamais touchés (zone interdite), Jeannot et la 4L sont protégés.

Contrôle obligatoire (par rapport à la v23) :
  python3 tools/controle_retouche.py assets/storyboards/a-valider/p02/p02-v23-maison-de-face.png \\
      assets/storyboards/a-valider/p02/p02-v24-maison-face-escaliers-droits.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie assets/storyboards/a-valider/p02/p02-v24-controle.jpg

Usage : python3 tools/p02_v24.py [SORTIE] [--essai]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v10  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v23-maison-de-face.png"
SORTIE = DOSSIER / "p02-v24-maison-face-escaliers-droits.png"

RETOUCHES = [
    dict(nom="escalier du jardin", fichier="v23-ia-escalier-jardin-droit.png",
         recadrage=(1030, 130, 1330, 300), seuil=14, zone=(1030, 130, 1330, 300),
         temoins=((1034, 1054), (1300, 1328)),
         interdit=[(1145, 130, 1212, 200)]),          # la porte et le mur de la maison : jamais touchés
    dict(nom="marches du trottoir", fichier="v23-ia-escalier-bas-droit.png",
         recadrage=(800, 370, 1080, 600), seuil=14, zone=(800, 370, 1080, 600),
         temoins=((803, 828),), interdit=[]),
]

FEATHER = 5
ZONES = [";".join([])] + [f"{p['zone'][0]},{p['zone'][1]},{p['zone'][2]},{p['zone'][3]}" for p in RETOUCHES]
ZONES = [z for z in ZONES if z]


def boite(x0, y0, x1, y1, H, W):
    m = np.zeros((H, W), bool)
    m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    return m


def retouche_ia(src, p, protege, H, W):
    x0, y0, x1, y1 = p["recadrage"]
    ia = np.asarray(Image.open(TRAVAIL / p["fichier"]).convert("RGB")
                    .resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
    ref = src[y0:y1, x0:x1]
    for i in range(y1 - y0):
        refi, iai = ref[i], ia[i]
        g = np.zeros(refi.shape[0], bool)
        for a, b in p["temoins"]:
            g[max(a - x0, 0):b - x0] = True
        g &= np.abs(refi - iai).max(1) < 60
        if g.sum() > 10:
            ia[i] = np.clip(iai + np.median(refi[g] - iai[g], axis=0), 0, 255)
    plein = src.copy()                     # hors du recadrage, « plein » = l'image : le fondu ne peut rien tacher
    plein[y0:y1, x0:x1] = ia
    d = np.abs(ia - ref).max(2)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = d > p["seuil"]
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    for bx0, by0, bx1, by1 in p["interdit"]:
        m &= ~boite(bx0, by0, bx1, by1, H, W)
    m &= ~protege
    return plein, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie", nargs="?", default=str(SORTIE))
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()

    src = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    H, W, _ = src.shape
    out = src.copy()
    jeannot, car = p02_v10.silhouettes(src.astype(np.uint8))
    protege = cv2.dilate((jeannot | car).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) | car

    for p in RETOUCHES:
        plein, m = retouche_ia(src, p, protege, H, W)
        alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), FEATHER / 2)[:, :, None]
        alpha[m] = 1.0
        out = out * (1 - alpha) + plein * alpha
        print(f"  {p['nom']} : {int(m.sum())} px")

    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(a.sortie)
    print(f"écrit : {a.sortie}")
    print("zones du contrôle : " + ";".join(ZONES))

    if a.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        Image.fromarray(out[130:300, 1030:1330]).resize((300 * 3, 170 * 3), Image.NEAREST).save(
            "/tmp/p02/v24-escalier-jardin.png")
        Image.fromarray(out[370:600, 800:1080]).resize((280 * 3, 230 * 3), Image.NEAREST).save(
            "/tmp/p02/v24-escalier-bas.png")
        print("planches : /tmp/p02/v24-escalier-{jardin,bas}.png")


if __name__ == "__main__":
    main()
