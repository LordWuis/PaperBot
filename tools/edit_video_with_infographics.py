from __future__ import annotations

import math
import subprocess
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 4.05.10 PM.mp4")
OUTPUT = ROOT / "output" / "sunk_cost_reel_premium_infographics.mp4"
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")

IVORY = (247, 243, 234, 255)
MUTED = (199, 200, 196, 255)
GOLD = (244, 184, 74, 255)
TEAL = (80, 218, 190, 255)
RED = (247, 91, 91, 255)
INK = (15, 17, 20, 232)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


F14 = font(FONT_SEMIBOLD, 14)
F16 = font(FONT_REGULAR, 16)
F18 = font(FONT_SEMIBOLD, 18)
F22 = font(FONT_SEMIBOLD, 22)
F26 = font(FONT_BOLD, 26)
F32 = font(FONT_BOLD, 32)
F42 = font(FONT_BOLD, 42)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def smoothstep(value: float) -> float:
    x = clamp01(value)
    return x * x * (3.0 - 2.0 * x)


def segment_alpha(t: float, start: float, end: float, transition: float = 0.28) -> float:
    return smoothstep((t - start) / transition) * smoothstep((end - t) / transition)


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], text: str, fill, text_fill=IVORY) -> None:
    draw.rounded_rectangle(xy, radius=(xy[3] - xy[1]) // 2, fill=fill)
    box = draw.textbbox((0, 0), text, font=F14)
    x = (xy[0] + xy[2] - (box[2] - box[0])) / 2
    y = (xy[1] + xy[3] - (box[3] - box[1])) / 2 - 2
    draw.text((x, y), text, font=F14, fill=text_fill)


def base_card(alpha: float, y: int = 548, height: int = 150) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    layer = Image.new("RGBA", (576, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    offset = int(round((1.0 - alpha) * 18))
    yy = y + offset
    a = int(220 * alpha)
    draw.rounded_rectangle((24, yy, 552, yy + height), radius=24, fill=(13, 15, 18, a), outline=(255, 255, 255, int(34 * alpha)), width=1)
    draw.rounded_rectangle((25, yy + 1, 551, yy + 3), radius=2, fill=(255, 255, 255, int(22 * alpha)))
    return layer, draw, yy


def apply_alpha(layer: Image.Image, alpha: float) -> Image.Image:
    if alpha >= 0.999:
        return layer
    channel = layer.getchannel("A").point(lambda value: int(value * alpha))
    layer.putalpha(channel)
    return layer


def draw_clock(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, progress: float) -> None:
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(255, 255, 255, 76), width=5)
    draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), -90, -90 + 360 * progress, fill=GOLD, width=6)
    angle = math.radians(-90 + 300 * progress)
    draw.line((cx, cy, cx + math.cos(angle) * radius * 0.55, cy + math.sin(angle) * radius * 0.55), fill=IVORY, width=4)
    draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=IVORY)


def card_queue(t: float, alpha: float) -> Image.Image:
    layer, draw, y = base_card(alpha)
    local = clamp01(t / 5.74)
    draw_clock(draw, 80, y + 72, 34, local)
    draw.text((132, y + 24), "40 MINUTES", font=F32, fill=IVORY)
    draw.text((132, y + 67), "waiting in line", font=F18, fill=MUTED)
    for i in range(5):
        x = 136 + i * 30
        draw.ellipse((x, y + 109, x + 13, y + 122), fill=(244, 184, 74, 225 - i * 20))
    pill(draw, (376, y + 91, 524, y + 129), "SOLD OUT", (169, 44, 44, 245))
    return apply_alpha(layer, alpha)


