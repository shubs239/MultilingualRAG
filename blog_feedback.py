from google import genai
from google.genai import types
from blog_draft import  first_draft
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the variables
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)

sys_instruct_feedback="""You are SEO Editor & Content Strategist
Objective: Critique blog drafts and suggest improvements. 
**Task**:  
1. **Flow Check**:  
   - Does the introduction clearly state the purpose?  
   - Are H2 sections ordered logically (e.g., problem → solution)?  
   - Flag abrupt transitions.  
2. **SEO Audit**:  
   - Are keywords in the title, first 100 words, and 2 H2s?  
   - Suggest focus key phrases for the blog
3. **Engagement Check**:  
   - Add 2 analogies or rhetorical questions.  
   - Replace passive voice with active voice.  
4. **Cultural Check**:  
   - Ensure Hindi concepts are explained for global readers.  

  """
#client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")
def first_feedback(link):
    feedback_response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_feedback
            ,max_output_tokens=20024),
        contents=[f"This is the Blog: {first_draft(link)}. **Output**: Bullet-pointed feedback with examples."]
    )
    return (feedback_response.text)


def write_blog(link):
    with open('blog_feedback.txt', 'w') as file:
    # Write content to the file
        file.write(first_feedback(link))
        print("Writing Done")

write_blog(link="GAmQe3nWhvc")