from google import genai
from google.genai import types
from blog_feedback import  first_feedback
from blog_draft import first_draft
from dotenv import load_dotenv
import os
import json
from pydantic import BaseModel
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
   - No repeatation of the same paragraph/heading/content in the article
   - Clear Conclusion
   - Clear CTA unde heading 'What can you do?'.
   
3. Output Format:
-JSON with below key pairs
[
{
    "title": "Title of the post",
    "content": content in html,
    "category": chose at least 3 from the list based on article [Caste and Society, Constitution,Debunk Fake Claims,History & Culture, Legal, Live Debates With Money Challenge,Philosophy & Ideology, Science & Rationality],
    "meta-title": meta-title,
    "meta-description": meta-description
    "focus-keyphrase": focus key phrase selected

}
]"""#client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")
link = input("Enter the link id: ")
print(link)


first_draft_response =first_draft(link=link)
feedback_response = first_feedback(link)

def final_draft():
    response_final = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_final,
            max_output_tokens=100024),
        contents=[f"This is the Article: {first_draft_response}. This is the feedback: {feedback_response} **Output**: Revised article with changes included as per suggestions in Json format as decsribed."]
    )
    return (response_final.text)

final_blog = final_draft()

#print(type(final_blog))
#print(final_blog))
#json_final = json.dump(final_blog)
#print(type(json_final))



def write_blog(link):
    with open(f'Blogs data/blog_initial.txt', 'w') as file:
    # Write content to the file
        file.write(first_draft_response)
        print("First Draft Done")
    with open(f'Blogs data/blog_Feedback.txt', 'w') as file:
    # Write content to the file
        file.write(feedback_response)
        print("Feeback of Blog Done")
    with open(f'Blogs data/blog_final.json', "w") as file:
        json.dump(final_blog, file)
        print("Final Draft Json Done")
    with open(f'Blogs data/blog_final.txt', 'w') as file:
    # Write content to the file
        file.write(final_blog)
        print("Final Draft Done")


write_blog(link)
#https://www.youtube.com/watch?v=t9UmqFaYvTo  https://www.youtube.com/watch?v=1-LxA5zFBiY&t=8118s
#https://www.youtube.com/watch?v=c0-Dk3l4D6I&t=2197s

#pqtEvLna8Sc