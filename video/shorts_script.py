"""
shorts_script.py — Stage 1 of the YouTube Shorts pipeline
Reads final_output.json, calls Gemini to generate a Hinglish punchy script,
validates with Pydantic, and saves production_sheet.json.
"""

import json
import os
import sys

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, ValidationError

load_dotenv()

API_KEY = os.getenv("API_KEY")
PRODUCTION_SHEET = "production_sheet.json"


# ── Pydantic schema ───────────────────────────────────────────────────────────

class ElevenLabsConfig(BaseModel):
    stability: float            # 0.2–0.35 for emotional segments
    similarity_boost: float     # 0.7–0.85
    style: float                # 0.7–0.9 for expressive
    use_speaker_boost: bool     # True
    emotion_tag: str            # prepended to text: "(with shock)"


class GeminiTTSStyle(BaseModel):
    style_instruction: str      # "[Style: angry, fast, rising pitch]"


class VisualConfig(BaseModel):
    image_prompt: str
    effect: str                 # "ken_burns_zoom_in" | "ken_burns_zoom_out" | "pan_left" | "pan_right" | "parallax_up"
    zoom_from: float
    zoom_to: float
    overlay_type: str | None    # "source_citation" | "quote" | None
    overlay_text: str | None
    overlay_attribution: str | None


class Segment(BaseModel):
    id: int
    estimated_duration_sec: float
    spoken_text: str
    emotion: str                # "shocking" | "angry" | "sad" | "urgent" | "calm" | "conspiratorial"
    elevenlabs: ElevenLabsConfig
    gemini_tts: GeminiTTSStyle
    visual: VisualConfig


class ProductionSheet(BaseModel):
    slug: str
    blog_h1: str
    target_duration_sec: int
    segments: list[Segment]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_gemini():
    if not API_KEY:
        raise EnvironmentError("API_KEY not set in .env")
    return genai.Client(api_key=API_KEY)


def make_slug(h1: str) -> str:
    import re
    slug = h1.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


SYSTEM_INSTRUCTION = """\
You are a Hinglish YouTube Shorts scriptwriter for CasteFreeIndia — an anti-caste, evidence-based channel.
Write punchy, rage-bait, fact-based scripts in casual spoken Hinglish (mix of Hindi and English).
Use natural code-switching. Provoke sharing and outrage: "yaar sun lo", "shock lag jayega", "ye log nahi chahte ke tum yeh jaano".
Output ONLY valid JSON — no markdown fences, no commentary."""

SEGMENT_STRUCTURE = """\
Structure:
- Hook (0–15s): shocking stat or provocative question
- Problem/Rage setup (15–40s): what the system/dominant narrative says
- Fact punches x3-4 (40–120s): evidence-based rebuttals, each ~15-20s
- Emotional call to action (120–150s): anger → action
- Sign-off (150–170s): share, follow, "Jai Bhim"

Effects available: ken_burns_zoom_in, ken_burns_zoom_out, pan_left, pan_right, parallax_up
Overlay types: source_citation, quote, null

For each segment produce:
- spoken_text: ONLY what the narrator says (clean Hinglish, no stage directions)
- emotion: one of shocking | angry | sad | urgent | calm | conspiratorial
- elevenlabs: {stability 0.2-0.35, similarity_boost 0.7-0.85, style 0.7-0.9, use_speaker_boost: true, emotion_tag: "(with shock)" style}
- gemini_tts: {style_instruction: "[Style: angry, fast, rising pitch]" style}
- visual: {image_prompt, effect, zoom_from, zoom_to, overlay_type, overlay_text, overlay_attribution}
  - image_prompt: "Editorial illustration of [concrete visual scene], flat design, muted earthy tones, Indian context, minimalist, NO TEXT"
  - zoom_from/zoom_to: 1.0 to max 1.4
"""

