#!/usr/bin/env python3
"""P02 v20 = la v14 avec la maison du fond refaite et les escaliers supprimés (avis du 15/10).

Consigne : « tu supprimes la maison du fond et tu refais une maison qui soit alignée avec les façades des autres,
elle doit s'arrêter avant la terrasse. La porte d'entrée devant. Les escaliers tu les supprimes aussi. On les refera
une fois la maison validée par moi. », puis « elle restera à la même hauteur et retrait qu'avant ».
Réponses aux deux questions posées : la maison s'arrête **juste avant la terrasse** (arête ouest du mur x = 1010 :
le garde-corps de la terrasse finit à x = 1006) et la **porte d'entrée est au centre** de la nouvelle façade.

1. LA MAISON (dessin procédural, aucune IA). L'arête ouest du mur passe de x 979 à x 1010 : les 31 px de mur à
   l'ouest de la nouvelle arête sont repeints au ton du mur de la v14 (médiane par ligne de la colonne de mur nu
   x 1225-1255), puis l'arête est retracée (liseré clair + trait de contour) comme celle de la v14. Rien ne change
   en hauteur ni en profondeur : avant-toit, toit, tuiles et bardeau de rive restent tels quels.
   La façade est recomposée à la même hauteur (aucun décalage vertical) : porte au centre (bloc 1209-1283, centre
   1246) et quatre fenêtres réparties symétriquement de part et d'autre (grandes 1118-1196 et 1296-1374, petites
   1043-1105 et 1387-1449), toutes recopiées de la v14.

2. LES ESCALIERS (retouches IA du dossier work/, recadrées, collées au pixel de la v14, Jeannot et la 4L protégés) :
   - work/v20-ia-sans-escalier-haut.png → l'escalier du seuil et le jardin qu'il coupait ;
   - work/v20-ia-sans-escalier-bas.png  → les marches posées sur le trottoir.
   La retouche du haut ne remplaçait pas toute la volée : le jardin est donc remplacé en bloc (jardin entier,
   x 1006-1348, y 186-272) par le jardin **intact de la v14** pris juste à droite (x 1348-1464) et tuilé en miroir,
   ligne par ligne, avec le ton recalé sur la v14. Le mur de pierre reste continu et la pelouse du jardin épouse la
   ligne du sol au pied de la maison (pente douce entre le jardin bas de l'ouest et le jardin haut de l'est).
   Une ligne d'arbustes (recopiée de la v14, au pied de la maison) est posée devant cette ligne de sol pour la
   raccorder au mur, comme les arbustes déjà présents à l'est de l'ancien escalier.
   Les escaliers seront refaits après validation de la maison.

Contrôle obligatoire (par rapport à la v14) :
  python3 tools/controle_retouche.py p02-v14-maison-escalier.png p02-v20-maison-droite.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v20-controle.jpg

Usage : python3 tools/p02_v20.py [SORTIE] [--essai]
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
SRC = DOSSIER / "p02-v14-maison-escalier.png"
SORTIE = DOSSIER / "p02-v20-maison-droite.png"

# ------------------------------------------------------------------ 1. la maison
OUEST_V14 = 979                     # arête ouest du mur dans la v14 (biaisée : à supprimer)
OUEST_V20 = 1010                    # nouvelle arête ouest, verticale : juste avant la terrasse (garde-corps à x 1006)
OUEST_FOND = (948, 979, 148)         # bande de fond de la v14 (forêt, buissons) prolongée à l'ouest de l'arête
MUR_SRC = (1225, 1256)              # colonne de mur nu de la v14 : ton de référence, ligne par ligne

BANDE = (1010, 1465, 58, 186)       # bande de façade refaite (mur nu) avant de recoller les blocs
# blocs recopiés tels quels de la v14 : (x0, x1, y0, y1, dx, nom)
BLOCS = [
    (999, 1061, 58, 178, 44, "petite fenêtre ouest"),        # -> 1043-1105
    (1249, 1327, 58, 178, -131, "grande fenêtre ouest"),     # -> 1118-1196
    (1140, 1214, 58, 197, 69, "porte d'entrée"),             # -> 1209-1283 (centre 1246)
    (1249, 1327, 58, 178, 47, "grande fenêtre est"),         # -> 1296-1374
    (999, 1061, 58, 178, 388, "petite fenêtre est"),         # -> 1387-1449
]

# ------------------------------------------------------------------ 2. le jardin (escalier du seuil)
JARDIN = dict(plage=(1012, 1250),              # plage refaite : du mur de la maison à la porte
              plage_y=(190, 252),              # du pied de la maison au chaperon du mur de pierre
              donateur=(1262, 1330))           # pelouse surélevée intacte de la v14 (à droite de la porte)

# ligne d'arbustes (recopiée de la v14, au pied de la maison) posée devant la ligne de sol
BUISSONS = dict(src=(1246, 184, 1330, 252), poses=(986, 1292, 1382), seuil=126)
# marches du trottoir
MARCHES = dict(fichier="v20-ia-sans-escalier-bas.png", recadrage=(840, 395, 1050, 575), seuil=16,
               zone=(835, 395, 1005, 578), interdit=[(1005, 0, 1920, 578)])

FEATHER = 5

ZONES = [f"{OUEST_FOND[0]-6},0,{OUEST_V20+6},212",
         f"{BANDE[0]-10},56,{BANDE[1]+17},254",
         f"{MARCHES['zone'][0]},{MARCHES['zone'][1]},{MARCHES['zone'][2]},{MARCHES['zone'][3]}",
         f"{BUISSONS['poses'][0]-8},{BUISSONS['src'][1]-2},{BUISSONS['poses'][-1]+84+8},{BUISSONS['src'][3]+2}"]


def boite(x0, y0, x1, y1, H, W):
    m = np.zeros((H, W), bool)
    m[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W)] = True
    return m


def gap_fill(m):
    """Bouche les trous d'un masque (les feuilles claires au milieu d'un arbuste)."""
    n, lab = cv2.connectedComponents(m.astype(np.uint8), connectivity=4)
    bords = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    return m | (~np.isin(lab, list(bords - {0})) & ~m)


def retouche_ia(src, p, protege, H, W):
    """Recadre la retouche IA sur la géométrie de la v14, ramène son ton et renvoie (image, masque)."""
    x0, y0, x1, y1 = p["recadrage"]
    ia = np.asarray(Image.open(TRAVAIL / p["fichier"]).convert("RGB")
                    .resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
    plein = np.zeros((H, W, 3), np.float32)
    plein[y0:y1, x0:x1] = ia
    ref = src[y0:y1, x0:x1]
    if "bloc" in p:
        m = boite(*p["bloc"], H, W)
        # ton : la v14 à la même ligne, juste à côté du bloc, rapportée sur la retouche
        xa, xb = p["donateur"]
        for i in range(y0, y1):
            refi = src[i, xa:xb]
            iai = ia[i - y0, xa - x0:xb - x0]
            g = (refi[:, 1] > refi[:, 0] + 6) & (refi[:, 1] > refi[:, 2] + 16)   # herbe seulement
            if g.sum() > 6:
                plein[i] = np.clip(plein[i] + np.median(refi[g] - iai[g], axis=0), 0, 255)
    else:
        d = np.abs(ia - ref).max(2)
        m = np.zeros((H, W), bool)
        m[y0:y1, x0:x1] = d > p["seuil"]
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
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

    rng = np.random.default_rng(4)
    jeannot, car = p02_v10.silhouettes(src.astype(np.uint8))
    protege = cv2.dilate((jeannot | car).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) | car

    # ------------------------------------------------ 2a. les marches du trottoir (retouche IA)
    plein, m = retouche_ia(src, MARCHES, protege, H, W)
    alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), FEATHER / 2)[:, :, None]
    alpha[m] = 1.0
    out = out * (1 - alpha) + plein * alpha
    print(f"  marches du trottoir : {int(m.sum())} px")

    # ------------------------------------------------ 2b. le jardin : pelouse plate de la v14 (bloc intact recopié)
    jx0, jx1 = JARDIN["plage"]                 # plage à refaire (au-dessus du mur de pierre)
    dy0, dy1 = JARDIN["plage_y"]
    dx0, dx1 = JARDIN["donateur"]              # jardin surélevé INTACT de la v14 (à droite de la porte)
    larg = dx1 - dx0
    for x in range(jx0, jx1):
        i = (x - jx0) % (2 * larg)
        i = i if i < larg else 2 * larg - 1 - i          # couture invisible : la bande est reprise en miroir
        out[dy0:dy1, x] = src[dy0:dy1, dx0 + i]
    print("  jardin : pelouse plate recopiée de la v14 (x %d-%d)" % (jx0, jx1))

    # bas du mur au-dessus de la pelouse : mur jusqu'à la ligne du sol (y 189), puis pelouse (reprise de la v14
    # à droite de la porte, où cette transition existe déjà)
    for x in range(JARDIN["plage"][0], 1254):
        out[172:190, x] = np.median(src[172:190, MUR_SRC[0]:MUR_SRC[1]].reshape(-1, 3), axis=0)
        out[190:199, x] = src[190:199, 1284 + (x * 7) % 22]

    # ------------------------------------------------ 1a. l'extrémité ouest : coupe verticale à x = 1010
    # le mur (et sa rive de toit) s'arrête à x = 1010 : à l'ouest, on prolonge le fond de la v14 (forêt, buissons)
    # et le garde-corps de la terrasse, sans rien déformer
    fond = src[0:135, 850:930].copy()                                # forêt / buissons du fond, prolongés
    for i in range(14):                                              # bord ouest fondu : aucune couture visible
        w = (i + 1) / 14.0
        fond[:, i] = fond[:, i] * w + src[0:135, 930 + i] * (1 - w)
    out[0:135, 930:OUEST_V20] = fond
    out[130:209, 984:OUEST_V20] = src[130:209, 958:984]              # garde-corps : dernier panneau prolongé
    for y in range(0, 209):                                          # arête : liseré clair + trait de contour
        out[y, OUEST_V20 - 1] = (79, 75, 66)
        out[y, OUEST_V20] = (40, 29, 15)
    print("  maison : extrémité ouest droite, arête verticale à x = %d" % OUEST_V20)

    # ------------------------------------------------ 1b. façade : bande de mur nu puis blocs recollés
    bx0, bx1, by0, by1 = BANDE
    for y in range(by0, by1 + 1):
        out[y, bx0:bx1] = np.median(src[y, MUR_SRC[0]:MUR_SRC[1]], axis=0)
    # raccord : on fond le mur refait avec le mur de la v14 sur son bord est (12 px)
    f0, f1 = bx1 - 14, bx1
    for i in range(f1 - f0):
        w = (i + 1) / (f1 - f0)
        out[:, f0 + i] = out[:, f0 + i] * w + src[:, f0 + i] * (1 - w)
    for (cx0, cx1, cy0, cy1, dx, nom) in BLOCS:
        out[cy0:cy1, cx0 + dx:cx1 + dx] = src[cy0:cy1, cx0:cx1]
        print(f"  façade : {nom} -> x {cx0+dx}-{cx1+dx}")

    # ------------------------------------------------ 2c. arbustes au pied de la maison
    sx0, sy0, sx1, sy1 = BUISSONS["src"]
    bloc = src[sy0:sy1, sx0:sx1]
    mb = bloc.mean(2) < BUISSONS["seuil"]
    mb = cv2.morphologyEx(mb.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(bool)
    mb = gap_fill(mb)
    mb = cv2.dilate(mb.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)[:, :, None]
    for px in BUISSONS["poses"]:
        cible = out[sy0:sy1, px:px + (sx1 - sx0)]
        out[sy0:sy1, px:px + (sx1 - sx0)] = np.where(mb, bloc, cible)
    print(f"  jardin : arbustes au pied de la maison (x {BUISSONS['poses'][0]} → {BUISSONS['poses'][-1]+sx1-sx0})")

    # ------------------------------------------------ 3. netteté : les collages IA sont recollés au trait de la v14
    mh = boite(MARCHES["zone"][0], MARCHES["zone"][1], MARCHES["zone"][2], MARCHES["zone"][3], H, W)
    sub = out[MARCHES["zone"][1]:MARCHES["zone"][3], MARCHES["zone"][0]:MARCHES["zone"][2]]
    flou = cv2.GaussianBlur(sub, (0, 0), 0.8)
    aigu = np.clip(sub + 0.55 * (sub - flou), 0, 255)
    zx0, zy0, zx1, zy1 = MARCHES["zone"]
    out[zy0:zy1, zx0:zx1] = np.where(mh[zy0:zy1, zx0:zx1, None], aigu, out[zy0:zy1, zx0:zx1])

    image = Image.fromarray(np.clip(out, 0, 255).astype("uint8"))
    image.save(a.sortie)
    print("écrit :", a.sortie)
    print("zones du contrôle :", ";".join(ZONES))
    if a.essai:
        from PIL import ImageDraw
        for (x0, y0, x1, y1, z, nom) in [(950, 0, 1080, 250, 5, "ouest"),
                                         (1000, 50, 1482, 215, 3, "facade"),
                                         (960, 150, 1360, 340, 3, "escalier-haut"),
                                         (820, 390, 1020, 585, 4, "escalier-bas")]:
            c = image.crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST)
            M = 70
            pl = Image.new("RGB", (c.width + M, c.height + M), (255, 255, 255))
            pl.paste(c, (M, M))
            d = ImageDraw.Draw(pl)
            for x in range(x0 - x0 % 20, x1 + 1, 20):
                px = M + (x - x0) * z
                lg = x % 100 == 0
                d.line([(px, 0), (px, M if lg else M - 16)], fill=(0, 0, 0) if lg else (150, 150, 150))
                if lg:
                    d.text((px - 20, 2), str(x), fill=(0, 0, 0))
                    d.line([(px, M), (px, M + c.height)], fill=(255, 140, 140))
            for y in range(y0 - y0 % 20, y1 + 1, 20):
                py = M + (y - y0) * z
                lg = y % 100 == 0
                d.line([(0, py), (M if lg else M - 16, py)], fill=(0, 0, 0) if lg else (150, 150, 150))
                d.text((2, py - 6), str(y), fill=(0, 0, 0))
                if lg:
                    d.line([(M, py), (M + c.width, py)], fill=(120, 180, 255))
            pl.save(f"/tmp/p02/v20-{nom}.png")
        print("planches : /tmp/p02/v20-{ouest,facade,escalier-haut,escalier-bas}.png")


if __name__ == "__main__":
    sys.exit(main())
