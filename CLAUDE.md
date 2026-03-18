# CasteFreeIndia — Blog Pipeline Project

## Project overview
This is an automated content pipeline for castefreeindia.com — an anti-caste, 
evidence-based blog. The pipeline converts YouTube video transcripts into 
blog posts and platform-specific content using AI.

## Folder structure
- /blog_draft.py — takes transcript, calls Gemini, outputs initial blog draft
- /blog_feedback.py — takes draft, runs critique/feedback pass
- /final blog.py — takes draft + feedback, produces final blog content
- /reedit_post.py — generates Reddit post, X post, and other social media content
- /wordpress_api.py — saves draft post to WordPress via REST API
- /fetch_caption.py — fetches captions from YouTube video
- /myenv — Python virtual environment (do not modify)
- /Blogs data — IGNORE THIS FOLDER ENTIRELY. Do not read, index, or load 
  anything from here unless explicitly asked. Do not push to GitHub.

## Pipeline flow
transcript → blog_draft.py → blog_feedback.py → final blog.py → wordpress_api.py
                                                               ↘ reedit_post.py

## Current status
- All scripts exist and work
- Output is currently .txt files
- Gemini API is already configured
- WordPress REST API posting is already working
- Goal: improve prompts + migrate all outputs to structured JSON

## Task 2 — Sourcing script (source_finder.py)

Create a new script: source_finder.py
Input: final_output.json
Output: adds a "sourcing_results" block to final_output.json (does not 
overwrite existing content, merges into the same file)
No Amazon affiliate links needed — skip that entirely for now.

### What it does
Reads claims_needing_citation from final_output.json and for each claim:

TYPE: "archive"
- Search Archive.org API for the scripture/book name
- Return the best matching URL
- Insert as inline hyperlink in blog_post_html at insert_after_paragraph

TYPE: "government"
- Search for the claim using DuckDuckGo search (ddg-search or duckduckgo_search 
  python library)
- Prefer these domains in order: ncrb.gov.in, data.gov.in, pib.gov.in, 
  mospi.gov.in, any other .gov.in
- Return best URL
- Insert as inline hyperlink in blog_post_html at insert_after_paragraph

TYPE: "news"
- Search DuckDuckGo for the claim
- Prefer these domains in order: thehindu.com, indianexpress.com, scroll.in, 
  thewire.in, bahujanpress.com, newslaundry.com
- Return best URL
- Insert as inline hyperlink in blog_post_html at insert_after_paragraph

TYPE: "research"
- Search DuckDuckGo for the claim
- Prefer: scholar links, jstor.org, epw.in (Economic and Political Weekly), 
  shodhganga.inflibnet.ac.in
- Return best URL
- Insert as inline hyperlink in blog_post_html at insert_after_paragraph

TYPE: "book_unavailable"
- Book is not on Archive.org, skip link insertion
- Insert a HTML comment placeholder only:
  <!-- SCREENSHOT: [book_title] by [book_author] — add screenshot here -->
- Do not search for anything

### Output block added to final_output.json
"sourcing_results": {
  "processed_at": "",
  "claims": [
    {
      "claim": "",
      "type": "",
      "source_found": true | false,
      "url": "",
      "domain": "",
      "inserted_at_paragraph": 0
    }
  ]
}

### Important
- If no source is found for a claim, log it but do not insert a broken link
- Do not modify any other part of final_output.json
- Run this BEFORE wordpress_api.py so the HTML already has links when posted

---

## Task 3 — Featured image (image_fetch.py)

Create a new script: image_fetch.py
Input: final_output.json
Output: downloads image to ./images/ folder, adds "featured_image" block 
to final_output.json

### What it does
- Use Runware API to generate a featured image for every post
- The image prompt is auto-generated from blog_h1 in final_output.json
- Prompt template to send to Runware:
  "Editorial illustration about [topic extracted from blog_h1], 
   flat design, no text, no letters, muted earthy tones, 
   Indian context, minimalist"
- Extract topic from blog_h1 by stripping the headline formula patterns 
  (remove "What X Actually..." wrapper, keep the core subject)
