"""Détourage fond vert -> sprite RGBA rogné.  python3 tools/sprite_chroma.py in.png out.png"""
import sys
import numpy as np
from PIL import Image
import cv2


def chroma(path):
    im = np.array(Image.open(path).convert("RGB")).astype(np.int16)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    green = (g > 120) & (g > r + 45) & (g > b + 45)
    # composante connexe du fond touchant les bords (évite de trouer des objets verts... ou les vitres : gardées transparentes)
    a = np.where(green, 0, 255).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    a = cv2.GaussianBlur(a, (3, 3), 0)
    out = im.copy()
    # despill : limiter le vert au max(r,b)+10 sur les bords
    m = np.maximum(r, b) + 10
    spill = (g > m) & (a > 0)
    out[..., 1] = np.where(spill, m, g)
    rgba = np.dstack([np.clip(out, 0, 255).astype(np.uint8), a])
    ys, xs = np.where(a > 20)
    return Image.fromarray(rgba).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


if __name__ == "__main__":
    s = chroma(sys.argv[1])
    s.save(sys.argv[2])
    print(sys.argv[2], s.size)
