"""
shorts_editor.py — Stage 4 of the YouTube Shorts pipeline
Reads production_sheet.json (with audio + visual paths populated by stages 2 & 3),
applies Ken Burns / pan effects per segment, adds text overlays via Pillow,
and assembles the final 1080×1920 vertical video with MoviePy.
"""

import json
import os
import sys
import textwrap
from io import BytesIO

import numpy as np
from dotenv import load_dotenv

load_dotenv()

PRODUCTION_SHEET = "video/production_sheet.json"
OUTPUT_VIDEO = "video/final_short.mp4"

VIDEO_W = 1080
VIDEO_H = 1920
FPS = 30

SAFFRON = (232, 101, 26)
DARK_BG = (26, 26, 26)
WHITE = (255, 255, 255)
MUTED_WHITE = (200, 200, 200)

FONT_PATH = "./fonts/NotoSans-Bold.ttf"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Bold.ttf"


# ── Font loader ───────────────────────────────────────────────────────────────

def load_font(size: int):
    from PIL import ImageFont
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
    import urllib.request
    os.makedirs("./fonts", exist_ok=True)
    if not os.path.exists(FONT_PATH):
        print("  Downloading NotoSans-Bold.ttf …")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return ImageFont.truetype(FONT_PATH, size)


# ── Ken Burns / pan effect ────────────────────────────────────────────────────

