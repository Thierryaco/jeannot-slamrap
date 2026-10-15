#!/usr/bin/env python3
"""P02 v9 = la v7 (« à retoucher » ; la v8 est écartée) avec le correctif 10 de la liste (avis du 14/10 sur la v3) :

10. lumière de plein jour comme dans P01 au lieu de la lumière chaude et sépia de fin d'après-midi.

Correction de couleur seule : rien ne bouge (formes, traits, personnages, positions). Le décor qui garde la lumière
sépia est recoloré matière par matière sur le décor de P01 v33 (moyenne et étalement Lab de la même matière) :
  - végétation (colline, buissons, grillage vert) : teinte de P01 (plus verte, moins jaune) ;
  - tons moyens (pierres, béton, crépi à l'ombre, ombres) : teinte de P01 (beaucoup moins jaune) et clarté
    rapprochée de P01 à 70 % ;
  - surfaces claires (murs crème) : teinte de P01, clarté gardée (les façades de P01 sont plus grises ; les
    assombrir ternirait l'image au lieu de l'éclairer) ; végétation : clarté gardée aussi.
Restent tels quels (déjà aux couleurs de P01) : Jeannot, Enji, la 4L, la route et les trottoirs, la bande de ciel,
ainsi que les traits sombres. Poids progressifs (pas de bord dur entre matières), mélange en RVB (poids 0 = pixel
strictement inchangé).

Contrôle obligatoire (couleurs visées = celles de P01 : --palette P01) :
  python3 tools/controle_retouche.py p02-v7-maison-route.png p02-v9-lumiere.png \\
      --zones "<voir ZONES affichées>" --plan P02 --sortie p02-v9-controle.jpg \\
      --palette assets/storyboards/a-valider/p01/p01-v33-net.png

Usage : python3 tools/p02_v9.py [SORTIE]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p02_v4  # noqa: E402  (masques du sol)
import p02_v6  # noqa: E402  (silhouettes d'Enji et de Jeannot)
import p02_v7  # noqa: E402  (silhouette de la 4L)

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "assets/storyboards/a-valider/p02"
SRC = DOSSIER / "p02-v7-maison-route.png"
V3 = DOSSIER / "p02-v3-cul-de-sac.png"
V5 = DOSSIER / "p02-v5-plaque-rouille.png"
P01 = ROOT / "assets/storyboards/a-valider/p01/p01-v33-net.png"
SORTIE = DOSSIER / "p02-v9-lumiere.png"

# décor de P01 v33 servant de modèle (maisons et murs de gauche, maisons de droite ; ciel exclu par la couleur)
P01_DECOR = [(0, 0, 700, 470), (1080, 80, 1920, 640)]
# part de l'écart de clarté moyenne rattrapée vers P01, par matière : la végétation et les murs clairs de P01 sont
# un peu plus sombres en moyenne — les assombrir irait contre le « plein jour » : on n'en prend que la teinte
CLARTE = {"vegetation": 0.0, "moyens": 0.7, "clairs": 0.0}


def _rampe(v, a, b):
    return np.clip((v - a) / (b - a), 0, 1)


def matieres(lab, fond):
    """Poids (0..1) des matières du décor : végétation, surfaces claires, tons moyens (ciel et traits exclus)."""
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    f = fond.astype(np.float32)
    pas_ciel = 1 - _rampe(-B, 4, 8) * _rampe(L, 140, 160)
    veg = f * pas_ciel * _rampe(-A, 3, 7) * _rampe(B, 2, 6) * _rampe(L, 30, 40) * (1 - _rampe(L, 205, 215))
    clair = f * pas_ciel * (1 - veg) * _rampe(L, 160, 180) * (1 - _rampe(np.abs(A), 10, 14)) * _rampe(B, 0, 4)
    moyen = (f * pas_ciel * (1 - veg) * (1 - _rampe(L, 160, 180)) * _rampe(L, 50, 70)
             * (1 - _rampe(np.hypot(A, B), 26, 34)))
    return {"vegetation": veg, "clairs": clair, "moyens": moyen}


def protege(v7):
    """Ce qui garde ses couleurs : sol (route, trottoirs, bordures), Jeannot, Enji, la 4L, bas de l'image."""
    H, W = v7.shape[:2]
    v3 = np.asarray(Image.open(V3).convert("RGB"))
    v5 = np.asarray(Image.open(V5).convert("RGB"))
    m = np.zeros((H, W), bool)
    for z in p02_v4.masques_sol(v3).values():
        m |= z
    for nom, fichier, rc, ret, boite in p02_v6.PERSOS:
        x0, y0, x1, y1 = rc
        _, nouvelle = p02_v6.masque(v5[y0:y1, x0:x1], p02_v6.charger(fichier, rc, ret), boite)
        m[y0:y1, x0:x1] |= nouvelle
    m |= p02_v7.silhouette_4l(v7)
    # le sol de la route de la v7 (bordures et caniveau redessinés) : tout ce qui est sous la ligne des
    # trottoirs dans le recadrage route, hors grillage et murs, est déjà du sol dans les masques ci-dessus
    m[960:, :] = True
    return m


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sortie = Path(args[0]) if args else SORTIE
    v7 = np.asarray(Image.open(SRC).convert("RGB"))
    p01 = np.asarray(Image.open(P01).convert("RGB"))
    prot = protege(v7)
    lab7 = cv2.cvtColor(v7, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab1 = cv2.cvtColor(p01, cv2.COLOR_RGB2LAB).astype(np.float32)
    fond1 = np.zeros(p01.shape[:2], bool)
    for x0, y0, x1, y1 in P01_DECOR:
        fond1[y0:y1, x0:x1] = True
    m7, m1 = matieres(lab7, ~prot), matieres(lab1, fond1)
    new = lab7.copy()
    total = np.zeros(v7.shape[:2], np.float32)
    infos = []
    for nom in ("vegetation", "moyens", "clairs"):
        w7, w1 = m7[nom], m1[nom]
        src, dst = lab7[w7 > 0.5], lab1[w1 > 0.5]
        mu_s, sd_s = src.mean(0), src.std(0) + 1e-3
        mu_d, sd_d = dst.mean(0), dst.std(0) + 1e-3
        k = np.clip(sd_d / sd_s, 0.7, 1.4)
        cible = (lab7 - mu_s) * k + mu_d
        cible[..., 0] = lab7[..., 0] + CLARTE[nom] * (mu_d[0] - mu_s[0])   # clarté : ombres et traits gardés
        new = new * (1 - w7[..., None]) + cible * w7[..., None]
        total = np.maximum(total, w7)
        infos.append(f"{nom} {int((w7 > 0.5).sum())} px (Δa {mu_d[1] - mu_s[1]:+.1f}, Δb {mu_d[2] - mu_s[2]:+.1f}, "
                     f"ΔL {CLARTE[nom] * (mu_d[0] - mu_s[0]):+.1f})")
    rgb = cv2.cvtColor(np.clip(new, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    t = total[..., None]
    out = v7.astype(np.float32) * (1 - t) + rgb * t
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    Image.fromarray(out).save(sortie, optimize=True)
    ch = np.abs(out.astype(int) - v7.astype(int)).max(axis=2) > 0
    ys, xs = np.nonzero(ch)
    zone = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    print(f"ok {sortie} | " + " · ".join(infos) + f" | {int(ch.sum())} px changés, protégés {int((ch & prot).sum())}")
    print("zones du contrôle : " + ",".join(map(str, zone)))


if __name__ == "__main__":
    main()
