from pathlib import Path

import cv2
import numpy as np


SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 3.29.29 PM.mp4")
OUTPUT = Path(__file__).resolve().parents[1] / "output" / "highway_59s_long_exposure_vehicle_ghosts.png"
SHORT_OUTPUT = Path(__file__).resolve().parents[1] / "output" / "highway_cinematic_4s_vehicle_ghosts.png"
END_SECONDS = 59.0
SHORT_START_SECONDS = 43.6333333333
SHORT_DURATION_SECONDS = 4.0


def main() -> None:
    capture = cv2.VideoCapture(str(SOURCE))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open {SOURCE}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    maximum_frames = int(np.floor(END_SECONDS * fps))
    accumulator: np.ndarray | None = None
    count = 0

    while count < maximum_frames:
        ok, frame = capture.read()
        if not ok:
            break
        if accumulator is None:
            accumulator = np.zeros(frame.shape, dtype=np.float64)
        accumulator += frame
        count += 1

    capture.release()
    if accumulator is None or count == 0:
        raise RuntimeError("No frames were decoded")

    long_exposure = np.clip(accumulator / count, 0, 255).astype(np.uint8)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(OUTPUT), long_exposure, [cv2.IMWRITE_PNG_COMPRESSION, 2]):
        raise RuntimeError(f"Could not write {OUTPUT}")

    # A shorter, traffic-dense interval produces visible translucent vehicles
    # instead of diluting each one across the entire minute.
    short_capture = cv2.VideoCapture(str(SOURCE))
    short_capture.set(cv2.CAP_PROP_POS_MSEC, SHORT_START_SECONDS * 1000.0)
    short_accumulator = np.zeros_like(accumulator)
    short_count = int(round(SHORT_DURATION_SECONDS / 0.5))
    decoded = 0
    for sample in range(short_count):
        short_capture.set(
            cv2.CAP_PROP_POS_MSEC,
            (SHORT_START_SECONDS + sample * 0.5) * 1000.0,
        )
        ok, frame = short_capture.read()
        if not ok:
            break
        short_accumulator += frame
        decoded += 1
    short_capture.release()
    cinematic = np.clip(short_accumulator / decoded, 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(SHORT_OUTPUT), cinematic, [cv2.IMWRITE_PNG_COMPRESSION, 2]):
        raise RuntimeError(f"Could not write {SHORT_OUTPUT}")

    height, width = long_exposure.shape[:2]
    print(f"fps={fps:.6f}")
    print(f"frames_averaged={count}")
    print(f"time_range=0.000-{count / fps:.3f}s")
    print(f"dimensions={width}x{height}")
    print(f"output={OUTPUT}")
    print(f"cinematic_window={SHORT_START_SECONDS:.3f}-{SHORT_START_SECONDS + SHORT_DURATION_SECONDS:.3f}s")
    print(f"cinematic_frames={decoded}")
    print(f"cinematic_output={SHORT_OUTPUT}")


if __name__ == "__main__":
    main()