def card_movie(t: float, alpha: float) -> Image.Image:
    layer, draw, y = base_card(alpha, height=140)
    draw.rounded_rectangle((48, y + 34, 116, y + 102), radius=18, fill=(33, 37, 43, 255), outline=(255, 255, 255, 38), width=1)
    draw.polygon([(75, y + 52), (75, y + 85), (101, y + 68)], fill=RED)
    draw.text((140, y + 29), "PLAN B", font=F14, fill=TEAL)
    draw.text((140, y + 52), "MOVIE NIGHT", font=F32, fill=IVORY)
    draw.text((140, y + 95), "Surely this will be better.", font=F16, fill=MUTED)
    return apply_alpha(layer, alpha)


def card_progress(t: float, alpha: float, terrible: bool) -> Image.Image:
    layer, draw, y = base_card(alpha, height=142)
    progress = clamp01((t - (10.68 if not terrible else 13.36)) / (2.34 if not terrible else 3.02))
    title = "THE MOVIE BEGINS" if not terrible else "30 MINUTES IN"
    accent = TEAL if not terrible else RED
    draw.text((48, y + 26), title, font=F26, fill=IVORY)
    draw.rounded_rectangle((48, y + 78, 528, y + 94), radius=8, fill=(255, 255, 255, 34))
    width = int(480 * (0.14 + (0.34 if terrible else 0.22) * progress))
    draw.rounded_rectangle((48, y + 78, 48 + width, y + 94), radius=8, fill=accent)
    draw.text((48, y + 105), "PLAYING", font=F14, fill=MUTED)
    if terrible:
        pill(draw, (402, y + 103, 528, y + 133), "BAD MOVIE", (126, 38, 43, 245))
    return apply_alpha(layer, alpha)


def card_quote(alpha: float) -> Image.Image:
    layer, draw, y = base_card(alpha, y=535, height=168)
    draw.text((48, y + 24), "“", font=F42, fill=GOLD)
    draw.text((82, y + 31), "I've already watched", font=F22, fill=IVORY)
    draw.text((82, y + 64), "30 minutes…", font=F32, fill=GOLD)
    draw.text((82, y + 109), "might as well finish it.", font=F18, fill=MUTED)
    return apply_alpha(layer, alpha)


def card_definition(alpha: float) -> Image.Image:
    layer, draw, y = base_card(alpha, y=523, height=180)
    pill(draw, (48, y + 22, 164, y + 52), "MENTAL TRAP", (35, 105, 94, 245))
    draw.text((48, y + 67), "SUNK COST", font=F42, fill=IVORY)
    draw.text((48, y + 111), "FALLACY", font=F32, fill=GOLD)
    draw.text((282, y + 126), "PAST COST  ≠  FUTURE VALUE", font=F14, fill=MUTED)
    return apply_alpha(layer, alpha)


def card_danger(t: float, alpha: float) -> Image.Image:
    layer, draw, y = base_card(alpha, y=531, height=168)
    local = clamp01((t - 26.60) / 6.52)
    draw.text((48, y + 24), "TRY TO SAVE THE LOSS", font=F18, fill=MUTED)
    draw.line((54, y + 69, 500, y + 69), fill=(255, 255, 255, 40), width=2)
    arrow_x = int(76 + 370 * local)
    draw.line((76, y + 69, arrow_x, y + 69), fill=RED, width=6)
    draw.polygon([(arrow_x, y + 60), (arrow_x + 18, y + 69), (arrow_x, y + 78)], fill=RED)
    draw.text((48, y + 92), "LOSE EVEN MORE", font=F32, fill=RED)
    draw.text((443, y + 99), "↓", font=F32, fill=GOLD)
    return apply_alpha(layer, alpha)


