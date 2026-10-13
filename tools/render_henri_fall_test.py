#!/usr/bin/env python3
"""Render a 12 fps cut-out action test of Henri tumbling down the stairs.

This is a first puppet/cut-out motion study from the approved 2D character cel,
not the final hand-drawn frame-by-frame animation. Requires av, numpy and pillow.
"""
from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLATE = ROOT / "assets/rigs/henri-stairs-clean-plate.png"
SPRITE_SOURCE = ROOT / "assets/rigs/henri-cutout-green.png"
AUDIO_PATH = ROOT / "audio/jeannot-slamrap.mp3"
OUTPUT = ROOT / "renders/henri-stairs-test-12fps.mp4"

WIDTH, HEIGHT = 1920, 1080
FPS = 12
DURATION = 2.75
FRAME_COUNT = round(DURATION * FPS)
AUDIO_START = 26.48  # entrée candidate du vers sur la chute, à confirmer à l'écoute
SAMPLE_RATE = 48_000
AUDIO_SAMPLES = round(DURATION * SAMPLE_RATE)
CAPTION = "Henri tombe des escaliers, toutes ses dents sont esquintées"


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def load_sprite() -> tuple[Image.Image, tuple[int, int, int, int]]:
    rgb = np.asarray(Image.open(SPRITE_SOURCE).convert("RGB"), dtype=np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    key_score = np.maximum(0, g - np.maximum(r, b) - 10)
    alpha = np.clip(255 - key_score * 4, 0, 255).astype(np.uint8)
    # Remove green spill on antialiased hair/clothing edges before compositing.
    clean_g = np.minimum(g, np.maximum(r, b) + 8)
    clean_rgb = np.stack([r, clean_g, b], axis=2).clip(0, 255).astype(np.uint8)
    rgba = Image.fromarray(np.dstack([clean_rgb, alpha]), "RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("Henri cutout has no foreground pixels")
    return rgba.crop(bbox), bbox


def load_plate(size: tuple[int, int]) -> Image.Image:
    plate = Image.open(PLATE).convert("RGB")
    if plate.size != size:
        plate = plate.resize(size, Image.Resampling.LANCZOS)
    return plate


def font_for(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def motion(t: float, bbox: tuple[int, int, int, int]) -> tuple[float, float, float]:
    left, top, right, bottom = bbox
    start_x = (left + right) / 2
    start_y = (top + bottom) / 2
    fall = smoothstep((t - .25) / 1.85)
    settle = max(0.0, min(1.0, (t - 2.10) / .35))
    center_x = start_x - 315 * fall
    center_y = start_y + 170 * fall
    # One fast, readable cartoon tumble; final orientation is horizontal.
    angle = 435 * fall
    if t >= 2.10:
        wobble = (1 - settle) * math.sin((t - 2.10) * 31) * 7
        angle = 435 + wobble
        center_x -= (1 - settle) * 10
        center_y += settle * 5
    return center_x, center_y, angle


def draw_speed_lines(base: Image.Image, t: float, bbox: tuple[int, int, int, int]) -> Image.Image:
    fall = smoothstep((t - .25) / 1.85)
    if fall < .08 or t > 2.2:
        return base
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    alpha = int(105 * math.sin(min(1.0, fall) * math.pi))
    for i in range(8):
        x = 170 + i * 83 + (t * 120) % 55
        y = 215 + i * 42
        draw.line((x, y, x - 70, y + 25), fill=(248, 243, 226, alpha), width=4)
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def composite_character(base: Image.Image, sprite: Image.Image, bbox: tuple[int, int, int, int], t: float) -> Image.Image:
    cx, cy, angle = motion(t, bbox)
    rotated = sprite.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    x = round(cx - rotated.width / 2)
    y = round(cy - rotated.height / 2)
    canvas = base.convert("RGBA")
    canvas.alpha_composite(rotated, dest=(x, y))
    return canvas.convert("RGB")


def add_impact(frame: Image.Image, t: float) -> Image.Image:
    if not 1.75 <= t <= 2.45:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade = max(0.0, 1 - (t - 1.75) / .70)
    if t < 1.94:
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(255, 251, 233, int(135 * fade)))
    else:
        x, y = 560, 690
        font = font_for(76)
        draw.text((x, y), "CRAC", font=font, fill=(246, 83, 66, int(255 * fade)), stroke_width=8, stroke_fill=(26, 31, 45, int(255 * fade)))
        # Small tooth-like glints, stylized, no missing teeth or gore.
        for i, (dx, dy) in enumerate([(410, 635), (470, 615), (520, 642)]):
            r = 9 + (i % 2) * 3
            draw.polygon([(dx, dy-r), (dx+r, dy), (dx, dy+r), (dx-r, dy)], fill=(255, 246, 208, int(230 * fade)), outline=(56, 49, 54, int(220 * fade)))
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def add_caption(frame: Image.Image, t: float) -> Image.Image:
    if t < .06 or t > 2.55:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    alpha = int(224 * min(1.0, (t - .06) / .14, (2.68 - t) / .16))
    draw.rounded_rectangle((120, 949, 1800, 1035), radius=18, fill=(15, 21, 33, int(alpha * .9)), outline=(255, 221, 112, alpha), width=3)
    font = font_for(37)
    box = draw.textbbox((0, 0), CAPTION, font=font, stroke_width=1)
    tw = box[2] - box[0]
    draw.text(((WIDTH - tw) / 2, 969), CAPTION, font=font, fill=(255, 248, 230, alpha), stroke_width=2, stroke_fill=(12, 17, 28, alpha))
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def render_frame(plate: Image.Image, sprite: Image.Image, bbox: tuple[int, int, int, int], i: int) -> Image.Image:
    t = i / FPS
    scene = draw_speed_lines(plate.copy(), t, bbox)
    scene = composite_character(scene, sprite, bbox, t)
    # Camera tilts/pans down-left to follow the fall and tightens slightly at landing.
    p = smoothstep(t / DURATION)
    zoom = 1.0 + .105 * p
    center_x = plate.width * (.50 - .055 * p)
    center_y = plate.height * (.50 + .13 * p)
    crop_w = (plate.height * 16 / 9) / zoom
    crop_h = plate.height / zoom
    left = max(0, min(plate.width - crop_w, center_x - crop_w / 2))
    top = max(0, min(plate.height - crop_h, center_y - crop_h / 2))
    frame = scene.crop((left, top, left + crop_w, top + crop_h)).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    shake = 0
    if 1.92 <= t < 2.12:
        shake = int(4 * (1 - (t - 1.92) / .20))
        frame = ImageChops.offset(frame, int(math.sin(i * 2) * shake), int(math.cos(i * 1.7) * shake))
    frame = add_impact(frame, t)
    return add_caption(frame, t)


def decode_audio() -> np.ndarray:
    container = av.open(str(AUDIO_PATH))
    stream = container.streams.audio[0]
    if stream.codec_context.sample_rate != SAMPLE_RATE:
        raise RuntimeError("Source MP3 must be 48 kHz for this test")
    start_pts = None
    chunks = []
    for frame in container.decode(stream):
        if start_pts is None:
            start_pts = float(frame.pts * frame.time_base)
        chunks.append(frame.to_ndarray().astype(np.float32, copy=False))
    container.close()
    pcm = np.concatenate(chunks, axis=1)
    idx = round((AUDIO_START - start_pts) * SAMPLE_RATE)
    segment = pcm[:, idx:idx + AUDIO_SAMPLES]
    if segment.shape[1] < AUDIO_SAMPLES:
        segment = np.pad(segment, ((0, 0), (0, AUDIO_SAMPLES - segment.shape[1])))
    return np.clip(segment, -1.0, 1.0)


def render() -> None:
    sprite, bbox = load_sprite()
    plate = load_plate((1376, 768))
    pcm = decode_audio()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    out = av.open(str(OUTPUT), mode="w", format="mp4", options={"movflags": "+faststart"})
    video = out.add_stream("libx264", rate=FPS)
    video.width, video.height, video.pix_fmt = WIDTH, HEIGHT, "yuv420p"
    video.options = {"preset": "medium", "crf": "18", "tune": "animation"}
    video.codec_context.time_base = Fraction(1, FPS)
    audio = out.add_stream("aac", rate=SAMPLE_RATE)
    audio.layout = "stereo"
    audio.bit_rate = 192_000
    audio.codec_context.time_base = Fraction(1, SAMPLE_RATE)

    packets = []
    for i in range(FRAME_COUNT):
        rgb = np.asarray(render_frame(plate, sprite, bbox, i), dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
        frame.pts, frame.time_base = i, Fraction(1, FPS)
        packets.extend(video.encode(frame))
    packets.extend(video.encode())

    for offset in range(0, pcm.shape[1], 1024):
        chunk = pcm[:, offset:offset + 1024]
        if chunk.shape[1] < 1024:
            chunk = np.pad(chunk, ((0, 0), (0, 1024 - chunk.shape[1])))
        frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
        frame.sample_rate = SAMPLE_RATE
        frame.pts, frame.time_base = offset, Fraction(1, SAMPLE_RATE)
        packets.extend(audio.encode(frame))
    packets.extend(audio.encode())

    def packet_time(packet) -> float:
        stamp = packet.dts if packet.dts is not None else packet.pts
        return float(stamp * packet.time_base) if stamp is not None else 0.0

    for packet in sorted(packets, key=packet_time):
        out.mux(packet)
    out.close()
    print(f"Rendered {FRAME_COUNT} frames at {FPS} fps: {OUTPUT}")
    print(f"Audio: {AUDIO_START:.2f}s–{AUDIO_START + DURATION:.2f}s from source MP3")


if __name__ == "__main__":
    render()
