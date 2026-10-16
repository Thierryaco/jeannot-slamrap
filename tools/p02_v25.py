#!/usr/bin/env python3
"""P02 v25 = la v24 avec la maison et l'escalier redessinés « par rapport à la rue » (avis du 16/10 05:07).

Avis : « quand je dis de face et 90° pour la maison et les escaliers c'est par rapport à la RUE pas à la
caméra ». Vu depuis cette caméra (qui regarde vers le nord-ouest), une façade parallèle à la rue se voit en
biais léger — ses lignes montent doucement vers la droite, comme le mur de soutènement (≈ −2°) — et un escalier
perpendiculaire à la rue se voit en trois-quarts : sa volée monte en diagonale vers la droite.

Par rapport à la v24 :
  1. le **pan de mur oblique** qui restait à l'ouest de la maison (≈ 45°, avec sa fenêtre en perspective) est
     supprimé : retouche IA `work/v25-ia-bout-ouest.png` (recadrage x 960-1180 / y 0-270) → le mur se termine
     par un angle droit vertical, la forêt apparaît derrière ;
  2. l'**escalier du jardin** est remis en trois-quarts (montée en diagonale vers la droite, comme un escalier
     vu de la rue) : retouche IA `work/v25-ia-escalier.png` (recadrage x 980-1340 / y 120-320).

Ton recalé ligne par ligne sur la v24, seuls les pixels qui changent sont collés (fondu 5 px), la porte et les
fenêtres ne sont jamais touchées, Jeannot et la 4L sont protégés.

Contrôle obligatoire (par rapport à la v24) :
  python3 tools/controle_retouche.py assets/storyboards/a-valider/p02/p02-v24-maison-face-escaliers-droits.png \\
      assets/storyboards/a-valider/p02/p02-v25-maison-rue.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie assets/storyboards/a-valider/p02/p02-v25-controle.jpg

Usage : python3 tools/p02_v25.py [SORTIE] [--essai]
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
SRC = DOSSIER / "p02-v24-maison-face-escaliers-droits.png"
SORTIE = DOSSIER / "p02-v25-maison-rue.png"

RETOUCHES = [
    dict(nom="bout ouest (fin du pan oblique)", fichier="v25-ia-bout-ouest.png",
         recadrage=(960, 0, 1180, 270), seuil=16, zone=(960, 0, 1180, 270),
         temoins=((962, 984),), interdit=[(1150, 0, 1180, 270)]),        # la porte : jamais touchée
    dict(nom="escalier du jardin (trois-quarts)", fichier="v25-ia-escalier.png",
         recadrage=(980, 120, 1340, 320), seuil=16, zone=(980, 120, 1340, 320),
         temoins=((984, 1004), (1316, 1338)), interdit=[(1148, 120, 1210, 205)]),  # la porte : jamais touchée
]

FEATHER = 5
ZONES = [f"{p['zone'][0]},{p['zone'][1]},{p['zone'][2]},{p['zone'][3]}" for p in RETOUCHES]


def boite(x0, y0, x1, y1, H, W):
    m = np.zeros((H, W), bool)
    m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    return m


def retouche_ia(src, p, protege, H, W):
    x0, y0, x1, y1 = p["recadrage"]
    ia = np.asarray(Image.open(TRAVAIL / p["fichier"]).convert("RGB")
                    .resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
    ref = src[y0:y1, x0:x1]
    # écart de ton par ligne, puis LISSÉ sur 25 lignes : un recalage ligne à ligne brut fait des stries
    ecarts = np.zeros((y1 - y0, 3), np.float32)
    for i in range(y1 - y0):
        refi, iai = ref[i], ia[i]
        # témoins = les pixels de la ligne que la retouche n'a PAS changés (même contenu des deux côtés) ;
        # les colonnes de temoins ne servent que de garde-fou si l'image est très différente
        g = np.abs(refi - iai).max(1) < 24
        for a, b in p["temoins"]:
            g[max(a - x0, 0):b - x0] &= True
        ecarts[i] = np.median(refi[g] - iai[g], axis=0) if g.sum() > 20 else np.nan
    # comble les lignes sans témoin, puis lisse (médiane glissante + moyenne glissante)
    for c in range(3):
        col = ecarts[:, c]
        idx = np.arange(len(col))
        ok = ~np.isnan(col)
        if ok.sum() > 2:
            col[~ok] = np.interp(idx[~ok], idx[ok], col[ok])
        else:
            col[:] = 0.0
        col = np.array([np.median(col[max(0, i - 12):i + 13]) for i in range(len(col))], np.float32)
        ecarts[:, c] = col
    ecarts = np.clip(ecarts, -8, 8)                     # un recalage de ton ne doit jamais dépasser ±8
    ia = np.clip(ia + ecarts[:, None, :], 0, 255)
    plein = src.copy()
    plein[y0:y1, x0:x1] = ia
    d = np.abs(ia - ref).max(2)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = d > p["seuil"]
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(np.uint8)
    # ouverture : supprime les lignes fantômes fines (moins de 3 px) que laisse la différence
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = m.astype(bool)
    m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    lx0, ly0, lx1, ly1 = p["zone"]
    m[:ly0 + 3, :] = False; m[ly1 - 3:, :] = False
    m[:, :lx0 + 3] = False; m[:, lx1 - 3:] = False
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
        Image.fromarray(out[0:280, 900:1400]).resize((500 * 3, 280 * 3), Image.NEAREST).save("/tmp/p02/v25-maison.png")
        print("planche : /tmp/p02/v25-maison.png")


if __name__ == "__main__":
    main()
