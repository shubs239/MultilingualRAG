from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import json
from pydantic import BaseModel


# Load environment variables from .env file
load_dotenv()
# class Recipe(BaseModel):
#   title: str
#   content: str
#   category: str
#   meta_title: str
#   meta_description: str
# Access the variables
api_key = os.getenv('API_KEY')
client = genai.Client(api_key=api_key)
from fetch_caption import  caption, get_captions_up_to_hour

sys_instruct_initial=""" You are an AI content repurposer. You will be given youtube video transcript in a list like below
[{'text': 'नमस्कार दोस्तों स्वागत है आप सभी का', 'start': 1.88, 'duration': 6.12}, {'text': 'रेशनल वर्ल्ड में दोस्तों आप लोग एक बार', 'start': 5.08, 'duration': 5.16}......}]
This is a transcript from youtube video. text is what the user says in the video, start is when user start saying in secs and duration is the amount of time in secs,  You have to follow the below instructions.
**Tone**: authoritative with knowledge
**Task**:  

1. Instructions:  
   - Introduction (hook + keyword mention)  
   - 7-10 H2 sections with 3–4 H3 subsections  
   - Data-driven examples (cite 8–10 sources which were used in the transcript)  
   - Conclusion with call-to-action under heading What you can do?
   - Write [insert image here -time] whenever mention any refreneces used in the context. Screenshot will be put in article as refrences. Also include time at which this screenshot needs to be taken 
   - Use bold tag wherever required
   - Focus on facts where refreneces are provided in the transcript
   - Avoid using names of the people who are discussing
   - Avoid any greetings
   - Add vertical table of contents after introduction which are clickable
   - Include a disclaimer which list the common terms used in the article and what it means in the context.
   - Include all the historical references, quotes from famous person/book used in the transcript
   - Only use transcript to write the article, do ont use your own knowledge
    
2. Ensure readability (Grade 8 level).  
    - Avoid repeatation of the same paragraph/heading/content in the article
3. Output Format:
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
        max_output_tokens=50024),
    contents=[f"This is the context: {caption(link=link)}. **Output**: Article of atleast 3000 words in English in HTML without style section."]
    )
    return (initial_response.text)

# result = first_draft(link="P_fHJIYENdI&pp")
# print(type(result))
#print(result)
# def write_blog(link):
#     with open('blog_initial.json', 'w') as file:
#     # Write content to the file
#         file.dump(result)
#         print("Writing Done")

# write_blog(link="P_fHJIYENdI&pp")
#https://www.youtube.com/watch?v=P_fHJIYENdI&pp=ygUKdmVyaXRhc2l1bQ%3D%3D

