#!/usr/bin/env python3
"""P02 v31 = v29 dont la ZONE (mur de soutènement + escalier + muret + terrasse + pelouse) est
REDESSINÉE d'un seul tenant par l'IA, puis recollée au masque.

Demande du 16/10 : « un rendu complet et propre de la zone : marches d'escalier continues et droites, la
première marche commence au début du muret, pas avant, la largeur de la maison du fond va du début de la
terrasse jusqu'à quasiment la maison de Jeannot » — après le rejet de la v30 (« muret en doublons »,
« bouts de chapeau ») : plus AUCUNE recopie de bandes de parement.

Méthode :
  - la zone a été redessinée par l'IA (`work/v31-ia-zone.png`, obtenue à partir du morceau
    `work/v31-entree-zone.png` = le recadrage (700,0)-(1560,580) de la v29) : un seul mur continu, marches
    régulières et continues, un seul muret ;
  - le haut du mur de ce dessin est ramené SUR LA LIGNE POINTÉE (1000,212) -> (1470,217) par un simple
    RÉÉCHANTILLONNAGE VERTICAL de la bande du mur, colonne par colonne : aucune bande recollée, aucune
    couture, presque aucun flou (décalage ≤ 1 px : 40 % des colonnes ne bougent pas, médiane 0,28 px) ;
  - le pied du mur ne bouge pas : le trottoir, la rue et les marches du trottoir restent ceux de la v29 ;
  - la 4L (x ≥ 1330 au-dessus de y 300) reste celle de la v29 ; Jeannot aussi (silhouette + chapeau +
    peau, recollement net) : aucun personnage ni véhicule n'est redessiné, aucun morceau de chapeau traîne ;
  - les arbres/forêt, le garage et la maison du fond restent ceux de la v29.

  python3 tools/p02_v31.py [--essai]     # --essai : n'écrit que /tmp/p02/v31-zone-essai.png
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import p02_v10

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v29-maison-remontee-rue.png"
IA = DOSSIER / "work/v31-ia-zone-3.png"
DST = DOSSIER / "p02-v31-zone-propre.png"

X0, Y0 = 700, 0            # coin du recadrage dans l'image
W, H = 860, 580            # taille du recadrage de la zone
IA_W2 = 700                # le morceau envoyé à l'IA s'arrête avant la 4L (x 700-1400)
X_DEB, X_FIN = 765, 1490   # du nez du mur (angle du garage) au mur de la maison de Jeannot
PENTE_PIED, C_PIED = 0.268, 289.7   # ligne pierre/trottoir de la v29 : (740,488)-(878,525)
PENTE_HAUT, C_HAUT = 0.0106, 212.0  # LIGNE POINTÉE du haut du mur : (1000,212)-(1470,217)
MARGE_PIED = 12            # le masque s'arrête 12 px au-dessus du pied du mur
FLET = 6                   # fondu du masque (px)
CAR_X, CAR_Y = 1330, 300   # à droite de ça / au-dessus de ça : la 4L, gardée de la v29


def chargement():
    v29 = np.asarray(Image.open(SRC).convert("RGB"))
    ia = Image.open(IA).convert("RGB").resize((IA_W2, H), Image.LANCZOS)
    return v29, np.asarray(ia)


def ligne_pied(x):
    return C_PIED + PENTE_PIED * x


def ligne_cible_haute(x):
    return C_HAUT + PENTE_HAUT * (x - 1000)


def profil_haut_v29(v29):
    """Haut du mur de la v29, colonne par colonne (même détecteur que pour le dessin IA)."""
    crop = v29[Y0:Y0 + H, X0:X0 + W]
    return profil_haut_ia(crop)


def profil_haut_ia(ia):
    """Haut du mur du dessin IA, colonne par colonne : 1re ligne « pierre/chaperon » avec de la pelouse
    (ou la façade crème) au-dessus. Interpolé puis prolongé à droite (la 4L brouille la mesure)."""
    R, G, B = (ia[..., i].astype(int) for i in range(3))
    vert = (G > R + 6) & (G > B + 18)
    clair = (R > 105) & (B > 85) & (np.maximum(np.maximum(R, G), B) - np.minimum(np.minimum(R, G), B) < 55)
    prof = np.full(W, np.nan)
    for xc in range(X_DEB - X0, 1300 - X0 + 1):
        for y in range(150, 420):
            if clair[y, xc] and clair[y:y + 3, xc].all() and vert[max(0, y - 14):y, xc].sum() >= 5:
                prof[xc] = y
                break
    ok = ~np.isnan(prof)
    idx = np.arange(W)
    prof = np.interp(idx, idx[ok], prof[ok])
    prof = ndimage.median_filter(prof, 31)
    a, b = np.polyfit(np.arange(1260 - X0, 1301 - X0), prof[1260 - X0:1301 - X0], 1)
    for xc in range(1300 - X0 + 1, W):
        prof[xc] = a * xc + b
    return prof


def _jaune(V):
    """Le chapeau jaune de Jeannot (jaune franc) — la pierre beige ne doit pas être prise pour la peau."""
    R, G, B = V[..., 0].astype(int), V[..., 1].astype(int), V[..., 2].astype(int)
    return (R > 185) & (G > 145) & (B < 150) & (R - B > 85)


def _peau(V):
    R, G, B = V[..., 0].astype(int), V[..., 1].astype(int), V[..., 2].astype(int)
    return (R > 165) & (R - B > 60) & (G - B > 25) & (B < 175)


def _bouche(couleur):
    """Enveloppe convexe des pixels d'une couleur (le chapeau/le visage : les trous du masque — le
    ruban sombre du chapeau, les ombres du visage — sont ainsi bouchés)."""
    ys, xs = np.where(couleur)
    if xs.size < 50:
        return np.zeros_like(couleur)
    from scipy.spatial import ConvexHull
    pts = np.column_stack([xs, ys]).astype(float)
    hull = ConvexHull(pts)
    from PIL import ImageDraw
    img = Image.new("1", (couleur.shape[1], couleur.shape[0]), 0)
    ImageDraw.Draw(img).polygon([tuple(pts[i]) for i in hull.vertices], fill=1)
    return np.asarray(img, bool)


TETE = (990, 175, 1210, 345)     # la tête de Jeannot dans l'image (chapeau + visage + cheveux)


def _tete(V):
    """Le chapeau (jaune) et la peau, DANS la boîte de la tête seulement : la pierre beige du mur ne
    doit pas être prise pour de la peau."""
    x0, y0, x1, y1 = TETE
    jaune, peau = _jaune(V), _peau(V)
    boite = np.zeros(V.shape[:2], bool)
    boite[y0:y1, x0:x1] = True
    return (jaune | peau) & boite


def _jeannot(V):
    """Jeannot d'une image : silhouette + l'enveloppe du chapeau/visage."""
    j, _ = p02_v10.silhouettes(V)
    return j | _bouche(_tete(V))


def protection_jeannot(v29):
    """Jeannot de la v29 : silhouette (p02_v10) + l'enveloppe du chapeau et du visage, dilatée de 2 px."""
    return ndimage.binary_dilation(_jeannot(v29), iterations=2)


