from google import genai
from google.genai import types
from blog_feedback import  first_feedback
from blog_draft import first_draft
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the variables
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)

sys_instruct_final="""Role: Technical Editor & SEO Optimizer
Objective: Revise the article using feedback from the Quality Analyst.
**Task**:  
1. Revise the article step-by-step:  
   - Adjust structure per flow suggestions.  
   - Add/replace keywords as advised.  
   - Add/replace focus key phrases
2. Ensure:  
   - Keyword density remains 1–2%.
   - Suggested changes are included."""#client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")

def final_draft(link):
    response_final = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_final,
            max_output_tokens=20024),
        contents=[f"This is the Article: {first_draft(link)}. This is the feedback: {first_feedback(link)} **Output**: Revised article with changes included as per suggestions."]
    )
    return (response_final.text)


def write_blog(link):
    with open('blog_initial.txt', 'w') as file:
    # Write content to the file
        file.write(first_draft(link))
        print("First Draft Done")
    with open('blog_Feedback.txt', 'w') as file:
    # Write content to the file
        file.write(first_feedback(link))
        print("Feeback of Blog Done")
    with open('blog_final.txt', 'w') as file:
    # Write content to the file
        file.write(final_draft(link))
        print("Final Draft Done")


write_blog(link="mWNwS_lHal0")