from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 3.29.29 PM.mp4")
BACKGROUND = ROOT / "output" / "highway_clean_no_vehicles_HQ_source_composite.png"
STILL = ROOT / "output" / "highway_motion_history_59s.png"
PREVIEW_VIDEO = ROOT / "output" / "highway_motion_history_preview.avi"
END_SECONDS = 59.0
INPUT_STRIDE = 5
OUTPUT_FPS = 24.0


def time_colour(progress: float) -> np.ndarray:
    # OpenCV HSV: blue -> violet -> red -> amber, returned as BGR float.
    hue = int(round(115 * (1.0 - progress) + 12 * progress))
    hsv = np.uint8([[[hue, 235, 255]]])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0].astype(np.float32)


def road_mask(height: int, width: int) -> np.ndarray:
    mask = np.zeros((height, width), np.uint8)
    polygons = [
        # Elevated roadway between its rear and front barriers.
        np.array([(0, 505), (width - 1, 557), (width - 1, 681), (0, 586)], np.int32),
        # Lower roadway passing beneath the flyover.
        np.array([(0, 684), (133, 703), (445, height - 1), (0, height - 1)], np.int32),
        # Small left-hand approach/ramp.
        np.array([(0, 468), (151, 498), (151, 555), (0, 531)], np.int32),
    ]
    cv2.fillPoly(mask, polygons, 255)
    return mask


def main() -> None:
    background = cv2.imread(str(BACKGROUND), cv2.IMREAD_COLOR)
    if background is None:
        raise RuntimeError(f"Could not read {BACKGROUND}")
    height, width = background.shape[:2]
    bg_gray = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    roads = road_mask(height, width)

    cap = cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {SOURCE}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    source_limit = int(np.floor(END_SECONDS * fps))
    samples = len(range(0, source_limit, INPUT_STRIDE))

    writer = cv2.VideoWriter(
        str(PREVIEW_VIDEO),
        cv2.VideoWriter_fourcc(*"MJPG"),
        OUTPUT_FPS,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create {PREVIEW_VIDEO}")

    energy = np.zeros((height, width, 3), np.float32)
    sampled = 0
    for frame_index in range(source_limit):
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % INPUT_STRIDE:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        delta = cv2.absdiff(gray, bg_gray)
        foreground = np.where((delta > 16) & (roads > 0), 255, 0).astype(np.uint8)
        foreground = cv2.morphologyEx(
            foreground, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        )
        foreground = cv2.morphologyEx(
            foreground, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 5))
        )

        # Remove compression speckles while keeping motorcycles and cars.
        clean = np.zeros_like(foreground)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground)
        for component in range(1, count):
            area = stats[component, cv2.CC_STAT_AREA]
            if 18 <= area <= 9000:
                clean[labels == component] = 255

        progress = sampled / max(1, samples - 1)
        colour = time_colour(progress)
        soft = cv2.GaussianBlur(clean, (0, 0), 2.2).astype(np.float32) / 255.0
        # Additive accumulation turns successive positions into continuous ribbons.
        energy += soft[..., None] * colour[None, None, :] * 0.075
        energy = np.minimum(energy, 210.0)

        # A soft bloom makes dense, repeatedly traversed paths glow.
        bloom = cv2.GaussianBlur(energy, (0, 0), 7.0)
        composite = np.clip(
            background.astype(np.float32) * 0.72 + energy * 1.15 + bloom * 0.42,
            0,
            255,
        ).astype(np.uint8)
        writer.write(composite)
        sampled += 1

    cap.release()
    writer.release()

    bloom = cv2.GaussianBlur(energy, (0, 0), 7.0)
    final = np.clip(
        background.astype(np.float32) * 0.72 + energy * 1.15 + bloom * 0.42,
        0,
        255,
    ).astype(np.uint8)
    if not cv2.imwrite(str(STILL), final, [cv2.IMWRITE_PNG_COMPRESSION, 2]):
        raise RuntimeError(f"Could not write {STILL}")

    print(f"source_window=0.000-{END_SECONDS:.3f}s")
    print(f"source_frames_considered={source_limit}")
    print(f"motion_samples={sampled}")
    print(f"animation_seconds={sampled / OUTPUT_FPS:.3f}")
    print(f"still={STILL}")
    print(f"preview_video={PREVIEW_VIDEO}")


if __name__ == "__main__":
    main()
