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


def get_page_token(user_or_page_token, page_id):
    """
    Exchange a User Access Token (or existing Page token) for the Page's own
    Access Token. Facebook requires page operations to be performed AS the page.
    """
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{page_id}",
        params={"fields": "access_token", "access_token": user_or_page_token},
    )
    token = r.json().get("access_token")
    if not token:
        print(f"  [fb] Could not get Page Access Token: {r.text[:200]}")
    return token


def post_to_facebook(slug, schedule_dt_str=None):
    """
    Post meme image + Facebook caption to Page.
    Requires FACEBOOK_PAGE_ACCESS_TOKEN in .env (User or Page token with
    pages_manage_posts + pages_read_engagement scopes).

    schedule_dt_str: 'YYYY-MM-DD HH:MM' IST — if None, publishes immediately.
    """
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

    # Always use the Page's own access token for page operations
    page_token = get_page_token(FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID)
    if not page_token:
        return

    base = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}"

    # Step 1 — Upload photo as unpublished to get a photo ID
    print("  [fb] Uploading image...")
    with open(meme_path, "rb") as img:
        r1 = requests.post(
            f"{base}/photos",
            files={"source": img},
            data={
                "published": "false",
                "access_token": page_token,
            },
        )
    if r1.status_code not in (200, 201):
        print(f"  [fb] Image upload failed {r1.status_code}: {r1.text[:300]}")
        return
    photo_id = r1.json().get("id")
    print(f"  [fb] Image uploaded → Photo ID: {photo_id}")

    # Step 2 — Create feed post with attached photo
    feed_data = {
        "message": caption,
        "attached_media": json.dumps([{"media_fbid": photo_id}]),
        "access_token": page_token,
    }

    if schedule_dt_str:
        unix_ts = parse_ist_to_unix(schedule_dt_str)
        feed_data["published"] = "false"
        feed_data["scheduled_publish_time"] = unix_ts
        action = f"Scheduling for {schedule_dt_str} IST"
    else:
        feed_data["published"] = "true"
        action = "Publishing now"

    print(f"  [fb] {action}...")
    r2 = requests.post(f"{base}/feed", data=feed_data)

    if r2.status_code in (200, 201):
        post_id = r2.json().get("id")
        if schedule_dt_str:
            print(f"  [fb] Scheduled successfully → Post ID: {post_id}")
        else:
            print(f"  [fb] Published successfully → Post ID: {post_id}")
    else:
        print(f"  [fb] Post failed {r2.status_code}: {r2.text[:300]}")


if __name__ == "__main__":
    slug = input("Enter slug: ").strip()
    mode = input("Publish now or schedule? (now/schedule): ").strip().lower()
    if mode == "schedule":
        scheduled_dt = input("Enter scheduled datetime IST (YYYY-MM-DD HH:MM): ").strip()
        post_to_facebook(slug, scheduled_dt)
    else:
        post_to_facebook(slug)
