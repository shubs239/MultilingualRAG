import importlib.util
import sys
from blog_draft import first_draft
from blog_feedback import first_feedback
from source_finder import process_claims
from image_fetch import fetch_featured_image
from image_gen import generate_images
from internal_linker import link_internal

# Load "final blog.py" (has a space — can't use normal import) // Why?
#
spec = importlib.util.spec_from_file_location("final_blog", "final blog.py")
final_blog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final_blog)

link = input("Enter YouTube video ID: ").strip()

print("\n--- Stage 1: Generating draft ---")
first_draft(link)

print("\n--- Stage 2: Running feedback ---")
first_feedback()

print("\n--- Stage 3: Generating final blog ---")
final_blog.final_draft()

print("\n--- Stage 4: Finding sources ---")
process_claims()

print("\n--- Stage 5: Fetching featured image ---")
fetch_featured_image()

print("\n--- Stage 6: Generating social images ---")
generate_images()

print("\n--- Stage 7: Inserting internal links ---")
link_internal()

print("\nDone. Check final_output.json and social_output.json.")
print("Next steps:")
print("  python wordpress_api.py   — post to WordPress as draft")
print("  python reedit_post.py     — generate social media content")
