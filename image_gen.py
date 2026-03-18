import json
import os
import re
import shutil

from PIL import Image, ImageDraw, ImageFont

# ── Colour palette ────────────────────────────────────────────────────────────
BG_DARK     = "#1a1a1a"
BG_MID      = "#222222"
CHAKRA_BLUE = "#06038D"
WHITE       = "#FFFFFF"
MUTED       = "#AAAAAA"
SITE_NAME   = "CasteFreeIndia.com"

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:80]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "./fonts/NotoSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


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
                     max_width: int, max_lines: int = 3, min_size: int = 28) -> tuple:
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


def draw_centered_text(draw: ImageDraw.ImageDraw, lines: list[str], font,
                       y_start: int, img_width: int, colour: str,
                       line_spacing: int = 12) -> int:
    """Draw centered multi-line text; returns y after last line."""
    y = y_start
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (img_width - w) // 2
        draw.text((x, y), line, font=font, fill=colour)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def hline(draw: ImageDraw.ImageDraw, y: int, img_width: int,
          colour: str, thickness: int = 4, margin: int = 60):
    draw.rectangle([(margin, y), (img_width - margin, y + thickness)], fill=colour)


# ── Image 1 — Quote card (1080×1080) ─────────────────────────────────────────

def make_quote_card(blog_h1: str, quote: str, slug: str, folder: str):
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Site name
    font_site = load_font(28)
    site_text = SITE_NAME.upper()
    bbox = draw.textbbox((0, 0), site_text, font=font_site)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 60), site_text,
              font=font_site, fill=CHAKRA_BLUE)

    # Top rule
    hline(draw, 120, W, CHAKRA_BLUE, thickness=4)

    # Quote (auto-shrink, max 3 lines)
    font_q, q_lines = auto_shrink_font(draw, quote, start_size=52,
                                       max_width=W - 120, max_lines=3)
    draw_centered_text(draw, q_lines, font_q, y_start=200, img_width=W,
                       colour=WHITE, line_spacing=16)

    # Bottom rule
    hline(draw, 820, W, CHAKRA_BLUE, thickness=4)

    # Blog h1 (truncate at 80 chars)
    h1_display = blog_h1 if len(blog_h1) <= 80 else blog_h1[:80] + "…"
    font_h1 = load_font(26)
    bbox = draw.textbbox((0, 0), h1_display, font=font_h1)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 840), h1_display,
              font=font_h1, fill=MUTED)

    # Bottom-right watermark
    font_wm = load_font(20)
    wm = "castefreeindia.com"
    bbox = draw.textbbox((0, 0), wm, font=font_wm)
    draw.text((W - (bbox[2] - bbox[0]) - 30, H - 40), wm,
              font=font_wm, fill=MUTED)

    path = os.path.join(folder, f"quote-{slug}.png")
    img.save(path)
    print(f"  Saved: {path}")


# ── Image 2 — X header (1600×900) ────────────────────────────────────────────

def make_x_header(blog_h1: str, slug: str, folder: str):
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Resolve x_hook
    x_hook = ""
    if os.path.exists("social_output.json"):
        with open("social_output.json", encoding="utf-8") as f:
            x_hook = json.load(f).get("x", {}).get("hook", "")
    x_hook = x_hook.replace("🧵", "").strip() or blog_h1

    # Site name (left-aligned)
    font_site = load_font(28)
    draw.text((80, 60), SITE_NAME.upper(), font=font_site, fill=CHAKRA_BLUE)

    # Rule below site name
    draw.rectangle([(80, 110), (W - 80, 113)], fill=CHAKRA_BLUE)

    # x_hook (auto-shrink)
    font_hook, hook_lines = auto_shrink_font(draw, x_hook, start_size=64,
                                             max_width=W - 160, max_lines=3)
    draw_centered_text(draw, hook_lines, font_hook, y_start=160,
                       img_width=W, colour=WHITE, line_spacing=20)

    # Rule above footer
    draw.rectangle([(80, 820), (W - 80, 823)], fill=CHAKRA_BLUE)

    # Footer (left-aligned)
    font_footer = load_font(28)
    draw.text((80, 840), "castefreeindia.com", font=font_footer, fill=MUTED)

    path = os.path.join(folder, f"x-header-{slug}.png")
    img.save(path)
    print(f"  Saved: {path}")


