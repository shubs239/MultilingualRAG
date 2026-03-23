"""
wiki_finder.py — Weekly Wikipedia opportunity scanner for castefreeindia.com

Run manually once a week: python wiki_finder.py

How it works:
  1. Fetch published WP posts → cache/post_index.json (refreshed if >7 days old)
  2. Extract Wikipedia-searchable entities from each post via Gemini
     → cache/wiki_topics_cache.json (incremental: only new posts each week)
  3. Confirm each topic has a Wikipedia page
     → cache/wiki_pages_cache.json (30-day expiry per entry)
  4. Scan confirmed pages for {{citation needed}} tags in wikitext
  5. TF-IDF cosine similarity: match claims to your posts (threshold 0.35)
  6. Generate pre-formatted citation markup + edit URLs + instructions
     → wiki_opportunities.json (sorted by relevance, top opportunities first)

IMPORTANT: This script does NOT edit Wikipedia. It only does research.
           You do the 3-minute copy-paste edits manually.
"""

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import numpy
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()
API_KEY     = os.getenv("API_KEY")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_PASSWORD = os.getenv("WP_PASSWORD")
WP_BASE     = "https://castefreeindia.com/wp-json"

CACHE_DIR              = "cache"
POST_INDEX_PATH        = os.path.join(CACHE_DIR, "post_index.json")
WIKI_TOPICS_CACHE_PATH = os.path.join(CACHE_DIR, "wiki_topics_cache.json")
WIKI_PAGES_CACHE_PATH  = os.path.join(CACHE_DIR, "wiki_pages_cache.json")
OUTPUT_PATH            = "wiki_opportunities.json"

POST_INDEX_MAX_AGE_DAYS   = 7
WIKI_PAGES_CACHE_MAX_DAYS = 30
MIN_RELEVANCE             = 0.35
WIKI_API_DELAY            = 0.5   # seconds between Wikipedia API calls
MIN_CLAIM_LEN             = 30    # skip claims shorter than this

WIKIPEDIA_API    = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_HEADERS = {
    "User-Agent": "CasteFreeIndia-WikiFinder/1.0 (https://castefreeindia.com; contact@castefreeindia.com) python-requests"
}

client = genai.Client(api_key=API_KEY)

STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of",
    "with","is","are","was","were","be","been","have","has","had",
    "do","does","did","will","would","could","should","may","might",
    "that","this","it","its","they","them","their","we","our","i",
    "my","he","she","his","her","as","by","from","not","no","if",
    "so","than","then","what","which","who","how","when","where",
    "about","into","through","after","before","also","more","such",
    "all","any","each","other","these","those",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_json(path: str, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def strip_html(html: str) -> str:
    return BeautifulSoup(html, "lxml").get_text(" ")


def tokenize(text: str) -> list:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if t not in STOP_WORDS and len(t) >= 3]


def build_tfidf_matrix(documents: list) -> tuple:
    """Returns (tfidf_matrix, vocab_list). Rows are L2-normalised."""
    tokenized = [tokenize(d) for d in documents]
    N = len(tokenized)
    vocab = sorted(set(tok for doc in tokenized for tok in doc))
    vocab_index = {w: i for i, w in enumerate(vocab)}
    V = len(vocab)
    if V == 0:
        return numpy.zeros((N, 1)), []
    tf = numpy.zeros((N, V), dtype=float)
    for di, tokens in enumerate(tokenized):
        if not tokens:
            continue
        for tok in tokens:
            tf[di, vocab_index[tok]] += 1
        tf[di] /= len(tokens)
    df = numpy.count_nonzero(tf, axis=0)
    idf = numpy.log((1 + N) / (1 + df)) + 1
    tfidf = tf * idf
    norms = numpy.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1
    tfidf /= norms
    return tfidf, vocab


# ── Step 0: Fetch / load post index ───────────────────────────────────────────

