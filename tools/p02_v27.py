#!/usr/bin/env python3
"""P02 v27 / v28 = la v26 avec la maison, le jardin et la terrasse cisailés pour que le BAS DU MUR
soit parallèle à la route (avis du 16/10).

Avis 06:58 : l'utilisateur a tracé sur l'image la ligne de façade (1000,212)->(1470,217) et la ligne
de route (498,429)->(993,619) : « dis-moi en quoi ces lignes sont parallèles ? » ; avis 06:59 : « la
maison n'a pas bougé d'un pouce, toujours mal orienté… regarde le plan de la carte interactive ».

Deux variantes, publiées toutes les deux (l'utilisateur tranche) :
  A = la façade prend la pente de la LIGNE DE ROUTE pointée   (+0,3838 = +21,0°) : les deux lignes
      tracées deviennent strictement parallèles — la maison descend vers la droite ;
  B = la façade prend la pente du MUR DE SOUTÈNEMENT (la terrasse, −0,0443 ≈ −2,5°), qui est
      l'autre ligne « parallèle à la rue » de l'image et la référence citée dans les avis (« de
      face / 90°, c'est par rapport à la rue ») — la maison monte doucement vers la droite.

Le bas du mur de la v26 est à +0,0553 (pente de la v13).  La correction est un CISAILLEMENT
VERTICAL PAR COLONNE à décalage ENTIER (aucun rééchantillonnage : les pixels sont recopiés tels
quels, les verticales restent verticales, les angles entre les lignes sont conservés) — c'est le
style « projection cavalière » déjà utilisé par la v26.  Il est ancré à l'ouest (x = 1000, rien ne
bouge) et s'arrête à x = 1505 (le mur de la maison voisine ne bouge pas).

Ce qui est cisaillé : toit (tuiles), mur, fenêtres, porte, jardin (herbe), chaperon et haut des
pierres, escaliers du jardin — tout ce qui est AU-DESSUS du haut de l'avant-plan (Jeannot, la 4L,
la rue) au pixel près : l'avant-plan n'est jamais touché, il n'y a donc rien à restaurer.
Le bandeau laissé libre est comblé soit par la forêt (variante A, copie en miroir des rangées
voisines : aucun flou), soit par la maçonnerie du mur (variante B, décalage modulo le rang de
pierres) — jamais d'interpolation.

Usage : python3 tools/p02_v27.py [--variante A|B|AB] [--essai]
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
SRC = DOSSIER / "p02-v26-maison-parallele.png"

X0, X1, RAMPE = 1000, 1505, 30
PENTE_V26 = 0.0016                  # bas du mur RÉELLEMENT peint dans la v26 (mesuré colonne par colonne :
                                    # 248 colonnes, x 1200-1470, y ≈ 205 : +0,16 %).  L'ancienne valeur 0,0553
                                    # (pente de la v13) donnait un bas du mur à 18,4° au lieu de 21,0° : la ligne
                                    # de la planche dérivait donc de 24 px — c'était la cause du refus du 16/10.
PENTE_ROUTE = 0.3838                # ligne de route pointée (498,429)->(993,619)
PENTE_MURET = -0.0443               # base du mur de soutènement (la terrasse), v13/v26
PAS_PIERRES = 40                    # hauteur d'un rang de pierres (variante B)
VARIANTES = {
    "A": dict(fichier="p02-v27-maison-pente-route.png", cible=PENTE_ROUTE,
              quoi="pente de la ligne de route pointée (+21,0°)"),
    "C": dict(fichier="p02-v29-maison-remontee-rue.png", cible=-0.12,
              quoi="remontée vers le point de fuite de la rue (330,364) — la maison suit la rue qui s'éloigne"),
    "B": dict(fichier="p02-v28-maison-pente-mur-soutenement.png", cible=PENTE_MURET,
              quoi="pente du mur de soutènement (−2,5°)"),
}


def lisse(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def deplacement(x, s):
    """Décalage vertical entier de la colonne x (positif = vers le bas), nul avant X0."""
    if x < X0 or x >= X1:
        return 0
    return int(round(s * (x - X0) * lisse((x - X0) / RAMPE)))


def haut_avant_plan(V):
    """Pour chaque colonne, la première ligne de l'avant-plan (Jeannot, la 4L) — jamais touchée."""
    jeannot, car = p02_v10.silhouettes(V)
    m = ((jeannot | car).astype(np.uint8) * 255)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    H, W = m.shape
    haut = np.full(W, H, np.int32)
    for x in range(X0, X1):
        col = np.where(m[:, x] > 0)[0]
        if len(col):
            haut[x] = col.min()
    haut[X0:X1] = np.minimum(haut[X0:X1], 496)          # la rue au bas de l'image : avant-plan
    # borne sûre : minimum sur ±8 colonnes, puis 2 px de marge
    h = haut.copy()
    for x in range(X0, X1):
        a, b = max(X0, x - 8), min(X1, x + 9)
        h[x] = max(1, haut[a:b].min() - 2)
    return h


