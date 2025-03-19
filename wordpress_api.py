import requests
import json

# Path to your JSON file
json_file_path = "Blogs data/data.json"

# Load the JSON data from the file
with open(json_file_path, "r") as file:
    ai_post_data = json.load(file)

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
# with open('token.txt', 'r') as file:
#     token =file.read()
    #print("Authentication successful!")

# Step 2: Create Post with JWT Token
#post_url = "https://castefreeindia.com/wp-json/wp/v2/posts/1134"
new_post_url = "https://castefreeindia.com/wp-json/wp/v2/posts"
#get_url ="https://castefreeindia.com/wp-json/wp/v2/posts/1058"
post_data = {
    "title": ai_post_data[0]['title'],
    "content": ai_post_data[0]['content'],
    "status": "draft",
    "category": ai_post_data[0]['category']
    
}
# saved_token = open('token.txt', 'r')
# token = saved_token.read()

headers_post = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}
def get_post(get_url, header):
    response = requests.get(url=get_url, headers=header)
    print(response.status_code)
    print(response.json().keys())
    print(response.json()['title'])

    return response

def edit_post(post_url, header):
    response = requests.post(url=post_url, json= post_data, headers=header)
    #print(response.status_code)
    return response

def create_post(new_post_url, header):
    response = requests.post(url=new_post_url, json= post_data, headers=header)
    #print(response.status_code)
    return response

create_response = create_post(new_post_url=new_post_url, header= headers_post)
#edit_response = edit_post(post_url=post_url, header=headers_post)
#get_response = get_post(get_url=get_url, header=headers_post)
if create_response.status_code == 201 or create_response.status_code == 200:
    print("Post created/edited successfully!")
else:
    print("Error:", create_response.status_code)
    print("Details:", create_response.json()['title'])
# response_edit= edit_post(post_url, headers_post)
# print(response_edit.status_code)
#print(response_edit.json())
# if edit_post(post_url, headers_post).status_code == 201:
#     print("Post Edited successfully!")
# else:
#     print("Error:", edit_post(post_url, headers_post).status_code)