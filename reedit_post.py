import requests
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('API_KEY')

# Initialize the Gemini client

client = genai.Client(api_key=api_key)
# System instruction for the RAG bot
sys_instruct = """
 You will be given the content of the article in html format. You have to repurpose it for reddit and X.
   Use Sarcastic and satirical tone. Promote discussion. Write a satire this time.
For Reddit: I want people to read a part of the article and make it so controversial that they want to click on the article link and read it completely. Add interesting and controversial parts from the article to make it enticing to open the link. 


For X: Here, you can create a short excerpt that is interesting and controversial so people want to read more. You also have to suggest hashtags accordingly.Remember to be within X's word limit.
"""


#print(post_data[0]['title'])
# Step 1: Get JWT Token
auth_url = "https://castefreeindia.com/wp-json/api/v1/token"
auth_data = {
    "username": "pappu4946@gmail.com",
    "password": "August@*28",
}

# Authenticate to get token
#check if file token.txt exist and is not empty, 


auth_response = requests.post(auth_url, data=auth_data)
#   print(auth_response.json()['jwt_token'])
token = auth_response.json()['jwt_token']
#print("Token:", token)
if not token:
    print("Authentication failed!")
    exit()
else:
    print("Authentication success")

post_id = input("Enter the post id: ")
get_url =f"https://castefreeindia.com/wp-json/wp/v2/posts/{post_id}"



headers_post = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}
def get_post(get_url, header):
    response = requests.get(url=get_url, headers=header)
    print(response.status_code)
    
    

    return response

def create_social_media_post(content):
    initial_response = client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(
        system_instruction=sys_instruct,
        max_output_tokens=20024),
    contents=[f"This is the content in HTML format: {content}. **Output**: Reddit Post and X post with hashtags."]
    )
    return (initial_response.text)

post_response = get_post(get_url, headers_post)

with open("Blogs data/redditpost.txt","w") as file:
    file.write(create_social_media_post(post_response.json()['content']['rendered']))
    print("File created successfully")
    file.close()
#print(create_social_media_post(post_response.json()['content']['rendered']))