# ── Image 3 — Meme (1080×1080) ───────────────────────────────────────────────

def make_meme(meme_top: str, meme_bottom: str, slug: str, folder: str):
    W, H = 1080, 1080
    DIVIDER_Y = 530
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Bottom panel background
    draw.rectangle([(0, DIVIDER_Y + 6), (W, H)], fill=BG_MID)

    # Divider line
    draw.rectangle([(0, DIVIDER_Y), (W, DIVIDER_Y + 6)], fill=CHAKRA_BLUE)

    # ── Top panel ──
    font_label = load_font(28)
    label_top = "What they say:"
    bbox = draw.textbbox((0, 0), label_top, font=font_label)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 60), label_top,
              font=font_label, fill=CHAKRA_BLUE)

    top_text = meme_top or "Caste is a thing of the past."
    font_top, top_lines = auto_shrink_font(draw, top_text, start_size=48,
                                           max_width=W - 120, max_lines=3)
    draw_centered_text(draw, top_lines, font_top, y_start=120,
                       img_width=W, colour=WHITE, line_spacing=14)

    # ── Bottom panel ──
    label_bot = "What the evidence shows:"
    bbox = draw.textbbox((0, 0), label_bot, font=font_label)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, DIVIDER_Y + 26), label_bot,
              font=font_label, fill=CHAKRA_BLUE)

    bot_text = meme_bottom or "Evidence tells a different story."
    font_bot, bot_lines = auto_shrink_font(draw, bot_text, start_size=48,
                                           max_width=W - 120, max_lines=3)
    draw_centered_text(draw, bot_lines, font_bot, y_start=DIVIDER_Y + 90,
                       img_width=W, colour=WHITE, line_spacing=14)

    # Source footer
    font_src = load_font(22)
    src = "Source: castefreeindia.com"
    bbox = draw.textbbox((0, 0), src, font=font_src)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, H - 50), src,
              font=font_src, fill=MUTED)

    path = os.path.join(folder, f"meme-{slug}.png")
    img.save(path)
    print(f"  Saved: {path}")


# ── social_output.json update ─────────────────────────────────────────────────

def update_social_output(folder: str, slug: str, quote: str,
                         meme_top: str, meme_bottom: str):
    existing = {}
    if os.path.exists("social_output.json"):
        with open("social_output.json", encoding="utf-8") as f:
            existing = json.load(f)
    existing["social_images"] = {
        "quote_card": f"./{folder}/quote-{slug}.png",
        "x_header": f"./{folder}/x-header-{slug}.png",
        "meme": f"./{folder}/meme-{slug}.png",
        "quote_used": quote,
        "meme_top_text": meme_top,
        "meme_bottom_text": meme_bottom,
    }
    with open("social_output.json", "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print("  Updated social_output.json → social_images block")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_images():
    with open("final_output.json", encoding="utf-8") as f:
        data = json.load(f)

    blog_h1     = data["title"]["blog_h1"]
    content     = data.get("content", {})
    quote       = content.get("most_shareable_quote", "") or blog_h1
    meme_top    = content.get("meme_top_text", "")
    meme_bottom = content.get("meme_bottom_text", "")

    slug   = make_slug(blog_h1)
    folder = os.path.join("images", slug)
    os.makedirs(folder, exist_ok=True)
    print(f"Output folder: ./{folder}/")

    make_quote_card(blog_h1, quote, slug, folder)
    make_x_header(blog_h1, slug, folder)
    make_meme(meme_top, meme_bottom, slug, folder)

    # Archive a copy of final_output.json alongside the images
    shutil.copy("final_output.json", os.path.join(folder, "final_output.json"))
    print(f"  Copied final_output.json → ./{folder}/final_output.json")

    update_social_output(folder, slug, quote, meme_top, meme_bottom)
    print(f"\nDone — images + JSON saved to ./{folder}/")


if __name__ == "__main__":
    generate_images()
