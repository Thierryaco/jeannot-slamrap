"""Contrôle obligatoire de toute nouvelle image par rapport à l'image de référence choisie.

Règle (docs/storyboard.md) : sauf demande explicite, une génération doit respecter le style, les couleurs,
l'apparence des lieux et des personnages, et leur positionnement. Si le contrôle échoue, on recommence.

Vérifications :
  1. même taille que la référence ;
  2. HORS des zones autorisées : l'image est identique à la référence (lieux, personnages, positions, couleurs
     intacts) — écart moyen < 1,5 et 99,9e centile < 16 (sur 255) ;
  3. DANS chaque zone autorisée : la retouche garde le style de son entourage
     - couleurs : au moins 90 % des nouveaux pixels ont une couleur déjà présente dans la référence ;
     - netteté : les ajouts ne doivent pas être plus flous que les éléments voisins de la référence
       (médiane, sur les tuiles 24×24 qui contiennent des traits, du 95e centile du gradient ; ratio ≥ 0,8).
       Le critère « grain » a été retiré (avis du 13/10 : il poussait à flouter les ajouts) ;
     - pas de bord visible : saut de couleur moyen le long du contour de la zone limité ;
  4. image de contrôle : référence | résultat | différences (zones autorisées en vert), + calque si --plan.

Usage :
  python3 tools/controle_retouche.py REF.png RESULTAT.png --zones "x0,y0,x1,y1;x0,y0,x1,y1" [--plan P01] [--sortie CTRL.jpg]
Code de sortie 0 = CONFORME, 1 = À REFAIRE.
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SEUIL_HORS_MOY, SEUIL_HORS_P999 = 1.5, 16.0
SEUIL_PALETTE = 0.90
RATIO_NET = 0.80    # netteté des ajouts ≥ 80 % de celle des éléments voisins de la référence
TRAIT = 25.0        # une tuile « contient des traits » si son 95e centile de gradient dépasse ce seuil
SEUIL_BORD = 28.0


def lap(g):
    return np.abs(g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])


def hist(px):
    q = (px // 32).astype(int)
    h = np.bincount(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], minlength=512).astype(float)
    return h / max(h.sum(), 1)


def qcol(px):
    q = (np.asarray(px) // 16).astype(int)
    return q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]


def carte_bruit(img):
    """Carte du grain (petites et moyennes taches) + masque des zones sans trait de contour."""
    g = Image.fromarray(np.clip(img.mean(2), 0, 255).astype("uint8"))
    f = lambda r: np.array(g.filter(ImageFilter.GaussianBlur(r))).astype(float)  # noqa: E731
    g0, g1, g4 = np.array(g).astype(float), f(1.0), f(4.0)
    gy, gx = np.gradient(g4)
    return np.abs(g0 - g1) + np.abs(g1 - g4), np.hypot(gx, gy) < 3


def tuiles(nb, plat, mask, t=24, part=0.5):
    """Grain moyen de chaque tuile t×t (aplats seulement) où le masque couvre au moins `part` de la tuile."""
    out = []
    H, W = nb.shape
    for y in range(0, H - t + 1, t):
        for x in range(0, W - t + 1, t):
            m = mask[y:y + t, x:x + t]; p = plat[y:y + t, x:x + t] & m
            if m.mean() >= part and p.sum() >= t * t * 0.25:
                out.append((float(np.median(nb[y:y + t, x:x + t][p])), x, y))  # médiane : un trait isolé ne compte pas, le grain si
    return out


def nettete(g, mask, t=24, part=0.3):
    """95e centile du gradient de chaque tuile t×t couverte au moins à `part` par le masque et contenant des traits."""
    gy, gx = np.gradient(g)
    gm = np.hypot(gx, gy)
    out = []
    for y in range(0, g.shape[0] - t + 1, t):
        for x in range(0, g.shape[1] - t + 1, t):
            mk = mask[y:y + t, x:x + t]
            if mk.mean() >= part:
                v = float(np.percentile(gm[y:y + t, x:x + t][mk], 95))
                if v > TRAIT:
                    out.append(v)
    return out


def controle(ref, res, zones, plan=None, sortie=None):
    global PAL, CTX
    msgs, ok = [], True
    if ref.size != res.size:
        return False, [f"ÉCHEC taille : {res.size} au lieu de {ref.size}"]
    A = np.array(ref.convert("RGB")).astype(float)
    B = np.array(res.convert("RGB")).astype(float)
    H, W = A.shape[:2]
    zm = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in zones:
        zm[y0:y1, x0:x1] = True
    d = np.abs(A - B).mean(2)
    hors = d[~zm]
    moy, p999 = hors.mean(), np.percentile(hors, 99.9)
    bon = moy < SEUIL_HORS_MOY and p999 < SEUIL_HORS_P999
    ok &= bon
    msgs.append(f"{'OK ' if bon else 'ÉCHEC'} hors zones : écart moyen {moy:.2f} (< {SEUIL_HORS_MOY}), "
                f"99,9e centile {p999:.1f} (< {SEUIL_HORS_P999}) — lieux/personnages/positions inchangés")
    PAL = np.bincount(qcol(A).ravel(), minlength=4096)
    PAL[PAL < 20] = 0                                     # couleurs vraiment présentes dans la référence


    def CTX(y0, y1, x0, x1):
        c = np.zeros((H, W), bool); c[y0:y1, x0:x1] = True
        return c
    for i, (x0, y0, x1, y1) in enumerate(zones, 1):
        m = 80   # contexte local de la scène dans la RÉFÉRENCE (zone élargie, objets voisins compris)
        X0, Y0, X1, Y1 = max(0, x0 - m), max(0, y0 - m), min(W, x1 + m), min(H, y1 + m)
        chg = np.zeros((H, W), bool); chg[y0:y1, x0:x1] = d[y0:y1, x0:x1] > 6
        if chg.sum() < 30:
            msgs.append(f"OK  zone {i} : (presque) pas modifiée")
            continue
        zin = B[chg]
        # couleurs : part des nouveaux pixels dont la couleur existe déjà dans la référence (palette de l'image)
        cov = np.mean(PAL[qcol(zin)] > 0)
        # netteté : les ajouts aussi nets que les éléments voisins (contexte élargi, hors zone) de la référence
        gA, gB = A.mean(2), B.mean(2)
        voisin = np.zeros((H, W), bool); voisin[Y0:Y1, X0:X1] = True; voisin[y0:y1, x0:x1] = False
        nz, nv = nettete(gB, chg), nettete(gA, voisin)
        ratio = (float(np.median(nz)) / float(np.median(nv))) if nz and nv else 1.0
        e = np.zeros((H, W), bool); e[y0:y1, x0:x1] = True
        bord = e & ~np.array(Image.fromarray(e.astype("uint8") * 255).filter(ImageFilter.MinFilter(5))).astype(bool)
        saut = d[bord].mean()
        c_t = True
        c_h = cov >= SEUIL_PALETTE
        c_g = ratio >= RATIO_NET
        c_b = saut < SEUIL_BORD
        ok &= c_t and c_h and c_g and c_b
        msgs.append(f"{'OK ' if c_t and c_h and c_g and c_b else 'ÉCHEC'} zone {i} {x0},{y0}–{x1},{y1} : "
                    f"couleurs déjà dans l'image {cov:.0%} (≥ {SEUIL_PALETTE:.0%}) {'✓' if c_h else '✗'} · "
                    f"netteté ×{ratio:.2f} (≥ {RATIO_NET}) {'✓' if c_g else '✗'} · "
                    f"bord {saut:.1f} (< {SEUIL_BORD:.0f}) {'✓' if c_b else '✗'}")
    if sortie:
        dv = Image.fromarray(np.clip(d * 4, 0, 255).astype("uint8")).convert("RGB")
        dr = ImageDraw.Draw(dv)
        for z in zones:
            dr.rectangle(z, outline=(0, 230, 0), width=4)
        tiles = [ref.convert("RGB"), res.convert("RGB"), dv]
        if plan:
            sys.path.insert(0, "tools")
            import calque
            tiles.append(Image.alpha_composite(res.convert("RGBA"), calque.calque(plan)).convert("RGB"))
        w = 720; h = round(H * w / W)
        cols = 2
        rows = (len(tiles) + 1) // 2
        sheet = Image.new("RGB", (w * cols, h * rows + 30 * rows), "white")
        noms = ["référence", "résultat", "différences (vert = zones autorisées)", f"calque {plan}"]
        for k, t in enumerate(tiles):
            x, y = (k % cols) * w, (k // cols) * (h + 30)
            sheet.paste(t.resize((w, h)), (x, y + 30))
            ImageDraw.Draw(sheet).text((x + 8, y + 8), noms[k], fill=(0, 0, 0))
        sheet.save(sortie, quality=82)
    msgs.append("=> CONFORME" if ok else "=> À REFAIRE (ne pas livrer : recommencer la retouche)")
    return ok, msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("res")
    ap.add_argument("--zones", default="")
    ap.add_argument("--plan"); ap.add_argument("--sortie")
    o = ap.parse_args()
    zones = [tuple(int(v) for v in z.split(",")) for z in o.zones.split(";") if z.strip()]
    ok, msgs = controle(Image.open(o.ref), Image.open(o.res), zones, o.plan, o.sortie)
    print("\n".join(msgs))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
