import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

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


def post_to_wordpress(slug=None):
    from utils import get_latest_slug
    if slug is None:
        slug = get_latest_slug("final_output")

    with open(f"final_output/{slug}.json", "r", encoding="utf-8") as f:
        final_data = json.load(f)

    auth_url = "https://castefreeindia.com/wp-json/api/v1/token"
    WP_USERNAME = os.getenv("WP_USERNAME")
    WP_PASSWORD = os.getenv("WP_PASSWORD")
    auth_response = requests.post(auth_url, data={"username": WP_USERNAME, "password": WP_PASSWORD})
    token = auth_response.json().get("jwt_token")
    if not token:
        print("Authentication failed!")
        return
    print("Authentication success")

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

    headers_post = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    new_post_url = "https://castefreeindia.com/wp-json/wp/v2/posts"

    type_of_edit = input("Type edit, new: ")
    if type_of_edit == "edit":
        post_id = input("Enter post id: ")
        post_url = f"https://castefreeindia.com/wp-json/wp/v2/posts/{post_id}"
        r = requests.post(url=post_url, json=post_data, headers=headers_post)
        print("Post edited successfully!" if r.status_code in (200, 201) else f"Error {r.status_code}: {r.json().get('message')}")
    else:
        r = requests.post(url=new_post_url, json=post_data, headers=headers_post)
        print("Post created successfully!" if r.status_code in (200, 201) else f"Error {r.status_code}: {r.json().get('message')}")


if __name__ == "__main__":
    slug_arg = input("Enter slug (leave blank for latest): ").strip() or None
    post_to_wordpress(slug_arg)
# response_edit= edit_post(post_url, headers_post)
# print(response_edit.status_code)
#print(response_edit.json())
# if edit_post(post_url, headers_post).status_code == 201:
#     print("Post Edited successfully!")
# else:
#     print("Error:", edit_post(post_url, headers_post).status_code)