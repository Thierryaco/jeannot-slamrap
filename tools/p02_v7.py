#!/usr/bin/env python3
"""P02 v7 = la v6 avec la 4e paire de correctifs de la liste (avis du 14/10 sur la v3) :

7. le bout de la maison de Jeannot (bord droit) comme dans P01 : le grand pignon aveugle posé sur le trottoir
   (avec sa gouttière, sa descente d'eau et son toit) est remplacé par un haut mur de jardin crème le long du
   trottoir et, en retrait derrière, l'étage d'une maison crème aux fenêtres à encadrement blanc ;
8. la route dessinée comme dans P01 : asphalte lisse, bordures claires, caniveau le long des trottoirs.

Méthode (retouches IA brutes dans p02/work/, faites d'après P01 : ref-p01-maison-mur.png, ref-p01-route.png) :
  - maison : v7-ia-maison-miroir.png (recadrage x 1100–1920, y 0–615 donné retourné ×1,5) ; l'IA a recadré plus
    large : elle est recalée sur la 4L (affine, ECC) et rééchantillonnée directement à l'échelle de la v6
    (1 px v6 ≈ 1,02 px IA : pas d'agrandissement) ; la coupe avec la v6 suit le bord droit du mur de pierre de
    l'escalier (x ≈ 1486) et contourne par la gauche le bout de gouttière et le coin du toit de l'ancien pignon
    (chemin de coût minimal là où les deux images se ressemblent le plus) ; la 4L de la v6 est gardée telle
    quelle (silhouette GrabCut) ;
  - route : v7-ia-route.png (recadrage x 0–1020, y 400–1080, ×1,5 ; déjà aligné) ; seul le SOL est collé (masques
    du sol de p02_v4 : chaussée, trottoirs, bordures) ; Enji et Jeannot de la v6 sont exclus (silhouettes de
    p02_v6).
  Tout le reste est identique à la v6.

Contrôle obligatoire :
  python3 tools/controle_retouche.py p02-v6-jeannot-enji.png p02-v7-maison-route.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v7-controle.jpg

Usage : python3 tools/p02_v7.py [SORTIE] [--seam IMG]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v4  # noqa: E402  (masques du sol)
import p02_v6  # noqa: E402  (silhouettes d'Enji et de Jeannot)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
TRAVAIL = DOSSIER / "work"
SRC = DOSSIER / "p02-v6-jeannot-enji.png"
V3 = DOSSIER / "p02-v3-cul-de-sac.png"
V5 = DOSSIER / "p02-v5-plaque-rouille.png"
SORTIE = DOSSIER / "p02-v7-maison-route.png"

CM = (1100, 0, 1920, 615)        # recadrage « maison » de la v6
CR = (0, 400, 1020, 1080)        # recadrage « route » de la v6
# recalage de l'IA maison : départ (trouvé à l'échelle du recadrage) et zone de la 4L (v6, y 400–615)
W_DEPART = np.array([[0.7031, 0.0088, -7.07], [-0.0013, 0.6968, 165.25]], np.float32)
# coupe maison/v6 : bande de recherche et contraintes (la gouttière et le coin du toit doivent passer côté IA)
BANDE = (1400, 1492)
BOTTES = (975, 880, 1095, 972)   # bottes de Jeannot (gardées de la v5) : ce qui n'y est pas du sol est protégé
CONTRAINTES = [((95, 170), (1400, 1438))]   # (lignes y0–y1) : x autorisés


def ia_maison():
    orig = np.asarray(ImageOps.mirror(Image.open(TRAVAIL / "v7-ia-maison-miroir.png").convert("RGB")))
    return orig


def recaler_maison(v6, orig):
    x0, y0, x1, y1 = CM
    ref = v6[y0:y1, x0:x1]
    H0, W0 = orig.shape[:2]
    sx, sy = W0 / (x1 - x0), H0 / (y1 - y0)
    w0 = W_DEPART.copy()
    w0[0] *= sx
    w0[1] *= sy
    g1 = cv2.GaussianBlur(cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY), (0, 0), 1.2).astype(np.float32)
    g2 = cv2.GaussianBlur(cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY), (0, 0), 1.2).astype(np.float32)
    m = np.zeros(g2.shape, np.uint8)
    ya, yb = int((0.6968 * 400 + 165.25) * sy), int((0.6968 * 615 + 165.25) * sy)
    m[ya:min(yb, H0), 0:min(int((0.7031 * 820 - 7.07) * sx), W0)] = 255
    cc, w = cv2.findTransformECC(g1, g2, w0, cv2.MOTION_AFFINE,
                                 (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 400, 1e-7), m, 5)
    al = cv2.warpAffine(orig, w, (x1 - x0, y1 - y0), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                        borderMode=cv2.BORDER_REPLICATE)
    return al, w, cc


def silhouette_4l(v6):
    """La 4L dans le recadrage maison (GrabCut) : la carrosserie vert amande est sûre ; le crépi crème relié au
    haut du recadrage (sans traverser de trait) est du décor sûr."""
    x0, y0, x1, y1 = CM
    c = v6[y0:y1, x0:x1]
    lab = cv2.cvtColor(c, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    H, W = L.shape
    menthe = cv2.erode(((A < -6) & (L > 90)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    menthe[:330, :] = False
    clair = (L > 150) & (np.abs(A) < 10)
    n, lbl = cv2.connectedComponents(clair.astype(np.uint8), connectivity=4)
    haut = set(np.unique(lbl[:300][clair[:300]]))
    decor = np.isin(lbl, list(haut - {0})) & clair
    gc = np.full((H, W), cv2.GC_PR_BGD, np.uint8)
    gc[330:, :] = cv2.GC_PR_FGD
    gc[decor] = cv2.GC_BGD
    gc[:300, :] = cv2.GC_BGD
    gc[menthe] = cv2.GC_FGD
    gc[540:, 120:] = cv2.GC_FGD          # bas du recadrage à droite de Jeannot : la 4L
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(0)
    cv2.grabCut(cv2.cvtColor(c, cv2.COLOR_RGB2BGR), gc, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
    m = ndi.binary_fill_holes((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD))
    # ouverture : retire les excroissances fines rattachées à tort à la 4L (bas de l'ancienne descente d'eau et
    # bord du mur de pierre au-dessus du toit) ; carrosserie, rétroviseur et montants sont bien plus épais
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n > 1:
        m = lbl == 1 + int(np.argmax(st[1:, 4]))
    full = np.zeros(v6.shape[:2], bool)
    full[y0:y1, x0:x1] = m
    return full


def coupe(v6, al_full, car):
    """Chemin vertical de coût minimal dans BANDE (programmation dynamique), lignes 0 → haut de la 4L."""
    xa, xb = BANDE
    d = np.abs(v6.astype(np.float32) - al_full.astype(np.float32)).sum(axis=2)
    d = cv2.GaussianBlur(d, (0, 0), 1.0)
    ymax = int(np.nonzero(car[:, xa:xb].any(axis=1))[0].min()) + 6
    cost = d[:ymax, xa:xb].copy()
    for (r0, r1), (c0, c1) in CONTRAINTES:
        cost[r0:r1, :max(0, c0 - xa)] = 1e9
        cost[r0:r1, c1 - xa:] = 1e9
    acc = cost.copy()
    for y in range(1, ymax):
        prev = acc[y - 1]
        best = np.minimum(prev, np.minimum(np.r_[1e12, prev[:-1]], np.r_[prev[1:], 1e12]))
        acc[y] += best
    path = np.zeros(ymax, int)
    path[-1] = int(np.argmin(acc[-1]))
    for y in range(ymax - 2, -1, -1):
        x = path[y + 1]
        lo, hi = max(0, x - 1), min(xb - xa, x + 2)
        path[y] = lo + int(np.argmin(acc[y, lo:hi]))
    return path + xa, ymax


def masque_maison(v6, al_full, car):
    path, ymax = coupe(v6, al_full, car)
    H, W = v6.shape[:2]
    m = np.zeros((H, W), bool)
    x0, y0, x1, y1 = CM
    for y in range(y0, y1):
        xc = path[y] if y < ymax else path[-1]
        m[y, xc:x1] = True
    m &= ~car
    return m, path, ymax


def masque_route(v6):
    """Sol de la v6 dans le recadrage route : masques de p02_v4 (calculés sur la v3), sans Enji ni Jeannot.
    Renvoie aussi les zones protégées (personnages, bottes de Jeannot) où le collage ne doit rien changer."""
    v3 = np.asarray(Image.open(V3).convert("RGB"))
    sol = np.zeros(v6.shape[:2], bool)
    for z in p02_v4.masques_sol(v3).values():
        sol |= z
    v5 = np.asarray(Image.open(V5).convert("RGB"))
    persos = np.zeros(v6.shape[:2], bool)
    for nom, fichier, rc, retournee, boite in p02_v6.PERSOS:
        x0, y0, x1, y1 = rc
        ia = p02_v6.charger(fichier, rc, retournee)
        _, nouvelle = p02_v6.masque(v5[y0:y1, x0:x1], ia, boite)
        persos[y0:y1, x0:x1] |= nouvelle
    persos = cv2.dilate(persos.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    x0, y0, x1, y1 = CR
    m = np.zeros(v6.shape[:2], bool)
    m[y0:y1, x0:x1] = sol[y0:y1, x0:x1]
    m &= ~persos
    bottes = np.zeros(v6.shape[:2], bool)
    bx0, by0, bx1, by1 = BOTTES
    bottes[by0:by1, bx0:bx1] = ~sol[by0:by1, bx0:bx1]
    return m, persos | bottes


def coller(res, src, m, protege=None):
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.6)   # bord anti-crénelé côté décor
    a[a < 0.02] = 0.0
    if protege is not None:
        a[protege] = 0.0                                       # 4L, personnages : strictement inchangés
    return res * (1 - a[..., None]) + src.astype(np.float32) * a[..., None], a


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v6 = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = v6.shape[:2]
    # maison
    al, w, cc = recaler_maison(v6, ia_maison())
    al_full = v6.copy()
    x0, y0, x1, y1 = CM
    al_full[y0:y1, x0:x1] = al
    car = silhouette_4l(v6)
    mm, path, ymax = masque_maison(v6, al_full, car)
    # route
    rx0, ry0, rx1, ry1 = CR
    route = np.asarray(Image.open(TRAVAIL / "v7-ia-route.png").convert("RGB").resize((rx1 - rx0, ry1 - ry0), Image.LANCZOS))
    route_full = v6.copy()
    route_full[ry0:ry1, rx0:rx1] = route
    mr, protege = masque_route(v6)
    res = v6.astype(np.float32)
    res, am = coller(res, al_full, mm, car)
    res, ar = coller(res, route_full, mr, protege | car)
    out = np.clip(np.rint(res), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    zones = []
    for a in (am, ar):
        ys, xs = np.nonzero(a > 0)
        zones.append((max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1), min(W, int(xs.max()) + 2),
                      min(H, int(ys.max()) + 2)))
    print(f"ok {sortie} | maison : recalage cc {cc:.4f}, {int(mm.sum())} px, coupe x {path.min()}–{path.max()} "
          f"(lignes 0–{ymax}) · 4L gardée {int(car.sum())} px | route : sol {int(mr.sum())} px")
    print("zones du contrôle : " + ";".join(",".join(map(str, z)) for z in zones))
    if "--seam" in sys.argv:
        vis = out.copy()
        for y in range(ymax):
            vis[y, max(0, path[y] - 1):path[y] + 1] = [255, 0, 255]
        e = car ^ cv2.erode(car.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        vis[e] = [0, 255, 255]
        Image.fromarray(vis).save(sys.argv[sys.argv.index("--seam") + 1])


if __name__ == "__main__":
    main()
