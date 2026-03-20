from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import os
import json
from datetime import datetime, timezone

load_dotenv()
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)


class Claim(BaseModel):
    claim: str
    type: str
    suggested_search: str
    insert_after_paragraph: int

class Title(BaseModel):
    blog_h1: str
    blog_seo_title: str

class FinalContent(BaseModel):
    blog_post_html: str
    meta_description: str
    keyword_list: List[str]
    most_shareable_quote: str
    meme_top_text: str
    meme_bottom_text: str

class Sourcing(BaseModel):
    claims_needing_citation: List[Claim]

class FinalOutput(BaseModel):
    title: Title
    content: FinalContent
    sourcing: Sourcing

sys_instruct_final = """You are a Technical Editor & SEO Optimizer for castefreeindia.com — an anti-caste, evidence-based blog.

You will be given an HTML blog post and a feedback block. Implement ALL feedback suggestions into the article.

REVISION RULES:
- Apply every issue fix and suggestion from the feedback
- Maintain keyword density at 1-2%
- No repetition of paragraphs, headings, or content
- Clear conclusion
- Clear CTA under heading "What Can You Do?"
- Valid HTML only — use <h2>, <h3>, <p>, <blockquote>, <ul>, <li>, <strong> — NO inline CSS
- Do NOT add social media content — that is handled by a separate script

HEADLINE RULES (refine from existing, keep factual and high-emotion):
blog_h1 patterns:
- "What [X] Actually [Says/Shows/Proves] — And Why [Consequence]"
- "How [Historical Fact] — And Why It Is Still [Happening/Defended/Ignored]"
- "The [Source] That Proves [Claim] — With Evidence"
blog_seo_title: under 60 characters, includes primary keyword
meta_description: 150-160 characters, includes primary keyword, factual
keyword_list: 5-10 SEO keywords as array of strings

SOURCING:
Update the claims_needing_citation list to reflect the revised article paragraph numbering.

SOCIAL IMAGE FIELDS:
most_shareable_quote: single most striking/standalone sentence from the blog — works as a pull-quote
meme_top_text: the popular misconception this post challenges — punchy, ≤15 words
meme_bottom_text: the factual counter from the post — punchy, ≤15 words, cite source inline if possible

OUTPUT FORMAT — respond ONLY with valid JSON, no markdown code blocks:
{
  "title": {
    "blog_h1": "",
    "blog_seo_title": ""
  },
  "content": {
    "blog_post_html": "",
    "meta_description": "",
    "keyword_list": [],
    "most_shareable_quote": "",
    "meme_top_text": "",
    "meme_bottom_text": ""
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


def final_draft():
    with open("feedback_output.json", "r", encoding="utf-8") as f:
        feedback_data = json.load(f)

    blog_html = feedback_data["content"]["blog_post_html"]
    feedback_block = feedback_data["feedback"]

    raw_response = client.models.generate_content(
        model="models/gemini-flash-lite-latest",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_final,
            response_mime_type="application/json",
            response_schema=FinalOutput,
            max_output_tokens=100024),
        contents=[f"This is the article HTML: {blog_html}\n\nThis is the feedback: {json.dumps(feedback_block)}\n\nOutput: Revised article with all feedback implemented, in JSON format as described."]
    )

    gemini_output = FinalOutput.model_validate_json(raw_response.text)

    blog_html_final = gemini_output.content.blog_post_html
    word_count = len(blog_html_final.split())

    final_output = {
        "meta": {
            "script_stage": "final",
            "source_video_url": feedback_data["meta"].get("source_video_url", ""),
            "transcript_file": feedback_data["meta"].get("transcript_file", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "word_count": word_count
        },
        "title": {
            "blog_h1": gemini_output.title.blog_h1,
            "blog_seo_title": gemini_output.title.blog_seo_title
        },
        "content": {
            "blog_post_html": blog_html_final,
            "meta_description": gemini_output.content.meta_description,
            "keyword_list": gemini_output.content.keyword_list,
            "most_shareable_quote": gemini_output.content.most_shareable_quote,
            "meme_top_text": gemini_output.content.meme_top_text,
            "meme_bottom_text": gemini_output.content.meme_bottom_text,
        },
        "sourcing": {
            "claims_needing_citation": [c.model_dump() for c in gemini_output.sourcing.claims_needing_citation]
        }
    }

    with open("final_output.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    print("Final blog saved to final_output.json")

    return final_output


if __name__ == "__main__":
    final_draft()
