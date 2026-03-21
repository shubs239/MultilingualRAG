"""
shorts_editor.py — Stage 4 of the YouTube Shorts pipeline
Reads production_sheet.json (with audio + visual paths populated by stages 2 & 3),
applies Ken Burns / pan effects per segment, adds text overlays via Pillow,
and assembles the final 1080×1920 vertical video with MoviePy.

Requires MoviePy 2.x (moviepy.editor no longer exists in 2.x).
"""

import json
import os
import sys

import numpy as np
from dotenv import load_dotenv

load_dotenv()

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_sheet(slug):
    _ps_dir = os.path.join(_SCRIPT_DIR, "production_sheet")
    if slug is None:
        import glob as _glob
        sheets = _glob.glob(os.path.join(_ps_dir, "*.json"))
        if not sheets:
            raise FileNotFoundError("No production sheets found in production_sheet/")
        slug = os.path.splitext(os.path.basename(max(sheets, key=os.path.getmtime)))[0]
    sheet_path = os.path.join(_ps_dir, f"{slug}.json")
    output_path = os.path.join(_SCRIPT_DIR, "output", f"{slug}.mp4")
    return sheet_path, output_path, slug

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
    Return a MoviePy VideoClip with the specified motion effect.
    Output size: VIDEO_W × VIDEO_H at FPS.
    MoviePy 2.x: use VideoClip(make_frame, duration=) instead of ImageClip(fn).
    """
    from moviepy import VideoClip
    from PIL import Image

    img_pil = Image.open(image_path).convert("RGB")
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
            h, w = img_arr.shape[:2]
            new_w = min(int(VIDEO_W * scale), w)
            new_h = min(int(VIDEO_H * scale), h)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
            cropped = img_arr[y1:y1+new_h, x1:x1+new_w]
            from PIL import Image as PILImage
            return np.array(PILImage.fromarray(cropped).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))

        elif effect == "pan_left":
            h, w = img_arr.shape[:2]
            offset_x = max(0, min(int(100 * (1.0 - progress)), w - VIDEO_W))
            crop = img_arr[0:VIDEO_H, offset_x:offset_x+VIDEO_W]
            if crop.shape[1] < VIDEO_W:
                from PIL import Image as PILImage
                crop = np.array(PILImage.fromarray(crop).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))
            return crop

        elif effect == "pan_right":
            h, w = img_arr.shape[:2]
            offset_x = max(0, min(int(100 * progress), w - VIDEO_W))
            crop = img_arr[0:VIDEO_H, offset_x:offset_x+VIDEO_W]
            if crop.shape[1] < VIDEO_W:
                from PIL import Image as PILImage
                crop = np.array(PILImage.fromarray(crop).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))
            return crop

        elif effect == "parallax_up":
            h, w = img_arr.shape[:2]
            offset_y = max(0, min(int(80 * (1.0 - progress)), h - VIDEO_H))
            crop = img_arr[offset_y:offset_y+VIDEO_H, 0:VIDEO_W]
            if crop.shape[0] < VIDEO_H:
                from PIL import Image as PILImage
                crop = np.array(PILImage.fromarray(crop).resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS))
            return crop

        else:
            h, w = img_arr.shape[:2]
            x1 = max(0, (w - VIDEO_W) // 2)
            y1 = max(0, (h - VIDEO_H) // 2)
            return img_arr[y1:y1+VIDEO_H, x1:x1+VIDEO_W]

    # MoviePy 2.x: VideoClip for dynamic frames, with_fps for fps
    clip = VideoClip(make_frame, duration=duration).with_fps(FPS)
    return clip


# ── Text overlay (Pillow → numpy → ImageClip) ─────────────────────────────────
# Both overlays sit at the bottom of the frame and are content-sized:
# text wraps at max 90% width, attribution immediately on the next line,
# bar height grows to fit — never a fixed fraction of the screen.

PAD_X = 32   # horizontal padding inside the bar
PAD_Y = 16   # vertical padding above/below text
LINE_GAP = 6  # gap between citation line(s) and attribution


def _measure_wrapped_lines(draw, text: str, font, max_px: int) -> list[str]:
    """Word-wrap text to fit within max_px, return list of lines."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_px:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_citation_overlay(text: str, attribution: str | None) -> np.ndarray:
    from PIL import Image, ImageDraw

    font_cite = load_font(32)
    font_attr = load_font(24)
    max_text_w = VIDEO_W - PAD_X * 2

    # Measure on a throw-away draw so we know bar height before creating the canvas
    tmp = Image.new("RGBA", (VIDEO_W, 10))
    d = ImageDraw.Draw(tmp)
    cite_lines = _measure_wrapped_lines(d, text, font_cite, max_text_w)
    cite_line_h = d.textbbox((0, 0), "Ag", font=font_cite)[3]  # single-line height
    attr_line_h = d.textbbox((0, 0), "Ag", font=font_attr)[3] if attribution else 0

    content_h = (cite_line_h + LINE_GAP) * len(cite_lines)
    if attribution:
        content_h += attr_line_h + LINE_GAP
    bar_h = content_h + PAD_Y * 2 + 3  # 3px for saffron rule

    overlay = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_y = VIDEO_H - bar_h
    draw.rectangle([(0, bar_y), (VIDEO_W, VIDEO_H)], fill=(0, 0, 0, 200))
    draw.rectangle([(0, bar_y), (VIDEO_W, bar_y + 3)], fill=(*SAFFRON, 255))

    y = bar_y + 3 + PAD_Y
    for line in cite_lines:
        draw.text((PAD_X, y), line, font=font_cite, fill=(*WHITE, 235))
        y += cite_line_h + LINE_GAP

    if attribution:
        draw.text((PAD_X, y), attribution, font=font_attr, fill=(*SAFFRON, 210))

    return np.array(overlay)


