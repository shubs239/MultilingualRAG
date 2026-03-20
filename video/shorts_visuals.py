"""
shorts_visuals.py — Stage 3 of the YouTube Shorts pipeline
Reads production_sheet.json, calls Runware for each segment's visual,
saves to video/images/segment-N.jpg (1080×1920 vertical).
"""

import json
import os
import sys
import time
import uuid

import requests
from dotenv import load_dotenv

load_dotenv()

RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY")
RUNWARE_API_URL = "https://api.runware.ai/v1"
MODEL_ID = "runware:400@3"

IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920

PRODUCTION_SHEET = "video/production_sheet.json"
IMAGES_DIR = "video/images"

NEGATIVE_PROMPT = (
    "text, letters, words, typography, fonts, writing, calligraphy, "
    "signs, labels, captions, watermarks, numbers, digits, headlines, "
    "titles, subtitles, inscriptions, banners, graffiti"
)

# Solid-colour placeholder (dark saffron gradient-ish) used on Runware failure
PLACEHOLDER_COLOR = (26, 26, 26)  # #1a1a1a


# ── Runware API ───────────────────────────────────────────────────────────────

def generate_image(prompt: str) -> str:
    """Call Runware and return image URL. Raises on failure."""
    if not RUNWARE_API_KEY:
        raise EnvironmentError("RUNWARE_API_KEY not set in .env")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNWARE_API_KEY}",
    }
    payload = [
        {
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "model": MODEL_ID,
            "positivePrompt": prompt,
            "negativePrompt": NEGATIVE_PROMPT,
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            "numberResults": 1,
            "outputType": "URL",
            "outputFormat": "JPG",
        }
    ]

    resp = requests.post(RUNWARE_API_URL, json=payload, headers=headers, timeout=90)
    if not resp.ok:
        raise RuntimeError(f"Runware error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    items = data.get("data", []) if isinstance(data, dict) else data
    if not items:
        raise ValueError(f"Empty Runware response: {data}")

    image_url = items[0].get("imageURL")
    if not image_url:
        raise ValueError(f"No imageURL in Runware response: {items[0]}")

    return image_url


def download_image(image_url: str, local_path: str) -> None:
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(resp.content)


def make_placeholder(local_path: str) -> None:
    """Generate a solid-colour placeholder image on Runware failure."""
    from PIL import Image, ImageDraw
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), PLACEHOLDER_COLOR)
    draw = ImageDraw.Draw(img)
    # Saffron diagonal stripe as minimal visual interest
    for i in range(0, IMAGE_WIDTH + IMAGE_HEIGHT, 60):
        draw.line([(i, 0), (0, i)], fill=(232, 101, 26, 80), width=2)
    img.save(local_path, "JPEG", quality=85)
    print(f"    Placeholder saved → {local_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_visuals(sheet_file: str = PRODUCTION_SHEET) -> None:
    print(f"Loading {sheet_file} …")
    with open(sheet_file, "r", encoding="utf-8") as f:
        sheet = json.load(f)

    os.makedirs(IMAGES_DIR, exist_ok=True)
    segments = sheet["segments"]

    for seg in segments:
        seg_id = seg["id"]
        prompt = seg["visual"]["image_prompt"]
        out_path = f"{IMAGES_DIR}/segment-{seg_id}.jpg"

        print(f"\n  Segment {seg_id}: {prompt[:60]}…")

        success = False
        for attempt in range(1, 3):  # try twice
            try:
                print(f"    → Runware attempt {attempt} …")
                image_url = generate_image(prompt)
                download_image(image_url, out_path)
                print(f"    Downloaded → {out_path}")
                success = True
                break
            except Exception as e:
                print(f"    Runware error (attempt {attempt}): {e}")
                if attempt < 2:
                    time.sleep(3)

        if not success:
            print(f"    Using placeholder for segment {seg_id}")
            make_placeholder(out_path)

        seg["visual"]["image_file"] = out_path

    with open(sheet_file, "w", encoding="utf-8") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=2)

    print(f"\n  Visuals complete. Updated {sheet_file}")


if __name__ == "__main__":
    sheet_file = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_SHEET
    generate_visuals(sheet_file)
