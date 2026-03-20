import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Load final output from pipeline
with open("final_output.json", "r", encoding="utf-8") as file:
    final_data = json.load(file)

# Step 1: Get JWT Token
auth_url = "https://castefreeindia.com/wp-json/api/v1/token"
WP_USERNAME = os.getenv("WP_USERNAME", "pappu4946@gmail.com")
WP_PASSWORD = os.getenv("WP_PASSWORD", "August@*28")
auth_data = {
    "username": WP_USERNAME,
    "password": WP_PASSWORD,
}
edit = False
# Authenticate to get token
#check if file token.txt exist and is not empty,


auth_response = requests.post(auth_url, data=auth_data)
#print(auth_response.json())
token = auth_response.json()['jwt_token']
#print("Token:", token)
if not token:
    print("Authentication failed!")
    exit()
else:
    print("Authentication success")

# Step 2: Create Post with JWT Token
post_url = "https://castefreeindia.com/wp-json/wp/v2/posts/"
new_post_url = "https://castefreeindia.com/wp-json/wp/v2/posts"
#get_url ="https://castefreeindia.com/wp-json/wp/v2/posts/1058"
def upload_featured_image(token, local_path):
    if not os.path.exists(local_path):
        print(f"  [media] File not found: {local_path}")
        return None
    filename = os.path.basename(local_path)
    ext = filename.rsplit(".", 1)[-1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": mime,
    }
    media_url = "https://castefreeindia.com/wp-json/wp/v2/media"
    with open(local_path, "rb") as f:
        r = requests.post(media_url, headers=headers, data=f)
    if r.status_code in (200, 201):
        media_id = r.json().get("id")
        print(f"  [media] Uploaded → ID {media_id}")
        return media_id
    print(f"  [media] Upload failed {r.status_code}: {r.text[:200]}")
    return None


post_data = {
    "title": final_data["title"]["blog_seo_title"],
    "content": final_data["content"]["blog_post_html"],
    "status": "draft",
}
featured_path = final_data.get("featured_image", {}).get("local_path")
if featured_path:
    media_id = upload_featured_image(token, featured_path)
    if media_id:
        post_data["featured_media"] = media_id
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


type_of_edit = input("Type edit, new: ")
if type_of_edit == "edit":
    edit = True
    id = input("Enter post id: ")
    post_url = f"https://castefreeindia.com/wp-json/wp/v2/posts/{id}"
    edit_response = edit_post(post_url=post_url, header=headers_post)
    #print(edit_response.status_code)
else:
    edit = False
    create_response = create_post(new_post_url=new_post_url, header= headers_post)

#get_response = get_post(get_url=get_url, header=headers_post)
if edit:
    if edit_response.status_code == 201 or edit_response.status_code == 200:
        print("Post edited successfully!")
    else:
        print("Error:", edit_response.status_code)
        print("Details:", edit_response.json()['title'])

if not edit:
    if create_response.status_code == 201 or create_response.status_code == 200:
        print("Post created successfully!")
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