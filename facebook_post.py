import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")


def parse_ist_to_unix(dt_str):
    """Parse 'YYYY-MM-DD HH:MM' as IST, return UTC Unix timestamp."""
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M")
    dt_ist = ist.localize(dt)
    return int(dt_ist.timestamp())


def post_to_facebook(slug, scheduled_dt_str):
    social_path = f"social_output/{slug}.json"
    if not os.path.exists(social_path):
        print(f"  [fb] social_output/{slug}.json not found. Run reedit_post.py and image_gen.py first.")
        return

    with open(social_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    caption = data.get("facebook", {}).get("post", "")
    meme_path = data.get("social_images", {}).get("meme", "")

    if not caption:
        print("  [fb] No Facebook caption found in social_output.")
        return
    if not meme_path or not os.path.exists(meme_path):
        print(f"  [fb] Meme image not found at: {meme_path}")
        return

    unix_ts = parse_ist_to_unix(scheduled_dt_str)

    url = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos"
    with open(meme_path, "rb") as img:
        r = requests.post(
            url,
            files={"source": img},
            data={
                "message": caption,
                "published": "false",
                "scheduled_publish_time": unix_ts,
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
            },
        )

    if r.status_code in (200, 201):
        post_id = r.json().get("id") or r.json().get("post_id")
        print(f"  [fb] Scheduled successfully → Post ID: {post_id}")
    else:
        print(f"  [fb] Error {r.status_code}: {r.text[:300]}")


if __name__ == "__main__":
    slug = input("Enter slug: ").strip()
    scheduled_dt = input("Enter scheduled datetime IST (YYYY-MM-DD HH:MM): ").strip()
    post_to_facebook(slug, scheduled_dt)
