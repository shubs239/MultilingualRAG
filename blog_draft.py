from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the variables
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)
from fetch_caption import  caption, get_captions_up_to_hour

sys_instruct_initial=""" You are an AI content repurposer. You will be given youtube video transcript in a list like below
[{'text': 'नमस्कार दोस्तों स्वागत है आप सभी का', 'start': 1.88, 'duration': 6.12}, {'text': 'रेशनल वर्ल्ड में दोस्तों आप लोग एक बार', 'start': 5.08, 'duration': 5.16}......}]
This is a transcript from youtube video. text is what the user says in the video, start is when user start saying in secs and duration is the amount of time in secs,  You have to follow the below instructions.
**Tone**: authoritative with knowledge
**Task**:  

1. Structure the article as follows:  
   - Introduction (hook + keyword mention)  
   - 7-10 H2 sections with 3–4 H3 subsections  
   - Data-driven examples (cite 8–10 sources which were used in the transcript)  
   - Conclusion with call-to-action 
   - Write [insert image here -time] whenever mention any refreneces used in the context. Screenshot will be put in article as refrences. Also include time at which this screenshot needs to be taken 
   - Don't include any names of the persons/people involved in converstaion in the context
   - Don't include ** in HTML, use bold tag instead
   - Add table of contents after introduction which are clickable
   - Include a disclaimer which list the common terms used in the article and what it means in the context like brahmin implied brahminism ideology etc.

2. Add SEO elements:  
   - Meta title (65 chars)  
   - Meta description (155 chars)  
    
3. Ensure readability (Grade 8 level).  
4. Output Format:
-JSON with 
[
{
    "title": "Title of the post",
    "content": content in html,
    "category": chose at least 3 from the list based on article [Caste and Society, Constitution,Debunk Fake Claims,History & Culture, Legal, Live Debates With Money Challenge,Philosophy & Ideology, Science & Rationality],
    "meta-title": meta-title,
    "meta-description": meta-description

}
"""
def first_draft(link):
    initial_response = client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(
        system_instruction=sys_instruct_initial,
        max_output_tokens=20024),
    contents=[f"This is the context: {caption(link=link)}. **Output**: Article of atleast 3000 words in English in HTML."]
    )
    return (initial_response.text)


def write_blog(link):
    with open('blog_initial.txt', 'w') as file:
    # Write content to the file
        file.write(first_draft(link))
        print("Writing Done")

#write_blog(link="P_fHJIYENdI&pp")
#https://www.youtube.com/watch?v=P_fHJIYENdI&pp=ygUKdmVyaXRhc2l1bQ%3D%3D