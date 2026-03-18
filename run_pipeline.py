import importlib.util
import sys
from blog_draft import first_draft
from blog_feedback import first_feedback
from source_finder import process_claims

# Load "final blog.py" (has a space — can't use normal import)
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

print("\nDone. Check final_output.json.")
print("Next steps:")
print("  python wordpress_api.py   — post to WordPress as draft")
print("  python reedit_post.py     — generate social media content")
