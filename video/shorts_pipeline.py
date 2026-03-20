"""
shorts_pipeline.py — Orchestrator for the YouTube Shorts pipeline
Runs all 4 stages in sequence: script → audio → visuals → edit
Pass the slug as argument or it will auto-detect the latest production sheet.
"""

import os
import sys

_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)


def generate_short(slug: str = None) -> None:
    from shorts_script import generate_script
    from shorts_audio import generate_audio
    from shorts_visuals import generate_visuals
    from shorts_editor import edit_video

    print("=" * 60)
    print("--- Shorts Stage 1: Generating Hinglish script ---")
    print("=" * 60)
    generate_script(slug=slug)

    print("\n" + "=" * 60)
    print("--- Shorts Stage 2: Generating audio (ElevenLabs → Gemini TTS) ---")
    print("=" * 60)
    generate_audio(slug=slug)

    print("\n" + "=" * 60)
    print("--- Shorts Stage 3: Generating visuals (Runware) ---")
    print("=" * 60)
    generate_visuals(slug=slug)

    print("\n" + "=" * 60)
    print("--- Shorts Stage 4: Editing video (MoviePy) ---")
    print("=" * 60)
    edit_video(slug=slug)

    print("\n" + "=" * 60)
    print(f"Done. Output: video/output/{slug}.mp4")
    print("=" * 60)


if __name__ == "__main__":
    slug_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_short(slug_arg)
