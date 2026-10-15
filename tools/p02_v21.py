#!/usr/bin/env python3
"""P02 v21 = LA V13, sa maison telle quelle, avec les escaliers en moins (15/10, après la v20).

Consigne de l'utilisateur : « je veux une maison comme dans la v13, pas tes versions difformes de maison de
barjo » puis, pour la suite : « Les escaliers tu les supprimes aussi. On les refera une fois la maison validée
par moi. »

Donc, par rapport à la v13 (`p02-v13-rue-droite.png`) :
  - **la maison ne change pas du tout** (gable ouest, porte d'entrée face à nous, fenêtres, buissons, toit,
    jardin, mur de pierre, grillage, rue : tout est recopié pixel à pixel de la v13) ;
  - **les escaliers sont supprimés** :
      * l'escalier du jardin, devant la porte (retouche IA work/v21-ia-sans-escalier-jardin.png, recadrage
        x 1030-1290 / y 140-300) → la pelouse et le petit muret de pierre du bas continuent sans marche ;
      * les marches posées sur le trottoir (retouche IA work/v20-ia-sans-escalier-bas.png, recadrage
        x 840-1050 / y 395-575) → le mur de pierre descend droit jusqu'au trottoir.
    Les deux retouches sont recadrées sur la géométrie de la v13, leur ton est recalé ligne par ligne sur la
    pelouse de la v13, et seuls les pixels qui changent sont collés (différence + fondu de 5 px). Jeannot et la
    4L sont protégés au pixel près.

Contrôle obligatoire (par rapport à la v13) :
  python3 tools/controle_retouche.py assets/storyboards/a-valider/p02/p02-v13-rue-droite.png \\
      assets/storyboards/a-valider/p02/p02-v21-maison-v13-sans-escalier.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie assets/storyboards/a-valider/p02/p02-v21-controle.jpg

Usage : python3 tools/p02_v21.py [SORTIE] [--essai]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v10  # noqa: E402  (silhouettes de Jeannot et de la 4L)

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v13-rue-droite.png"
SORTIE = DOSSIER / "p02-v21-maison-v13-sans-escalier.png"

# escalier du jardin (devant la porte) : retouche IA, recadrage, seuil de différence, zone de contrôle
JARDIN = dict(fichier="v21-ia-sans-escalier-jardin.png", recadrage=(1030, 140, 1290, 300), seuil=14,
              zone=(1028, 138, 1292, 302),
              # les bandes de part et d'autre de l'escalier (pelouse, mur, pierres) servent à recaler le ton,
              # ligne par ligne, pour que la retouche se fonde exactement dans la v13
              temoins=((1032, 1082), (1240, 1288)),
              # on ne colle jamais plus loin que le bas du jardin (mur de pierre) ni sur la maison
              limite=(1030, 140, 1292, 302))
# marches posées sur le trottoir : retouche IA déjà faite pour la v20 (région identique dans la v13)
MARCHES = dict(fichier="v20-ia-sans-escalier-bas.png", recadrage=(840, 395, 1050, 575), seuil=16,
               zone=(835, 395, 1005, 578), interdit=[(1005, 0, 1920, 578)])

FEATHER = 5
ZONES = [f"{MARCHES['zone'][0]},{MARCHES['zone'][1]},{MARCHES['zone'][2]},{MARCHES['zone'][3]}",
         f"{JARDIN['zone'][0]},{JARDIN['zone'][1]},{JARDIN['zone'][2]},{JARDIN['zone'][3]}"]


def boite(x0, y0, x1, y1, H, W):
    m = np.zeros((H, W), bool)
    m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    return m


def retouche_ia(src, p, protege, H, W):
    """Recadre la retouche IA sur la géométrie de la v13, recale son ton (pelouse) et renvoie (image, masque)."""
    x0, y0, x1, y1 = p["recadrage"]
    ia = np.asarray(Image.open(TRAVAIL / p["fichier"]).convert("RGB")
                    .resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
    ref = src[y0:y1, x0:x1]
    if "temoins" in p:
        # recalage du ton, ligne par ligne, sur les témoins de pelouse communs aux deux images
        for i in range(y1 - y0):
            refi, iai = ref[i], ia[i]
            g = np.zeros(refi.shape[0], bool)
            for a, b in p["temoins"]:
                g[a - x0:b - x0] = True
            # on calcule l'écart de ton sur les pixels proches (la géométrie des témoins ne bouge pas)
            d0 = np.abs(refi - iai).max(1)
            g &= d0 < 60
            if g.sum() > 10:
                ia[i] = np.clip(iai + np.median(refi[g] - iai[g], axis=0), 0, 255)
    plein = np.zeros((H, W, 3), np.float32)
    plein[y0:y1, x0:x1] = ia
    d = np.abs(ia - ref).max(2)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = d > p["seuil"]
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if "limite" in p:                      # jamais de couture droite sur le bord du recadrage
        lx0, ly0, lx1, ly1 = p["limite"]
        m[:ly0 + 4, :] = False; m[ly1 - 4:, :] = False
        m[:, :lx0 + 4] = False; m[:, lx1 - 4:] = False
        m &= boite(lx0 + 4, ly0 + 4, lx1 - 4, ly1 - 4, H, W)
    if "limite" in p:
        m &= boite(*p["limite"], H, W)
    for bx0, by0, bx1, by1 in p.get("interdit", []):
        m &= ~boite(bx0, by0, bx1, by1, H, W)
    m &= ~protege
    return plein, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie", nargs="?", default=str(SORTIE))
    ap.add_argument("--essai", action="store_true", help="écrit des planches de relecture dans /tmp/p02")
    a = ap.parse_args()

    src = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    H, W, _ = src.shape
    out = src.copy()

    jeannot, car = p02_v10.silhouettes(src.astype(np.uint8))
    protege = cv2.dilate((jeannot | car).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) | car

    for nom, p in (("marches du trottoir", MARCHES), ("escalier du jardin", JARDIN)):
        plein, m = retouche_ia(src, p, protege, H, W)
        alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), FEATHER / 2)[:, :, None]
        alpha[m] = 1.0
        out = out * (1 - alpha) + plein * alpha
        print(f"  {nom} : {int(m.sum())} px retouchés")

    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(a.sortie)
    print(f"écrit : {a.sortie}")
    print("zones du contrôle : " + ";".join(ZONES))

    if a.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        for nom, (zx0, zy0, zx1, zy1), ech in (("jardin", JARDIN["zone"], 3), ("marches", MARCHES["zone"], 2)):
            p0 = max(zx0 - 60, 0), max(zy0 - 40, 0)
            p1 = min(zx1 + 60, W), min(zy1 + 40, H)
            Image.fromarray(out[p0[1]:p1[1], p0[0]:p1[0]]).resize(
                ((p1[0] - p0[0]) * ech, (p1[1] - p0[1]) * ech), Image.NEAREST).save(f"/tmp/p02/v21-{nom}.png")
        print("planches : /tmp/p02/v21-{jardin,marches}.png")


if __name__ == "__main__":
    main()
