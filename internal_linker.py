import json
import os
import re
from datetime import datetime, timezone

import numpy
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ── Constants ─────────────────────────────────────────────────────────────────
WP_BASE   = "https://castefreeindia.com/wp-json"
AUTH_URL  = f"{WP_BASE}/api/v1/token"
POSTS_URL = f"{WP_BASE}/wp/v2/posts"

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

def get_wp_token(username: str, password: str) -> str:
    r = requests.post(AUTH_URL, data={"username": username, "password": password})
    r.raise_for_status()
    token = r.json().get("jwt_token")
    if not token:
        raise ValueError("No jwt_token in auth response")
    return token


def fetch_published_posts(token: str, per_page: int = 100) -> list:
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{POSTS_URL}?status=publish&per_page={per_page}", headers=headers)
    if r.status_code != 200:
        print(f"  [linker] Could not fetch posts: {r.status_code}")
        return []
    return r.json()


def strip_html(html: str) -> str:
    return BeautifulSoup(html, "lxml").get_text(" ")


def tokenize(text: str) -> list:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if t not in STOP_WORDS and len(t) >= 3]


def build_tfidf_matrix(documents: list) -> tuple:
    """
    Returns (tfidf_matrix, vocab_list).
    tfidf_matrix shape: (n_docs, n_vocab), L2-normalised rows.
    """
    tokenized = [tokenize(d) for d in documents]
    N = len(tokenized)

    # Build vocabulary
    vocab = sorted(set(tok for doc in tokenized for tok in doc))
    vocab_index = {w: i for i, w in enumerate(vocab)}
    V = len(vocab)

    if V == 0:
        return numpy.zeros((N, 1)), []

    # TF matrix
    tf = numpy.zeros((N, V), dtype=float)
    for di, tokens in enumerate(tokenized):
        if not tokens:
            continue
        for tok in tokens:
            tf[di, vocab_index[tok]] += 1
        tf[di] /= len(tokens)

    # IDF vector (smooth — sklearn formula)
    df = numpy.count_nonzero(tf, axis=0)  # shape (V,)
    idf = numpy.log((1 + N) / (1 + df)) + 1

    # TF-IDF
    tfidf = tf * idf

    # L2 normalise
    norms = numpy.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1  # guard zero-norm rows
    tfidf /= norms

    return tfidf, vocab


def find_best_paragraph(post_vec, para_vecs, used_indices: set) -> int:
    scores = numpy.dot(para_vecs, post_vec)
    for idx in used_indices:
        if 0 <= idx < len(scores):
            scores[idx] = -1
    best = int(numpy.argmax(scores))
    # fall back to first unused index if all zeros
    if scores[best] <= 0:
        for i in range(len(scores)):
            if i not in used_indices:
                return i
        return 0
    return best


def insert_internal_link(html: str, para_idx: int, post_url: str, post_title: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return html
    # clamp to valid range
    para_idx = max(0, min(para_idx, len(paragraphs) - 1))
    target_p = paragraphs[para_idx]
    link_tag = soup.new_tag("a", href=post_url, title=post_title)
    link_tag.string = f"Read more: {post_title}"
    target_p.append(" ")
    target_p.append(link_tag)
    return str(soup)


# ── Main entry ────────────────────────────────────────────────────────────────

def link_internal(slug: str = None, input_file: str = None) -> None:
    if input_file is None:
        if slug is None:
            from utils import get_latest_slug
            slug = get_latest_slug("final_output")
        input_file = f"final_output/{slug}.json"
    load_dotenv()
    WP_USERNAME = os.getenv("WP_USERNAME")
    WP_PASSWORD = os.getenv("WP_PASSWORD")

    # Load final output
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = data["content"]["blog_post_html"]
    current_text = strip_html(html)

    # Parse paragraphs from current post
    soup = BeautifulSoup(html, "lxml")
    paragraphs = soup.find_all("p")
    para_texts = [p.get_text(" ") for p in paragraphs]

    # Auth + fetch posts
    try:
        token = get_wp_token(WP_USERNAME, WP_PASSWORD)
    except Exception as e:
        print(f"  [linker] Auth failed: {e} — skipping internal linking")
        data["internal_links"] = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "links_inserted": [],
        }
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return

    posts = fetch_published_posts(token)

    if not posts:
        print("  [linker] No published posts found — skipping internal linking")
        data["internal_links"] = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "links_inserted": [],
        }
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return

    # Build post texts (title + content)
    post_texts = [
        strip_html(p.get("title", {}).get("rendered", ""))
        + " "
        + strip_html(p.get("content", {}).get("rendered", ""))
        for p in posts
    ]

    # Build unified TF-IDF matrix:
    # index 0              → current blog
    # indices 1..len(para) → individual paragraphs
    # indices after that   → published posts
    all_docs = [current_text] + para_texts + post_texts
    matrix, _ = build_tfidf_matrix(all_docs)

    current_vec = matrix[0]
    para_vecs   = matrix[1 : 1 + len(para_texts)]
    post_vecs   = matrix[1 + len(para_texts):]

    # Rank posts by similarity to current blog
    similarities = numpy.dot(post_vecs, current_vec)
    top_n = min(3, len(posts))
    top_indices = numpy.argsort(similarities)[::-1][:top_n]

    used_para_indices: set = set()
    links_inserted = []

    for rank_idx in top_indices:
        post = posts[rank_idx]
        post_vec = post_vecs[rank_idx]

        if not para_texts:
            print("  [linker] No paragraphs found in blog — skipping remaining links")
            break

        best_para = find_best_paragraph(post_vec, para_vecs, used_para_indices)

        # Skip if we've already used all paragraphs
        if best_para in used_para_indices and len(used_para_indices) >= len(para_texts):
            print("  [linker] All paragraphs already used")
            break

        used_para_indices.add(best_para)
        post_url   = post.get("link", "")
        post_title = BeautifulSoup(
            post.get("title", {}).get("rendered", ""), "lxml"
        ).get_text()
        sim_score  = float(similarities[rank_idx])

        html = insert_internal_link(html, best_para, post_url, post_title)

        links_inserted.append({
            "post_id":               post.get("id"),
            "post_title":            post_title,
            "post_url":              post_url,
            "similarity_score":      round(sim_score, 4),
            "inserted_at_paragraph": best_para + 1,  # 1-indexed
        })
        print(f"  [linker] Linked '{post_title}' → paragraph {best_para + 1} "
              f"(score {sim_score:.3f})")

    data["content"]["blog_post_html"] = html
    data["internal_links"] = {
        "processed_at":  datetime.now(timezone.utc).isoformat(),
        "links_inserted": links_inserted,
    }

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  [linker] Done — {len(links_inserted)} link(s) inserted.")


if __name__ == "__main__":
    link_internal()