FORET_BLOC = (430, 0, 985, 176)     # rectangle de forêt pure, à gauche de la maison (variante A)


def comble_foret(src, out, s):
    """Comble le bandeau libéré au-dessus du toit par la forêt voisine, copiée en miroir 2D dans
    un rectangle de forêt (aucun flou, aucune couleur nouvelle)."""
    x0, y0, x1, y1 = FORET_BLOC
    Wb, Hb = x1 - x0, y1 - y0
    for x in range(X0, X1):
        d = int(round(s * (x - X0) * lisse((x - X0) / RAMPE)))
        if d <= 0:
            continue
        ys = np.arange(d)
        u = (x - X0) % (2 * Wb)
        u = u if u < Wb else 2 * Wb - 1 - u
        v = ys % (2 * Hb)
        v = np.where(v < Hb, v, 2 * Hb - 1 - v)
        out[ys, x] = src[y0 + v, x0 + u]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", default="AB", choices=["A", "B", "C", "AB", "C"])
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()

    src = np.asarray(Image.open(SRC).convert("RGB"))
    H, W, _ = src.shape
    haut = haut_avant_plan(src)
    print(f"  avant-plan : haut de {haut[X0:X1].min()} à {haut[X0:X1].max()} (x {X0}-{X1})")

    Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
    sorties = {}
    for v in a.variante:
        cfg = VARIANTES[v]
        s = cfg["cible"] - PENTE_V26
        out = src.copy()
        for x in range(X0, X1):
            d = deplacement(x, s)
            if d == 0:
                continue
            ylim = int(haut[x])
            if v == "A":                                    # translation vers le bas
                ys = np.arange(ylim)
                src_y = ys - d
                col = np.empty((ylim, 3), np.uint8)
                bas = src_y >= 0
                col[bas] = src[src_y[bas], x]
                out[:ylim, x] = col
            else:                                           # translation vers le haut
                ad = -d
                ys = np.arange(ylim)
                src_y = ys + ad
                src_y = np.where(src_y > ylim - 1,
                                 src_y - PAS_PIERRES * np.maximum(1, np.round((src_y - (ylim - 1)) / PAS_PIERRES)), src_y)
                src_y = np.clip(src_y, 0, ylim - 1).astype(np.int32)
                out[:ylim, x] = src[src_y, x]
        if v == "A":
            comble_foret(src, out, s)
        Image.fromarray(out).save(DOSSIER / cfg["fichier"])
        sorties[v] = out
        print(f"  v{v} : {cfg['quoi']} — pente du bas du mur {100 * cfg['cible']:+.2f} % "
              f"(v26 {100 * PENTE_V26:+.2f} %), décalage max {deplacement(X1 - 1, s):+d} px")
        print(f"        écrit : {cfg['fichier']}  ·  zones du contrôle : {X0},0,{X1},620")

        if a.essai:
            n = "v27" if v == "A" else "v28"
            p = Path("/tmp/p02") / f"{n}-maison.png"
            Image.fromarray(out[0:520, 940:1560]).resize((620 * 2, 520 * 2), Image.LANCZOS).save(p)
            Image.fromarray(out[0:200, 940:1560]).resize((620 * 3, 200 * 3), Image.NEAREST).save(
                Path("/tmp/p02") / f"{n}-toit.png")
            bande = np.concatenate([src[0:700, 900:1560], out[0:700, 900:1560]], axis=1)
            Image.fromarray(bande).resize((bande.shape[1], bande.shape[0])).save(
                Path("/tmp/p02") / f"{n}-v26-vs.png")
            Image.fromarray(out[0:1080:2, 0:1920:2]).save(Path("/tmp/p02") / f"{n}-entier.png")
            print(f"        planches : /tmp/p02/{n}-{{maison,toit,v26-vs,entier}}.png")


if __name__ == "__main__":
    main()
