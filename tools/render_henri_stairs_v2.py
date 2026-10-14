#!/usr/bin/env python3
"""Henri falls from the TOP door landing down the stairs to the MIDDLE landing.

6.0 s, 24 fps. Unique drawings held on twos/threes while position and
perspective scale are interpolated every frame. Front railing removed.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLATE = ROOT / "assets/rigs/henri-stairs-no-front-rail.png"
CEL_DIR = ROOT / "assets/cels/henri-fall"
AUDIO_PATH = ROOT / "audio/jeannot-slamrap.mp3"
OUTPUT = ROOT / "renders/henri-stairs-cels-24fps.mp4"
PREVIEW = ROOT / "renders/henri-stairs-v2-preview.jpg"

WIDTH, HEIGHT = 1920, 1080
FPS = 24
DURATION = 6.0
FRAME_COUNT = int(DURATION * FPS)  # 144
AUDIO_START = 23.00  # covers the previous line then "Henri tombe des escaliers"
CAPTION = "Henri tombe des escaliers, toutes ses dents sont esquintées"
# Body height in pixels at perspective scale 1.0 (on the middle landing).
BODY_AT_1 = 560

# Timeline keys: (time_s, x_frac, y_frac, perspective, drawing_name, anchor)
# anchor: "feet" sits the bbox bottom on the step; "center" for airborne.
# x/y are 0-1 on the 1920×1080 plate.
KEYS = [
    (0.00, 0.218, 0.285, 0.42, "d01", "feet"),
    (0.40, 0.205, 0.325, 0.45, "d02", "feet"),
    (0.80, 0.195, 0.365, 0.46, "d03", "feet"),
    (1.20, 0.198, 0.420, 0.50, "d04", "feet"),
    (1.55, 0.205, 0.470, 0.55, "d05", "feet"),
    (1.90, 0.215, 0.520, 0.60, "d06", "feet"),
    (2.25, 0.230, 0.565, 0.66, "d07", "feet"),
    (2.60, 0.255, 0.610, 0.72, "d08", "center"),
    (2.95, 0.290, 0.645, 0.78, "d09", "center"),
    (3.25, 0.325, 0.670, 0.82, "05", "center"),
    (3.50, 0.355, 0.688, 0.84, "06", "center"),
    (3.70, 0.380, 0.700, 0.85, "07", "center"),
    (3.90, 0.400, 0.710, 0.86, "08", "center"),
    (4.10, 0.415, 0.718, 0.87, "09", "center"),
    (4.30, 0.430, 0.725, 0.88, "10", "center"),
    (4.48, 0.442, 0.732, 0.88, "11", "center"),
    (4.66, 0.452, 0.738, 0.89, "12", "center"),
    (4.84, 0.460, 0.745, 0.89, "13", "center"),
    (5.00, 0.468, 0.755, 0.90, "14", "center"),
    (5.12, 0.472, 0.762, 0.90, "18", "center"),
    (5.28, 0.476, 0.755, 0.91, "19", "center"),
    (5.42, 0.480, 0.762, 0.90, "20", "center"),
    (5.58, 0.488, 0.768, 0.91, "21", "center"),
    (5.74, 0.495, 0.772, 0.92, "22", "center"),
    (5.90, 0.500, 0.776, 0.92, "23", "center"),
    (6.00, 0.505, 0.778, 0.92, "24", "center"),
]


def smoothstep(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def key_green(rgb_img: Image.Image) -> Image.Image:
    rgb = np.asarray(rgb_img.convert("RGB"), dtype=np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    key_score = np.maximum(0, g - np.maximum(r, b) - 10)
    alpha = np.clip(255 - key_score * 4, 0, 255).astype(np.uint8)
    clean_g = np.minimum(g, np.maximum(r, b) + 8)
    clean_rgb = np.stack([r, clean_g, b], axis=2).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([clean_rgb, alpha]), "RGBA")


def body_measure(sprite: Image.Image) -> float:
    """Stable 'body size' so outstretched limbs don't explode the scale."""
    w, h = sprite.size
    aspect = h / max(1, w)
    if aspect >= 1.05:
        return float(h)
    if aspect <= 0.72:
        return float(h) * 1.65
    return float(max(w, h)) * 0.82


def load_cels() -> dict[str, Image.Image]:
    cels: dict[str, Image.Image] = {}
    names = [k[4] for k in KEYS]
    for name in names:
        path = CEL_DIR / f"{name}.png"
        if not path.exists():
            raise FileNotFoundError(path)
        keyed = key_green(Image.open(path))
        bbox = keyed.getchannel("A").getbbox()
        if not bbox:
            raise RuntimeError(f"{path} empty after key")
        cels[name] = keyed.crop(bbox)
    return cels


