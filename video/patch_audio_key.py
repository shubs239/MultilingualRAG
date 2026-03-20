"""
patch_audio_key.py — one-off utility
Scans the audio/ folder for existing segment-N.mp3 files and writes the
"audio" key into production_sheet.json so shorts_editor.py can find them.

Run from the video/ directory:
    python patch_audio_key.py
"""

import json
import os
import re

PRODUCTION_SHEET = "production_sheet.json"
AUDIO_DIR = "audio"


def measure_duration(path: str) -> float:
    from pydub import AudioSegment
    return len(AudioSegment.from_file(path)) / 1000.0


def patch():
    with open(PRODUCTION_SHEET, "r", encoding="utf-8") as f:
        sheet = json.load(f)

    if "audio" in sheet:
        print("production_sheet.json already has an 'audio' key.")
        print("Delete it first if you want to re-patch.")
        return

    # Find segment files
    segment_files = {}
    pattern = re.compile(r"segment-(\d+)\.mp3$")
    for fname in sorted(os.listdir(AUDIO_DIR)):
        m = pattern.match(fname)
        if m:
            seg_id = m.group(1)
            path = f"{AUDIO_DIR}/{fname}"
            print(f"  Measuring {path} …", end=" ", flush=True)
            dur = measure_duration(path)
            print(f"{dur:.1f}s")
            segment_files[seg_id] = {
                "file": path,
                "actual_duration_sec": round(dur, 2),
            }

    # Compute start/end offsets
    cursor = 0.0
    for seg_id in sorted(segment_files, key=lambda x: int(x)):
        dur = segment_files[seg_id]["actual_duration_sec"]
        segment_files[seg_id]["start_sec"] = round(cursor, 2)
        segment_files[seg_id]["end_sec"] = round(cursor + dur, 2)
        cursor += dur

    full_audio = f"{AUDIO_DIR}/full_audio.mp3"

    sheet["audio"] = {
        "provider": "manual",
        "segment_files": segment_files,
        "full_audio": full_audio,
        "total_duration_sec": round(cursor, 2),
    }

    with open(PRODUCTION_SHEET, "w", encoding="utf-8") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=2)

    print(f"\nPatched {len(segment_files)} segments, total {cursor:.1f}s → {PRODUCTION_SHEET}")


if __name__ == "__main__":
    patch()
