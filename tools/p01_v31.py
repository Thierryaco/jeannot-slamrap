"""P01 v31 — la v29 avec la tête d'Henri refaite d'après P08 v1 et le regard vers la 4L (14/10).

Demandes de l'utilisateur :
  - « continu mais base toi sur la v29 pour les modif » ;
  - dans l'essai ed5 (perdu, vu seulement en capture d'écran), ce qui était mieux : « il ne donnait
    pas l'impression de regarder le mur ou la porte mais bien en direction de la 4L, et il ressemble
    un peu plus à Henri que l'on voit dans la V1 du P08 qui doit être la réf pour la tête d'Henri ».

La 4L est au premier plan, en bas à gauche, plus près de nous qu'Henri : pour qu'il la regarde, son
visage doit être de trois quarts FACE, les yeux baissés vers l'avant et vers la gauche. Regarder vers
le bas à gauche du recadrage, c'est regarder le mur et l'escalier (défaut de la v30).

Méthode :
  1. retouche IA de la tête sur le recadrage (700, 270)–(900, 470) de la v29 agrandi en 1024 px, EN
     MIROIR (work/crop-v30-1024-miroir.png ; demandé « vers la gauche », le modèle tourne Henri vers
     la droite), avec la tête de P08 v1 comme référence (work/ref-tete-henri-p08-v1.png). Deux
     propositions ; l'utilisateur a choisi la 2 (work/crop-v31-ed1-miroir.png), remise à l'endroit
     dans work/crop-v31-ed1.png ;
  2. le modèle a aussi redessiné légèrement tous les contours du décor : on ne recolle donc que
     Henri, isolé par différence avec le recadrage de l'escalier vide (work/crop-v29-1024.png), plus
     ses mèches fines et sa fumée, isolées par leur teinte gris bleuté ;
  3. on part de la v28 avec Henri effacé des marches (tools/p01_v29.py, `retirer_henri`) : partout
     ailleurs qu'Henri, l'image est donc exactement la v29.

Usage : python3 tools/p01_v31.py [OUT.png]   (depuis la racine du dépôt)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p01_v29 import retirer_henri  # noqa: E402

P = "assets/storyboards/a-valider/p01/"
V28 = P + "p01-v28-trait.png"
V29 = P + "p01-v29-henri-palier.png"
W = P + "work/"
RECADRAGE = (700, 270, 900, 470)       # zone envoyée à l'IA (agrandie ×5,12 en 1024 px)
# zones dans le recadrage 1024 (x0, y0, x1, y1)
ZONE = (440, 380, 820, 740)            # là où Henri peut se trouver
CHEVEUX = (440, 380, 820, 600)         # mèches fines (gris bleuté sur la brique et le mur)
FUMEE = (700, 560, 780, 700)           # filet de fumée au-dessus de la cigarette


def remettre_a_l_endroit():
    """work/crop-v31-ed1-miroir.png (choix de l'utilisateur, en miroir) → work/crop-v31-ed1.png."""
    src, dst = W + "crop-v31-ed1-miroir.png", W + "crop-v31-ed1.png"
    if not os.path.exists(dst):
        ImageOps.mirror(Image.open(src).convert("RGB").resize((1024, 1024), Image.LANCZOS)).save(dst)
    return dst


def _dans(shape, box):
    m = np.zeros(shape, bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def masque_henri():
    """Silhouette du nouvel Henri (mèches et fumée comprises) dans le recadrage 1024, alpha 0..1."""
    avant = np.asarray(Image.open(W + "crop-v29-1024.png").convert("RGB"), float)   # escalier vide
    apres = np.asarray(Image.open(remettre_a_l_endroit()).convert("RGB"), float)
    d = np.abs(apres - avant).max(2)
    # 1. le corps : plus grande composante de la différence, dans la zone d'Henri
    lab, _ = ndi.label(ndi.binary_opening((d > 25) & _dans(d.shape, ZONE), iterations=1))
    tailles = np.bincount(lab.ravel())
    tailles[0] = 0
    corps = ndi.binary_fill_holes(ndi.binary_closing(lab == tailles.argmax(), iterations=3))
    # 2. mèches fines et fumée : gain de bleu (B − R) par rapport à l'escalier vide ; le gris des
    #    cheveux et de la fumée tranche sur la brique rouge et le crépi beige
    bleu = (apres[..., 2] - apres[..., 0]) - (avant[..., 2] - avant[..., 0])
    lab_m, _ = ndi.label((bleu > 12) & _dans(d.shape, CHEVEUX))
    touche = np.unique(lab_m[ndi.binary_dilation(corps, iterations=6)])
    meches = np.isin(lab_m, touche[touche > 0])
    lab_f, _ = ndi.label(ndi.binary_opening((bleu > 12) & _dans(d.shape, FUMEE), iterations=1))
    tailles_f = np.bincount(lab_f.ravel())
    tailles_f[0] = 0
    fumee = np.isin(lab_f, np.nonzero(tailles_f >= 30)[0])
    m = ndi.binary_dilation(corps | meches | fumee, iterations=2)
    return gaussian_filter(m.astype(float), 1.2), apres


def poser_henri(img):
    a = np.asarray(img.convert("RGB"), float).copy()
    alpha, apres = masque_henri()
    x0, y0, x1, y1 = RECADRAGE
    w, h = x1 - x0, y1 - y0
    petit = np.asarray(Image.fromarray(np.clip(apres, 0, 255).astype("uint8")).resize((w, h), Image.LANCZOS), float)
    al = np.asarray(Image.fromarray((alpha * 255).astype("uint8")).resize((w, h), Image.BOX), float)[..., None] / 255
    a[y0:y1, x0:x1] = petit * al + a[y0:y1, x0:x1] * (1 - al)
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype("uint8"))


if __name__ == "__main__":
    im = poser_henri(retirer_henri(Image.open(V28)))
    if len(sys.argv) > 1:
        sortie = sys.argv[1]
    else:
        from chemins import sortie_par_defaut
        sortie = sortie_par_defaut("v31.png")
    im.save(sortie)
    v29 = np.asarray(Image.open(V29).convert("RGB"), float)
    d = np.abs(np.asarray(im, float) - v29).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée depuis la v29 : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
