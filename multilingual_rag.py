import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from fetch_caption import caption
# Load environment variables
load_dotenv()
api_key = os.getenv('API_KEY')

# Initialize the Gemini client

client = genai.Client(api_key=api_key)
# System instruction for the RAG bot
sys_instruct = """
You are a helpful AI assistant designed to answer questions based on the provided youtube transcript.
Transcript willl be in json, with start time in sec, text, and suration in sec.
If the answer is not found in the transcript, respond with 'I'm sorry, but I cannot find the answer to that question within the provided documents.'.
Be concise and provide direct answers whenever possible.
"""
transcript = caption(link="Ehce8IIxwX0")
# Function to create a new chat session
def create_chat_session(history):
    response_final = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_instruct,
            
            temperature=0.2,
            max_output_tokens=20024),
        contents=[f"This is the Transcript: {transcript}.This is history of chat. {history}"]
    )
    return (response_final)

# Function to load context from files
history={}
while True:

    question = input("Question: ")
    history["user"]=question
    ans = create_chat_session(history=history)
    print(ans.text)
    history["ai"]=ans.text

