"""
utils.py — shared helpers used across the CasteFreeIndia pipeline
"""

import os
import re


def make_slug(h1: str) -> str:
    """Convert a blog_h1 headline into a URL/filename-safe slug."""
    slug = h1.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def get_latest_slug(folder: str) -> str:
    """
    Return the slug (filename without .json) of the most recently
    modified JSON file in `folder`. Used when a script is run standalone
    without an explicit slug argument.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder '{folder}' does not exist.")
    files = [f for f in os.listdir(folder) if f.endswith(".json")]
    if not files:
        raise FileNotFoundError(f"No JSON files found in '{folder}/'")
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    return latest[:-5]  # strip .json extension


def get_search_suggestions(query: str) -> list:
    """Fetch Google autocomplete suggestions. Returns up to 5 English-only results. Never raises."""
    try:
        import requests
        url = "http://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "q": query, "hl": "en"}
        r = requests.get(url, params=params, timeout=5)
        suggestions = r.json()[1][:5]
        return [s for s in suggestions if all(ord(c) < 128 for c in s)]
    except Exception:
        return []


def extract_search_topic(h1: str, gemini_client) -> str:
    """Extract 2-4 word searchable topic from headline via Gemini. Falls back to first 4 words."""
    try:
        prompt = (
            f"Extract the core searchable topic from this headline "
            f"as 2-4 words for a Google search query. "
            f"Return only the query string, nothing else.\n"
            f"Headline: {h1}"
        )
        response = gemini_client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt
        )
        return response.text.strip().lower()
    except Exception:
        return " ".join(h1.split()[:4]).lower()
