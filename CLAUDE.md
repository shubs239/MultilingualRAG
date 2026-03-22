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

---

## Pending tasks

### Task - Fix the folder structure. I ran run pipeline.py file from root, it created all the folders but it failed on youtube shorts because of config error in hosrts_visual.py file. Fixed it. Ran each .py file in video folder from root folder, now I have images, audio, output folder in the root, even though they are already in video folder,which should have been used.
### Task  - Change the name of audio files, image files, should also have slug name after segment. Final audio file should be slug name as well.
### Task 3.1 - Also, output files generated by code should not be updated to github. Add this somewhere you can remember.
### Task - Source finder is not working. I mean source are okay, but it is not placed in correct places. And i need to add these to trusted domain - "britannica.com", "researchgate.net", "academia.edu", "books.google". How is this working, I need explaination, Is brave search searching facts on these domains??
### Task 8 — Schedule X (Twitter) posts
### Task 9 — Facebook & Instagram page automation

---

## .env keys needed

```
GEMINI_API_KEY=
RUNWARE_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

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