def preparer(v29, ia_name="v31-entree-zone-3.png"):
    """Le morceau envoyé à l'IA : le recadrage SANS la 4L (700,0)-(1400,580) de la v29, Jeannot effacé
    (remplacé par un très gros flou local, pour que l'IA redessine le mur et l'escalier derrière lui).
    Consigne donnée à l'IA : ne dessiner NI personnage NI véhicule (ils sont recollés depuis la v29)."""
    from PIL import ImageFilter
    crop = v29[Y0:Y0 + H, X0:X0 + IA_W2].copy()
    j, _ = p02_v10.silhouettes(v29)
    m = ndimage.binary_dilation(j | _bouche(_tete(v29)), iterations=5)[Y0:Y0 + H, X0:X0 + IA_W2]
    flou = np.asarray(Image.fromarray(crop).filter(ImageFilter.GaussianBlur(28)))
    m3 = np.repeat(m[..., None], 3, axis=2)
    melange = np.clip(crop * (1 - m3) + flou * m3 + 0.5, 0, 255).astype(np.uint8)
    # le haut du mur est déjà mis sur la ligne pointée : l'IA dessine donc la bonne géométrie
    prof = profil_haut_ia(crop)      # mesuré AVANT l'effacement (sinon la tache floue fausse la mesure)
    out = etirer(melange, prof, X_DEB, X0 + IA_W2)
    Image.fromarray(out).save(DOSSIER / "work" / ia_name)
    print("entrée IA ->", ia_name, "| Jeannot effacé :", int(m.sum()), "px | haut du mur v29 :",
          [int(prof[x - X0]) for x in (765, 1000, 1245, 1370)])


