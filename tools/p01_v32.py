"""P01 v32 — la v29 avec l'Henri de l'essai ed5, repris d'une capture d'écran de l'utilisateur.

L'essai crop-v29-ed5.png (retouche IA du recadrage (700, 270)–(900, 470) agrandi en 1024 px) a été
perdu lors d'une remise à zéro. L'utilisateur en a une capture d'écran : c'est son Henri préféré
(« il ne donnait pas l'impression de regarder le mur ou la porte mais bien en direction de la 4L »).

Une capture n'a ni la taille ni le cadrage exacts du recadrage. Méthode :
  1. recaler la capture sur le recadrage de l'escalier vide (work/crop-v29-1024.png), dont ed5 est
     issu : points SIFT, puis similitude (échelle + décalage + petite rotation) estimée par RANSAC
     sur le décor ; Henri, absent de la référence, tombe dans les points rejetés ;
  2. corriger la teinte globale de la capture (gamma et profil d'écran) : droite par canal ajustée
     sur le décor ;
  3. isoler Henri comme pour la v31 : plus grande composante de la différence avec l'escalier vide
     dans la zone d'Henri, plus les mèches fines et la fumée, isolées par leur teinte gris bleuté ;
  4. le recoller sur la v28 dont Henri a été effacé des marches (`retirer_henri`) : partout ailleurs
     qu'Henri, l'image est exactement la v29.

Usage : python3 tools/p01_v32.py [OUT.png] [--capture CHEMIN]   (depuis la racine du dépôt)
        par défaut, capture = assets/storyboards/a-valider/p01/work/ed5-capture.png
"""
import argparse
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p01_v29 import retirer_henri  # noqa: E402

P = "assets/storyboards/a-valider/p01/"
V28 = P + "p01-v28-trait.png"
V29 = P + "p01-v29-henri-palier.png"
W = P + "work/"
CAPTURE = W + "ed5-capture.png"
RECADRAGE = (700, 270, 900, 470)       # zone envoyée à l'IA (agrandie ×5,12 en 1024 px)
# zones dans le recadrage 1024 (x0, y0, x1, y1)
ZONE = (440, 360, 840, 740)            # là où Henri peut se trouver
CHEVEUX = (440, 360, 840, 600)         # mèches fines
FUMEE = (690, 520, 800, 710)           # filet de fumée au-dessus de la cigarette


def _dans(shape, box):
    m = np.zeros(shape, bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def recaler(capture):
    """Capture → recadrage 1024. Renvoie (image recalée float, masque valide, infos)."""
    ref = np.asarray(Image.open(W + "crop-v29-1024.png").convert("RGB"))
    cap = np.asarray(Image.open(capture).convert("RGB"))
    sift = cv2.SIFT_create(nfeatures=6000)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(cap, cv2.COLOR_RGB2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY), None)
    paires = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    bons = [m for m, n in (p for p in paires if len(p) == 2) if m.distance < 0.75 * n.distance]
    src = np.float32([k1[m.queryIdx].pt for m in bons])
    dst = np.float32([k2[m.trainIdx].pt for m in bons])
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0,
                                         maxIters=20000, confidence=0.9995)
    inl = inl.ravel().astype(bool)
    proj = src[inl] @ M[:, :2].T + M[:, 2]
    err = np.linalg.norm(proj - dst[inl], axis=1)
    echelle = float(np.hypot(M[0, 0], M[1, 0]))
    angle = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    infos = dict(capture=cap.shape[1::-1], paires=len(bons), retenues=int(inl.sum()),
                 echelle=echelle, angle=angle, decalage=(float(M[0, 2]), float(M[1, 2])),
                 erreur_mediane=float(np.median(err)))
    rec = cv2.warpAffine(cap.astype(np.float32), M, (1024, 1024), flags=cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REPLICATE)
    valide = cv2.warpAffine(np.ones(cap.shape[:2], np.float32), M, (1024, 1024),
                            flags=cv2.INTER_NEAREST, borderValue=0) > 0.5
    return rec, valide, infos


