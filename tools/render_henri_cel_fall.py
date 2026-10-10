#!/usr/bin/env python3
"""Composite Henri fall cels (green-screen drawings) onto the locked stairs plate.

Expects assets/cels/henri-fall/01.png … 24.png. Missing numbers are skipped.
This replaces the old single-cutout rotation test.

Uses imageio-ffmpeg (bundled ffmpeg) so it runs without system ffmpeg / PyAV.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLATE = ROOT / "assets/rigs/henri-stairs-clean-plate.png"
CEL_DIR = ROOT / "assets/cels/henri-fall"
AUDIO_PATH = ROOT / "audio/jeannot-slamrap.mp3"
OUTPUT = ROOT / "renders/henri-stairs-cels-12fps.mp4"
FRAME_DIR = ROOT / "renders/henri-fall-frames"

WIDTH, HEIGHT = 1920, 1080
FPS = 12
DURATION = 2.50
FRAME_COUNT = round(DURATION * FPS)  # 30 video frames: 24 drawings + holds
AUDIO_START = 26.48
CAPTION = "Henri tombe des escaliers, toutes ses dents sont esquintées"
BASE_SIZE = 500  # max sprite side in plate pixels, before per-pose scale

# Placement on the 1376×768 working plate: (cx, cy, scale)
# Stay on the landing; tumble left and slightly down; do not leave the frame.
PLACEMENT = {
    1: (760, 470, 0.95),
    2: (750, 468, 0.95),
    3: (730, 455, 0.98),
    4: (700, 440, 1.00),
    5: (660, 430, 1.05),
    6: (620, 420, 1.08),
    7: (590, 475, 0.82),
    8: (560, 440, 1.00),
    9: (540, 410, 1.05),
    10: (520, 450, 1.08),
    11: (510, 485, 0.88),
    12: (500, 445, 1.10),
    13: (490, 415, 1.05),
    14: (480, 500, 0.82),
    15: (470, 435, 1.02),
    16: (465, 470, 0.98),
    17: (460, 490, 1.05),
    18: (455, 535, 0.78),
    19: (455, 505, 0.98),
    20: (458, 525, 0.85),
    21: (470, 535, 0.95),
    22: (480, 530, 0.95),
    23: (475, 540, 0.95),
    24: (490, 535, 0.98),
}


def key_green(rgb_img: Image.Image) -> Image.Image:
    rgb = np.asarray(rgb_img.convert("RGB"), dtype=np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    key_score = np.maximum(0, g - np.maximum(r, b) - 10)
    alpha = np.clip(255 - key_score * 4, 0, 255).astype(np.uint8)
    clean_g = np.minimum(g, np.maximum(r, b) + 8)
    clean_rgb = np.stack([r, clean_g, b], axis=2).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([clean_rgb, alpha]), "RGBA")


def load_cels() -> dict[int, Image.Image]:
    cels: dict[int, Image.Image] = {}
    for i in range(1, 25):
        path = CEL_DIR / f"{i:02d}.png"
        if not path.exists():
            continue
        keyed = key_green(Image.open(path))
        bbox = keyed.getchannel("A").getbbox()
        if not bbox:
            raise RuntimeError(f"{path} has no foreground after key")
        cels[i] = keyed.crop(bbox)
    if not cels:
        raise RuntimeError(f"No cels in {CEL_DIR}")
    return cels


def font_for(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def drawing_index(frame_i: int) -> int:
    """Map 30 video frames onto 24 drawings; hold the last pose at the end."""
    if frame_i < 24:
        return frame_i + 1
    return 24


def add_impact(frame: Image.Image, drawing: int) -> Image.Image:
    if drawing not in {18, 19, 20}:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    if drawing == 18:
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(255, 251, 233, 120))
    else:
        fade = 1.0 if drawing == 19 else 0.55
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


def add_caption(frame: Image.Image, t: float) -> Image.Image:
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    alpha = int(224 * min(1.0, t / 0.12, (DURATION - t) / 0.16))
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


def render_frame(plate: Image.Image, cels: dict[int, Image.Image], i: int) -> Image.Image:
    drawing = drawing_index(i)
    available = sorted(cels)
    # If some cels are still missing, clamp to the nearest existing drawing.
    use = drawing if drawing in cels else min(available, key=lambda n: abs(n - drawing))
    sprite = cels[use]
    cx, cy, scale = PLACEMENT.get(use, PLACEMENT[min(PLACEMENT)])
    longest = max(sprite.width, sprite.height)
    factor = (BASE_SIZE * scale) / longest
    w = max(1, int(sprite.width * factor))
    h = max(1, int(sprite.height * factor))
    scaled = sprite.resize((w, h), Image.Resampling.LANCZOS)
    scene = plate.convert("RGBA")
    x = round(cx - scaled.width / 2)
    y = round(cy - scaled.height / 2)
    scene.alpha_composite(scaled, dest=(x, y))

    t = i / FPS
    p = min(1.0, t / DURATION)
    zoom = 1.0 + 0.10 * p
    center_x = plate.width * (0.50 - 0.06 * p)
    center_y = plate.height * (0.50 + 0.12 * p)
    crop_w = (plate.height * 16 / 9) / zoom
    crop_h = plate.height / zoom
    left = max(0, min(plate.width - crop_w, center_x - crop_w / 2))
    top = max(0, min(plate.height - crop_h, center_y - crop_h / 2))
    frame = scene.convert("RGB").crop((left, top, left + crop_w, top + crop_h))
    frame = frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    if use in {18, 19}:
        shake = 5 if use == 18 else 3
        frame = ImageChops.offset(frame, (i % 3 - 1) * shake, ((i + 1) % 3 - 1) * shake)
    frame = add_impact(frame, use)
    return add_caption(frame, t)


def render() -> None:
    cels = load_cels()
    print(f"Loaded {len(cels)} cels: {sorted(cels)}")
    plate = Image.open(PLATE).convert("RGB")
    if plate.size != (1376, 768):
        plate = plate.resize((1376, 768), Image.Resampling.LANCZOS)

    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(FRAME_COUNT):
        frame = render_frame(plate, cels, i)
        frame.save(FRAME_DIR / f"frame_{i:03d}.png")
        print(f"frame {i + 1}/{FRAME_COUNT}")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAME_DIR / "frame_%03d.png"),
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
    subprocess.run(cmd, check=True)
    print(f"Rendered {FRAME_COUNT} frames at {FPS} fps: {OUTPUT}")


if __name__ == "__main__":
    render()
