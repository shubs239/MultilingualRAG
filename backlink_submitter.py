"""
backlink_submitter.py — Submit post URLs to Google Indexing API + ping services.

Usage:
  python backlink_submitter.py          # asks for URL, submits single post
  python backlink_submitter.py --bulk   # submits all 105+ published WP posts (run once)
"""

import json
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

WP_POSTS_API = "https://castefreeindia.com/wp-json/wp/v2/posts"
INDEXING_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"

BLOG_NAME = "CasteFreeIndia"
BLOG_URL = "https://castefreeindia.com/"
BLOG_RSS = "https://castefreeindia.com/feed/"

PING_SERVICES = [
    ("Pingomatic",         "http://rpc.pingomatic.com/"),
    ("Yandex",             "http://ping.blogs.yandex.ru/RPC2"),
    ("Google Blog Search", "http://blogsearch.google.com/ping/RPC2"),
]


# ─── Google Indexing API ──────────────────────────────────────────────────────

def _get_google_session():
    """Return an authorized Google session, or None if credentials unavailable."""
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as g_requests
    except ImportError:
        print("[google] google-auth not installed — run: pip install google-auth")
        return None

    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_file or not os.path.exists(sa_file):
        print(f"[google] Service account file not found: {sa_file!r} — skipping Google step.")
        return None

    scopes = ["https://www.googleapis.com/auth/indexing"]
    creds = service_account.Credentials.from_service_account_file(sa_file, scopes=scopes)
    return g_requests.AuthorizedSession(creds)


def _submit_google(session, url: str) -> dict:
    if session is None:
        return {"status": "skipped", "reason": "no credentials"}
    r = session.post(INDEXING_ENDPOINT, json={"url": url, "type": "URL_UPDATED"})
    if r.status_code == 200:
        print(f"  [google] ✓ submitted")
        return {"status": "ok", "response": r.json()}
    print(f"  [google] ✗ {r.status_code}: {r.text[:200]}")
    return {"status": "error", "code": r.status_code, "body": r.text[:500]}


# ─── XML-RPC Pings ────────────────────────────────────────────────────────────

_PING_XML = """<?xml version="1.0"?>
<methodCall>
  <methodName>weblogUpdates.extendedPing</methodName>
  <params>
    <param><value><string>{blog_name}</string></value></param>
    <param><value><string>{blog_url}</string></value></param>
    <param><value><string>{post_url}</string></value></param>
    <param><value><string>{rss_url}</string></value></param>
  </params>
</methodCall>"""


def _ping_services(post_url: str) -> list:
    body = _PING_XML.format(
        blog_name=BLOG_NAME, blog_url=BLOG_URL,
        post_url=post_url, rss_url=BLOG_RSS,
    ).encode("utf-8")
    headers = {"Content-Type": "text/xml"}
    results = []
    for name, endpoint in PING_SERVICES:
        try:
            r = requests.post(endpoint, data=body, headers=headers, timeout=10)
            print(f"  [ping]   {name}: {r.status_code}")
            results.append({"service": name, "status_code": r.status_code})
        except Exception as e:
            print(f"  [ping]   {name}: skipped ({e})")
            results.append({"service": name, "status_code": "skipped", "error": str(e)})
    return results


# ─── WordPress REST API ───────────────────────────────────────────────────────

def _get_wp_token() -> str | None:
    """Get a JWT Bearer token from WordPress."""
    WP_USERNAME = os.getenv("WP_USERNAME")
    WP_PASSWORD = os.getenv("WP_PASSWORD")
    r = requests.post(
        "https://castefreeindia.com/wp-json/api/v1/token",
        data={"username": WP_USERNAME, "password": WP_PASSWORD},
        timeout=15,
    )
    token = r.json().get("jwt_token")
    if not token:
        print(f"[wp] Auth failed: {r.text[:200]}")
    return token


def _get_all_published_urls() -> list:
    """Paginate through WP REST API and return all published post URLs."""
    token = _get_wp_token()
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    urls = []
    page = 1
    while True:
        r = requests.get(
            WP_POSTS_API,
            params={"status": "publish", "per_page": 100, "page": page, "_fields": "link"},
            headers=headers,
            timeout=30,
        )
        if r.status_code not in (200, 201):
            break
        batch = r.json()
        if not batch:
            break
        urls.extend(p["link"] for p in batch)
        print(f"[wp] Page {page} fetched — {len(urls)} posts so far")
        page += 1
    return urls


# ─── Log helper ───────────────────────────────────────────────────────────────

def _save_log(path: str, data: dict) -> None:
    os.makedirs("backlink_log", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\n[backlink] Log saved → {path}")


# ─── Modes ────────────────────────────────────────────────────────────────────

def submit_single() -> None:
    url = input(
        "\nEnter the full post URL to submit\n"
        "(e.g. https://castefreeindia.com/your-post-slug/): "
    ).strip()
    if not url:
        print("No URL entered. Exiting.")
        sys.exit(1)

    print(f"\n[backlink] Submitting: {url}\n")
    session = _get_google_session()
    google_result = _submit_google(session, url)
    ping_results = _ping_services(url)

    slug = url.rstrip("/").rsplit("/", 1)[-1] or "unknown"
    _save_log(f"backlink_log/{slug}.json", {
        "url": url,
        "submitted_at": datetime.utcnow().isoformat() + "Z",
        "google": google_result,
        "pings": ping_results,
    })
    print("[backlink] Done.")


def submit_bulk() -> None:
    print("\n[backlink] Bulk mode — fetching all published posts from WordPress...\n")
    urls = _get_all_published_urls()
    if not urls:
        print("[backlink] No published posts found. Check WP REST API.")
        return

    print(f"\n[backlink] {len(urls)} posts found. Submitting to Google + pinging...\n")
    session = _get_google_session()
    results = []

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        google_result = _submit_google(session, url)
        ping_results = _ping_services(url)
        results.append({
            "url": url,
            "google": google_result,
            "pings": ping_results,
        })
        if i < len(urls):
            time.sleep(1)  # Google Indexing API rate limit

    _save_log("backlink_log/bulk_run.json", {
        "submitted_at": datetime.utcnow().isoformat() + "Z",
        "total": len(urls),
        "results": results,
    })
    print(f"[backlink] Bulk done — {len(urls)} URLs submitted.")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--bulk" in sys.argv:
        submit_bulk()
    else:
        submit_single()