def make_visual_clip(image_path: str, duration: float, effect: str,
                     zoom_from: float, zoom_to: float):
    """
    Return a MoviePy ImageClip with the specified motion effect applied.
    All clips are 1080×1920 at FPS frames/sec.
    """
    from moviepy.editor import ImageClip
    from PIL import Image

    img_pil = Image.open(image_path).convert("RGB")
    # Ensure source image is large enough for zoom (pad if needed)
    src_w, src_h = img_pil.size
    max_zoom = max(zoom_from, zoom_to)
    need_w = int(VIDEO_W * max_zoom) + 2
    need_h = int(VIDEO_H * max_zoom) + 2
    if src_w < need_w or src_h < need_h:
        img_pil = img_pil.resize(
            (max(src_w, need_w), max(src_h, need_h)),
            Image.LANCZOS,
        )
    img_arr = np.array(img_pil)

    def make_frame(t: float) -> np.ndarray:
        progress = t / duration if duration > 0 else 0.0

        if effect in ("ken_burns_zoom_in", "ken_burns_zoom_out"):
            scale = zoom_from + (zoom_to - zoom_from) * progress
            # Centre-crop to VIDEO_W × VIDEO_H
            h, w = img_arr.shape[:2]
            new_w = int(VIDEO_W * scale)
            new_h = int(VIDEO_H * scale)
            # Clamp to source dimensions
            new_w = min(new_w, w)
            new_h = min(new_h, h)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
            cropped = img_arr[y1:y1+new_h, x1:x1+new_w]
            from PIL import Image as PILImage
            resized = PILImage.fromarray(cropped).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS)
            return np.array(resized)

        elif effect == "pan_left":
            h, w = img_arr.shape[:2]
            offset_x = int(100 * (1.0 - progress))  # +100px → 0
            x1 = min(offset_x, w - VIDEO_W)
            x1 = max(0, x1)
            crop = img_arr[0:VIDEO_H, x1:x1+VIDEO_W]
            if crop.shape[1] < VIDEO_W:
                from PIL import Image as PILImage
                crop = np.array(PILImage.fromarray(crop).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))
            return crop

        elif effect == "pan_right":
            h, w = img_arr.shape[:2]
            offset_x = int(100 * progress)  # 0 → +100px
            x1 = min(offset_x, w - VIDEO_W)
            x1 = max(0, x1)
            crop = img_arr[0:VIDEO_H, x1:x1+VIDEO_W]
            if crop.shape[1] < VIDEO_W:
                from PIL import Image as PILImage
                crop = np.array(PILImage.fromarray(crop).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))
            return crop

        elif effect == "parallax_up":
            h, w = img_arr.shape[:2]
            offset_y = int(80 * (1.0 - progress))  # +80px → 0
            y1 = min(offset_y, h - VIDEO_H)
            y1 = max(0, y1)
            crop = img_arr[y1:y1+VIDEO_H, 0:VIDEO_W]
            if crop.shape[0] < VIDEO_H:
                from PIL import Image as PILImage
                crop = np.array(PILImage.fromarray(crop).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))
            return crop

        else:
            # Default: static centre crop
            h, w = img_arr.shape[:2]
            x1 = max(0, (w - VIDEO_W) // 2)
            y1 = max(0, (h - VIDEO_H) // 2)
            crop = img_arr[y1:y1+VIDEO_H, x1:x1+VIDEO_W]
            return crop

    clip = ImageClip(make_frame, duration=duration, ismask=False)
    clip = clip.set_fps(FPS)
    return clip


# ── Text overlay (Pillow → numpy array → ImageClip) ──────────────────────────

def render_citation_overlay(text: str, attribution: str | None) -> np.ndarray:
    """
    Render a semi-transparent dark bar (bottom 12% of frame) with citation text.
    Returns a numpy RGBA array of size VIDEO_W × VIDEO_H.
    """
    from PIL import Image, ImageDraw
    bar_h = int(VIDEO_H * 0.12)
    bar_y = VIDEO_H - bar_h

    overlay = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Dark bar
    draw.rectangle([(0, bar_y), (VIDEO_W, VIDEO_H)], fill=(0, 0, 0, 190))

    # Saffron rule
    draw.rectangle([(0, bar_y), (VIDEO_W, bar_y + 3)], fill=(*SAFFRON, 255))

    font_cite = load_font(34)
    font_attr = load_font(26)
    PAD = 36

    # Citation text (wrap to 2 lines)
    wrapped = textwrap.fill(text, width=44)
    y = bar_y + 14
    draw.text((PAD, y), wrapped, font=font_cite, fill=(*WHITE, 230))

    if attribution:
        bbox = draw.textbbox((0, 0), wrapped, font=font_cite)
        text_h = bbox[3] - bbox[1]
        y += text_h + 8
        draw.text((PAD, y), attribution, font=font_attr, fill=(*SAFFRON, 200))

    return np.array(overlay)


def render_quote_overlay(text: str, attribution: str | None) -> np.ndarray:
    """
    Render a stylised mid-frame quote box.
    Returns a numpy RGBA array of size VIDEO_W × VIDEO_H.
    """
    from PIL import Image, ImageDraw
    overlay = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    box_w = int(VIDEO_W * 0.88)
    box_x = (VIDEO_W - box_w) // 2
    box_y = int(VIDEO_H * 0.35)
    box_h = int(VIDEO_H * 0.28)

    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=18,
        fill=(0, 0, 0, 200),
    )
    # Saffron left accent
    draw.rectangle([(box_x, box_y), (box_x + 6, box_y + box_h)], fill=(*SAFFRON, 255))

    font_q = load_font(40)
    font_a = load_font(28)
    PAD = 28
    max_w = box_w - PAD * 2 - 10

    wrapped = textwrap.fill(text, width=38)
    draw.text((box_x + PAD + 10, box_y + PAD), wrapped, font=font_q,
              fill=(*WHITE, 240))

    if attribution:
        draw.text(
            (box_x + PAD + 10, box_y + box_h - 50),
            attribution, font=font_a, fill=(*SAFFRON, 220),
        )

    return np.array(overlay)


def make_overlay_clip(overlay_arr: np.ndarray, duration: float):
    from moviepy.editor import ImageClip
    clip = ImageClip(overlay_arr, ismask=False, duration=duration)
    clip = clip.set_fps(FPS)
    return clip


# ── Segment clip builder ──────────────────────────────────────────────────────

def make_segment_clip(seg: dict, audio_info: dict):
    from moviepy.editor import CompositeVideoClip

    seg_id = str(seg["id"])
    image_file = seg["visual"].get("image_file")
    effect = seg["visual"].get("effect", "ken_burns_zoom_in")
    zoom_from = seg["visual"].get("zoom_from", 1.0)
    zoom_to = seg["visual"].get("zoom_to", 1.3)
    overlay_type = seg["visual"].get("overlay_type")
    overlay_text = seg["visual"].get("overlay_text")
    overlay_attribution = seg["visual"].get("overlay_attribution")

    # Duration from actual audio; fall back to estimate
    if seg_id in audio_info:
        duration = audio_info[seg_id]["actual_duration_sec"]
    else:
        duration = seg["estimated_duration_sec"]

    if not image_file or not os.path.exists(image_file):
        # Solid colour fallback
        from PIL import Image
        arr = np.full((VIDEO_H, VIDEO_W, 3), DARK_BG, dtype=np.uint8)
        from moviepy.editor import ImageClip
        visual = ImageClip(arr, duration=duration).set_fps(FPS)
    else:
        visual = make_visual_clip(image_file, duration, effect, zoom_from, zoom_to)

    layers = [visual]

    if overlay_type == "source_citation" and overlay_text:
        ov_arr = render_citation_overlay(overlay_text, overlay_attribution)
        overlay_clip = make_overlay_clip(ov_arr, duration)
        layers.append(overlay_clip)
    elif overlay_type == "quote" and overlay_text:
        ov_arr = render_quote_overlay(overlay_text, overlay_attribution)
        overlay_clip = make_overlay_clip(ov_arr, duration)
        layers.append(overlay_clip)

    if len(layers) > 1:
        return CompositeVideoClip(layers, size=(VIDEO_W, VIDEO_H))
    return visual


# ── Main ──────────────────────────────────────────────────────────────────────

def edit_video(sheet_file: str = PRODUCTION_SHEET) -> None:
    # Check ffmpeg is available
    import shutil
    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found. Install it first:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: apt-get install ffmpeg")
        sys.exit(1)

    print(f"Loading {sheet_file} …")
    with open(sheet_file, "r", encoding="utf-8") as f:
        sheet = json.load(f)

    from moviepy.editor import AudioFileClip, concatenate_videoclips

    audio_info = sheet.get("audio", {}).get("segment_files", {})
    full_audio_path = sheet.get("audio", {}).get("full_audio", "video/audio/full_audio.mp3")

    segments = sheet["segments"]
    print(f"  Building {len(segments)} segment clips …")

    clips = []
    for seg in segments:
        print(f"    Segment {seg['id']} ({seg['emotion']}) …")
        clip = make_segment_clip(seg, audio_info)
        clips.append(clip)

    print("  Concatenating …")
    video = concatenate_videoclips(clips, method="compose")

    if os.path.exists(full_audio_path):
        print(f"  Attaching audio: {full_audio_path}")
        audio = AudioFileClip(full_audio_path)
        # Trim audio to video length if needed
        if audio.duration > video.duration:
            audio = audio.subclip(0, video.duration)
        video = video.set_audio(audio)
    else:
        print(f"  Warning: {full_audio_path} not found — video will be silent")

    os.makedirs(os.path.dirname(OUTPUT_VIDEO) or ".", exist_ok=True)
    print(f"  Writing {OUTPUT_VIDEO} …")
    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        logger="bar",
    )
    print(f"\n  Done. Output: {OUTPUT_VIDEO}")


if __name__ == "__main__":
    sheet_file = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_SHEET
    edit_video(sheet_file)
