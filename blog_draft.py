from google import genai
from google.genai import types
from fetch_caption import  caption
client = genai.Client(api_key="AIzaSyAldWTRZwX-4UZcMwJYwwdnL_DGTleNTLM")
sys_instruct_initial="""You are AI Content repurposer. You will be given Context in hindi and you have to follow the below instructions.
 
**Tone**: authoritative with knowledge
**Keyword**: Caste, SC, ST, OBC, Brahminism, Hinduism 
**Task**:  

1. Structure the blog as follows:  
   - Introduction (hook + keyword mention)  
   - 7-10 H2 sections with 3–4 H3 subsections  
   - Data-driven examples (cite 8–10 sources which were used in the context)  
   - Conclusion with call-to-action 
   - Write [insert image here] whenever you mention any refreneces used in the context. 
   - Quote the refrences used in the context
   - Don't include any names of the persons/people involved in converstaion in the context
   - Include a disclaimer which list the common terms used in the blog and what it means in the context like brahmin implied brahminism ideology etc.
   - Start HTML from heading tag
2. Add SEO elements:  
   - Meta title (65 chars)  
   - Meta description (155 chars)  
    
3. Ensure readability (Grade 8 level).  
"""
def first_draft(link):
    initial_response = client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(
        system_instruction=sys_instruct_initial,
        max_output_tokens=20024),
    contents=[f"This is the context: {caption(link=link)}. **Output**: Blog of atleast 3000 words in English in HTML."]
    )
    return (initial_response.text)


def write_blog(link):
    with open('blog_initial.txt', 'w') as file:
    # Write content to the file
        file.write(first_draft(link))
        print("Writing Done")

write_blog(link="GAmQe3nWhvc")