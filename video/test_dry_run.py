"""
test_dry_run.py — Zero-cost dry-run test for the Shorts pipeline
Fakes Stages 1–3 with fixture data and silent audio / solid-color images,
then runs Stage 4 (shorts_editor.py) for real via MoviePy + ffmpeg.

Run from repo root:
    python video/test_dry_run.py
"""

import importlib.util
import json
import os
import sys

# ── Constants ─────────────────────────────────────────────────────────────────

SLUG = "test-dry-run"
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))   # …/video/
_REPO_ROOT = os.path.dirname(_THIS_DIR)

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_failures: list[str] = []


def _check(label: str, condition: bool) -> None:
    if condition:
        print(f"{_PASS} {label}")
    else:
        print(f"{_FAIL} {label}")
        _failures.append(label)


# ── Step 1: Create fixture production sheet ───────────────────────────────────

def create_production_sheet() -> tuple[str, dict]:
    ps_dir = os.path.join(_THIS_DIR, "production_sheet")
    os.makedirs(ps_dir, exist_ok=True)
    ps_path = os.path.join(ps_dir, f"{SLUG}.json")

    sheet: dict = {
        "slug": SLUG,
        "blog_h1": "Test Dry Run — Caste Discrimination in India",
        "target_duration_sec": 170,
        "segments": [
            {
                "id": 1,
                "estimated_duration_sec": 3.0,
                "spoken_text": "Yaar sun lo, ye fact sun ke shock lag jayega!",
                "emotion": "shocking",
                "elevenlabs": {
                    "stability": 0.25,
                    "similarity_boost": 0.80,
                    "style": 0.85,
                    "use_speaker_boost": True,
                    "emotion_tag": "(with shock)",
                },
                "gemini_tts": {
                    "style_instruction": "[Style: shocked, fast, rising pitch]"
                },
                "visual": {
                    "image_prompt": "Placeholder hook image",
                    "effect": "ken_burns_zoom_in",
                    "zoom_from": 1.0,
                    "zoom_to": 1.3,
                    "overlay_type": "source_citation",
                    "overlay_text": "NCRB 2023: Test data point for dry run",
                    "overlay_attribution": "— NCRB 2023",
                },
            },
            {
                "id": 2,
                "estimated_duration_sec": 3.0,
                "spoken_text": "Ek aur baat — ye system nahi chahta ke tum yeh jaano.",
                "emotion": "angry",
                "elevenlabs": {
                    "stability": 0.30,
                    "similarity_boost": 0.75,
                    "style": 0.80,
                    "use_speaker_boost": True,
                    "emotion_tag": "(with anger)",
                },
                "gemini_tts": {"style_instruction": "[Style: angry, forceful]"},
                "visual": {
                    "image_prompt": "Placeholder fact-punch image",
                    "effect": "pan_left",
                    "zoom_from": 1.0,
                    "zoom_to": 1.2,
                    "overlay_type": "quote",
                    "overlay_text": "Ambedkar: Education is the weapon of liberation.",
                    "overlay_attribution": "— Dr. B.R. Ambedkar",
                },
            },
            {
                "id": 3,
                "estimated_duration_sec": 3.0,
                "spoken_text": "Share karo, follow karo. Jai Bhim!",
                "emotion": "calm",
                "elevenlabs": {
                    "stability": 0.35,
                    "similarity_boost": 0.70,
                    "style": 0.75,
                    "use_speaker_boost": True,
                    "emotion_tag": "(calm)",
                },
                "gemini_tts": {"style_instruction": "[Style: calm, resolved]"},
                "visual": {
                    "image_prompt": "Placeholder sign-off image",
                    "effect": "ken_burns_zoom_out",
                    "zoom_from": 1.2,
                    "zoom_to": 1.0,
                    "overlay_type": None,
                    "overlay_text": None,
                    "overlay_attribution": None,
                },
            },
        ],
    }

    with open(ps_path, "w", encoding="utf-8") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=2)

    _check(f"video/production_sheet/{SLUG}.json created", os.path.exists(ps_path))
    return ps_path, sheet


# ── Step 2 & 3: Create silent MP3s and stitch full audio ─────────────────────