- Image dimensions: 1200x630 (standard blog featured image / OG image size)
- Save to ./images/featured-[post-slug].jpg
  (post-slug = blog_h1 lowercased, spaces replaced with hyphens, 
   special chars stripped)
- Runware API key is in .env as RUNWARE_API_KEY

### Output block added to final_output.json
"featured_image": {
  "source": "runware",
  "local_path": "./images/featured-[post-slug].jpg",
  "alt_text": "[blog_h1 value]",
  "prompt_used": ""
}

### Important
- image_fetch.py must run BEFORE wordpress_api.py
- wordpress_api.py should be updated to read featured_image.local_path 
  from final_output.json, upload it via WordPress media API, and attach 
  as featured_media when creating the post

---

## Task 5 — Image and meme generator (image_gen.py)

Create a new script: image_gen.py
Input: final_output.json
Output: generates 3 images, saves to ./images/, adds "social_images" block 
to social_output.json (creates social_output.json if it doesn't exist)

Use the Pillow library for all image generation.

### Image 1 — Quote card (Instagram + Facebook)
- Size: 1080x1080px
- Background: dark (#1a1a1a or similar deep dark)
- Accent colour: saffron (#E8651A)
- Layout:
  - Top: "CasteFreeIndia.com" in small caps, saffron, top centre
  - Middle: key quote from blog (Gemini should pick the single most 
    shareable/striking sentence from blog_post_html — add this to the 
    final blog.py prompt as an extra field: "most_shareable_quote")
  - Bottom: blog_h1 in smaller text, muted white
  - Bottom right: small logo or site name watermark
- Font: use a bold sans-serif (download Noto Sans Bold or use a system font)
- Text wrapping: handle long quotes gracefully — reduce font size if quote 
  exceeds 3 lines
- Save to: ./images/quote-[post-slug].png

### Image 2 — X header image (first tweet visual)
- Size: 1600x900px
- Same dark background + saffron accent
- Layout:
  - Large bold text: x_hook from final_output.json (without the 🧵 emoji)
  - Bottom left: "castefreeindia.com"
  - Subtle horizontal saffron line separating headline from source line
- Save to: ./images/x-header-[post-slug].png

### Image 3 — Meme (two-panel format)
- Size: 1080x1080px
- Two equal horizontal panels divided by a saffron line
- Top panel: dark background, text = meme_top_text (misconception / 
  "what they say")
- Bottom panel: slightly lighter dark background, text = meme_bottom_text 
  (the factual rebuttal from the post)
- Label top panel: "What they say:" in small saffron text above the quote
- Label bottom panel: "What the evidence shows:" in small saffron text
- Bottom: "Source: castefreeindia.com" in small muted text
- Save to: ./images/meme-[post-slug].png

### Meme text generation
Add these two fields to the final blog.py Gemini prompt output:
"meme_top_text": "The common misconception or dominant narrative this 
                   post challenges — one punchy sentence"
"meme_bottom_text": "The factual rebuttal from the post — one punchy 
                     sentence with source if possible"

These fields go into final_output.json under "content".

### Output block added to social_output.json
"social_images": {
  "quote_card": "./images/quote-[post-slug].png",
  "x_header": "./images/x-header-[post-slug].png",
  "meme": "./images/meme-[post-slug].png",
  "quote_used": "",
  "meme_top_text": "",
  "meme_bottom_text": ""
}

---

## Updated pipeline order (after all tasks complete)

fetch_caption.py         → transcript
blog_draft.py            → draft_output.json
blog_feedback.py         → feedback_output.json  
final blog.py            → final_output.json
source_finder.py         → final_output.json (sourcing_results added)
image_fetch.py           → final_output.json (featured_image added)
image_gen.py             → social_output.json (social_images added)
wordpress_api.py         → posts to WordPress (reads final_output.json)
reedit_post.py           → social_output.json (x, reddit, insta, fb content)

## Updated .env keys needed
GEMINI_API_KEY=
RUNWARE_API_KEY=

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