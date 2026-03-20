"""
shorts_pipeline.py — Orchestrator for the YouTube Shorts pipeline
Runs all 4 stages in sequence: script → audio → visuals → edit
"""

import os
import sys

# Allow running from repo root OR from inside video/
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)


def generate_short(input_file: str = "../final_output.json") -> None:
    from shorts_script import generate_script
    from shorts_audio import generate_audio
    from shorts_visuals import generate_visuals
    from shorts_editor import edit_video

    print("=" * 60)
    print("--- Shorts Stage 1: Generating Hinglish script ---")
    print("=" * 60)
    generate_script(input_file)

    print("\n" + "=" * 60)
    print("--- Shorts Stage 2: Generating audio (ElevenLabs → Gemini TTS) ---")
    print("=" * 60)
    generate_audio()

    print("\n" + "=" * 60)
    print("--- Shorts Stage 3: Generating visuals (Runware) ---")
    print("=" * 60)
    generate_visuals()

    print("\n" + "=" * 60)
    print("--- Shorts Stage 4: Editing video (MoviePy) ---")
    print("=" * 60)
    edit_video()

    print("\n" + "=" * 60)
    print("Done. Output: video/final_short.mp4")
    print("=" * 60)


if __name__ == "__main__":
    # When running as `python video/shorts_pipeline.py` from repo root,
    # final_output.json is in the current directory (repo root).
    # When running as `python shorts_pipeline.py` from inside video/,
    # it's one level up.
    if os.path.exists("final_output.json"):
        input_file = "final_output.json"
    elif os.path.exists("../final_output.json"):
        input_file = "../final_output.json"
    else:
        input_file = sys.argv[1] if len(sys.argv) > 1 else "../final_output.json"

    generate_short(input_file)
