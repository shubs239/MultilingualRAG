import importlib.util
import os
import sys

from blog_draft import first_draft
from blog_feedback import first_feedback
from source_finder import process_claims
from image_fetch import fetch_featured_image
from image_gen import generate_images
from internal_linker import link_internal

# Load "final blog.py" (space in filename — can't use normal import)
spec = importlib.util.spec_from_file_location("final_blog", "final blog.py")
final_blog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final_blog)

link = input("Enter YouTube video ID: ").strip()

print("\n--- Stage 1: Generating draft ---")
_, slug = first_draft(link)
print(f"  Slug: {slug}")

print("\n--- Stage 2: Running feedback ---")
first_feedback(slug)

print("\n--- Stage 3: Generating final blog ---")
final_blog.final_draft(slug)

print("\n--- Stage 4: Finding sources ---")
process_claims(slug=slug)

print("\n--- Stage 5: Fetching featured image ---")
fetch_featured_image(slug=slug)

print("\n--- Stage 6: Generating social images ---")
generate_images(slug)

print("\n--- Stage 7: Inserting internal links ---")
link_internal(slug=slug)

print(f"\n--- Blog pipeline complete ---")
print(f"  Slug            : {slug}")
print(f"  draft_output/{slug}.json")
print(f"  feedback_output/{slug}.json")
print(f"  final_output/{slug}.json")
print(f"  social_output/{slug}.json")

# ── Optional: YouTube Shorts video ────────────────────────────────────────────
run_video = input("\nGenerate YouTube Shorts video now? (y/n): ").strip().lower()
if run_video == "y":
    video_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video")
    if video_dir not in sys.path:
        sys.path.insert(0, video_dir)
    from .video import shorts_pipeline
    shorts_pipeline.generate_short(slug=slug)

# ── Manual follow-up steps ─────────────────────────────────────────────────────
print("\nNext steps:")
print(f"  python wordpress_api.py {slug}   — post to WordPress as draft")
print(f"  python reedit_post.py {slug}     — generate social media content")
print(f"  python video/shorts_pipeline.py {slug}  — generate Shorts video later")
