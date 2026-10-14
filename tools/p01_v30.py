"""P01 v30 — Henri sur son palier, la tête tournée franchement vers la 4L (demande du 14/10).

L'utilisateur préférait un essai précédent (crop-v29-ed5, perdu lors d'une remise à zéro de la
session) où « le regard et la tête d'Henri étaient mieux situés », et veut Henri « tourné plus
franchement vers la voiture ». Dans la v29 (essai ed6), Henri a la tête droite : il regarde à
l'horizontale, vers la façade. La 4L est au premier plan, en bas à gauche : il doit regarder vers le
bas et vers la gauche.

Méthode :
  1. on repart de la v28 et on efface Henri des marches exactement comme pour la v29
     (tools/p01_v29.py, `retirer_henri`, au pixel et sans IA) ;
  2. Henri est redessiné par IA sur le recadrage (700, 270)–(900, 470) de la v29 agrandi en 1024 px
     (work/crop-v30-1024.png). Demandé tel quel (« vers la gauche »), l'IA le tourne vers la droite
     (work/crop-v30-ed2.png, écarté). Astuce qui marche : on lui donne le recadrage EN MIROIR
     (work/crop-v30-1024-miroir.png) en demandant qu'il regarde en bas à DROITE
     (work/crop-v30-ed3-miroir.png), puis on remet le résultat à l'endroit (work/crop-v30-ed3.png) ;
  3. on ne recolle que la silhouette d'Henri et sa fumée, isolées par différence avec le recadrage
     de l'escalier déjà vide (work/crop-v29-1024.png), avec un bord adouci.

Usage : python3 tools/p01_v30.py [OUT.png]   (depuis la racine du dépôt)
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
W = P + "work/"
RECADRAGE = (700, 270, 900, 470)       # zone envoyée à l'IA (agrandie ×5,12 en 1024 px)
FUMEE = (690, 540, 780, 700)           # zone de la fumée dans le recadrage 1024 (x0, y0, x1, y1)


def remettre_a_l_endroit():
    """work/crop-v30-ed3-miroir.png (sortie de l'IA, en miroir) → work/crop-v30-ed3.png."""
    src, dst = W + "crop-v30-ed3-miroir.png", W + "crop-v30-ed3.png"
    if not os.path.exists(dst):
        ImageOps.mirror(Image.open(src).convert("RGB").resize((1024, 1024), Image.LANCZOS)).save(dst)
    return dst


def masque_henri():
    """Silhouette d'Henri (et de sa fumée) dans le recadrage 1024, en alpha 0..1."""
    avant = np.asarray(Image.open(W + "crop-v29-1024.png").convert("RGB"), float)   # escalier vide
    apres = np.asarray(Image.open(remettre_a_l_endroit()).convert("RGB"), float)
    d = np.abs(apres - avant).max(2)
    lab, _ = ndi.label(ndi.binary_opening(d > 20, iterations=1))
    tailles = np.bincount(lab.ravel())
    tailles[0] = 0
    corps = ndi.binary_fill_holes(ndi.binary_closing(lab == tailles.argmax(), iterations=3))
    # fumée : isolée par sa couleur gris bleuté (gain de B − R > 12 par rapport à l'escalier vide),
    # et non par simple différence : le fond rendu par l'IA diffère de 6 à 13 niveaux, ce qui ferait
    # des taches autour du filet de fumée
    x0, y0, x1, y1 = FUMEE
    bleu = (apres[..., 2] - apres[..., 0]) - (avant[..., 2] - avant[..., 0])
    fumee = np.zeros_like(corps)
    fumee[y0:y1, x0:x1] = bleu[y0:y1, x0:x1] > 12
    lab_f, _ = ndi.label(ndi.binary_opening(fumee, iterations=1))
    tailles_f = np.bincount(lab_f.ravel())
    tailles_f[0] = 0
    fumee = np.isin(lab_f, np.nonzero(tailles_f >= 30)[0])
    m = ndi.binary_dilation(corps | fumee, iterations=2)
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
        sortie = sortie_par_defaut("v30.png")
    im.save(sortie)
    v29 = np.asarray(Image.open(P + "p01-v29-henri-palier.png").convert("RGB"), float)
    d = np.abs(np.asarray(im, float) - v29).max(2)
    ys, xs = np.nonzero(d > 0)
    print("zone modifiée depuis la v29 : %d,%d,%d,%d" % (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