def etirer(img, prof, x_deb, x_fin, avec_masque=False):
    """Rééchantillonne verticalement, colonne par colonne, la bande [haut mesuré -> pied du mur] de façon
    que le haut du mur tombe sur la ligne pointée ; le pied du mur ne bouge pas. `img` couvre l'image à
    partir de (X0, Y0) et doit avoir H lignes."""
    out = img.copy()
    masque = np.zeros(img.shape[:2], bool)
    for x in range(x_deb, x_fin + 1):
        xc = x - X0
        if not (0 <= xc < img.shape[1]):
            continue
        haut_src, haut_dst = prof[xc], ligne_cible_haute(x)
        bas = min(ligne_pied(x) - MARGE_PIED, img.shape[0] - 1)
        if bas <= haut_dst + 4:
            continue
        k = (bas - haut_src) / (bas - haut_dst)
        ys = np.arange(int(np.ceil(haut_dst)), int(bas))
        src = np.clip(haut_src + (ys - haut_dst) * k, 0, img.shape[0] - 1.001)
        s0 = np.floor(src).astype(int)
        f = (src - s0)[:, None]
        out[ys, xc] = (img[s0, xc] * (1 - f) + img[s0 + 1, xc] * f).astype(np.uint8)
        masque[int(np.ceil(haut_dst)):int(bas), xc] = True
    return (out, masque) if avec_masque else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--preparer", action="store_true")
    args = ap.parse_args()
    if args.preparer:
        preparer(chargement()[0])
        return

    v29, ia = chargement()
    prof = profil_haut_ia(ia)
    # --- ce qui reste à corriger sur le dessin IA (le morceau envoyé était déjà étiré) : on remet le haut
    #     du mur sur la ligne pointée, le pied du mur ne bouge pas
    out, masque = etirer(ia, prof, X_DEB, X0 + IA_W2, avec_masque=True)
    xx = np.arange(X0, X0 + IA_W2)[None, :] + 0
    yy = np.arange(Y0, Y0 + H)[:, None] + 0
    masque &= ~((xx >= CAR_X) & (yy >= CAR_Y))       # la 4L reste celle de la v29
    al = np.clip(ndimage.distance_transform_edt(masque) / FLET, 0, 1)[..., None]

    res = v29.copy()
    sub = res[Y0:Y0 + H, X0:X0 + IA_W2].astype(float)
    res[Y0:Y0 + H, X0:X0 + IA_W2] = np.clip(sub * (1 - al) + out.astype(float) * al + 0.5, 0, 255).astype(np.uint8)

    # --- Jeannot recollé NET par-dessus (son dessin de la v29, exactement)
    prot = protection_jeannot(v29)
    res[prot] = v29[prot]

    if args.essai:
        Path("/tmp/p02").mkdir(parents=True, exist_ok=True)
        Image.fromarray(res[Y0:Y0 + H, X0:X0 + W]).save("/tmp/p02/v31-zone-essai.png")
        print("essai -> /tmp/p02/v31-zone-essai.png | masque :", int(masque.sum()), "px | Jeannot :",
              int(prot[Y0:Y0 + H, X0:X0 + W].sum()), "px | haut du mur IA :",
              [int(prof[x - X0]) for x in (765, 1000, 1245, 1370)])
        return
    Image.fromarray(res).save(DST)
    print("écrit", DST.name)


if __name__ == "__main__":
    main()
