import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone

load_dotenv()
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)


class XContent(BaseModel):
    hook: str
    thread: List[str]

class RedditContent(BaseModel):
    title: str
    post: str

class InstagramContent(BaseModel):
    caption_line1: str
    caption_full: str

class FacebookContent(BaseModel):
    post: str

class SocialOutput(BaseModel):
    x: XContent
    reddit: RedditContent
    instagram: InstagramContent
    facebook: FacebookContent

sys_instruct = """You are a social media content strategist for castefreeindia.com — an anti-caste, evidence-based blog.

You will be given the final blog post HTML and its title. Create platform-specific social media content.

PLATFORM RULES:

X (TWITTER) HOOK — first tweet of thread:
- Lead with a number, date, or single hard fact from the article
- No hedging language (no "seems", "apparently", "might")
- Under 240 characters
- End with 🧵

X THREAD:
- 3-5 tweets expanding on key findings from the article
- Each tweet standalone, factual, under 280 characters
- End the final tweet with: [LINK]

REDDIT TITLE:
- Deliver the actual finding in the title itself — not just a tease
- Never sounds promotional
- Rage-baity but 100% supported by the content

REDDIT POST:
- 5-8 detailed bullet points from the article
- Controversial and interesting — make people want to click for more
- Scathing but factual — focus on how historical injustices were normalised and defended
- End with: [LINK]

INSTAGRAM CAPTION LINE 1 (caption_line1):
- Direct address: "They tell you..." / "Nobody talks about..." / "Here is what they removed from..."
- Max 12 words
- Must work without any context

INSTAGRAM CAPTION FULL:
- caption_line1 as the first line
- 3-5 lines with key facts from the article
- Relevant hashtags at the end

FACEBOOK POST:
- 2 sentences max before the link
- Slightly warmer tone than X
- Written to make someone tag a friend
- End with: [LINK]

OUTPUT FORMAT — respond ONLY with valid JSON, no markdown code blocks:
{
  "x": {
    "hook": "",
    "thread": ["tweet 1", "tweet 2", "tweet 3"]
  },
  "reddit": {
    "title": "",
    "post": ""
  },
  "instagram": {
    "caption_line1": "",
    "caption_full": ""
  },
  "facebook": {
    "post": ""
  }
}
"""


def create_social_media_post():
    with open("final_output.json", "r", encoding="utf-8") as f:
        final_data = json.load(f)

    blog_html = final_data["content"]["blog_post_html"]
    blog_h1 = final_data["title"]["blog_h1"]

    raw_response = client.models.generate_content(
        model="models/gemini-flash-lite-latest",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct,
            response_mime_type="application/json",
            response_schema=SocialOutput,
            max_output_tokens=20024),
        contents=[f"Blog title: {blog_h1}\n\nBlog content HTML: {blog_html}\n\nOutput: Social media posts in JSON format as described."]
    )

    gemini_output = SocialOutput.model_validate_json(raw_response.text)

    social_output = {
        "meta": {
            "script_stage": "social",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_post_title": blog_h1
        },
        "x": gemini_output.x.model_dump(),
        "reddit": gemini_output.reddit.model_dump(),
        "instagram": gemini_output.instagram.model_dump(),
        "facebook": gemini_output.facebook.model_dump()
    }

    with open("social_output.json", "w", encoding="utf-8") as f:
        json.dump(social_output, f, ensure_ascii=False, indent=2)
    print("Social media content saved to social_output.json")

    return social_output


if __name__ == "__main__":
    create_social_media_post()
