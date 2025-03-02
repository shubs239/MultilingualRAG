import requests

url = "https://castefreeindia.com/wp-json/wp/v2/posts"

response = requests.get(url)

# Checking if the request was successful
if response.status_code == 200:
    # Parsing the JSON response
    posts = response.json()
    
    # Printing the posts
    for post in posts:
        print(f"Title: {post['title']['rendered']}")
        #print(f"Content: {post['content']['rendered']}")
        print(f"Date: {post['date']}")
        print("-" * 40)
else:
    print(f"Failed to retrieve data. Status code: {response.status_code}")