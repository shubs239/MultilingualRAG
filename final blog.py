from google import genai
from google.genai import types
from blog_feedback import  first_feedback
from blog_draft import first_draft
from dotenv import load_dotenv
import os
import json
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
   - Suggested changes are included.
   
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
]"""#client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")

def final_draft(link):
    response_final = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_final,
            max_output_tokens=20024),
        contents=[f"This is the Article: {first_draft(link)}. This is the feedback: {first_feedback(link)} **Output**: Revised article with changes included as per suggestions in Json format as decsribed."]
    )
    return (response_final.text)

final_blog = final_draft(link="WLCqaUqvOP4")


def write_blog(link):
    with open('blog_initial.txt', 'w') as file:
    # Write content to the file
        file.write(first_draft(link))
        print("First Draft Done")
    with open('blog_Feedback.txt', 'w') as file:
    # Write content to the file
        file.write(first_feedback(link))
        print("Feeback of Blog Done")
    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(final_blog, file)
        print("Final Draft Json Done")
    with open('blog_final.txt', 'w') as file:
    # Write content to the file
        file.write(final_blog)
        print("Final Draft Done")


write_blog(link="WLCqaUqvOP4")
#https://www.youtube.com/watch?v=t9UmqFaYvTo  https://www.youtube.com/watch?v=1-LxA5zFBiY&t=8118s