def corriger_teinte(rec, valide):
    """Droite par canal (capture → référence), ajustée sur le décor hors de la zone d'Henri."""
    ref = np.asarray(Image.open(W + "crop-v29-1024.png").convert("RGB"), float)
    decor = valide & ~_dans(valide.shape, ZONE)
    decor = ndi.binary_erosion(decor, iterations=8)
    out = rec.copy()
    pentes = []
    for c in range(3):
        a, b = np.polyfit(rec[..., c][decor], ref[..., c][decor], 1)
        out[..., c] = rec[..., c] * a + b
        pentes.append((round(float(a), 3), round(float(b), 1)))
    return np.clip(out, 0, 255), pentes


def masque_henri(apres, valide):
    """Silhouette d'Henri (mèches et fumée comprises) dans le recadrage 1024, alpha 0..1."""
    avant = np.asarray(Image.open(W + "crop-v29-1024.png").convert("RGB"), float)   # escalier vide
    d = np.abs(apres - avant).max(2)
    d[~valide] = 0
    lab, _ = ndi.label(ndi.binary_opening((d > 22) & _dans(d.shape, ZONE), iterations=1))
    tailles = np.bincount(lab.ravel())
    tailles[0] = 0
    corps = ndi.binary_fill_holes(ndi.binary_closing(lab == tailles.argmax(), iterations=3))
    bleu = (apres[..., 2] - apres[..., 0]) - (avant[..., 2] - avant[..., 0])
    bleu[~valide] = 0
    lab_m, _ = ndi.label((bleu > 12) & _dans(d.shape, CHEVEUX))
    touche = np.unique(lab_m[ndi.binary_dilation(corps, iterations=6)])
    meches = np.isin(lab_m, touche[touche > 0])
    lab_f, _ = ndi.label(ndi.binary_opening((bleu > 12) & _dans(d.shape, FUMEE), iterations=1))
    tailles_f = np.bincount(lab_f.ravel())
    tailles_f[0] = 0
    fumee = np.isin(lab_f, np.nonzero(tailles_f >= 30)[0])
    m = ndi.binary_dilation(corps | meches | fumee, iterations=2) & valide
    return gaussian_filter(m.astype(float), 1.2)


def poser_henri(img, apres, alpha):
    a = np.asarray(img.convert("RGB"), float).copy()
    x0, y0, x1, y1 = RECADRAGE
    w, h = x1 - x0, y1 - y0
    petit = np.asarray(Image.fromarray(np.clip(np.round(apres), 0, 255).astype("uint8")).resize((w, h), Image.LANCZOS), float)
    al = np.asarray(Image.fromarray((alpha * 255).astype("uint8")).resize((w, h), Image.BOX), float)[..., None] / 255
    a[y0:y1, x0:x1] = petit * al + a[y0:y1, x0:x1] * (1 - al)
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8"))


def construire(capture=CAPTURE, bavard=True):
    rec, valide, infos = recaler(capture)
    apres, pentes = corriger_teinte(rec, valide)
    alpha = masque_henri(apres, valide)
    if bavard:
        print("capture %s : %d paires, %d retenues, échelle ×%.3f, rotation %.2f°, décalage (%.1f, %.1f), "
              "erreur médiane %.2f px" % (infos["capture"], infos["paires"], infos["retenues"], infos["echelle"],
                                          infos["angle"], *infos["decalage"], infos["erreur_mediane"]))
        print("correction de teinte (pente, décalage) par canal R, V, B :", pentes)
    return poser_henri(retirer_henri(Image.open(V28)), apres, alpha), apres, alpha


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie", nargs="?")
    ap.add_argument("--capture", default=CAPTURE)
    args = ap.parse_args()
    im, apres, alpha = construire(args.capture)
    if args.sortie:
        sortie = args.sortie
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v32.png")
    im.save(sortie)
    v29 = np.asarray(Image.open(V29).convert("RGB"), float)
    d = np.abs(np.asarray(im, float) - v29).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée depuis la v29 : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
