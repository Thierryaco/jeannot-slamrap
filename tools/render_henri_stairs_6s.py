#!/usr/bin/env python3
"""Henri falls from the door landing down to the middle landing.

6.0 s, 24 fps. Drawings held on twos (12 pose slots/s) while position,
scale and a light bob are interpolated every frame. Consistent body size
from perspective, not from the cel bounding-box.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLATE = ROOT / "assets/rigs/henri-stairs-no-rail.png"
STAIRS = ROOT / "assets/cels/henri-stairs"
FALL = ROOT / "assets/cels/henri-fall"
AUDIO = ROOT / "audio/jeannot-slamrap.mp3"
FRAME_DIR = ROOT / "renders/henri-stairs-6s-frames"
OUTPUT = ROOT / "renders/henri-stairs-6s-24fps.mp4"
PREVIEW = ROOT / "renders/henri-stairs-6s-preview.jpg"

WIDTH, HEIGHT = 1920, 1080
FPS = 24
DURATION = 6.0
FRAME_COUNT = round(DURATION * FPS)  # 144
AUDIO_START = 23.50
CAPTION = "Henri tombe des escaliers, toutes ses dents sont esquintées"

# Path: (t 0-1, feet_x, feet_y) on the 1376×768 plate.
# Start = palier de la porte ; end = palier du milieu.
PATH = [
    (0.00, 300, 238),
    (0.10, 298, 240),
    (0.18, 286, 272),
    (0.26, 274, 304),
    (0.34, 262, 338),
    (0.42, 250, 372),
    (0.50, 240, 408),
    (0.56, 236, 448),
    (0.62, 250, 495),
    (0.70, 300, 545),
    (0.78, 370, 590),
    (0.86, 445, 630),
    (0.93, 500, 655),
    (1.00, 530, 668),
]

# Pose timeline: (t_start, cel). Held until the next key. Walk cycle then tumble.
POSES: list[tuple[float, Path]] = [
    (0.00, STAIRS / "01.png"),
    (0.45, STAIRS / "02.png"),
    (0.70, STAIRS / "03.png"),
    (0.95, STAIRS / "04.png"),
    (1.20, STAIRS / "02.png"),
    (1.45, STAIRS / "03.png"),
    (1.70, STAIRS / "05.png"),
    (1.95, STAIRS / "02.png"),
    (2.20, STAIRS / "04.png"),
    (2.45, STAIRS / "03.png"),
    (2.70, STAIRS / "05.png"),
    (2.95, STAIRS / "06.png"),  # slip
    (3.25, STAIRS / "07.png"),
    (3.55, STAIRS / "08.png"),
    (3.85, STAIRS / "09.png"),
    (4.10, FALL / "10.png"),
    (4.30, FALL / "12.png"),
    (4.50, FALL / "13.png"),
    (4.70, FALL / "08.png"),
    (4.90, FALL / "17.png"),
    (5.10, FALL / "18.png"),  # squash / CRAC
    (5.30, FALL / "19.png"),
    (5.50, FALL / "21.png"),
    (5.70, FALL / "22.png"),
    (5.85, FALL / "24.png"),
]


def key_green(img: Image.Image) -> Image.Image:
    rgb = np.asarray(img.convert("RGB"), dtype=np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    key = np.maximum(0, g - np.maximum(r, b) - 10)
    alpha = np.clip(255 - key * 4, 0, 255).astype(np.uint8)
    clean_g = np.minimum(g, np.maximum(r, b) + 8)
    clean = np.stack([r, clean_g, b], axis=2).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([clean, alpha]), "RGBA")


def load_cel(path: Path) -> Image.Image:
    keyed = key_green(Image.open(path))
    bbox = keyed.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"no foreground in {path}")
    return keyed.crop(bbox)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def path_at(t: float) -> tuple[float, float]:
    t = min(1.0, max(0.0, t))
    for i in range(len(PATH) - 1):
        t0, x0, y0 = PATH[i]
        t1, x1, y1 = PATH[i + 1]
        if t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return lerp(x0, x1, u), lerp(y0, y1, u)
    return PATH[-1][1], PATH[-1][2]


def height_at_y(y: float) -> float:
    """Perspective: smaller at the door, larger on the middle landing."""
    u = min(1.0, max(0.0, (y - 238) / (668 - 238)))
    return lerp(168, 292, u)


def pose_at(time_s: float) -> Path:
    current = POSES[0][1]
    for t0, path in POSES:
        if time_s + 1e-6 >= t0:
            current = path
        else:
            break
    return current


def scale_sprite(sprite: Image.Image, target_h: float) -> Image.Image:
    w, h = sprite.size
    if w > h * 1.2:
        factor = (target_h * 1.08) / max(w, 1)
    else:
        factor = target_h / max(h, 1)
    nw, nh = max(1, int(w * factor)), max(1, int(h * factor))
    return sprite.resize((nw, nh), Image.Resampling.LANCZOS)


def font_for(size: int) -> ImageFont.ImageFont:
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def add_caption(frame: Image.Image, t: float) -> Image.Image:
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    alpha = int(220 * min(1.0, t / 0.25, (DURATION - t) / 0.25))
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


def add_crac(frame: Image.Image, t: float) -> Image.Image:
    if not 5.05 <= t <= 5.55:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade = 1.0 - (t - 5.05) / 0.50
    if t < 5.18:
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(255, 251, 233, int(110 * fade)))
    font = font_for(78)
    draw.text(
        (780, 620),
        "CRAC",
        font=font,
        fill=(246, 83, 66, int(255 * fade)),
        stroke_width=8,
        stroke_fill=(26, 31, 45, int(255 * fade)),
    )
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def camera_crop(scene: Image.Image, t_norm: float) -> Image.Image:
    # Follow Henri: start on the door, tilt down to the middle landing.
    zoom = lerp(1.18, 1.06, t_norm)
    cx = lerp(340, 560, t_norm)
    cy = lerp(260, 560, t_norm)
    crop_h = scene.height / zoom
    crop_w = crop_h * 16 / 9
    left = max(0, min(scene.width - crop_w, cx - crop_w / 2))
    top = max(0, min(scene.height - crop_h, cy - crop_h / 2))
    return scene.crop((left, top, left + crop_w, top + crop_h)).resize(
        (WIDTH, HEIGHT), Image.Resampling.LANCZOS
    )


def render_frame(plate: Image.Image, cache: dict[Path, Image.Image], i: int) -> Image.Image:
    t = i / FPS
    t_norm = t / DURATION
    fx, fy = path_at(t_norm)
    # Walk bob, then tumble wobble.
    if t < 2.95:
        fy += math.sin(t * 10.5) * 3.0
    elif t < 5.10:
        fy += math.sin(t * 18) * 4.0
        fx += math.cos(t * 14) * 3.0
    target_h = height_at_y(fy)
    cel_path = pose_at(t)
    sprite = scale_sprite(cache[cel_path], target_h)
    scene = plate.convert("RGBA")
    w, h = sprite.size
    # Feet-anchored while walking; body-centered once he leaves the steps.
    if t < 3.20:
        x = round(fx - w / 2)
        y = round(fy - h + 6)
    else:
        x = round(fx - w / 2)
        y = round(fy - h * 0.55)
    scene.alpha_composite(sprite, dest=(x, y))
    frame = camera_crop(scene.convert("RGB"), t_norm)
    if 5.08 <= t < 5.28:
        shake = int(6 * (1 - (t - 5.08) / 0.20))
        frame = ImageChops.offset(frame, (i % 3 - 1) * shake, ((i + 1) % 3 - 1) * shake)
    frame = add_crac(frame, t)
    return add_caption(frame, t)


def load_cache() -> dict[Path, Image.Image]:
    cache: dict[Path, Image.Image] = {}
    for _, path in POSES:
        if path not in cache:
            if not path.exists():
                raise FileNotFoundError(path)
            cache[path] = load_cel(path)
            print(f"cel {path.name} cropped {cache[path].size}")
    return cache


def preview(plate: Image.Image, cache: dict[Path, Image.Image]) -> None:
    times = [0.0, 0.8, 1.6, 2.5, 3.4, 4.3, 5.15, 5.9]
    thumbs = []
    for ts in times:
        i = min(FRAME_COUNT - 1, int(ts * FPS))
        im = render_frame(plate, cache, i)
        im.thumbnail((480, 270))
        thumbs.append(im)
    sheet = Image.new("RGB", (4 * 480, 2 * 270), (12, 18, 28))
    for n, im in enumerate(thumbs):
        r, c = divmod(n, 4)
        sheet.paste(im, (c * 480, r * 270))
    sheet.save(PREVIEW, quality=85)
    print("preview", PREVIEW)


def encode() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-framerate", str(FPS),
        "-i", str(FRAME_DIR / "frame_%03d.png"),
        "-ss", str(AUDIO_START),
        "-t", str(DURATION),
        "-i", str(AUDIO),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "18", "-tune", "animation",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        str(OUTPUT),
    ]
    subprocess.run(cmd, check=True)
    print("wrote", OUTPUT)


def main() -> None:
    plate = Image.open(PLATE).convert("RGB")
    if plate.size != (1376, 768):
        plate = plate.resize((1376, 768), Image.Resampling.LANCZOS)
    cache = load_cache()
    preview(plate, cache)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(FRAME_COUNT):
        render_frame(plate, cache, i).save(FRAME_DIR / f"frame_{i:03d}.png")
        if i % 24 == 0:
            print(f"frame {i}/{FRAME_COUNT}")
    encode()


if __name__ == "__main__":
    main()
