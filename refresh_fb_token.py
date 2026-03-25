"""
refresh_fb_token.py — One-time tool to get a never-expiring Facebook Page Access Token.

How it works:
  1. You paste a short-lived User Access Token (from Meta Graph API Explorer)
  2. This script exchanges it for a long-lived user token (60 days)
  3. Then fetches the Page Access Token from that — this one NEVER expires
  4. Updates FACEBOOK_PAGE_ACCESS_TOKEN in your .env automatically

Run:
  python refresh_fb_token.py

When to run again:
  Never — unless you revoke app permissions or rotate the app secret.
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = "2310811919414018"
APP_SECRET = "2e7b5a3fd689605e51bac055e4a1fc06"
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "951818741358386")
GRAPH = "https://graph.facebook.com/v19.0"


def exchange_for_long_lived(short_token: str) -> str | None:
    """Exchange short-lived user token → long-lived user token (60 days)."""
    r = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        },
    )
    data = r.json()
    if "access_token" not in data:
        print(f"[fb] Failed to get long-lived token: {data}")
        return None
    expires = data.get("expires_in", "unknown")
    print(f"[fb] Long-lived user token obtained (expires in {expires}s ≈ 60 days)")
    return data["access_token"]


def get_never_expiring_page_token(long_lived_user_token: str) -> str | None:
    """Exchange long-lived user token → Page Access Token (never expires)."""
    r = requests.get(
        f"{GRAPH}/{PAGE_ID}",
        params={
            "fields": "access_token",
            "access_token": long_lived_user_token,
        },
    )
    data = r.json()
    if "access_token" not in data:
        print(f"[fb] Failed to get page token: {data}")
        return None
    print(f"[fb] Page Access Token obtained — this one never expires.")
    return data["access_token"]


def patch_env(key: str, value: str) -> None:
    """Replace the value of a key in .env file."""
    env_path = ".env"
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = rf'^({re.escape(key)}=).*$'
    new_line = f'{key}="{value}"'
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content += f'\n{new_line}\n'

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[env] Updated {key} in .env")


if __name__ == "__main__":
    print("=" * 60)
    print("Facebook Page Access Token — One-Time Setup")
    print("=" * 60)
    print("""
Steps to get a short-lived User Access Token:
  1. Go to https://developers.facebook.com/tools/explorer/
  2. Select your App (CasteFreeIndia / app ID 2310811919414018)
  3. Click 'Generate Access Token'
  4. Grant permissions: pages_manage_posts, pages_read_engagement,
     pages_show_list, instagram_basic, instagram_content_publish
  5. Copy the token and paste below
""")

    short_token = input("Paste your short-lived User Access Token: ").strip()
    if not short_token:
        print("No token entered. Exiting.")
        exit(1)

    print("\n[fb] Exchanging for long-lived token...")
    long_token = exchange_for_long_lived(short_token)
    if not long_token:
        exit(1)

    print("[fb] Fetching never-expiring Page Access Token...")
    page_token = get_never_expiring_page_token(long_token)
    if not page_token:
        exit(1)

    patch_env("FACEBOOK_PAGE_ACCESS_TOKEN", page_token)

    print("\n✓ Done! Your .env has been updated.")
    print("  facebook_post.py and instagram_post.py will use the new token automatically.")
    print("  You never need to refresh this token again.")
