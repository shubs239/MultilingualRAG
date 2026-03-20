import json
import os
import re
import urllib.request
import uuid

import requests
from dotenv import load_dotenv
from google import genai
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY")
API_KEY  = os.getenv("API_KEY")
_gemini_client  = None


def get_gemini():
    global _gemini_client
    if _gemini_client is None:
        if not API_KEY:
            raise EnvironmentError("API_KEY not set in .env")
        _gemini_client = genai.Client(api_key=API_KEY)
    return _gemini_client


RUNWARE_API_URL = "https://api.runware.ai/v1"
MODEL_ID = "runware:400@3"
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 624
IMAGES_DIR = "./images"

# ── Colour palette (matches image_gen.py) ────────────────────────────────────
CHAKRA_BLUE  = "#06038D"
TEXT_WHITE   = "#FFFFFF"
OVERLAY_BG   = (0, 0, 0, 180)   # semi-transparent black

# ── Font (same loading logic as image_gen.py) ─────────────────────────────────
FONT_PATH = "./fonts/NotoSans-Bold.ttf"
FONT_URL  = "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Bold.ttf"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        FONT_PATH,
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    os.makedirs("./fonts", exist_ok=True)
    if not os.path.exists(FONT_PATH):
        print("  Downloading NotoSans-Bold.ttf …")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return ImageFont.truetype(FONT_PATH, size)


# ── Text helpers (reused from image_gen.py) ───────────────────────────────────

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def auto_shrink_font(draw: ImageDraw.ImageDraw, text: str, start_size: int,
                     max_width: int, max_lines: int = 3, min_size: int = 24) -> tuple:
    """Return (font, lines) shrinking font until text fits within max_lines."""
    size = start_size
    while size >= min_size:
        font = load_font(size)
        lines = wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        size -= 4
    font = load_font(min_size)
    return font, wrap_text(draw, text, font, max_width)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_slug(h1: str) -> str:
    """Convert blog_h1 to a URL-safe slug."""
    slug = h1.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


NEGATIVE_PROMPT = (
    "text, letters, words, typography, fonts, writing, calligraphy, "
    "signs, labels, captions, watermarks, numbers, digits, headlines, "
    "titles, subtitles, inscriptions, banners, graffiti"
)


def build_prompt(blog_h1: str, meta_description: str) -> str:
    """
    Ask Gemini to convert the blog's meta description into a purely visual scene
    description with zero title words — so the diffusion model cannot render them
    as text.
    """
    system_instruction = (
        "You are an art director converting blog summaries into image-generation prompts. "
        "Your output must describe ONLY visual elements: people, objects, colours, "
        "settings, lighting, mood. Never include any words, letters, labels, or text "
        "that should appear inside the image. Never repeat the blog title verbatim."
    )
    user_message = (
        f"Blog title: {blog_h1}\n"
        f"Blog summary: {meta_description}\n\n"
        "Write a single image-generation prompt (max 60 words) for a flat-design "
        "editorial illustration. Use the summary to pick a concrete visual scene — "
        "people, objects, symbols — that captures the post's argument in an Indian context. "
        "Do NOT use the title words. Do NOT mention text or labels. "
        "End with: flat design, muted tones, deep blue accents, minimalist."
    )
    print("  Asking Gemini for visual prompt …")
    resp = get_gemini().models.generate_content(
        model="models/gemini-2.5-flash-lite",
        contents=user_message,
        config={"system_instruction": system_instruction,
                "temperature": 0.7, "max_output_tokens": 120},
    )
    visual_prompt = resp.text.strip().replace("\n", " ")
    print(f"  Gemini prompt: {visual_prompt}")
    return visual_prompt


# ── Runware API ───────────────────────────────────────────────────────────────

