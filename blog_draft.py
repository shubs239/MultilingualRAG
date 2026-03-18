from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timezone
from fetch_caption import caption, get_captions_up_to_hour

load_dotenv()
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)

sys_instruct_initial = """You are an expert content writer for castefreeindia.com — an anti-caste, evidence-based blog rooted in Ambedkarite and Phule-Periyar thought.

You will be given a YouTube video transcript. Write a long-form blog post from it.

WRITING RULES:
- Tone: authoritative, clear, direct — not academic jargon
- Audience: English-reading Indians, diaspora, researchers, allies
- Only use content from the transcript — do not add your own knowledge
- Avoid repeating paragraphs, headings, or content
- Avoid using names of people who are discussing (presenters/hosts)
- Avoid greetings and avoid using the word "transcript"
- Structure: Introduction (hook + keyword mention) → 7-10 H2 sections with 3-4 H3 subsections → Conclusion with CTA under "What Can You Do?"
- Include all historical references, scripture quotes, and quotes from famous persons mentioned — use <blockquote> tags
- Write [insert image here - Xm Ys] wherever a screenshot reference is needed (include timestamp from transcript)
- Include a Disclaimer section listing key terms and their meaning in context
- Use <strong> tags for bold where required
- Valid HTML only — use <h2>, <h3>, <p>, <blockquote>, <ul>, <li>, <strong> — NO inline CSS
- Minimum 2000 words in English

HEADLINE RULES:
blog_h1 — choose the pattern that fits best:
- "What [X] Actually [Says/Shows/Proves] — And Why [Consequence]"
- "How [Historical Fact] — And Why It Is Still [Happening/Defended/Ignored]"
- "The [Source] That Proves [Claim] — With Evidence"
- Must be rage bait to induce emotional response and drive clicks, but also factually accurate and curiosity-driven
Must be: SEO-friendly, curiosity-driven, factually accurate, high-emotion enough to drive clicks

blog_seo_title: under 60 characters, includes primary keyword, factual

SOURCING:
Identify every factual claim that needs a citation (scripture, government data, news, research paper). For each:
- claim: exact claim text
- type: "scripture" | "government" | "news" | "research"
- suggested_search: a search query to find the source
- insert_after_paragraph: paragraph number (1-indexed) after which to insert the citation

OUTPUT FORMAT — respond ONLY with valid JSON, no markdown code blocks:
{
  "headlines": {
    "blog_h1": "",
    "blog_seo_title": ""
  },
  "content": {
    "blog_post_html": ""
  },
  "sourcing": {
    "claims_needing_citation": [
      {
        "claim": "",
        "type": "scripture",
        "suggested_search": "",
        "insert_after_paragraph": 0
      }
    ]
  }
}
"""


def first_draft(link):
    transcript = get_captions_up_to_hour(captions=caption(link=link), input_minutes=60)

    raw_response = client.models.generate_content(
        model="models/gemini-2.5-flash-lite",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_initial,
            max_output_tokens=50024),
        contents=[f"This is the transcript: {transcript}. Output: Article of at least 2000 words in English in HTML without style section."]
    )

    response_text = raw_response.text.strip()
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        response_text = response_text.split("```", 2)[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.rsplit("```", 1)[0].strip()

    gemini_output = json.loads(response_text)

    blog_html = gemini_output.get("content", {}).get("blog_post_html", "")
    word_count = len(blog_html.split())

    draft_output = {
        "meta": {
            "script_stage": "draft",
            "source_video_url": f"https://www.youtube.com/watch?v={link}",
            "transcript_file": "",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "word_count": word_count
        },
        "headlines": {
            "blog_h1": gemini_output.get("headlines", {}).get("blog_h1", ""),
            "blog_seo_title": gemini_output.get("headlines", {}).get("blog_seo_title", "")
        },
        "content": {
            "blog_post_html": blog_html
        },
        "feedback": {
            "issues_found": [],
            "suggestions": [],
            "score": 0
        },
        "sourcing": {
            "claims_needing_citation": gemini_output.get("sourcing", {}).get("claims_needing_citation", [])
        }
    }

    with open("draft_output.json", "w", encoding="utf-8") as f:
        json.dump(draft_output, f, ensure_ascii=False, indent=2)
    print("Draft saved to draft_output.json")

    return draft_output


if __name__ == "__main__":
    link = input("Enter the YouTube video ID: ")
    first_draft(link)