def font_for(size: int) -> ImageFont.ImageFont:
    for path in (
        str(ROOT / "assets/fonts/DejaVuSans-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def sample_keys(t: float) -> tuple[float, float, float, str, str]:
    if t <= KEYS[0][0]:
        _, xf, yf, sc, name, anc = KEYS[0]
        return xf, yf, sc, name, anc
    if t >= KEYS[-1][0]:
        _, xf, yf, sc, name, anc = KEYS[-1]
        return xf, yf, sc, name, anc
    for i in range(len(KEYS) - 1):
        t0, x0, y0, s0, n0, a0 = KEYS[i]
        t1, x1, y1, s1, n1, a1 = KEYS[i + 1]
        if t0 <= t <= t1:
            u = smoothstep((t - t0) / max(1e-6, t1 - t0))
            xf = x0 + (x1 - x0) * u
            yf = y0 + (y1 - y0) * u
            sc = s0 + (s1 - s0) * u
            # Keep current drawing until the next key; switch at midpoint for less pop.
            name, anc = (n0, a0) if u < 0.55 else (n1, a1)
            return xf, yf, sc, name, anc
    _, xf, yf, sc, name, anc = KEYS[-1]
    return xf, yf, sc, name, anc


def add_caption(frame: Image.Image, t: float) -> Image.Image:
    # Show the lyric around the estimated fall line (26.48 in the song = 3.48 in this clip).
    local = t - 3.30
    if local < -0.15 or t > DURATION - 0.05:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade_in = min(1.0, max(0.0, (local + 0.15) / 0.25))
    fade_out = min(1.0, max(0.0, (DURATION - t) / 0.20))
    alpha = int(224 * fade_in * fade_out)
    draw.rounded_rectangle(
        (120, 949, 1800, 1035),
        radius=18,
        fill=(15, 21, 33, int(alpha * 0.9)),
        outline=(255, 221, 112, alpha),
        width=3,
    )
    font = font_for(37)
    box = draw.textbbox((0, 0), CAPTION, font=font, stroke_width=1)
    tw = box[2] - box[0]
    draw.text(
        ((WIDTH - tw) / 2, 969),
        CAPTION,
        font=font,
        fill=(255, 248, 230, alpha),
        stroke_width=2,
        stroke_fill=(12, 17, 28, alpha),
    )
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def add_impact(frame: Image.Image, t: float) -> Image.Image:
    if not 5.05 <= t <= 5.45:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade = max(0.0, 1.0 - (t - 5.05) / 0.40)
    if t < 5.16:
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(255, 251, 233, int(100 * fade)))
    else:
        font = font_for(76)
        draw.text(
            (520, 690),
            "CRAC",
            font=font,
            fill=(246, 83, 66, int(255 * fade)),
            stroke_width=8,
            stroke_fill=(26, 31, 45, int(255 * fade)),
        )
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def composite(plate: Image.Image, cels: dict[str, Image.Image], t: float) -> Image.Image:
    xf, yf, persp, name, anchor = sample_keys(t)
    sprite = cels[name]
    target = BODY_AT_1 * persp
    factor = target / max(1.0, body_measure(sprite))
    w = max(1, int(sprite.width * factor))
    h = max(1, int(sprite.height * factor))
    scaled = sprite.resize((w, h), Image.Resampling.LANCZOS)
    cx = xf * plate.width
    cy = yf * plate.height
    if anchor == "feet":
        x = round(cx - scaled.width / 2)
        y = round(cy - scaled.height * 0.92)
    else:
        x = round(cx - scaled.width / 2)
        y = round(cy - scaled.height / 2)
    scene = plate.convert("RGBA")
    scene.alpha_composite(scaled, dest=(x, y))

    # Camera stays on Henri so he remains readable at the top of the stairs.
    p = min(1.0, t / DURATION)
    zoom = 1.38 - 0.12 * p
    cam_x = xf * plate.width + plate.width * 0.16
    cam_y = yf * plate.height + plate.height * 0.10
    crop_w = WIDTH / zoom
    crop_h = HEIGHT / zoom
    # Keep 16:9 crop inside plate.
    if crop_w > plate.width:
        crop_w = plate.width
        crop_h = crop_w * HEIGHT / WIDTH
    if crop_h > plate.height:
        crop_h = plate.height
        crop_w = crop_h * WIDTH / HEIGHT
    left = max(0, min(plate.width - crop_w, cam_x - crop_w / 2))
    top = max(0, min(plate.height - crop_h, cam_y - crop_h / 2))
    frame = scene.convert("RGB").crop((left, top, left + crop_w, top + crop_h))
    frame = frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    if 5.08 <= t <= 5.22:
        shake = int(6 * (1 - (t - 5.08) / 0.14))
        i = int(t * FPS)
        frame = ImageChops.offset(frame, (i % 3 - 1) * shake, ((i + 1) % 3 - 1) * shake)
    frame = add_impact(frame, t)
    return add_caption(frame, t)


def render() -> None:
    cels = load_cels()
    print(f"Loaded {len(cels)} drawings")
    plate = Image.open(PLATE).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    # Placement contact sheet.
    thumbs = []
    for t in (0.0, 1.2, 2.25, 3.5, 5.12, 5.9):
        im = composite(plate, cels, t).copy()
        draw = ImageDraw.Draw(im)
        draw.text((24, 24), f"t={t:.2f}s", fill=(255, 221, 112), font=font_for(32))
        im.thumbnail((640, 360))
        thumbs.append(im)
    sheet = Image.new("RGB", (1920, 720), (12, 18, 28))
    for i, im in enumerate(thumbs):
        r, c = divmod(i, 3)
        sheet.paste(im, (c * 640, r * 360))
    sheet.save(PREVIEW, quality=85)
    print("wrote", PREVIEW)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-ss",
        str(AUDIO_START),
        "-t",
        str(DURATION),
        "-i",
        str(AUDIO_PATH),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-tune",
        "animation",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-shortest",
        "-movflags",
        "+faststart",
        str(OUTPUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for i in range(FRAME_COUNT):
        t = i / FPS
        frame = composite(plate, cels, t)
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if i % 24 == 0:
            print(f"frame {i}/{FRAME_COUNT} t={t:.2f}")
    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg exited {rc}")
    print(f"Rendered {FRAME_COUNT} frames at {FPS} fps: {OUTPUT}")


if __name__ == "__main__":
    render()