USER_TEMPLATE = """\
Blog title: {blog_h1}
Key quote: {most_shareable_quote}
Meme top (misconception): {meme_top_text}
Meme bottom (rebuttal): {meme_bottom_text}
Keywords: {keywords}
Blog summary (first 1200 chars of HTML stripped):
{blog_excerpt}

{structure}

Output a single JSON object matching this schema exactly:
{{
  "slug": "...",
  "blog_h1": "...",
  "target_duration_sec": 170,
  "segments": [
    {{
      "id": 1,
      "estimated_duration_sec": 15.0,
      "spoken_text": "...",
      "emotion": "shocking",
      "elevenlabs": {{
        "stability": 0.25,
        "similarity_boost": 0.80,
        "style": 0.85,
        "use_speaker_boost": true,
        "emotion_tag": "(with shock)"
      }},
      "gemini_tts": {{
        "style_instruction": "[Style: shocked, fast, rising pitch]"
      }},
      "visual": {{
        "image_prompt": "Editorial illustration of ..., flat design, muted earthy tones, Indian context, minimalist, NO TEXT",
        "effect": "ken_burns_zoom_in",
        "zoom_from": 1.0,
        "zoom_to": 1.3,
        "overlay_type": "source_citation",
        "overlay_text": "NCRB 2023: ...",
        "overlay_attribution": "— NCRB 2023"
      }}
    }}
  ]
}}
"""


def strip_html(html: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_script(input_file: str = "") -> None:
    if not input_file:
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        input_file = os.path.join(_script_dir, "..", "final_output.json")
    print(f"Loading {input_file} …")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    blog_h1 = data.get("title", {}).get("blog_h1", "")
    content = data.get("content", {})
    blog_post_html = content.get("blog_post_html", "")
    most_shareable_quote = content.get("most_shareable_quote", "")
    meme_top_text = content.get("meme_top_text", "")
    meme_bottom_text = content.get("meme_bottom_text", "")
    keyword_list = data.get("seo", {}).get("keyword_list", [])
    keywords = ", ".join(keyword_list[:8]) if keyword_list else ""

    blog_excerpt = strip_html(blog_post_html)[:1200]
    slug = make_slug(blog_h1)

    print(f"  blog_h1 : {blog_h1}")
    print(f"  slug    : {slug}")

    prompt = USER_TEMPLATE.format(
        blog_h1=blog_h1,
        most_shareable_quote=most_shareable_quote,
        meme_top_text=meme_top_text,
        meme_bottom_text=meme_bottom_text,
        keywords=keywords,
        blog_excerpt=blog_excerpt,
        structure=SEGMENT_STRUCTURE,
    )

    print("  Calling Gemini for Hinglish script …")
    client = get_gemini()
    resp = client.models.generate_content(
        model="models/gemini-2.5-flash-lite",
        contents=prompt,
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "temperature": 0.8,
            "max_output_tokens": 4096,
        },
    )

    raw = resp.text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        sheet_dict = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  Raw output (first 500 chars): {raw[:500]}")
        sys.exit(1)

    # Ensure slug is set
    sheet_dict["slug"] = slug
    sheet_dict["blog_h1"] = blog_h1

    try:
        sheet = ProductionSheet.model_validate(sheet_dict)
    except ValidationError as e:
        print(f"  Pydantic validation error:\n{e}")
        print("  Saving raw JSON anyway for inspection …")
        os.makedirs(os.path.dirname(os.path.abspath(PRODUCTION_SHEET)) or ".", exist_ok=True)
        with open(PRODUCTION_SHEET, "w", encoding="utf-8") as f:
            json.dump(sheet_dict, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(PRODUCTION_SHEET)) or ".", exist_ok=True)
    with open(PRODUCTION_SHEET, "w", encoding="utf-8") as f:
        json.dump(sheet.model_dump(), f, ensure_ascii=False, indent=2)

    total_est = sum(s.estimated_duration_sec for s in sheet.segments)
    print(f"\n  Segments : {len(sheet.segments)}")
    print(f"  Est. duration : {total_est:.1f}s")
    print(f"  Saved → {PRODUCTION_SHEET}")


if __name__ == "__main__":
    # Resolve default input path relative to this script's location,
    # so it works from any working directory.
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _default_input = os.path.join(_script_dir, "..", "final_output.json")
    input_file = sys.argv[1] if len(sys.argv) > 1 else _default_input
    generate_script(input_file)
