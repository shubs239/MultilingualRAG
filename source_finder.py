import json
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment

# Domain preference lists per claim type
GOVERNMENT_DOMAINS = ["ncrb.gov.in", "data.gov.in", "pib.gov.in", "mospi.gov.in", ".gov.in"]
NEWS_DOMAINS = [
    "thehindu.com", "indianexpress.com", "scroll.in", "thewire.in",
    "bhaskar.com", "newslaundry.com", "caravanmagazine.in", "themooknayak.com",
]
RESEARCH_DOMAINS = [
    "scholar.google", "jstor.org", "epw.in", "britannica.com", "researchgate.net", "academia.edu", "books.google"
]

# Map types that Gemini might emit → search strategy
# "archive" / "government" / "news" / "research" / "book_unavailable" are from the spec.
# "legal_ruling" / "legal_precedent" / "administrative_fact" / "commentary" are real-world
# types Gemini currently outputs — mapped to the best domain list here.
TYPE_DOMAIN_MAP = {
    "government": GOVERNMENT_DOMAINS,
    "legal_ruling": NEWS_DOMAINS,       # SC rulings are best found on news/legal sites
    "legal_precedent": RESEARCH_DOMAINS,
    "administrative_fact": GOVERNMENT_DOMAINS,
    "news": NEWS_DOMAINS,
    "research": RESEARCH_DOMAINS,
    "commentary": NEWS_DOMAINS,
}


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def search_archive(query: str) -> str | None:
    """Search Archive.org for a text query and return the best result URL."""
    try:
        params = {
            "q": query,
            "fl[]": "identifier",
            "rows": 5,
            "output": "json",
        }
        resp = requests.get(
            "https://archive.org/advancedsearch.php",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
        if docs:
            return f"https://archive.org/details/{docs[0]['identifier']}"
    except Exception as e:
        print(f"  [archive] Search failed: {e}")
    return None


def search_duckduckgo(query: str, preferred_domains: list[str]) -> str | None:
    """
    Search DuckDuckGo and return the first URL that matches a preferred domain.
    Falls back to the first result if no preferred domain matches.
    """
    # Domains that are useless as citation sources
    BLOCKLIST = ["baidu.com", "quora.com", "youtube.com", "reddit.com", "facebook.com","wikipedia.org"]

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=15))

        if not results:
            return None

        # Filter out blocked domains
        results = [r for r in results if not any(b in r.get("href", "") for b in BLOCKLIST)]
        if not results:
            return None

        # Try preferred domains in priority order
        for domain in preferred_domains:
            for r in results:
                href = r.get("href", "")
                if domain in href:
                    return href

        # Fallback: first non-blocked result
        return results[0].get("href")

    except Exception as e:
        print(f"  [ddg] Search failed for '{query}': {e}")
        return None


# ---------------------------------------------------------------------------
# HTML insertion helpers
# ---------------------------------------------------------------------------

def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


_STOPWORDS = {
    "a", "an", "the", "is", "in", "of", "that", "this", "it", "to", "and",
    "or", "for", "on", "at", "by", "with", "was", "are", "as", "from", "be",
    "has", "had", "have", "he", "she", "they", "we", "you", "i", "its", "their",
    "which", "who", "not", "but", "so", "if", "also", "into", "than", "been",
    "were", "will", "would", "could", "should", "do", "did", "does", "more",
    "about", "over", "such", "these", "those", "can", "may", "said", "says",
}


def _find_best_paragraph(paragraphs, claim_text: str):
    """
    Score each <p> tag by how many significant words from claim_text it contains.
    Returns the index of the best match (min 2 word matches), or None.
    """
    words = [w for w in claim_text.lower().split() if w.isalpha() and w not in _STOPWORDS]
    if not words:
        return None

    best_idx, best_score = None, 0
    for i, p in enumerate(paragraphs):
        p_text = p.get_text().lower()
        score = sum(1 for w in words if w in p_text)
        if score > best_score:
            best_score, best_idx = score, i

    return best_idx if best_score >= 2 else None


