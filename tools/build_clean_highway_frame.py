from pathlib import Path

import cv2
import numpy as np


SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 3.29.29 PM.mp4")
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
END_SECONDS = 59.0
SAMPLE_INTERVAL_SECONDS = 0.5


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(SOURCE))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open {SOURCE}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    sample_step = max(1, round(fps * SAMPLE_INTERVAL_SECONDS))
    end_frame = min(frame_count, int(np.floor(END_SECONDS * fps)))

    frames: list[np.ndarray] = []
    sample_indices = list(range(0, end_frame, sample_step))
    for frame_index in sample_indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode frame {frame_index}")
        if frame.shape[:2] != (height, width):
            raise RuntimeError(f"Unexpected dimensions at frame {frame_index}: {frame.shape}")
        frames.append(frame)
    capture.release()

    # A temporal median retains the stationary scene while rejecting moving vehicles.
    # Partition by rows to keep peak memory use modest and write losslessly as PNG.
    clean = np.empty((height, width, 3), dtype=np.uint8)
    stripe_height = 48
    for y0 in range(0, height, stripe_height):
        y1 = min(height, y0 + stripe_height)
        stripe = np.stack([frame[y0:y1] for frame in frames], axis=0)
        clean[y0:y1] = np.median(stripe, axis=0).astype(np.uint8)

    output_path = OUTPUT_DIR / "highway_clean_no_vehicles_first_59s.png"
    if not cv2.imwrite(str(output_path), clean, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise RuntimeError(f"Could not write {output_path}")

    print(f"source_fps={fps:.6f}")
    print(f"source_frames={frame_count}")
    print(f"used_before_seconds={END_SECONDS}")
    print(f"samples={len(frames)}")
    print(f"dimensions={width}x{height}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
