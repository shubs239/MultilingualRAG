import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_PASSWORD = os.getenv("WP_PASSWORD")


def parse_ist_to_unix(dt_str):
    """Parse 'YYYY-MM-DD HH:MM' as IST, return UTC Unix timestamp."""
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M")
    dt_ist = ist.localize(dt)
    return int(dt_ist.timestamp())


def get_wp_token():
    auth_url = "https://castefreeindia.com/wp-json/api/v1/token"
    r = requests.post(auth_url, data={"username": WP_USERNAME, "password": WP_PASSWORD})
    token = r.json().get("jwt_token")
    if not token:
        print("  [ig] WordPress authentication failed.")
    return token


def upload_image_to_wp(token, local_path):
    filename = os.path.basename(local_path)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "image/png",
    }
    media_url = "https://castefreeindia.com/wp-json/wp/v2/media"
    with open(local_path, "rb") as f:
        r = requests.post(media_url, headers=headers, data=f)
    if r.status_code in (200, 201):
        source_url = r.json().get("source_url")
        print(f"  [ig] Uploaded to WordPress → {source_url}")
        return source_url
    print(f"  [ig] WP upload failed {r.status_code}: {r.text[:200]}")
    return None


def post_to_instagram(slug, schedule_dt_str=None):
    """
    Post quote card + Instagram caption via Meta Graph API.
    schedule_dt_str: 'YYYY-MM-DD HH:MM' IST — if None, publishes immediately.
    Note: Instagram scheduling requires time to be 10 min–30 days in the future.
    """
    social_path = f"social_output/{slug}.json"
    if not os.path.exists(social_path):
        print(f"  [ig] social_output/{slug}.json not found. Run reedit_post.py and image_gen.py first.")
        return

    with open(social_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    caption = data.get("instagram", {}).get("caption_full", "")
    quote_path = data.get("social_images", {}).get("quote_card", "")

    if not caption:
        print("  [ig] No Instagram caption found in social_output.")
        return
    if not quote_path or not os.path.exists(quote_path):
        print(f"  [ig] Quote card image not found at: {quote_path}")
        return

    # Upload quote card to WordPress to get a public URL (IG requires public URL)
    wp_token = get_wp_token()
    if not wp_token:
        return
    image_url = upload_image_to_wp(wp_token, quote_path)
    if not image_url:
        return

    base_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}"

    # Step 1 — Create media container
    container_params = {
        "image_url": image_url,
        "caption": caption,
        "media_type": "IMAGE",
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }

    if schedule_dt_str:
        unix_ts = parse_ist_to_unix(schedule_dt_str)
        container_params["published"] = "false"
        container_params["scheduled_publish_time"] = unix_ts
        action = f"Scheduling for {schedule_dt_str} IST"
    else:
        action = "Publishing now"

    print(f"  [ig] {action}...")

    r1 = requests.post(f"{base_url}/media", params=container_params)
    if r1.status_code not in (200, 201):
        print(f"  [ig] Container creation failed {r1.status_code}: {r1.text[:300]}")
        return
    creation_id = r1.json().get("id")
    print(f"  [ig] Media container created → ID: {creation_id}")

    # Step 2 — Publish the container
    r2 = requests.post(
        f"{base_url}/media_publish",
        params={
            "creation_id": creation_id,
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        },
    )
    if r2.status_code in (200, 201):
        publish_id = r2.json().get("id")
        if schedule_dt_str:
            print(f"  [ig] Scheduled successfully → Publish ID: {publish_id}")
        else:
            print(f"  [ig] Published successfully → Publish ID: {publish_id}")
    else:
        print(f"  [ig] Publish failed {r2.status_code}: {r2.text[:300]}")


if __name__ == "__main__":
    slug = input("Enter slug: ").strip()
    mode = input("Publish now or schedule? (now/schedule): ").strip().lower()
    if mode == "schedule":
        scheduled_dt = input("Enter scheduled datetime IST (YYYY-MM-DD HH:MM): ").strip()
        post_to_instagram(slug, scheduled_dt)
    else:
        post_to_instagram(slug)
