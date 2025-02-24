from google import genai
from google.genai import types
from blog_feedback import  first_feedback
from blog_draft import first_draft
client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")
sys_instruct_final="""Role: Technical Editor & SEO Optimizer
Objective: Revise the blog using feedback from the Quality Analyst.
**Task**:  
1. Revise the blog step-by-step:  
   - Adjust structure per flow suggestions.  
   - Add/replace keywords as advised.  
2. Ensure:  
   - Keyword density remains 1–2%."""#client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")

def final_draft(link):
    response_final = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct_final,
            max_output_tokens=20024),
        contents=[f"This is the Blog: {first_draft(link)}. This is the feedback: {first_feedback(link)} **Output**: Revised blog with changes shown if any "]
    )
    return (response_final.text)


def write_blog(link):
    with open('blog1.txt', 'w') as file:
    # Write content to the file
        file.write(final_draft(link))
        print("Writing Done")

write_blog(link="GAmQe3nWhvc")