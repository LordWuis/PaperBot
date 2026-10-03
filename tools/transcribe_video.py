import json
from pathlib import Path

from faster_whisper import WhisperModel


SOURCE = Path(r"C:\Users\Aman\Downloads\WhatsApp Video 2026-09-21 at 4.05.10 PM.mp4")
MODEL = Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-base"
OUTPUT = Path(__file__).resolve().parents[1] / "output" / "edited_video_transcript.json"


def main() -> None:
    snapshots = sorted((MODEL / "snapshots").iterdir())
    if not snapshots:
        raise RuntimeError(f"No cached model snapshot found in {MODEL}")
    model = WhisperModel(str(snapshots[-1]), device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(SOURCE),
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
        language="en",
    )
    result = {
        "language": info.language,
        "duration": info.duration,
        "segments": [],
    }
    for segment in segments:
        result["segments"].append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [
                    {"start": word.start, "end": word.end, "word": word.word.strip()}
                    for word in (segment.words or [])
                ],
            }
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    for segment in result["segments"]:
        print(f"{segment['start']:6.2f}-{segment['end']:6.2f}  {segment['text']}")
    print(f"output={OUTPUT}")


if __name__ == "__main__":
    main()