def create_audio_files() -> tuple[dict, str]:
    from pydub import AudioSegment

    audio_dir = os.path.join(_THIS_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    silence = AudioSegment.silent(duration=3000)  # 3 s

    segment_audio: dict = {}
    for i in range(1, 4):
        path = os.path.join(audio_dir, f"{SLUG}-segment-{i}.mp3")
        silence.export(path, format="mp3")
        _check(f"video/audio/{SLUG}-segment-{i}.mp3 created", os.path.exists(path))
        segment_audio[str(i)] = {"actual_duration_sec": 3.0, "path": path}

    full_audio_path = os.path.join(audio_dir, f"{SLUG}-full_audio.mp3")
    (silence + silence + silence).export(full_audio_path, format="mp3")
    _check(f"video/audio/{SLUG}-full_audio.mp3 created", os.path.exists(full_audio_path))

    return segment_audio, full_audio_path


# ── Step 4: Create placeholder images ────────────────────────────────────────

def create_images() -> dict:
    from PIL import Image

    images_dir = os.path.join(_THIS_DIR, "images")
    os.makedirs(images_dir, exist_ok=True)

    colors = [(30, 90, 180), (180, 60, 30), (60, 160, 80)]
    image_paths: dict = {}
    for i, color in enumerate(colors, start=1):
        path = os.path.join(images_dir, f"{SLUG}-segment-{i}.jpg")
        Image.new("RGB", (1200, 624), color=color).save(path, "JPEG")
        _check(f"video/images/{SLUG}-segment-{i}.jpg created", os.path.exists(path))
        image_paths[str(i)] = path

    return image_paths


# ── Step 5: Patch production sheet with audio + image paths ──────────────────

def patch_production_sheet(
    ps_path: str,
    sheet: dict,
    segment_audio: dict,
    full_audio_path: str,
    image_paths: dict,
) -> None:
    for seg in sheet["segments"]:
        seg_id = str(seg["id"])
        seg["visual"]["image_file"] = image_paths[seg_id]

    sheet["audio"] = {
        "segment_files": segment_audio,
        "full_audio": full_audio_path,
    }

    with open(ps_path, "w", encoding="utf-8") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=2)

    print("  Production sheet patched with audio + image paths.")


# ── Step 6: Import and run shorts_editor.edit_video ──────────────────────────

def run_editor() -> None:
    editor_path = os.path.join(_THIS_DIR, "shorts_editor.py")
    spec = importlib.util.spec_from_file_location("shorts_editor", editor_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    module.edit_video(SLUG)

    output_path = os.path.join(_THIS_DIR, "output", f"{SLUG}.mp4")
    _check(f"video/output/{SLUG}.mp4 rendered", os.path.exists(output_path))


# ── Step 7: Verify no stray folders created at repo root ─────────────────────

STRAY_CANDIDATES = ["audio", "images", "output", "production_sheet"]


def snapshot_root_dirs() -> set[str]:
    """Return which stray-candidate folders already exist at repo root."""
    return {d for d in STRAY_CANDIDATES if os.path.isdir(os.path.join(_REPO_ROOT, d))}


def check_no_new_stray_folders(before: set[str]) -> None:
    after = snapshot_root_dirs()
    new_stray = after - before
    if new_stray:
        print(f"{_FAIL} No stray folders created at repo root — new: {sorted(new_stray)}")
        _failures.append("No stray folders at repo root")
    else:
        print(f"{_PASS} No stray folders at repo root")
        if before:
            print(f"  (pre-existing from before fix: {sorted(before)} — not checked here)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Shorts Pipeline — Zero-Cost Dry-Run Test")
    print("=" * 60)
    print()

    # Snapshot stray folders BEFORE we run anything
    stray_before = snapshot_root_dirs()

    print("--- Stage 1: Fixture production sheet ---")
    ps_path, sheet = create_production_sheet()
    print()

    print("--- Stage 2: Silent audio files ---")
    segment_audio, full_audio_path = create_audio_files()
    print()

    print("--- Stage 3: Placeholder images ---")
    image_paths = create_images()
    print()

    print("--- Patching production sheet ---")
    patch_production_sheet(ps_path, sheet, segment_audio, full_audio_path, image_paths)
    print()

    print("--- Stage 4: shorts_editor (real MoviePy + ffmpeg render) ---")
    run_editor()
    print()

    print("--- Stray folder check ---")
    check_no_new_stray_folders(stray_before)
    print()

    print("=" * 60)
    if _failures:
        print(f"--- {len(_failures)} TEST(S) FAILED ---")
        for label in _failures:
            print(f"  {_FAIL} {label}")
        sys.exit(1)
    else:
        print("--- ALL TESTS PASSED ---")
    print("=" * 60)


if __name__ == "__main__":
    main()
