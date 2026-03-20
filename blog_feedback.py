from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import os
import json

load_dotenv()
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)


class FeedbackOutput(BaseModel):
    issues_found: List[str]
    suggestions: List[str]
    score: int

sys_instruct_feedback = """You are an SEO Editor & Content Strategist for an anti-caste, evidence-based blog.

You will be given an HTML blog post. Analyse it and return ONLY a feedback block — do not rewrite the article.

ANALYSIS CHECKS:

1. Flow Check:
   - Does the introduction clearly state the purpose?
   - Are H2 sections ordered logically (problem → evidence → solution)?
   - Flag any abrupt transitions

2. SEO Audit:
   - Are keywords in the title, first 100 words, and at least 2 H2s?
   - Suggest one focus key phrase
   - Check if focus key phrase is present in heading, subheading, and meta description
   - Check if title length is under 60 characters
   - Check if passive sentences are at most 10%
   - Check if transition words are adequate
   - Check if sentences over 20 words are under 25% of total
   - Headline word balance: 20-30% common, 10-20% uncommon, 10-15% emotional, at least 1 power word

3. Engagement Check:
   - Does it use analogies or rhetorical questions?
   - Is passive voice minimised?

4. Cultural Check:
   - Are Hindi/Sanskrit concepts explained for global readers?
   - Is the article entirely in English?

OUTPUT FORMAT — respond ONLY with valid JSON, no markdown code blocks:
{
  "issues_found": ["issue 1", "issue 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "score": 75
}

score is 0-100 based on overall quality.
"""


def first_feedback():
    with open("draft_output.json", "r", encoding="utf-8") as f:
        draft = json.load(f)

    blog_html = draft["content"]["blog_post_html"]

    raw_response = client.models.generate_content(
        model="models/gemini-flash-lite-latest",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_feedback,
            response_mime_type="application/json",
            response_schema=FeedbackOutput,
            max_output_tokens=20024),
        contents=[f"This is the blog post HTML: {blog_html}. Output: Feedback in JSON format as described."]
    )

    feedback_block = FeedbackOutput.model_validate_json(raw_response.text)

    draft["feedback"] = {
        "issues_found": feedback_block.issues_found,
        "suggestions": feedback_block.suggestions,
        "score": feedback_block.score
    }

    with open("feedback_output.json", "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    print("Feedback saved to feedback_output.json")

    return draft


if __name__ == "__main__":
    first_feedback()