def get_wp_token() -> str:
    r = requests.post(
        f"{WP_BASE}/api/v1/token",
        data={"username": WP_USERNAME, "password": WP_PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    token = r.json().get("jwt_token")
    if not token:
        raise ValueError("No jwt_token in auth response")
    return token


def fetch_all_posts(token: str) -> list:
    headers = {"Authorization": f"Bearer {token}"}
    posts, page = [], 1
    while True:
        r = requests.get(
            f"{WP_BASE}/wp/v2/posts",
            params={"status": "publish", "per_page": 100, "page": page},
            headers=headers,
            timeout=15,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def load_post_index() -> list:
    """Return cached post index, refreshing if older than POST_INDEX_MAX_AGE_DAYS."""
    cache = load_json(POST_INDEX_PATH, None)
    if cache:
        fetched_at = datetime.fromisoformat(cache.get("fetched_at", "2000-01-01T00:00:00+00:00"))
        age = datetime.now(timezone.utc) - fetched_at
        if age < timedelta(days=POST_INDEX_MAX_AGE_DAYS):
            print(f"[post_index] Using cached index ({len(cache['posts'])} posts, "
                  f"{age.days}d old)")
            return cache["posts"]

    print("[post_index] Fetching fresh post list from WordPress...")
    try:
        token = get_wp_token()
        raw_posts = fetch_all_posts(token)
    except Exception as e:
        print(f"[post_index] WP fetch failed: {e}")
        if cache:
            print("[post_index] Falling back to stale cache")
            return cache["posts"]
        raise

    posts = []
    for p in raw_posts:
        slug = p.get("slug", "")
        title = BeautifulSoup(
            p.get("title", {}).get("rendered", ""), "lxml"
        ).get_text()
        excerpt = BeautifulSoup(
            p.get("excerpt", {}).get("rendered", ""), "lxml"
        ).get_text()
        link = p.get("link", f"https://castefreeindia.com/{slug}/")
        modified = p.get("modified_gmt", p.get("date_gmt", ""))
        posts.append({
            "slug": slug,
            "title": title,
            "excerpt": excerpt,
            "url": link,
            "modified_gmt": modified,
        })

    save_json(POST_INDEX_PATH, {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "posts": posts,
    })
    print(f"[post_index] Saved {len(posts)} posts to cache")
    return posts


# ── Step 1: Extract Wikipedia-searchable topics ───────────────────────────────

def extract_topics_for_post(post: dict) -> list:
    """Call Gemini to extract Wikipedia-searchable entities from a post."""
    prompt = (
        "Extract 3-5 named entities and key concepts from this blog post "
        "that are likely to have their own Wikipedia page. "
        "Return ONLY a JSON array of strings, no explanation.\n"
        "Examples: people (B. R. Ambedkar), texts (Manusmriti), "
        "events (Poona Pact), concepts (varna system), "
        "organisations (Constituent Assembly of India).\n"
        "Only include entities specific enough to have a dedicated Wikipedia page. "
        "Do not include generic terms like 'caste' or 'discrimination' alone.\n\n"
        f"Title: {post['title']}\n"
        f"Excerpt: {post['excerpt']}"
    )
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        topics = json.loads(text)
        if isinstance(topics, list):
            return [str(t).strip() for t in topics if t]
    except Exception as e:
        print(f"  [topics] Gemini failed for '{post['slug']}': {e}")
    return []


def load_topics_for_posts(posts: list) -> dict:
    """
    Return {slug: [topic, ...]} for all posts.
    Incremental: only call Gemini for posts not yet cached.
    """
    cache = load_json(WIKI_TOPICS_CACHE_PATH, {})
    updated = False

    for post in posts:
        slug = post["slug"]
        modified = post.get("modified_gmt", "")
        cached = cache.get(slug, {})
        # Re-process if post was modified since last extraction
        if cached and cached.get("modified_gmt") == modified:
            continue
        print(f"  [topics] Extracting topics for: {post['title'][:60]}")
        topics = extract_topics_for_post(post)
        cache[slug] = {
            "topics": topics,
            "modified_gmt": modified,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        updated = True
        time.sleep(0.2)  # small pause between Gemini calls

    if updated:
        save_json(WIKI_TOPICS_CACHE_PATH, cache)
        print(f"[topics] Cache updated — {len(cache)} posts processed")
    else:
        print(f"[topics] All {len(cache)} posts already cached — no new Gemini calls")

    # Build deduplicated topic list: topic → [post_slug, ...]
    topic_to_slugs: dict = {}
    for slug, data in cache.items():
        for topic in data.get("topics", []):
            topic_lower = topic.lower()
            if topic_lower not in topic_to_slugs:
                topic_to_slugs[topic_lower] = {"canonical": topic, "slugs": []}
            if slug not in topic_to_slugs[topic_lower]["slugs"]:
                topic_to_slugs[topic_lower]["slugs"].append(slug)

    print(f"[topics] {len(topic_to_slugs)} unique topics across all posts")
    return topic_to_slugs


# ── Step 2: Confirm Wikipedia pages exist ────────────────────────────────────

def is_cache_fresh(entry: dict, max_days: int) -> bool:
    ts = entry.get("cached_at")
    if not ts:
        return False
    age = datetime.now(timezone.utc) - datetime.fromisoformat(ts)
    return age < timedelta(days=max_days)


def search_wikipedia_page(topic: str) -> str | None:
    """Return the canonical Wikipedia page title for a topic, or None."""
    try:
        r = requests.get(
            WIKIPEDIA_API,
            params={"action": "query", "list": "search",
                    "srsearch": topic, "format": "json", "srlimit": 1},
            headers=WIKIPEDIA_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            print(f"  [pages] Wikipedia API error for '{topic}': {data['error']}")
            return None
        results = data.get("query", {}).get("search", [])
        if not results:
            return None
        return results[0]["title"]
    except Exception as e:
        print(f"  [pages] Request failed for '{topic}': {e}")
        return None


def load_confirmed_pages(topic_to_slugs: dict) -> dict:
    """
    Return {topic_key: {"page_title": str, "slugs": list}} for all confirmed pages.
    Uses cache/wiki_pages_cache.json with 30-day expiry.
    """
    # Connectivity check before the full loop
    print("  [pages] Testing Wikipedia API connectivity...")
    test_result = search_wikipedia_page("B. R. Ambedkar")
    if test_result is None:
        print("  [pages] WARNING: Test lookup for 'B. R. Ambedkar' returned None.")
        print("  [pages] Check your internet connection or Wikipedia API access.")
    else:
        print(f"  [pages] Connectivity OK — test result: '{test_result}'")

    cache = load_json(WIKI_PAGES_CACHE_PATH, {})
    confirmed = {}
    new_lookups = 0

    total_topics = len(topic_to_slugs)
    for idx, (topic_key, info) in enumerate(topic_to_slugs.items(), 1):
        canonical_topic = info["canonical"]

        if topic_key in cache and is_cache_fresh(cache[topic_key], WIKI_PAGES_CACHE_MAX_DAYS):
            page_title = cache[topic_key].get("page_title")
        else:
            page_title = search_wikipedia_page(canonical_topic)
            cache[topic_key] = {
                "page_title": page_title,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }
            new_lookups += 1
            if idx % 10 == 0 or idx == total_topics:
                print(f"  [pages] {idx}/{total_topics} looked up, {len(confirmed)} confirmed so far...")
            time.sleep(WIKI_API_DELAY)

        if page_title:
            confirmed[topic_key] = {
                "page_title": page_title,
                "slugs": info["slugs"],
            }

    if new_lookups:
        save_json(WIKI_PAGES_CACHE_PATH, cache)
        print(f"[pages] {new_lookups} new Wikipedia lookups; "
              f"{len(confirmed)} pages confirmed")
    else:
        print(f"[pages] All lookups from cache; {len(confirmed)} pages confirmed")

    return confirmed


# ── Step 3: Scan pages for citation-needed tags ───────────────────────────────

def strip_wikitext(text: str) -> str:
    """Remove common wikitext markup to get plain claim text."""
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)  # [[Link|Text]] → Text
    text = re.sub(r"\{\{[^}]*\}\}", "", text)                       # remove templates
    text = re.sub(r"'{2,3}", "", text)                              # remove bold/italic
    text = re.sub(r"<[^>]+>", "", text)                             # remove HTML tags
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_citation_needed_claims(page_title: str) -> list:
    """
    Fetch wikitext for a page and return list of:
      {"section": str, "section_number": int, "claim_text": str}
    for each {{citation needed}} / {{cn}} occurrence.
    """
    try:
        r = requests.get(
            WIKIPEDIA_API,
            params={"action": "parse", "page": page_title,
                    "prop": "wikitext", "format": "json"},
            headers=WIKIPEDIA_HEADERS,
            timeout=15,
        )
        wikitext = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
    except Exception as e:
        print(f"  [scan] Failed to fetch wikitext for '{page_title}': {e}")
        return []

    claims = []
    current_section = "Introduction"
    section_number = 0

    for line in wikitext.split("\n"):
        # Track section headings
        section_match = re.match(r"^(==+)\s*(.+?)\s*\1\s*$", line)
        if section_match:
            current_section = section_match.group(2).strip()
            # Count == level-2 sections only for edit URL numbering
            if len(section_match.group(1)) == 2:
                section_number += 1
            continue

        # Find citation needed tags (case-insensitive)
        if not re.search(r"\{\{\s*(?:citation needed|cn)\s*(?:\|[^}]*)?\}\}", line, re.IGNORECASE):
            continue

        # Extract the claim text: text before the {{citation needed}} tag
        claim_raw = re.split(
            r"\{\{\s*(?:citation needed|cn)\s*(?:\|[^}]*)?\}\}",
            line, flags=re.IGNORECASE
        )[0]
        claim_text = strip_wikitext(claim_raw).strip()

        # Skip very short claims
        if len(claim_text) < MIN_CLAIM_LEN:
            continue

        claims.append({
            "section": current_section,
            "section_number": section_number,
            "claim_text": claim_text,
        })

    return claims


# ── Step 4: Match claims to posts via TF-IDF ─────────────────────────────────

def match_claims_to_posts(claims_by_page: list, posts: list) -> list:
    """
    claims_by_page: list of {page_title, page_url, edit_url, section,
                              section_number, claim_text}
    posts: list of {slug, title, excerpt, url}
    Returns list of opportunity dicts with relevance_score >= MIN_RELEVANCE.
    """
    if not claims_by_page or not posts:
        return []

    claim_texts = [c["claim_text"] for c in claims_by_page]
    post_texts  = [p["title"] + " " + p["excerpt"] for p in posts]

    all_docs = claim_texts + post_texts
    matrix, _ = build_tfidf_matrix(all_docs)

    n_claims = len(claim_texts)
    claim_vecs = matrix[:n_claims]
    post_vecs  = matrix[n_claims:]

    # similarities[i, j] = similarity between claim i and post j
    similarities = numpy.dot(claim_vecs, post_vecs.T)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    opportunities = []

    for i, claim_info in enumerate(claims_by_page):
        best_j = int(numpy.argmax(similarities[i]))
        score  = float(similarities[i, best_j])
        if score < MIN_RELEVANCE:
            continue

        post = posts[best_j]
        citation_markup = (
            f"<ref>{{{{cite web"
            f"|url={post['url']}"
            f"|title={post['title']}"
            f"|website=CasteFreeIndia"
            f"|access-date={today}"
            f"}}}}}}</ref>"
        )
        instructions = (
            f"1. Open the edit URL in your browser.\n"
            f"2. Use Ctrl+F to find this text: \"{claim_info['claim_text'][:60]}...\"\n"
            f"3. Place your cursor immediately after the {{{{citation needed}}}} tag.\n"
            f"4. Delete the {{{{citation needed}}}} tag and replace it with:\n"
            f"   {citation_markup}\n"
            f"5. Click 'Show preview' to verify the citation renders correctly.\n"
            f"6. Add edit summary: 'Added citation from castefreeindia.com'\n"
            f"7. Click 'Publish changes'."
        )
        opportunities.append({
            "wikipedia_page":    claim_info["page_title"],
            "wikipedia_url":     claim_info["page_url"],
            "edit_url":          claim_info["edit_url"],
            "section":           claim_info["section"],
            "claim_text":        claim_info["claim_text"],
            "your_post_title":   post["title"],
            "your_post_url":     post["url"],
            "relevance_score":   round(score, 4),
            "citation_markup":   citation_markup,
            "instructions":      instructions,
        })

    opportunities.sort(key=lambda x: x["relevance_score"], reverse=True)
    return opportunities


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ensure_cache_dir()
    print("\n=== wiki_finder.py — Wikipedia Opportunity Scanner ===\n")

    # Step 0: Load post index
    print("── Step 0: Loading post index ──")
    posts = load_post_index()
    if not posts:
        print("No posts found — aborting.")
        return

    # Step 1: Extract Wikipedia topics
    print("\n── Step 1: Extracting Wikipedia topics from posts ──")
    topic_to_slugs = load_topics_for_posts(posts)
    if not topic_to_slugs:
        print("No topics extracted — aborting.")
        return

    # Step 2: Confirm Wikipedia pages
    print("\n── Step 2: Confirming Wikipedia pages ──")
    confirmed_pages = load_confirmed_pages(topic_to_slugs)
    if not confirmed_pages:
        print("No confirmed Wikipedia pages — aborting.")
        return

    # Step 3: Scan pages for citation-needed tags
    print("\n── Step 3: Scanning Wikipedia pages for citation-needed tags ──")
    all_claims = []
    for topic_key, page_info in confirmed_pages.items():
        page_title = page_info["page_title"]
        page_url   = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
        print(f"  Scanning: {page_title}")
        claims = fetch_citation_needed_claims(page_title)
        for c in claims:
            section_param = f"&section={c['section_number']}" if c["section_number"] else ""
            edit_url = (
                f"https://en.wikipedia.org/w/index.php"
                f"?title={page_title.replace(' ', '_')}"
                f"&action=edit{section_param}"
            )
            all_claims.append({
                "page_title":     page_title,
                "page_url":       page_url,
                "edit_url":       edit_url,
                "section":        c["section"],
                "section_number": c["section_number"],
                "claim_text":     c["claim_text"],
            })
        time.sleep(WIKI_API_DELAY)

    print(f"\n[scan] Found {len(all_claims)} citation-needed claims across "
          f"{len(confirmed_pages)} pages")

    if not all_claims:
        print("No citation-needed claims found — nothing to match.")
        save_json(OUTPUT_PATH, {"generated_at": datetime.now(timezone.utc).isoformat(),
                                "opportunities": []})
        return

    # Step 4 + 5: Match claims to posts and generate output
    print("\n── Step 4: Matching claims to your posts via TF-IDF ──")
    opportunities = match_claims_to_posts(all_claims, posts)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_claims_scanned": len(all_claims),
        "total_pages_scanned": len(confirmed_pages),
        "opportunities_found": len(opportunities),
        "opportunities": opportunities,
    }
    save_json(OUTPUT_PATH, output)

    print(f"\n=== Done ===")
    print(f"  Claims scanned:    {len(all_claims)}")
    print(f"  Pages scanned:     {len(confirmed_pages)}")
    print(f"  Opportunities:     {len(opportunities)}")
    print(f"  Output saved to:   {OUTPUT_PATH}")

    if opportunities:
        print("\nTop 3 opportunities:")
        for opp in opportunities[:3]:
            print(f"  [{opp['relevance_score']:.3f}] {opp['wikipedia_page']} "
                  f"→ '{opp['your_post_title'][:50]}'")
        print("\nOpen wiki_opportunities.json and do the top 3 edits manually.")
        print("Each edit takes ~3 minutes.")


if __name__ == "__main__":
    main()