def generate_image(prompt: str) -> str:
    """Call Runware API and return the image URL."""
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

    print(f"  Calling Runware API (model={MODEL_ID}) …")
    resp = requests.post(RUNWARE_API_URL, json=payload, headers=headers, timeout=60)
    if not resp.ok:
        print(f"  Runware error {resp.status_code}: {resp.text}")
    resp.raise_for_status()

    data = resp.json()
    items = data.get("data", []) if isinstance(data, dict) else data
    if not items:
        raise ValueError(f"Empty response from Runware: {data}")

    image_url = items[0].get("imageURL")
    if not image_url:
        raise ValueError(f"No imageURL in response: {items[0]}")

    return image_url


def download_image(image_url: str, local_path: str) -> None:
    """Download image from URL and save to local_path."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(resp.content)
    print(f"  Downloaded → {local_path}")


# ── Pillow text overlay ───────────────────────────────────────────────────────

def add_text_overlay(local_path: str, blog_h1: str) -> None:
    """
    Open AI-generated image and add:
    - Semi-transparent dark bar (bottom 35%)
    - blog_h1 in white, left-aligned, auto-wrapped
    - Thin CHAKRA_BLUE rule
    - "CasteFreeIndia.com" in CHAKRA_BLUE below headline
    Saves back to the same path.
    """
    img = Image.open(local_path).convert("RGBA")
    W, H = img.size

    bar_h = int(H * 0.35)
    bar_y = H - bar_h

    # Semi-transparent overlay bar
    overlay = Image.new("RGBA", (W, bar_h), OVERLAY_BG)
    img.paste(overlay, (0, bar_y), overlay)

    draw = ImageDraw.Draw(img)
    PAD = 48

    # Thin blue rule at top of bar
    rule_y = bar_y + 8
    draw.rectangle([(PAD, rule_y), (W - PAD, rule_y + 3)], fill=CHAKRA_BLUE)

    # blog_h1 text (auto-shrink, left-aligned, max 2 lines)
    max_text_w = W - PAD * 2
    font_h1, h1_lines = auto_shrink_font(
        draw, blog_h1, start_size=44, max_width=max_text_w, max_lines=2
    )

    y = rule_y + 18
    for line in h1_lines:
        draw.text((PAD, y), line, font=font_h1, fill=TEXT_WHITE)
        bbox = draw.textbbox((0, 0), line, font=font_h1)
        y += (bbox[3] - bbox[1]) + 10

    # "CasteFreeIndia.com" in CHAKRA_BLUE
    font_site = load_font(26)
    draw.text((PAD, y + 6), "CasteFreeIndia.com", font=font_site, fill=CHAKRA_BLUE)

    # Save as RGB JPG
    final = img.convert("RGB")
    final.save(local_path, "JPEG", quality=92)
    print(f"  Overlay applied → {local_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def fetch_featured_image(slug: str = None, input_file: str = None) -> None:
    if input_file is None:
        if slug is None:
            from utils import get_latest_slug
            slug = get_latest_slug("final_output")
        input_file = f"final_output/{slug}.json"
    if not RUNWARE_API_KEY:
        raise EnvironmentError("RUNWARE_API_KEY not set in .env")

    print(f"Loading {input_file} …")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    blog_h1 = data.get("title", {}).get("blog_h1", "")
    if not blog_h1:
        raise ValueError("blog_h1 not found in final_output.json → title.blog_h1")

    meta_description = data.get("content", {}).get("meta_description", "")

    print(f"  blog_h1          : {blog_h1}")
    print(f"  meta_description : {meta_description[:80]} …")

    prompt = build_prompt(blog_h1, meta_description)
    print(f"  prompt   : {prompt}")

    slug = make_slug(blog_h1)
    local_path = f"{IMAGES_DIR}/featured-{slug}.jpg"

    image_url = generate_image(prompt)
    print(f"  image URL: {image_url[:80]} …")

    download_image(image_url, local_path)
    add_text_overlay(local_path, blog_h1)

    # Merge featured_image block into final_output.json
    data["featured_image"] = {
        "source": "runware",
        "local_path": local_path,
        "alt_text": blog_h1,
        "prompt_used": prompt,
    }

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. featured_image block added to {input_file}")


if __name__ == "__main__":
    fetch_featured_image()
