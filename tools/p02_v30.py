#!/usr/bin/env python3
"""P02 v30 = v29 + le mur de soutènement CONTINU dont le HAUT suit la ligne pointée.

Avis du 16/10 : « maintenant tu me fais le mur de soutènement continu jusqu'au mur de chez jeannot,
pareil pour le haut du mur tu suivra la ligne du haut du mur que je t'avais pointé. l'escalier coupera
le mur en 2 jusqu'à la porte. »

  - ligne pointée du haut du mur : (1000,212) -> (1470,217)  =>  Y(x) = 212 + 0,0106·(x - 1000) ;
  - le haut du mur de la v29 est relevé colonne par colonne (transition herbe -> pierre) puis lu sur
    onze ancres mesurées ; le parement est remonté jusqu'à la ligne : les pixels du chaperon et des
    rangs de pierre situés SOUS l'ancien haut sont recopiés vers le haut (aucun pixel inventé,
    aucun flou, aucun rééchantillonnage) ;
  - le chaperon d'origine est remplacé par des pierres : un seul chaperon, celui du nouveau haut ;
  - l'escalier n'est PAS touché : la bande des marches est laissée telle quelle, le mur est donc
    coupé en deux tronçons qui se raccordent à la même ligne ;
  - les personnages et la 4L sont restaurés (masques `p02_v10.silhouettes`).

Usage : python3 tools/p02_v30.py [--essai]
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

import p02_v10

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v29-maison-remontee-rue.png"
DST = DOSSIER / "p02-v30-mur-continu-haut-ligne.png"

X_DEB, X_FIN = 765, 1490        # du nez du mur (angle du garage) au mur de la maison de Jeannot
ESC0, ESC1 = 1082, 1245         # la coupe de l'escalier : on n'y touche pas
PENTE, Y0 = 0.0106, 212.0       # ligne pointée du haut du mur : (1000,212)->(1470,217)
COPE = 10                       # épaisseur du chaperon recopié
MARGE = 4                       # on descend de quelques px sous l'ancien haut (on est sûr d'être en pierre)
# haut du mur relevé (mesuré colonne par colonne puis lu sur ces ancres, en image) :
ANCRES = [(765, 272), (860, 270), (1000, 262), (1040, 258), (1075, 255),
          (1245, 233), (1300, 226), (1360, 219), (1400, 213), (1450, 208), (1490, 207)]


def profil_haut(V):
    """Haut du mur colonne par colonne : 1re ligne « pierre » avec >= 14 lignes d'herbe au-dessus."""
    W = V.shape[1]
    p = np.full(W, np.nan)
    vert = (V[..., 1] > V[..., 0] + 6) & (V[..., 1] > V[..., 2] + 18)
    for x in range(X_DEB, X_FIN + 1):
        for y in range(150, 345):
            if vert[y - 14:y, x].any() and not vert[y:y + 14, x].any():
                p[x] = y
                break
    return p


def modele(profil):
    """Le haut du mur lu sur les ancres (le relevé automatique sert de contrôle)."""
    xs = np.array([a for a, _ in ANCRES], float)
    ys = np.array([b for _, b in ANCRES], float)
    x = np.arange(profil.size)
    return np.interp(x, xs, ys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()

    src = np.asarray(Image.open(SRC).convert("RGB"))
    H, W, _ = src.shape
    out = src.copy()

    mesure = profil_haut(src.astype(int))
    p = modele(mesure)
    ecart = [abs(mesure[x] - p[x]) for x in range(X_DEB, X_FIN + 1)
             if not np.isnan(mesure[x]) and not (ESC0 <= x <= ESC1)]
    print(f"  relevé automatique : {len(ecart)} colonnes ; écart au modèle "
          f"médian {np.median(ecart):.0f} px, max {max(ecart):.0f} px")

    ligne = Y0 + PENTE * (np.arange(W) - 1000.0)
    n, rel = 0, []
    for x in range(X_DEB, X_FIN + 1):
        if ESC0 <= x <= ESC1:
            continue
        y_old = int(round(p[x])) + MARGE
        y_new = int(round(ligne[x]))
        h = y_old - y_new
        if h <= COPE + 2 or y_old + COPE >= H:
            continue
        out[y_new:y_old, x] = src[y_old - COPE:y_old - COPE + h, x]
        out[y_old - COPE:y_old, x] = src[y_old:y_old + COPE, x]
        n += 1
        rel.append(h)
    print(f"  {n} colonnes remontées ; +{min(rel)} à +{max(rel)} px")

    for m in p02_v10.silhouettes(src):
        out[m] = src[m]

    Image.fromarray(out).save(DST)
    print(f"  écrit : {DST.name}  ·  zone du contrôle : {X_DEB-5},195,{X_FIN+5},300")
    if a.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        Image.fromarray(out[150:330, 740:1500]).resize((760 * 2, 180 * 2), Image.NEAREST).save(
            "/tmp/p02/v30-bande.png")


if __name__ == "__main__":
    main()
