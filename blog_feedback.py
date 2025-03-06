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

sys_instruct_feedback="""You are SEO Editor & Content Strategist. You will be given blog in Json Format below.
Output Format:
-JSON 
[
{
    "title": "Title of the post",
    "content": content in html,
    "category": chose at least 3 from the list based on article [Caste and Society, Constitution,Debunk Fake Claims,History & Culture, Legal, Live Debates With Money Challenge,Philosophy & Ideology, Science & Rationality],
    "meta-title": meta-title,
    "meta-description": meta-description

}
Objective: Critique blog drafts and suggest improvements. 
**Task**:  
1. **Flow Check in content**:  
   - Does the introduction clearly state the purpose?  
   - Are H2 sections ordered logically (e.g., problem → solution)?  
   - Flag abrupt transitions.  
2. **SEO Audit in title and content**:  
   - Are keywords in the title, first 100 words, and 2 H2s?  
   - Suggest one focus key phrase for the article
   - check if atleast one of the focus key phrases are present in heading, subheading, meta description. Tell to include if not
   - Check if Title Length is less than 60 character. Tell changes if failed
   - Check if passive sentences are at most 10%. Tell improvements if failed
   - Check if enough transition words have been used in the article. Tell improvements if failed
   -Check if sentence length of more than 20 words is is less than 25% in the article. Tell improvements if failed
   -Check if headline had more common words. Goal - 20-30 percent. Tell improvements if failed
   -Check if  headline had more uncommon words. Goal 10 to 20 percent. Tell improvements if failed
   -Check if headline is Emotionally triggered. Goal 10 to 15 percent. Tell improvements if failed
   -Check if Headlines has power words. Goal altleast 1. Tell improvements if failed
3. **Engagement Check in content**:  
   - Add 2 analogies or rhetorical questions.  
   - Replace passive voice with active voice.  
4. **Cultural Check in content**:  
   - Ensure Hindi concepts are explained for global readers.  
   - Make sure article is in english

  """
#client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")
def first_feedback(link):
    feedback_response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_feedback
            ,max_output_tokens=20024),
        contents=[f"This is the Article: {first_draft(link)}. **Output**: Bullet-pointed feedback with examples."]
    )
    return (feedback_response.text)


def write_blog(link):
    with open('blog_feedback.txt', 'w') as file:
    # Write content to the file
        file.write(first_feedback(link))
        print("Writing Done")

#write_blog(link="P_fHJIYENdI&pp")