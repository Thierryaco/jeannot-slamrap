"""Reprojette une plaque de fond d'une caméra A vers une caméra B via un modèle 3D simple de la rue
(sol, façades nord y=340, côté sud = un seul plan y=612 pour clôtures + façades, comme sur la plaque ; au-delà = infini).

python3 tools/warp_camera.py plaque_A.png camA.json camB.json sortie.png
"""
import json
import math
import sys

import cv2
import numpy as np

M = 0.037
W, H = 1920, 1080
XFAR = 1220


def basis(c):
    a = math.radians(c.get("angle", 0))
    F = (W / 2) / math.tan(math.radians(c["fov"]) / 2)
    return dict(o=np.array([c["x"] * M, c["y"] * M, 1.6]), f=np.array([math.cos(a), math.sin(a), 0.0]),
                r=np.array([-math.sin(a), math.cos(a), 0.0]), up=np.array([0, 0, 1.0]), F=F)


def rays(cb):
    u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    d = (cb["f"][None, None] + ((u - W / 2) / cb["F"])[..., None] * cb["r"][None, None]
         + (-(v - H / 2) / cb["F"])[..., None] * cb["up"][None, None])
    return d


def hit(cb, d):
    o = cb["o"]
    t = np.full(d.shape[:2], np.inf)
    # sol
    with np.errstate(divide="ignore", invalid="ignore"):
        tg = np.where(d[..., 2] < -1e-6, -o[2] / d[..., 2], np.inf)
        pg = o + tg[..., None] * d
        tg = np.where(pg[..., 0] <= 1545 * M, tg, np.inf)  # au-delà du passage à niveau : la route plonge
        t = np.minimum(t, tg)
        for yp, hmax in ((340 * M, 16.0), (612 * M, 16.0)):
            ty = np.where(np.abs(d[..., 1]) > 1e-6, (yp - o[1]) / d[..., 1], np.inf)
            ty = np.where(ty > 0, ty, np.inf)
            p = o + ty[..., None] * d
            ok = (p[..., 2] >= 0) & (p[..., 2] <= hmax) & (p[..., 0] >= 60 * M) & (p[..., 0] <= 1530 * M)
            t = np.minimum(t, np.where(ok, ty, np.inf))
    return t


def project(ca, P=None, D=None):
    """Projette des points 3D (P) ou des directions à l'infini (D) dans la caméra A -> (u, v)."""
    q = (P - ca["o"]) if P is not None else D
    z = (q * ca["f"]).sum(-1)
    r = (q * ca["r"]).sum(-1)
    y = (q * ca["up"]).sum(-1)
    z = np.where(z > 1e-3, z, np.nan)
    return W / 2 + ca["F"] * r / z, H / 2 - ca["F"] * y / z


def warp(plate, camA, camB):
    ca, cb = basis(camA), basis(camB)
    d = rays(cb)
    t = hit(cb, d)
    fin = np.isfinite(t)
    P = cb["o"] + np.where(fin, t, 0)[..., None] * d
    uA, vA = project(ca, P=P)
    uI, vI = project(ca, D=d)
    mx = np.where(fin, uA, uI)
    my = np.where(fin, vA, vI)
    # bout de la rue (garage, Estafette, passage à niveau, collines basses) : un seul plan transversal x = 1220 px
    # (tout y est à ~40-50 m : évite les doublons aux ruptures de profondeur du modèle)
    with np.errstate(divide="ignore", invalid="ignore"):
        tf = (XFAR * M - cb["o"][0]) / d[..., 0]
    Pf = cb["o"] + tf[..., None] * d
    uF, vF = project(ca, P=Pf)
    loin = ((~fin) | (P[..., 0] >= 1080 * M)) & (Pf[..., 2] < 9.0) & (tf > 0)
    mx = np.where(loin, uF, mx).astype(np.float32)
    my = np.where(loin, vF, my).astype(np.float32)
    mx = np.nan_to_num(mx, nan=-1)
    my = np.nan_to_num(my, nan=-1)
    return cv2.remap(plate, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), (mx, my)


def a_to_b(camA, camB, uA, vA, plane):
    """Point image A sur un plan donné ('sol' ou ('y', valeur_px)) -> image B."""
    ca, cb = basis(camA), basis(camB)
    d = ca["f"] + (uA - W / 2) / ca["F"] * ca["r"] + (-(vA - H / 2) / ca["F"]) * ca["up"]
    o = ca["o"]
    t = -o[2] / d[2] if plane == "sol" else (plane[1] * M - o[1]) / d[1]
    p = o + t * d
    u, v = project(cb, P=p[None])
    return float(u[0]), float(v[0])


if __name__ == "__main__":
    plate = cv2.imread(sys.argv[1])
    A, B = json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    out, _ = warp(plate, A, B)
    cv2.imwrite(sys.argv[4], out)
    print(sys.argv[4])
