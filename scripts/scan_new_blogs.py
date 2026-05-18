#!/usr/bin/env python3
"""Scan only newly added blogs that haven't been processed yet."""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.blogs_loader import load_blogs
from config.settings import DATA_DIR
from storage.database import init_db
from storage.cache import load_cache, save_cache
from core.scorer import score_blog

PROCESSED_TRACKER = "data/processed_blogs.json"

def load_tracker():
    """Load processed blogs tracker."""
    if os.path.exists(PROCESSED_TRACKER):
        with open(PROCESSED_TRACKER, 'r') as f:
            return json.load(f)
    return {"processed": {}, "failed": {}}

def save_tracker(tracker):
    """Save processed blogs tracker."""
    os.makedirs(os.path.dirname(PROCESSED_TRACKER), exist_ok=True)
    with open(PROCESSED_TRACKER, 'w') as f:
        json.dump(tracker, f, indent=2)

def mark_processed(blog_name, tracker, success=True):
    """Mark blog as processed or failed."""
    if success:
        tracker["processed"][blog_name] = datetime.now().isoformat()
        if blog_name in tracker["failed"]:
            del tracker["failed"][blog_name]
    else:
        tracker["failed"][blog_name] = datetime.now().isoformat()
    save_tracker(tracker)

def is_unprocessed(blog_name, tracker):
    """Check if blog hasn't been processed yet."""
    return blog_name not in tracker["processed"] and blog_name not in tracker["failed"]

def get_unprocessed_blogs():
    """Get list of blogs that haven't been processed."""
    all_blogs = load_blogs()
    tracker = load_tracker()
    unprocessed = []
    
    for name, url, rss_override in all_blogs:
        if is_unprocessed(name, tracker):
            unprocessed.append((name, url, rss_override))
    
    return unprocessed, tracker

def main():
    print("🚀 Blog Scout - New Blogs Scanner")
    print(f"📁 Data directory: {DATA_DIR}")
    print("-" * 50)
    
    # Get unprocessed blogs
    unprocessed_blogs, tracker = get_unprocessed_blogs()
    
    if not unprocessed_blogs:
        print("✨ No new blogs to scan! All blogs have been processed.")
        print("\n📝 To add new blogs:")
        print("   1. Edit config/blogs.csv manually")
        print("   2. Or run: python scripts/manage_blogs.py")
        return
    
    print(f"📊 Found {len(unprocessed_blogs)} new blog(s) to scan:")
    for name, url, _ in unprocessed_blogs:
        print(f"   - {name} ({url})")
    print("-" * 50)
    
    # Initialize database
    init_db()
    cache = load_cache()
    
    # Process only new blogs
    for name, url, rss_override in unprocessed_blogs:
        print(f"\n🆕 Processing new blog: {name}")
        try:
            score_blog(name, url, rss_override, cache)
            mark_processed(name, tracker, success=True)
            print(f"✅ Successfully processed {name}")
        except Exception as e:
            print(f"❌ Failed to process {name}: {e}")
            mark_processed(name, tracker, success=False)
        print()
    
    # Save cache
    save_cache(cache)
    
    print("-" * 50)
    print(f"✅ Scan complete!")
    print(f"   - Successfully processed: {len(tracker['processed'])} blogs")
    print(f"   - Failed: {len(tracker['failed'])} blogs")
    
    if tracker["failed"]:
        print("\n❌ Failed blogs:")
        for blog in tracker["failed"]:
            print(f"   - {blog}")

if __name__ == "__main__":
    main()