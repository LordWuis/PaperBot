from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 3.29.29 PM.mp4")
BACKGROUND = ROOT / "output" / "highway_clean_no_vehicles_HQ_source_composite.png"
OUTPUT = ROOT / "output" / "highway_continuous_vehicle_trails.png"
START_SECONDS = 43.7333333333
DURATION_SECONDS = 1.0


def main() -> None:
    background = cv2.imread(str(BACKGROUND), cv2.IMREAD_COLOR)
    if background is None:
        raise RuntimeError(f"Could not read {BACKGROUND}")

    cap = cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {SOURCE}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_MSEC, START_SECONDS * 1000.0)
    wanted = int(round(DURATION_SECONDS * fps))
    total = np.zeros_like(background, dtype=np.float64)
    count = 0
    for _ in range(wanted):
        ok, frame = cap.read()
        if not ok:
            break
        total += frame
        count += 1
    cap.release()
    if count == 0:
        raise RuntimeError("No frames decoded")

    # This is a literal temporal average of every consecutive frame—equivalent
    # to holding a virtual shutter open for the full interval.
    result = np.clip(total / count, 0, 255).astype(np.uint8)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(OUTPUT), result, [cv2.IMWRITE_PNG_COMPRESSION, 2]):
        raise RuntimeError(f"Could not write {OUTPUT}")
    h, w = result.shape[:2]
    print(f"frames={count}")
    print(f"fps={fps:.6f}")
    print(f"window={START_SECONDS:.3f}-{START_SECONDS + count / fps:.3f}s")
    print(f"dimensions={w}x{h}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
