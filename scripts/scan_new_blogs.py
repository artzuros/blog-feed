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
from api.logger import scan_logger

PROCESSED_TRACKER = "data/processed_blogs.json"

def load_tracker():
    """Load processed blogs tracker."""
    scan_logger.debug(f"Loading tracker from {PROCESSED_TRACKER}")
    
    if os.path.exists(PROCESSED_TRACKER):
        try:
            with open(PROCESSED_TRACKER, 'r') as f:
                content = f.read().strip()
                if content:
                    tracker = json.loads(content)
                    scan_logger.debug(f"Loaded tracker: {len(tracker.get('processed', {}))} processed, {len(tracker.get('failed', {}))} failed")
                    return tracker
                else:
                    return {"processed": {}, "failed": {}}
        except json.JSONDecodeError as e:
            scan_logger.error(f"Tracker file corrupted: {e}", exc_info=True)
            return {"processed": {}, "failed": {}}
    
    scan_logger.debug("No tracker file found, creating new")
    return {"processed": {}, "failed": {}}

def save_tracker(tracker):
    """Save processed blogs tracker."""
    try:
        os.makedirs(os.path.dirname(PROCESSED_TRACKER), exist_ok=True)
        with open(PROCESSED_TRACKER, 'w') as f:
            json.dump(tracker, f, indent=2)
        scan_logger.debug(f"Tracker saved: {len(tracker.get('processed', {}))} processed, {len(tracker.get('failed', {}))} failed")
    except Exception as e:
        scan_logger.error(f"Failed to save tracker: {e}", exc_info=True)

def mark_processed(blog_name, tracker, success=True):
    """Mark blog as processed or failed."""
    if success:
        tracker["processed"][blog_name] = datetime.now().isoformat()
        if blog_name in tracker["failed"]:
            del tracker["failed"][blog_name]
        scan_logger.info(f"Blog marked as processed: {blog_name}")
    else:
        tracker["failed"][blog_name] = datetime.now().isoformat()
        scan_logger.error(f"Blog marked as failed: {blog_name}")
    
    save_tracker(tracker)

def is_unprocessed(blog_name, tracker):
    """Check if blog hasn't been processed yet."""
    unprocessed = blog_name not in tracker["processed"] and blog_name not in tracker["failed"]
    if unprocessed:
        scan_logger.debug(f"Blog is unprocessed: {blog_name}")
    return unprocessed

def get_unprocessed_blogs():
    """Get list of blogs that haven't been processed."""
    all_blogs = load_blogs()
    tracker = load_tracker()
    unprocessed = []
    
    for name, url, rss_override in all_blogs:
        if is_unprocessed(name, tracker):
            unprocessed.append((name, url, rss_override))
    
    scan_logger.info(f"Found {len(unprocessed)} unprocessed blogs out of {len(all_blogs)} total")
    return unprocessed, tracker

def main():
    print("🚀 Blog Scout - New Blogs Scanner")
    print(f"📁 Data directory: {DATA_DIR}")
    print("-" * 50)
    
    scan_logger.info("Starting new blogs scanner")
    
    # Get unprocessed blogs
    unprocessed_blogs, tracker = get_unprocessed_blogs()
    
    if not unprocessed_blogs:
        scan_logger.info("No new blogs to scan")
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
    try:
        init_db()
        scan_logger.info("Database initialized")
    except Exception as e:
        scan_logger.error(f"Failed to initialize database: {e}", exc_info=True)
        print(f"❌ Database initialization failed: {e}")
        return
    
    cache = load_cache()
    success_count = 0
    fail_count = 0
    
    # Process only new blogs
    for name, url, rss_override in unprocessed_blogs:
        print(f"\n🆕 Processing new blog: {name}")
        scan_logger.info(f"Processing blog: {name} ({url})")
        
        try:
            score_blog(name, url, rss_override, cache)
            mark_processed(name, tracker, success=True)
            success_count += 1
            print(f"✅ Successfully processed {name}")
        except Exception as e:
            scan_logger.error(f"Failed to process {name}: {e}", exc_info=True)
            mark_processed(name, tracker, success=False)
            fail_count += 1
            print(f"❌ Failed to process {name}: {e}")
        print()
    
    # Save cache
    save_cache(cache)
    
    print("-" * 50)
    print(f"✅ Scan complete!")
    print(f"   - Successfully processed: {success_count} blogs")
    print(f"   - Failed: {fail_count} blogs")
    
    scan_logger.info(f"Scan complete: {success_count} succeeded, {fail_count} failed")
    
    if tracker["failed"]:
        print("\n❌ Failed blogs:")
        for blog in tracker["failed"]:
            print(f"   - {blog}")

if __name__ == "__main__":
    main()