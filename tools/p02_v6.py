#!/usr/bin/env python3
"""P02 v6 = la v5 avec la 3e paire de correctifs de la liste (avis du 14/10 sur la v3) :

5. Jeannot comme dans P01 v33 : visage plus plein, sourcils et cheveux sombres et bouclés sous le bob, barbe
   poivre et sel, cordon au cou, bleu de travail cobalt de P01 avec quelques taches de peinture jaune-ocre
   irrégulières (au lieu des traînées ocre), bob jaune doré de P01 ;
6. Enji comme dans P01 v33 et sur sa fiche (assets/art/enji-character.png) : même pelage noir et feu (selle
   noire, pattes et poitrail feu, museau grisé, oreille pliée, collier brun), dessin plus simple, moins réaliste.

Méthode :
  - retouche IA de chaque personnage sur un recadrage de la v5 agrandi ×2 (Jeannot est donné retourné pour être
    orienté comme son modèle de P01, puis remis à l'endroit) ; résultats bruts dans p02/work/ ;
  - le résultat est ramené à la taille du recadrage (il est déjà aligné : décalage < 0,1 px, aucun recalage) ;
  - on ne colle QUE la silhouette du personnage : union de l'ancienne (v5) et de la nouvelle (IA), découpées par
    GrabCut à partir des zones nettement modifiées, l'autre personnage étant exclu par la boîte ;
  - Jeannot est ensuite recoloré matière par matière sur le Jeannot de P01 (bleu de travail, peau, bob, taches
    de peinture : moyenne et étalement Lab de la même matière dans P01, ombres gardées, poids progressifs) — la
    retouche IA avait un bleu plus clair, une peau plus rose et un bob trop pâle.
  Contrôle avec --palette P01 v33 : le bleu cobalt et le jaune doré demandés n'existent pas dans la v5.
  Tout le reste est identique à la v5 (lieux, 4L, volant, sol, plaque).

Entrées (p02/work/) : v6-entree-jeannot-miroir.png, v6-entree-enji.png (recadrages ×2 de la v5 donnés à l'IA),
ref-p01-jeannot.png, ref-p01-enji.png (modèles), v6-ia-jeannot-miroir-2.png, v6-ia-enji.png (retouches IA ;
v6-ia-jeannot-miroir.png = 1er essai écarté : bleu roi et grosses étoiles jaunes, cheveux gris).

Contrôle obligatoire :
  python3 tools/controle_retouche.py p02-v5-plaque-rouille.png p02-v6-jeannot-enji.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v6-controle.jpg \\
      --palette assets/storyboards/a-valider/p01/p01-v33-net.png

Usage : python3 tools/p02_v6.py [SORTIE]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v5-plaque-rouille.png"
SORTIE = DOSSIER / "p02-v6-jeannot-enji.png"

# recadrages de la v5 (x0, y0, x1, y1) et boîte du personnage dans le recadrage (l'autre personnage en est exclu)
PERSOS = [
    # nom, retouche IA, recadrage, retournée ?, boîte
    ("enji", "v6-ia-enji.png", (420, 620, 1050, 1040), False, (15, 15, 578, 412)),
    ("jeannot", "v6-ia-jeannot-miroir-2.png", (830, 200, 1350, 980), True, (100, 25, 400, 778)),
]
P01 = ROOT / "assets/storyboards/a-valider/p01/p01-v33-net.png"
# Jeannot dans P01 v33 : recadrage, bob, bas de la tête (y) — et les mêmes repères dans P02
P01_JEANNOT = (190, 445, 380, 885)
P01_BOB = (240, 450, 340, 500)
P01_TETE_BAS = 560
P02_BOB = (1020, 240, 1160, 330)
P02_TETE_BAS = 400
# part de l'écart de clarté moyenne vers P01 (1 = clarté de P01 ; 0 = clarté de la retouche) : le bleu de P01 est
# plus sombre ; à 1 les traits paraissent moins nets sur le tissu, à 0 les bleus clairs sortent de la palette
CLARTE_P01 = 0.7


def charger(nom, recadrage, retournee):
    im = Image.open(TRAVAIL / nom).convert("RGB")
    if retournee:
        im = ImageOps.mirror(im)
    w, h = recadrage[2] - recadrage[0], recadrage[3] - recadrage[1]
    return np.asarray(im.resize((w, h), Image.LANCZOS))


def silhouette(img, boite, sur, probable, iters=6):
    """GrabCut : hors boîte = décor ; zones nettement modifiées = personnage ; leur voisinage = probable."""
    H, W = img.shape[:2]
    gc = np.full((H, W), cv2.GC_BGD, np.uint8)
    x0, y0, x1, y1 = boite
    gc[y0:y1, x0:x1] = cv2.GC_PR_BGD
    gc[probable & (gc == cv2.GC_PR_BGD)] = cv2.GC_PR_FGD
    gc[sur & (gc != cv2.GC_BGD)] = cv2.GC_FGD
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(0)
    cv2.grabCut(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), gc, None, bg, fg, iters, cv2.GC_INIT_WITH_MASK)
    m = ndi.binary_fill_holes((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n > 1:
        m = lbl == 1 + int(np.argmax(st[1:, 4]))
    return m


def masque(ref, ia, boite):
    d = np.abs(ref.astype(int) - ia.astype(int)).max(axis=2).astype(np.float32)
    d = cv2.GaussianBlur(d, (0, 0), 1.5)
    sur = cv2.erode((d > 45).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    probable = cv2.dilate((d > 25).astype(np.uint8),
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))).astype(bool)
    nouvelle = silhouette(ia, boite, sur, probable)
    ancienne = silhouette(ref, boite, sur, probable)
    return nouvelle | ancienne, nouvelle


def _lab(img):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.float32)
    return lab, lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128


def _rampe(v, a, b):
    return np.clip((v - a) / (b - a), 0, 1)


def matieres(img, sil, bob, tete_bas, y0):
    """Poids (0..1) de chaque matière de Jeannot : bleu de travail, peau, bob, taches de peinture."""
    _, L, A, B = _lab(img)
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    yy = yy + y0
    s = sil.astype(np.float32)
    bx0, by0, bx1, by1 = bob
    dans_bob = ((xx >= bx0) & (xx < bx1) & (yy >= by0) & (yy < by1)).astype(np.float32)
    jaune = _rampe(B, 14, 24) * (1 - _rampe(A, 9, 14)) * _rampe(L, 70, 90)
    return {
        "bleu": s * _rampe(-B, 6, 12) * _rampe(L, 20, 35),
        "peau": s * _rampe(A, 8, 13) * _rampe(B, 8, 13) * _rampe(L, 80, 95) * (1 - _rampe(L, 225, 240)) * (1 - dans_bob),
        "bob": s * dans_bob * jaune,
        "taches": s * (yy > tete_bas) * jaune * (1 - _rampe(A, 8, 11)),
    }


def silhouette_p01():
    """Jeannot dans P01 v33 (GrabCut : le bleu de travail et le bob sûrs, les bords du recadrage = décor)."""
    p01 = np.asarray(Image.open(P01).convert("RGB"))
    x0, y0, x1, y1 = P01_JEANNOT
    c = p01[y0:y1, x0:x1]
    _, L, A, B = _lab(c)
    sur = cv2.erode(((B < -15) & (L > 30)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    H, W = L.shape
    gc = np.full((H, W), cv2.GC_PR_FGD, np.uint8)
    gc[:6, :] = gc[-2:, :] = gc[:, :6] = gc[:, -6:] = cv2.GC_BGD
    gc[sur] = cv2.GC_FGD
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(0)
    cv2.grabCut(cv2.cvtColor(c, cv2.COLOR_RGB2BGR), gc, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
    m = ndi.binary_fill_holes((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n > 1:
        m = lbl == 1 + int(np.argmax(st[1:, 4]))
    return c, m


def vers_p01(img, sil_jeannot):
    """Recolore chaque matière de Jeannot sur la même matière dans P01 (moyenne et écart-type Lab)."""
    c01, s01 = silhouette_p01()
    b = P01_BOB
    # boîtes : x dans le recadrage, y dans l'image entière (comme matieres() les compare)
    m01 = matieres(c01, s01, (b[0] - P01_JEANNOT[0], b[1], b[2] - P01_JEANNOT[0], b[3]), P01_TETE_BAS, P01_JEANNOT[1])
    lab01, _, _, _ = _lab(c01)
    ys, xs = np.nonzero(sil_jeannot)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    c = img[y0:y1, x0:x1]
    lab, _, _, _ = _lab(c)
    bob = (P02_BOB[0] - x0, P02_BOB[1], P02_BOB[2] - x0, P02_BOB[3])
    m02 = matieres(c, sil_jeannot[y0:y1, x0:x1], bob, P02_TETE_BAS, y0)
    new = lab.copy()
    total = np.zeros(lab.shape[:2], np.float32)
    infos = []
    for nom in ("bleu", "peau", "bob", "taches"):
        w2, w1 = m02[nom], m01[nom]
        if (w2 > 0.5).sum() < 50 or (w1 > 0.5).sum() < 50:
            continue
        src, dst = lab[w2 > 0.5], lab01[w1 > 0.5]
        mu_s, sd_s = src.mean(0), src.std(0) + 1e-3
        mu_d, sd_d = dst.mean(0), dst.std(0) + 1e-3
        k = np.clip(sd_d / sd_s, 0.5, 2.0)
        cible = (lab - mu_s) * k + mu_d
        # clarté gardée telle quelle (ombres, traits, contraste avec les contours) : seules la teinte et la
        # saturation (a, b) suivent P01 — le bleu plus sombre de P01 faisait passer les traits pour moins nets
        cible[..., 0] = lab[..., 0] + CLARTE_P01 * (mu_d[0] - mu_s[0])
        new = new * (1 - w2[..., None]) + cible * w2[..., None]
        total = np.maximum(total, w2)
        infos.append(f"{nom} {int((w2 > 0.5).sum())}→P01 {int((w1 > 0.5).sum())}")
    rgb = cv2.cvtColor(np.clip(new, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    out = img.astype(np.float32).copy()
    t = total[..., None]
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - t) + rgb * t      # mélange RVB : poids 0 = pixel inchangé
    return np.clip(np.rint(out), 0, 255).astype(np.uint8), infos


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v5 = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = v5.shape[:2]
    res = v5.astype(np.float32).copy()
    zones, infos, sil_jeannot = [], [], np.zeros((H, W), bool)
    for nom, fichier, rc, retournee, boite in PERSOS:
        x0, y0, x1, y1 = rc
        ref = v5[y0:y1, x0:x1]
        ia = charger(fichier, rc, retournee)
        m, nouvelle = masque(ref, ia, boite)
        a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.6)   # bord anti-crénelé (1 px), pas de flou
        a[a < 0.02] = 0.0
        res[y0:y1, x0:x1] = res[y0:y1, x0:x1] * (1 - a[..., None]) + ia.astype(np.float32) * a[..., None]
        ys, xs = np.nonzero(a > 0)
        zones.append((int(xs.min()) + x0 - 2, int(ys.min()) + y0 - 2, int(xs.max()) + x0 + 3, int(ys.max()) + y0 + 3))
        infos.append(f"{nom} {int(m.sum())} px")
        if nom == "jeannot":
            sil_jeannot[y0:y1, x0:x1] = nouvelle
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    out, mat = vers_p01(out, sil_jeannot)
    Image.fromarray(out).save(sortie, optimize=True)
    print(f"ok {sortie} | " + " · ".join(infos) + " | Jeannot → P01 : " + " · ".join(mat))
    print("zones du contrôle : " + ";".join(",".join(map(str, z)) for z in zones))


if __name__ == "__main__":
    main()
