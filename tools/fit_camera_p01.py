"""Ajuste la caméra de la carte P01 sur l'image (moindres carrés) : bordures de trottoir proches ET lointaines,
contraintes latérales des éléments (4L et Estafette contre le trottoir, Diego au début de la chaussée, nez de la
Coccinelle au bord du trottoir, Jeannot et Enji sur le trottoir) + passage à niveau. Même modèle que tools/calque.py."""
import json
import math
import numpy as np
from scipy.optimize import least_squares

M, W, H = 0.037, 1920, 1080
# (u, v) image 1920  ->  contrainte : ('y', valeur) latérale sur la carte, ou ('x', valeur) en profondeur
OBS = [((0, 1078), 'y', 425, 'bordure gauche (près)'), ((366, 860), 'y', 425, 'bordure gauche (près)'),
       ((740, 680), 'y', 425, 'bordure gauche (loin)'), ((993, 600), 'y', 425, 'bordure gauche (loin)'),
       ((1297, 577), 'y', 565, 'bordure droite'), ((1837, 951), 'y', 565, 'bordure droite'),
       ((287, 860), 'y', 405, 'pieds de Jeannot (trottoir)'), ((127, 907), 'y', 400, 'Enji (trottoir)'),
       ((543, 870), 'y', 447, "arrière de la 4L (contre le trottoir)"),
       ((1066, 584), 'y', 451, "avant de l'Estafette (contre le trottoir)"),
       ((995, 603), 'y', 437, 'Diego (début de la chaussée)'),
       ((965, 588), 'y', 425, 'nez de la Coccinelle (bord du trottoir)'),
       ((1086, 547), 'x', 1538, 'passage à niveau')]
ELTS = {'jeannot': (287, 860), 'enji': (127, 907), '4l_arriere': (543, 870), 'estafette_avant': (1066, 584),
        'diego': (995, 603), 'coccinelle_nez': (965, 588)}


def sol(c, u, v):
    cx, cy, a, p, F, eye = c
    a, p = math.radians(a), math.radians(p)
    r, y = (u - W / 2) / F, (H / 2 - v) / F
    fd = math.cos(p) - y * math.sin(p)
    ud = math.sin(p) + y * math.cos(p)
    if ud >= -1e-6:
        return None
    t = -eye / ud
    f, rr = t * fd, t * r
    dx = f * math.cos(a) - rr * math.sin(a)
    dy = f * math.sin(a) + rr * math.cos(a)
    return cx + dx / M, cy + dy / M


def res(c):
    out = []
    for (u, v), k, val, _ in OBS:
        g = sol(c, u, v)
        out.append(1e3 if g is None else (g[1] - val if k == 'y' else (g[0] - val) * 0.3))
    return out


if __name__ == "__main__":
    x0 = [-175, 500, -1.88, -1.61, 3837, 1.9]
    r = least_squares(res, x0, bounds=([-900, 380, -15, -15, 600, 1.0], [300, 620, 15, 15, 8000, 5.0]))
    c = r.x
    print("caméra :", dict(zip(['x', 'y', 'angle', 'inclinaison', 'F', 'oeil'], np.round(c, 2))),
          "fov %.1f°" % (2 * math.degrees(math.atan(W / 2 / c[4]))))
    for (o, rv) in zip(OBS, res(c)):
        print(f"  {o[3]:42s} écart {rv:+6.1f} px carte ({rv * M:+.2f} m)")
    pos = {k: tuple(round(t) for t in sol(c, *uv)) for k, uv in ELTS.items()}
    print("positions au sol :", pos)
    from chemins import sortie_par_defaut
    with open(sortie_par_defaut("fit2.json"), "w", encoding="utf-8") as fh:
        json.dump({"cam": list(c), "pos": pos}, fh)
