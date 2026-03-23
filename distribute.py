"""
distribute.py — One-shot post distribution after WordPress publish.

Run: python distribute.py
Asks for slug → checks/generates social copy → posts to X, Facebook, Instagram.
"""
import json
import os

from reedit_post import create_social_media_post
from x_post import post_x_thread
from facebook_post import post_to_facebook
from instagram_post import post_to_instagram


def _social_output_complete(slug: str) -> bool:
    """Return True if social_output/{slug}.json exists with x, facebook, instagram keys."""
    path = f"social_output/{slug}.json"
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return all(k in data for k in ("x", "facebook", "instagram"))


def distribute(slug: str) -> None:
    if not _social_output_complete(slug):
        print("[distribute] Social copy not found — generating now...")
        create_social_media_post(slug)

    print(f"\n[distribute] Distributing: {slug}\n")

    print("[X] Posting thread...")
    try:
        post_x_thread(slug)
    except Exception as e:
        print(f"  [x] Error: {e}")

    print("\n[Facebook] Posting...")
    try:
        post_to_facebook(slug)
    except Exception as e:
        print(f"  [fb] Error: {e}")

    print("\n[Instagram] Posting...")
    try:
        post_to_instagram(slug)
    except Exception as e:
        print(f"  [ig] Error: {e}")

    print("\n[distribute] Done.")


if __name__ == "__main__":
    slug = input("Enter slug: ").strip()
    distribute(slug)
