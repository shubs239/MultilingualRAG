# CasteFreeIndia — Blog Pipeline Project

## Project ambition

Build a fully automated content engine for **castefreeindia.com** — an anti-caste, evidence-based blog rooted in Ambedkarite and Phule-Periyar thought.

The goal: paste a YouTube video ID → get a complete, publish-ready output package:
- SEO blog post with citations, internal links, featured image
- WordPress draft posted automatically
- 3 social media images (quote card, X header, meme)
- X/Twitter thread + Reddit post + Instagram/Facebook caption
- YouTube Shorts video (Hinglish script → TTS audio → visuals → edited .mp4)

Audience: English-reading Indians, diaspora, researchers, allies.

---

## Folder structure

```
MultilingualRAG/
├── run_pipeline.py          — Master orchestrator. Runs all blog stages in sequence, then optionally triggers Shorts video
├── fetch_caption.py         — Fetches YouTube transcript via youtube-transcript-api
├── blog_draft.py            — Stage 1: Gemini generates initial HTML blog draft + citation claims → draft_output/{slug}.json
├── blog_feedback.py         — Stage 2: Gemini critiques the draft → feedback_output/{slug}.json
├── final blog.py            — Stage 3: Gemini produces final blog with meme/quote fields → final_output/{slug}.json
├── source_finder.py         — Stage 4: Auto-finds citations (Archive.org, DDG search) and inserts links into HTML → updates final_output/{slug}.json
├── image_fetch.py           — Stage 5: Runware generates featured image, Pillow overlays title → images/featured-{slug}.jpg; adds featured_image block to final_output
├── image_gen.py             — Stage 6: Pillow generates quote card + X header + meme → images/; adds social_images block to social_output/{slug}.json
├── internal_linker.py       — Stage 7: TF-IDF cosine similarity vs published WP posts, inserts top-3 internal links → adds internal_links block to final_output
├── wordpress_api.py         — Reads final_output/{slug}.json, uploads featured image, creates WordPress draft post
├── reedit_post.py           — Generates X thread, Reddit post, Instagram/Facebook captions → social_output/{slug}.json
├── utils.py                 — Shared helpers (make_slug, get_captions_up_to_hour, etc.)
├── image.png                — Meme template image used by image_gen.py
├── images/                  — All generated images (featured, quote card, X header, meme) — gitignored
├── video/
│   ├── shorts_pipeline.py   — Orchestrator for Shorts: runs all 4 stages in order
│   ├── shorts_script.py     — Stage 1: Gemini generates Hinglish punchy script → video/production_sheet.json
│   ├── shorts_audio.py      — Stage 2: ElevenLabs TTS per segment (Gemini TTS fallback) → video/audio/ + full_audio.mp3
│   ├── shorts_visuals.py    — Stage 3: Runware 1080×1920 vertical images per segment → video/images/
│   ├── shorts_editor.py     — Stage 4: MoviePy Ken Burns/pan + Pillow text overlays → video/output/{slug}.mp4
│   ├── patch_audio_key.py   — Utility: patches ElevenLabs API key issue
│   ├── audio/               — Generated segment audio files (gitignored)
│   ├── images/              — Generated segment visuals (gitignored)
│   └── output/              — Final rendered .mp4 files (gitignored)
├── draft_output/            — Per-slug JSON from blog_draft.py (gitignored)
├── feedback_output/         — Per-slug JSON from blog_feedback.py (gitignored)
├── final_output/            — Per-slug JSON from final blog.py + enriched by later stages (gitignored)
├── social_output/           — Per-slug JSON from reedit_post.py + image_gen.py (gitignored)
├── fonts/                   — Auto-downloaded NotoSans-Bold.ttf for image generation
├── myenv/                   — Python virtual environment (do not modify)
├── Blogs data/              — IGNORE THIS FOLDER ENTIRELY. Do not read, index, or load anything from here unless explicitly asked. Do not push to GitHub.
└── CLAUDE.md                — Project instructions for Claude
```

---

## Pipeline flow

```
python run_pipeline.py
  ↓ input: YouTube video ID + transcript minutes
  Stage 1: blog_draft.py        → draft_output/{slug}.json
  Stage 2: blog_feedback.py     → feedback_output/{slug}.json
  Stage 3: final blog.py        → final_output/{slug}.json
  Stage 4: source_finder.py     → final_output/{slug}.json  (sourcing_results block added)
  Stage 5: image_fetch.py       → images/featured-{slug}.jpg + final_output (featured_image block)
  Stage 6: image_gen.py         → images/{quote,x-header,meme}-{slug}.png + social_output/{slug}.json
  Stage 7: internal_linker.py   → final_output/{slug}.json  (internal_links block added)
  ↓ prompts: Generate YouTube Shorts? (y/n)
  Optional: video/shorts_pipeline.py
    → shorts_script.py  → video/production_sheet.json
    → shorts_audio.py   → video/audio/ + full_audio.mp3
    → shorts_visuals.py → video/images/
    → shorts_editor.py  → video/output/{slug}.mp4

Manual follow-up (after pipeline):
  python wordpress_api.py   — prompts for slug, posts to WordPress as draft
  python reedit_post.py     — prompts for slug, generates social media content
```

---

## Current status

- All blog pipeline stages (1–7) complete and wired into `run_pipeline.py`
- YouTube Shorts pipeline complete; on branch `task10-youtube-shorts` — not yet merged to master
- All standalone scripts use `input()` prompts — no CLI arguments needed
- `blog_draft.py` accepts `input_minutes` parameter (default 60), passed from `run_pipeline.py`
- WordPress posting works; featured image upload + attachment works
- All outputs are structured JSON (per-slug files in their respective folders)

---

## Completed tasks

