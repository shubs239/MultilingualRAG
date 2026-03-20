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
