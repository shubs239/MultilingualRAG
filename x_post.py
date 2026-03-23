"""
x_post.py — Post X (Twitter) thread from social_output/{slug}.json

Standalone: python x_post.py (prompts for slug)
Importable:  from x_post import post_x_thread; post_x_thread(slug)

Requires in .env:
    TWITTER_API_KEY
    TWITTER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN_SECRET
"""
import json
import os
import tweepy
from dotenv import load_dotenv

load_dotenv()


def _get_client():
    return tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )


def post_x_thread(slug: str) -> None:
    social_path = f"social_output/{slug}.json"
    if not os.path.exists(social_path):
        print(f"  [x] social_output/{slug}.json not found. Run reedit_post.py first.")
        return

    with open(social_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hook = data.get("x", {}).get("hook", "")
    thread = data.get("x", {}).get("thread", [])

    if not hook:
        print("  [x] No X hook found in social_output.")
        return

    client = _get_client()

    # Post hook (first tweet)
    try:
        resp = client.create_tweet(text=hook)
        prev_id = resp.data["id"]
        print(f"  [x] Hook posted → https://x.com/i/web/status/{prev_id}")
    except Exception as e:
        print(f"  [x] Failed to post hook: {e}")
        return

    # Post each reply in the thread
    for tweet in thread:
        try:
            resp = client.create_tweet(
                text=tweet,
                reply={"in_reply_to_tweet_id": prev_id},
            )
            prev_id = resp.data["id"]
            print(f"  [x] Reply posted  → https://x.com/i/web/status/{prev_id}")
        except Exception as e:
            print(f"  [x] Failed to post reply: {e}")
            # Continue to next tweet — don't abort entire thread


if __name__ == "__main__":
    slug = input("Enter slug: ").strip()
    post_x_thread(slug)