def render_quote_overlay(text: str, attribution: str | None) -> np.ndarray:
    from PIL import Image, ImageDraw

    font_q = load_font(36)
    font_a = load_font(26)
    box_w = int(VIDEO_W * 0.88)
    max_text_w = box_w - PAD_X * 2 - 10

    tmp = Image.new("RGBA", (box_w, 10))
    d = ImageDraw.Draw(tmp)
    q_lines = _measure_wrapped_lines(d, text, font_q, max_text_w)
    q_line_h = d.textbbox((0, 0), "Ag", font=font_q)[3]
    attr_line_h = d.textbbox((0, 0), "Ag", font=font_a)[3] if attribution else 0

    content_h = (q_line_h + LINE_GAP) * len(q_lines)
    if attribution:
        content_h += attr_line_h + LINE_GAP
    box_h = content_h + PAD_Y * 2

    box_x = (VIDEO_W - box_w) // 2
    # Position in lower third so it doesn't dominate the frame
    box_y = VIDEO_H - box_h - int(VIDEO_H * 0.08)

    overlay = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=14, fill=(0, 0, 0, 210),
    )
    draw.rectangle([(box_x, box_y), (box_x + 5, box_y + box_h)], fill=(*SAFFRON, 255))

    y = box_y + PAD_Y
    for line in q_lines:
        draw.text((box_x + PAD_X + 8, y), line, font=font_q, fill=(*WHITE, 240))
        y += q_line_h + LINE_GAP

    if attribution:
        draw.text((box_x + PAD_X + 8, y), attribution, font=font_a, fill=(*SAFFRON, 220))

    return np.array(overlay)


def make_overlay_clip(overlay_arr: np.ndarray, duration: float):
    # overlay_arr is RGBA; MoviePy 2.x ImageClip accepts numpy arrays
    from moviepy import ImageClip
    clip = ImageClip(overlay_arr, duration=duration).with_fps(FPS)
    return clip


# ── Segment clip builder ──────────────────────────────────────────────────────