def insert_link_at_paragraph(html: str, paragraph_num: int, url: str, claim_text: str = "") -> str:
    """
    Insert a [source] superscript link into the best-matching paragraph.
    Uses semantic word matching against claim_text when provided; falls back
    to position-based (paragraph_num, 1-indexed).
    Returns the modified HTML string.
    """
    soup = BeautifulSoup(html, "lxml")
    paragraphs = soup.find_all("p")

    if not paragraphs:
        return html

    # Try semantic match first
    idx = _find_best_paragraph(paragraphs, claim_text) if claim_text else None
    # Fall back to position-based
    if idx is None:
        idx = max(0, min(paragraph_num - 1, len(paragraphs) - 1))

    target = paragraphs[idx]

    # Build <sup><a href="..." target="_blank" rel="noopener">[source]</a></sup>
    sup = soup.new_tag("sup")
    a = soup.new_tag("a", href=url, target="_blank", rel="noopener")
    a.string = "[source]"
    sup.append(a)
    target.append(sup)

    return str(soup)


def insert_book_unavailable_comment(html: str, paragraph_num: int, claim_text: str) -> str:
    """
    Append an HTML comment placeholder after the target paragraph
    for book_unavailable claims.
    """
    soup = BeautifulSoup(html, "lxml")
    paragraphs = soup.find_all("p")

    if not paragraphs:
        return html

    idx = max(0, min(paragraph_num - 1, len(paragraphs) - 1))
    target = paragraphs[idx]

    comment_text = f" SCREENSHOT: {claim_text[:120]} — add screenshot here "
    comment = Comment(comment_text)
    target.insert_after(comment)

    return str(soup)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def process_claims(slug: str = None, input_file: str = None) -> None:
    if input_file is None:
        if slug is None:
            from utils import get_latest_slug
            slug = get_latest_slug("final_output")
        input_file = f"final_output/{slug}.json"
    print(f"Loading {input_file} …")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = data.get("sourcing", {}).get("claims_needing_citation", [])
    if not claims:
        print("No claims found in sourcing.claims_needing_citation — nothing to do.")
        return

    html = data["content"]["blog_post_html"]
    results = []

    for i, claim in enumerate(claims, 1):
        claim_text = claim.get("claim", "")
        claim_type = claim.get("type", "")
        query = claim.get("suggested_search", claim_text[:120])
        paragraph_num = claim.get("insert_after_paragraph", 1)

        print(f"\n[{i}/{len(claims)}] type={claim_type}")
        print(f"  query: {query[:80]}")

        url = None

        if claim_type == "archive":
            url = search_archive(query)

        elif claim_type == "book_unavailable":
            html = insert_book_unavailable_comment(html, paragraph_num, claim_text)
            results.append({
                "claim": claim_text,
                "type": claim_type,
                "source_found": False,
                "url": "",
                "domain": "",
                "inserted_at_paragraph": paragraph_num,
            })
            print("  → book_unavailable: inserted HTML comment placeholder")
            continue

        else:
            # Map the type to a domain preference list
            preferred = TYPE_DOMAIN_MAP.get(claim_type, [])
            url = search_duckduckgo(query, preferred)

        if url:
            print(f"  → found: {url[:80]}")
            html = insert_link_at_paragraph(html, paragraph_num, url, claim_text=claim_text)
            results.append({
                "claim": claim_text,
                "type": claim_type,
                "source_found": True,
                "url": url,
                "domain": _get_domain(url),
                "inserted_at_paragraph": paragraph_num,
            })
        else:
            print("  → no source found, skipping link insertion")
            results.append({
                "claim": claim_text,
                "type": claim_type,
                "source_found": False,
                "url": "",
                "domain": "",
                "inserted_at_paragraph": paragraph_num,
            })

        # Be polite to external services
        time.sleep(1.5)

    # Write updated HTML back
    data["content"]["blog_post_html"] = html

    # Merge sourcing_results block
    data["sourcing_results"] = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "claims": results,
    }

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    found = sum(1 for r in results if r["source_found"])
    print(f"\nDone. {found}/{len(results)} claims sourced. {input_file} updated.")


if __name__ == "__main__":
    process_claims()
