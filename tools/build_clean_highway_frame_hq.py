from pathlib import Path

import cv2
import numpy as np


SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 3.29.29 PM.mp4")
OUTPUT = Path(__file__).resolve().parents[1] / "output" / "highway_clean_no_vehicles_HQ_source_composite.png"
END_SECONDS = 59.0
SAMPLE_INTERVAL_SECONDS = 0.25
TILE = 72
OVERLAP = 16


def read_frames() -> tuple[list[np.ndarray], float]:
    cap = cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {SOURCE}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    end_frame = int(np.floor(END_SECONDS * fps))
    step = max(1, round(SAMPLE_INTERVAL_SECONDS * fps))
    frames: list[np.ndarray] = []
    for index in range(0, end_frame, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode frame {index}")
        frames.append(frame)
    cap.release()
    return frames, fps


def temporal_median(frames: list[np.ndarray]) -> np.ndarray:
    height, width = frames[0].shape[:2]
    result = np.empty_like(frames[0])
    for y0 in range(0, height, 48):
        y1 = min(height, y0 + 48)
        stripe = np.stack([f[y0:y1] for f in frames])
        result[y0:y1] = np.median(stripe, axis=0).astype(np.uint8)
    return result


def starts(length: int) -> list[int]:
    step = TILE - OVERLAP
    values = list(range(0, max(1, length - TILE + 1), step))
    last = max(0, length - TILE)
    if not values or values[-1] != last:
        values.append(last)
    return values


def main() -> None:
    frames, fps = read_frames()
    reference = temporal_median(frames)
    height, width = reference.shape[:2]

    # Scores are measured on luminance after removing each tile's mean offset.
    # This rejects cars and their shadows without penalizing gradual exposure changes.
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).astype(np.float32)

    accum = np.zeros((height, width, 3), np.float32)
    weights = np.zeros((height, width), np.float32)
    window_1d = np.hanning(TILE).astype(np.float32)
    window = np.maximum(np.outer(window_1d, window_1d), 0.03)
    chosen: list[int] = []

    for y0 in starts(height):
        y1 = min(height, y0 + TILE)
        for x0 in starts(width):
            x1 = min(width, x0 + TILE)
            target = ref_gray[y0:y1, x0:x1]
            scores = []
            for gray in grays:
                candidate = gray[y0:y1, x0:x1]
                delta = candidate - target
                delta -= np.median(delta)
                # The 80th percentile strongly penalizes a vehicle occupying the tile.
                scores.append(float(np.percentile(np.abs(delta), 80)))
            best = int(np.argmin(scores))
            chosen.append(best)
            patch = frames[best][y0:y1, x0:x1].astype(np.float32)
            w = window[: y1 - y0, : x1 - x0]
            accum[y0:y1, x0:x1] += patch * w[..., None]
            weights[y0:y1, x0:x1] += w

    result = np.clip(accum / weights[..., None], 0, 255).astype(np.uint8)

    # Nothing moves in the upper part of the scene. Preserve it from one sharp
    # decoded source frame so thin structures (especially the overhead cable)
    # cannot be doubled by tile-to-tile timestamp changes.
    upper_limit = 455
    sharpness = [
        cv2.Laplacian(g[:upper_limit].astype(np.uint8), cv2.CV_32F).var()
        for g in grays
    ]
    base = frames[int(np.argmax(sharpness))]
    blend_start, blend_end = 430, upper_limit
    result[:blend_start] = base[:blend_start]
    alpha = np.linspace(0.0, 1.0, blend_end - blend_start, dtype=np.float32)[:, None, None]
    result[blend_start:blend_end] = np.clip(
        base[blend_start:blend_end].astype(np.float32) * (1.0 - alpha)
        + result[blend_start:blend_end].astype(np.float32) * alpha,
        0,
        255,
    ).astype(np.uint8)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(OUTPUT), result, [cv2.IMWRITE_PNG_COMPRESSION, 2]):
        raise RuntimeError(f"Cannot write {OUTPUT}")

    unique = len(set(chosen))
    print(f"fps={fps:.6f}")
    print(f"cutoff={END_SECONDS:.3f}s")
    print(f"samples={len(frames)}")
    print(f"source_frames_used_for_tiles={unique}")
    print(f"dimensions={width}x{height}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