def card_scale(t: float, alpha: float) -> Image.Image:
    layer, draw, y = base_card(alpha, y=518, height=187)
    draw.text((48, y + 24), "THE SAME THINKING", font=F14, fill=GOLD)
    draw.rounded_rectangle((48, y + 54, 194, y + 126), radius=18, fill=(255, 255, 255, 18), outline=(255, 255, 255, 35))
    draw.text((72, y + 65), "1 HOUR", font=F26, fill=IVORY)
    draw.text((70, y + 99), "bad movie", font=F14, fill=MUTED)
    draw.text((216, y + 72), "→", font=F32, fill=RED)
    draw.rounded_rectangle((272, y + 54, 528, y + 126), radius=18, fill=(121, 39, 43, 88), outline=(247, 91, 91, 105))
    draw.text((298, y + 65), "YEARS", font=F32, fill=IVORY)
    draw.text((298, y + 102), "of your life", font=F14, fill=(255, 192, 192, 255))
    labels = ["CAREER", "BUSINESS", "FRIENDSHIP", "RELATIONSHIP"]
    x_positions = [48, 158, 274, 398]
    for i, label in enumerate(labels):
        reveal = smoothstep(((t - 33.42) - i * 0.55) / 0.35)
        if reveal > 0:
            fill = (255, 255, 255, int(25 * reveal))
            text_fill = (210, 211, 208, int(255 * reveal))
            width = [98, 104, 114, 130][i]
            pill(draw, (x_positions[i], y + 145, min(544, x_positions[i] + width), y + 175), label, fill, text_fill)
    return apply_alpha(layer, alpha)


def card_takeaway(alpha: float, final: bool = False) -> Image.Image:
    layer, draw, y = base_card(alpha, y=526, height=170)
    # Draw the retreat arrow as vector geometry so it renders consistently.
    draw.line((76, y + 39, 54, y + 61), fill=TEAL, width=5)
    draw.line((54, y + 61, 54, y + 43), fill=TEAL, width=5)
    draw.line((54, y + 61, 72, y + 61), fill=TEAL, width=5)
    if final:
        draw.text((105, y + 29), "KNOW WHEN TO", font=F22, fill=MUTED)
        draw.text((105, y + 65), "WALK AWAY.", font=F42, fill=IVORY)
        pill(draw, (105, y + 123, 283, y + 153), "THAT IS CLARITY", (35, 105, 94, 245))
    else:
        draw.text((105, y + 25), "STEPPING BACK", font=F32, fill=IVORY)
        draw.text((105, y + 70), "isn't giving up.", font=F22, fill=MUTED)
        draw.text((105, y + 112), "Sometimes, it's the smart move.", font=F18, fill=TEAL)
    return apply_alpha(layer, alpha)


def overlay_for_time(t: float) -> Image.Image | None:
    segments = [
        (0.00, 5.74, lambda a: card_queue(t, a)),
        (6.32, 10.20, lambda a: card_movie(t, a)),
        (10.68, 13.02, lambda a: card_progress(t, a, False)),
        (13.36, 16.38, lambda a: card_progress(t, a, True)),
        (16.84, 22.02, lambda a: card_quote(a)),
        (22.32, 26.60, lambda a: card_definition(a)),
        (26.60, 33.12, lambda a: card_danger(t, a)),
        (33.42, 40.98, lambda a: card_scale(t, a)),
        (41.40, 45.60, lambda a: card_takeaway(a, False)),
        (45.60, 47.25, lambda a: card_takeaway(a, True)),
    ]
    for start, end, renderer in segments:
        if start <= t <= end:
            return renderer(segment_alpha(t, start, end))
    return None


def main() -> None:
    capture = cv2.VideoCapture(str(SOURCE))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open {SOURCE}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", f"{fps:.6f}", "-i", "-",
        "-i", str(SOURCE), "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(OUTPUT),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    if encoder.stdin is None:
        raise RuntimeError("Could not open encoder input")

    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        t = frame_index / fps
        overlay = overlay_for_time(t)
        if overlay is not None:
            base = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
            base.alpha_composite(overlay)
            frame = cv2.cvtColor(np.asarray(base.convert("RGB")), cv2.COLOR_RGB2BGR)
        encoder.stdin.write(frame.tobytes())
        frame_index += 1

    capture.release()
    encoder.stdin.close()
    return_code = encoder.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with {return_code}")
    print(f"frames={frame_index}/{frame_count}")
    print(f"dimensions={width}x{height}")
    print(f"fps={fps:.6f}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    import numpy as np

    main()
