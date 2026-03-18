import json
import os
import re
import shutil
import urllib.request

from PIL import Image, ImageColor, ImageDraw, ImageFont

# ── Colour palette ────────────────────────────────────────────────────────────
CHAKRA_BLUE = "#06038D"   # Ashoka Chakra blue — accent lines, labels
TEXT_DARK   = "#1A1A1A"   # primary text on light background
MUTED       = "#666666"   # secondary text / captions
SITE_NAME   = "CasteFreeIndia.com"

# ── Font ──────────────────────────────────────────────────────────────────────
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


# ── Gradient background ───────────────────────────────────────────────────────

def make_gradient_bg(size, color_top="#FFFBF5", color_bottom="#EDE8DF"):
    W, H = size
    img = Image.new("RGB", (W, H))
    r1, g1, b1 = ImageColor.getrgb(color_top)
    r2, g2, b2 = ImageColor.getrgb(color_bottom)
    pixels = []
    for y in range(H):
        t = y / H
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        pixels.extend([(r, g, b)] * W)
    img.putdata(pixels)
    return img


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:80]


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


def extract_bullets(html: str, max_bullets: int = 4) -> list[str]:
    """Pull first max_bullets <li> items, strip inner HTML tags."""
    items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE)
    clean = []
    for item in items:
        text = re.sub(r'<[^>]+>', '', item).strip()
        text = re.sub(r'\s+', ' ', text)
        if text and len(text) > 10:          # skip navigation/short items
            clean.append(text[:120])         # cap per-bullet length
        if len(clean) == max_bullets:
            break
    return clean or ["See blog for details."]


# ── Image 1 — Quote card (1080×1080) ─────────────────────────────────────────

def make_quote_card(blog_h1: str, quote: str, slug: str, folder: str):
    W, H = 1080, 1080
    img = make_gradient_bg((W, H))
    draw = ImageDraw.Draw(img)

    # Site name (centered, small caps style)
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
                       colour=TEXT_DARK, line_spacing=16)

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


# ── Image 2 — X header (1600×900) — bullet-point layout ──────────────────────

def make_x_header(blog_h1: str, blog_html: str, slug: str, folder: str):
    W, H = 1600, 900
    img = make_gradient_bg((W, H))
    draw = ImageDraw.Draw(img)

    # ── Site name (left-aligned)
    font_site = load_font(30)
    draw.text((80, 50), SITE_NAME.upper(), font=font_site, fill=CHAKRA_BLUE)

    # Rule below site name
    draw.rectangle([(80, 100), (W - 80, 103)], fill=CHAKRA_BLUE)

    # ── Blog h1 (auto-shrink, left-aligned)
    font_h1, h1_lines = auto_shrink_font(draw, blog_h1, start_size=44,
                                         max_width=W - 160, max_lines=2)
    y = 140
    for line in h1_lines:
        draw.text((80, y), line, font=font_h1, fill=TEXT_DARK)
        bbox = draw.textbbox((0, 0), line, font=font_h1)
        y += (bbox[3] - bbox[1]) + 12

    # ── Bullet points
    bullets = extract_bullets(blog_html, max_bullets=4)
    font_bullet = load_font(32)
    y = max(y + 20, 240)
    bullet_max_w = W - 160

    for bullet in bullets:
        bullet_text = "• " + bullet
        b_lines = wrap_text(draw, bullet_text, font_bullet, bullet_max_w)
        for line in b_lines:
            draw.text((100, y), line, font=font_bullet, fill=TEXT_DARK)
            bbox = draw.textbbox((0, 0), line, font=font_bullet)
            y += (bbox[3] - bbox[1]) + 12
            if y > 780:
                break
        y += 20   # gap between bullets
        if y > 780:
            break

    # Rule above footer
    draw.rectangle([(80, 820), (W - 80, 823)], fill=CHAKRA_BLUE)

    # Footer (left-aligned)
    font_footer = load_font(28)
    draw.text((80, 840), "castefreeindia.com", font=font_footer, fill=MUTED)

    path = os.path.join(folder, f"x-header-{slug}.png")
    img.save(path)
    print(f"  Saved: {path}")


# ── Image 3 — Meme (1080×1080) — quote-box style ─────────────────────────────

def make_meme(meme_top: str, meme_bottom: str, slug: str, folder: str):
    W, H = 1080, 1080
    DIVIDER_Y = 530

    img = make_gradient_bg((W, H))
    draw = ImageDraw.Draw(img)

    # Divider line
    draw.rectangle([(0, DIVIDER_Y), (W, DIVIDER_Y + 6)], fill=CHAKRA_BLUE)

    # ── Top panel ──
    font_label = load_font(28)

    label_top = "What they say:"
    bbox = draw.textbbox((0, 0), label_top, font=font_label)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 30), label_top,
              font=font_label, fill=CHAKRA_BLUE)

    # Quote box (border only)
    BOX_MARGIN = 60
    BOX_TOP = 80
    BOX_BOTTOM = 430
    draw.rectangle(
        [(BOX_MARGIN, BOX_TOP), (W - BOX_MARGIN, BOX_BOTTOM)],
        outline=CHAKRA_BLUE, width=3
    )

    # meme_top_text inside the box, vertically centred
    top_text = meme_top or "Caste is a thing of the past."
    font_top, top_lines = auto_shrink_font(draw, top_text, start_size=46,
                                           max_width=W - BOX_MARGIN * 2 - 40,
                                           max_lines=4)
    line_h = draw.textbbox((0, 0), "Ag", font=font_top)[3] + 14
    total_h = len(top_lines) * line_h
    y_text = BOX_TOP + ((BOX_BOTTOM - BOX_TOP) - total_h) // 2
    draw_centered_text(draw, top_lines, font_top, y_start=y_text,
                       img_width=W, colour=TEXT_DARK, line_spacing=14)

    # ── Bottom panel ──
    label_bot = "What the evidence shows:"
    bbox = draw.textbbox((0, 0), label_bot, font=font_label)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, DIVIDER_Y + 26), label_bot,
              font=font_label, fill=CHAKRA_BLUE)

    bot_text = meme_bottom or "Evidence tells a different story."
    font_bot, bot_lines = auto_shrink_font(draw, bot_text, start_size=46,
                                           max_width=W - 120, max_lines=4)
    draw_centered_text(draw, bot_lines, font_bot, y_start=DIVIDER_Y + 90,
                       img_width=W, colour=TEXT_DARK, line_spacing=14)

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
    blog_html   = content.get("blog_post_html", "")

    slug   = make_slug(blog_h1)
    folder = os.path.join("images", slug)
    os.makedirs(folder, exist_ok=True)
    print(f"Output folder: ./{folder}/")

    make_quote_card(blog_h1, quote, slug, folder)
    make_x_header(blog_h1, blog_html, slug, folder)
    make_meme(meme_top, meme_bottom, slug, folder)

    # Archive a copy of final_output.json alongside the images
    shutil.copy("final_output.json", os.path.join(folder, "final_output.json"))
    print(f"  Copied final_output.json → ./{folder}/final_output.json")

    update_social_output(folder, slug, quote, meme_top, meme_bottom)
    print(f"\nDone — images + JSON saved to ./{folder}/")


if __name__ == "__main__":
    generate_images()