| Task | Script | What it does |
|------|--------|--------------|
| Task 2 | `source_finder.py` | Citation auto-finder (Archive.org + DDG search), inserts links into HTML |
| Task 3 | `image_fetch.py` | Featured image via Runware + Pillow title overlay |
| Task 5 | `image_gen.py` | 3 social images (quote card 1080×1080, X header 1600×900, meme 1080×1080) |
| Task 6 | `run_pipeline.py` | Full pipeline wiring (stages 1–7 + optional Shorts) |
| Task 7 | `internal_linker.py` | TF-IDF internal linking against published WP posts |
| Task 10 | `video/` | YouTube Shorts pipeline (script → audio → visuals → edit) |
| Task 10.1 | `video/shorts_visuals.py` | Switch to runware:108@1 with native 9:16 (1080×1920) dimensions |
| Task 10.2 | `video/shorts_visuals.py` | Strengthen Indian context in STYLE_SUFFIX; block Egyptian/Greek imagery in NEGATIVE_PROMPT |
| Source finder fix | `source_finder.py` | Semantic paragraph matching for correct citation placement; added caravanmagazine.in + themooknayak.com to NEWS_DOMAINS; added britannica.com, researchgate.net, academia.edu, books.google to trusted domains |
| Task 9 | `facebook_post.py`, `instagram_post.py` | Post meme to Facebook Page + quote card to Instagram Business account via Meta Graph API v19.0; publish now or schedule (IST); auto-exchanges for Page Access Token; auto-looks up Instagram Business Account ID |
| Task 9.1 | `reedit_post.py` | Replace `[LINK]` placeholder with real blog URL (`https://castefreeindia.com/{slug}/`) in Facebook, Reddit, and X thread captions |
| Task 10.3 | `video/shorts_script.py` | Add `youtube_title` (punchy, Title Case enforced) and `youtube_description` (SEO-optimised, 150–300 words with hashtags + blog URL) to production sheet |
| Task T1 | `utils.py`, `blog_draft.py`, `blog_feedback.py`, `final blog.py` | Google Suggest integration: extract search topic via Gemini, fetch autocomplete suggestions, feed SEO context into feedback + final prompts, add `seo` block to draft JSON and `headline_options` to feedback JSON |
| Task T3 | `wiki_finder.py` | Weekly Wikipedia citation-needed scanner: Gemini entity extraction per post → Wikipedia API confirmation → wikitext scan for `{{citation needed}}` → TF-IDF claim matching → `wiki_opportunities.json` with pre-formatted citation markup + edit URLs. Run manually: `python wiki_finder.py` |

---

## Pending tasks

### Task — Schedule X (Twitter) posts
### Task — Backlink automation — research and design how to automatically acquire backlinks for published posts (e.g. submit to directories, outreach to allied sites, auto-comment with links on relevant forums)
## Traffic & Growth Tasks


---


### Task T4 (Step 4 only) — Medium summary generator

Add Step 4 to backlink_submitter.py.
If backlink_submitter.py does not exist yet, create it
as a standalone script — Steps 1, 2, 3 are separate tasks
added later. For now build Step 4 only.

Called at the end of run_pipeline.py after wordpress_api.py
confirms successful post. If wordpress_api.py fails,
do not run this step.

Input: reads blog_h1, blog_post_html, post_url from
       final_output/{slug}.json
Output: saves medium_summary to social_output/{slug}.json

─── What it does ───

Call Gemini with the final blog content:
  "Generate a Medium cross-post summary for this blog post.
   Format:
   - Opening paragraph (2-3 sentences): the core argument
     or most striking finding from the post
   - 3 bullet points: key evidence or findings
   - Closing line: 'Read the full post with primary sources: [URL]'
   - Final note in italics: 'Originally published at
     castefreeindia.com — read there for full citations
     and source links.'

   Keep total length under 200 words.
   Tone: direct and factual, same as the blog.
   Do not use phrases like 'In this post' or 'The author'."

Save to social_output/{slug}.json under key medium_summary:
{
  "medium_summary": {
    "text": "",
    "generated_at": "",
    "word_count": 0
  }
}

Do NOT auto-post to Medium.
Saved for manual review and posting only.
When you post to Medium manually: paste the summary,
add canonical URL pointing to castefreeindia.com
(Medium Settings → Advanced → Canonical URL).
This prevents duplicate content penalty from Google.

If Gemini call fails: log warning, skip silently.
Do not fail run_pipeline.py over this step.

No new .env keys needed.


---


## General rules for all traffic tasks

NEVER implement:
- Automated Wikipedia edits (account ban risk)
- Auto-commenting on external blogs or forums
- Mass directory submission to 100+ directories
- Any paid link service or PBN
- Reciprocal link exchange schemes

ALWAYS run after each publish (backlink_submitter.py):
- Medium summary saved for manual posting

Manual weekly tasks — not automated, you do these:
- Post 2-3 times to Reddit using social_output/{slug}.json
- Run wiki_finder.py and do 3 Wikipedia edits
- Upload 2-3 YouTube Shorts from video/output/
- Post Medium summary manually with canonical URL set
---

## Content guidelines

- Anti-caste, evidence-based, rooted in Ambedkarite and Phule-Periyar thought
- Sources: scriptures (Archive.org links), NCRB data, government reports, news articles
- Tone: clear, direct, accessible — not academic jargon
- Audience: English-reading Indians + diaspora + researchers + allies

---

## General guidelines

- Push all changes to GitHub
- Never push the /Blogs data folder to GitHub (.gitignore it)
- Do not load anything from /Blogs data unless explicitly asked
- Do not combine scripts — they are intentionally separate stages
- Do not change WordPress posting logic unless asked
- Do not restructure the folder layout without asking first