def make_segment_clip(seg: dict, audio_info: dict):
    from moviepy import CompositeVideoClip, ImageClip

    seg_id = str(seg["id"])
    image_file = seg["visual"].get("image_file")
    effect = seg["visual"].get("effect", "ken_burns_zoom_in")
    zoom_from = seg["visual"].get("zoom_from", 1.0)
    zoom_to = seg["visual"].get("zoom_to", 1.3)
    overlay_type = seg["visual"].get("overlay_type")
    overlay_text = seg["visual"].get("overlay_text")
    overlay_attribution = seg["visual"].get("overlay_attribution")

    duration = (
        audio_info[seg_id]["actual_duration_sec"]
        if seg_id in audio_info
        else seg["estimated_duration_sec"]
    )

    if not image_file or not os.path.exists(image_file):
        arr = np.full((VIDEO_H, VIDEO_W, 3), DARK_BG, dtype=np.uint8)
        visual = ImageClip(arr, duration=duration).with_fps(FPS)
    else:
        visual = make_visual_clip(image_file, duration, effect, zoom_from, zoom_to)

    layers = [visual]

    if overlay_type == "source_citation" and overlay_text:
        layers.append(make_overlay_clip(render_citation_overlay(overlay_text, overlay_attribution), duration))
    elif overlay_type == "quote" and overlay_text:
        layers.append(make_overlay_clip(render_quote_overlay(overlay_text, overlay_attribution), duration))

    if len(layers) > 1:
        return CompositeVideoClip(layers, size=(VIDEO_W, VIDEO_H))
    return visual


# ── Main ──────────────────────────────────────────────────────────────────────

def edit_video(slug: str = None) -> None:
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found. Install it first:")
        print("  macOS: brew install ffmpeg")
        sys.exit(1)

    sheet_file, output_video, slug = _resolve_sheet(slug)

    print(f"Loading {sheet_file} …")
    with open(sheet_file, "r", encoding="utf-8") as f:
        sheet = json.load(f)

    from moviepy import concatenate_videoclips

    audio_info = sheet.get("audio", {}).get("segment_files", {})

    # Resolve full_audio path — prefer production sheet, fall back to known location
    full_audio_path = sheet.get("audio", {}).get("full_audio")
    if not full_audio_path or not os.path.exists(full_audio_path):
        alt = os.path.join(_SCRIPT_DIR, "audio", f"{slug}-full_audio.mp3")
        if os.path.exists(alt):
            full_audio_path = alt
        elif not full_audio_path:
            full_audio_path = alt  # let the warning below trigger
    print(f"  Audio path: {full_audio_path} (exists={os.path.exists(full_audio_path)})")

    segments = sheet["segments"]
    print(f"  Building {len(segments)} segment clips …")

    clips = []
    for seg in segments:
        print(f"    Segment {seg['id']} ({seg['emotion']}) …")
        clips.append(make_segment_clip(seg, audio_info))

    print("  Concatenating …")
    video = concatenate_videoclips(clips, method="compose")

    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    # Step 1: write video-only track (no audio — MoviePy 2.x audio attachment
    # is unreliable for VideoClip-based clips; we mux with ffmpeg instead)
    video_only_path = output_video.replace(".mp4", "_noaudio.mp4")
    print(f"  Writing video track → {video_only_path} …")
    video.write_videofile(
        video_only_path,
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="medium",
        logger="bar",
    )

    # Step 2: mux audio with ffmpeg
    if os.path.exists(full_audio_path):
        print(f"  Muxing audio ({full_audio_path}) with ffmpeg …")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_only_path,
            "-i", full_audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ffmpeg error:\n{result.stderr[-500:]}")
            print(f"  Keeping video-only file at {video_only_path}")
        else:
            os.remove(video_only_path)
            print(f"  Audio muxed successfully.")
    else:
        print(f"  Warning: {full_audio_path} not found — keeping silent video")
        os.rename(video_only_path, output_video)

    print(f"\n  Done. Output: {output_video}")


if __name__ == "__main__":
    slug_arg = input("Enter slug (leave blank for latest): ").strip() or None
    edit_video(slug_arg)
