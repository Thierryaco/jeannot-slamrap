#!/usr/bin/env python3
"""Render a short 12 fps camera/smoke motion test from the approved Jeannot keyframe.

The character illustration is raster artwork; this script animates the camera and
smoke as a first motion study. It is not the final hand-drawn character animation.
Requires: av, numpy, pillow.
"""
from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets/art/jeannot-4l-style-frame-v2.png"
AUDIO = ROOT / "audio/jeannot-slamrap.mp3"
OUTPUT = ROOT / "renders/jeannot-intro-test-12fps.mp4"

WIDTH, HEIGHT = 1920, 1080
FPS = 12
TEST_SECONDS = 3.0
FRAME_COUNT = round(TEST_SECONDS * FPS)
SOURCE_START_SECONDS = 16.35  # première entrée vocale candidate, à confirmer
SAMPLE_RATE = 48_000
AUDIO_SAMPLES = round(TEST_SECONDS * SAMPLE_RATE)
LYRIC = "Jeannot est là, et toujours là !"


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def font_for(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def read_source_image() -> Image.Image:
    image = Image.open(ART).convert("RGB")
    return ImageOps.fit(image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def add_smoke(base: Image.Image, t: float) -> Image.Image:
    """Add a restrained hand-drawn wisp that evolves frame-by-frame from the cigarette."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    # Approximate cigarette tip after scaling the reference frame to 1920x1080.
    origin_x, origin_y = 1150.0, 386.0
    for strand in range(3):
        age = (t * 0.78 + strand * 0.34) % 1.0
        length = 30 + age * 115
        x0 = origin_x + strand * 5
        y0 = origin_y - strand * 2
        pts = []
        for k in range(9):
            u = k / 8
            x = x0 + math.sin((age + u * 0.8) * math.tau + strand) * (5 + 13 * u)
            y = y0 - length * u
            pts.append((x, y))
        alpha = int(62 + (1 - age) * 52)
        width = max(5, int(11 - age * 4))
        draw.line(pts, fill=(245, 244, 233, alpha), width=width, joint="curve")
        # A few soft puffs break up the regular line and give the smoke a cel-like edge.
        if strand == 1 and age < .82:
            px, py = pts[5]
            r = 4 + (1 - age) * 5
            draw.ellipse((px - r, py - r, px + r, py + r), fill=(238, 240, 235, int(alpha * .45)))
    layer = layer.filter(ImageFilter.GaussianBlur(2.2))
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")


def add_caption(frame: Image.Image, t: float) -> Image.Image:
    if t < .08 or t > 2.78:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    fade = min(1.0, (t - .08) / .18, (2.92 - t) / .18)
    alpha = int(220 * max(0.0, min(1.0, fade)))
    box = (260, 946, 1660, 1036)
    draw.rounded_rectangle(box, radius=18, fill=(16, 22, 35, int(alpha * .88)), outline=(255, 221, 112, alpha), width=3)
    font = font_for(42, bold=True)
    bbox = draw.textbbox((0, 0), LYRIC, font=font, stroke_width=1)
    text_w = bbox[2] - bbox[0]
    x = (WIDTH - text_w) / 2
    y = 967
    draw.text((x, y), LYRIC, font=font, fill=(255, 248, 230, alpha), stroke_width=2, stroke_fill=(12, 17, 28, alpha))
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def make_frame(source: Image.Image, frame_no: int) -> Image.Image:
    t = frame_no / FPS
    p = smoothstep(t / TEST_SECONDS)
    # Un seul mouvement continu : plan large -> léger travelling avant sur Jeannot et la 4L.
    zoom = 1.0 + .105 * p
    center_x = WIDTH * (.50 + .025 * p)
    center_y = HEIGHT * (.50 - .006 * p)
    crop_w, crop_h = WIDTH / zoom, HEIGHT / zoom
    left = min(max(center_x - crop_w / 2, 0), WIDTH - crop_w)
    top = min(max(center_y - crop_h / 2, 0), HEIGHT - crop_h)

    moving = add_smoke(source, t)
    frame = moving.crop((left, top, left + crop_w, top + crop_h)).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    # Très léger mouvement de caméra sur les accents, pas de tremblement décoratif permanent.
    accent = math.exp(-((t - 1.85) / .12) ** 2)
    if accent > .02:
        dx = int(math.sin(frame_no * 2.1) * 2 * accent)
        dy = int(math.cos(frame_no * 1.7) * accent)
        frame = ImageChops.offset(frame, dx, dy)
    return add_caption(frame, t)


def decode_audio_segment() -> np.ndarray:
    container = av.open(str(AUDIO))
    stream = container.streams.audio[0]
    sample_rate = stream.codec_context.sample_rate
    if sample_rate != SAMPLE_RATE:
        raise RuntimeError(f"Expected {SAMPLE_RATE} Hz audio, got {sample_rate} Hz")
    start_pts = None
    chunks: list[np.ndarray] = []
    for audio_frame in container.decode(stream):
        if start_pts is None:
            start_pts = float(audio_frame.pts * audio_frame.time_base)
        arr = audio_frame.to_ndarray().astype(np.float32, copy=False)
        if arr.ndim != 2:
            raise RuntimeError(f"Unexpected decoded audio layout: {arr.shape}")
        chunks.append(arr)
    container.close()
    if not chunks or start_pts is None:
        raise RuntimeError("Could not decode source MP3")
    pcm = np.concatenate(chunks, axis=1)
    start_index = round((SOURCE_START_SECONDS - start_pts) * SAMPLE_RATE)
    segment = pcm[:, start_index:start_index + AUDIO_SAMPLES]
    if segment.shape[1] < AUDIO_SAMPLES:
        segment = np.pad(segment, ((0, 0), (0, AUDIO_SAMPLES - segment.shape[1])))
    return np.clip(segment, -1.0, 1.0)


def render() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    source = read_source_image()
    pcm = decode_audio_segment()

    out = av.open(str(OUTPUT), mode="w", format="mp4", options={"movflags": "+faststart"})
    video = out.add_stream("libx264", rate=FPS)
    video.width = WIDTH
    video.height = HEIGHT
    video.pix_fmt = "yuv420p"
    video.options = {"preset": "medium", "crf": "18", "tune": "animation"}
    video.codec_context.time_base = Fraction(1, FPS)

    audio = out.add_stream("aac", rate=SAMPLE_RATE)
    audio.layout = "stereo"
    audio.bit_rate = 192_000
    audio.codec_context.time_base = Fraction(1, SAMPLE_RATE)

    # Encode frames at 12 unique drawings per second, then interleave AAC packets by PTS.
    packets = []
    for i in range(FRAME_COUNT):
        image = make_frame(source, i)
        rgb = np.asarray(image, dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
        frame.pts = i
        frame.time_base = Fraction(1, FPS)
        packets.extend(video.encode(frame))
    packets.extend(video.encode())

    for offset in range(0, pcm.shape[1], 1024):
        chunk = pcm[:, offset:offset + 1024]
        if chunk.shape[1] < 1024:
            chunk = np.pad(chunk, ((0, 0), (0, 1024 - chunk.shape[1])))
        frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
        frame.sample_rate = SAMPLE_RATE
        frame.pts = offset
        frame.time_base = Fraction(1, SAMPLE_RATE)
        packets.extend(audio.encode(frame))
    packets.extend(audio.encode())

    def packet_time(packet) -> float:
        stamp = packet.dts if packet.dts is not None else packet.pts
        return float(stamp * packet.time_base) if stamp is not None else 0.0

    for packet in sorted(packets, key=packet_time):
        out.mux(packet)
    out.close()
    print(f"Rendered {FRAME_COUNT} frames at {FPS} fps: {OUTPUT}")
    print(f"Audio: {SOURCE_START_SECONDS:.2f}s–{SOURCE_START_SECONDS + TEST_SECONDS:.2f}s from the MP3")


if __name__ == "__main__":
    render()
