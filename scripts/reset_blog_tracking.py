#!/usr/bin/env python3
"""Reset tracking for specific blogs (to force re-scan)."""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.logger import scan_logger

PROCESSED_TRACKER = "data/processed_blogs.json"

def load_tracker():
    scan_logger.debug(f"Loading tracker from {PROCESSED_TRACKER}")
    
    if os.path.exists(PROCESSED_TRACKER):
        try:
            with open(PROCESSED_TRACKER, 'r') as f:
                tracker = json.load(f)
                scan_logger.debug(f"Tracker loaded: {len(tracker.get('processed', {}))} processed, {len(tracker.get('failed', {}))} failed")
                return tracker
        except json.JSONDecodeError as e:
            scan_logger.error(f"Tracker file corrupted: {e}")
            return {"processed": {}, "failed": {}}
    return {"processed": {}, "failed": {}}

def save_tracker(tracker):
    try:
        with open(PROCESSED_TRACKER, 'w') as f:
            json.dump(tracker, f, indent=2)
        scan_logger.debug(f"Tracker saved: {len(tracker.get('processed', {}))} processed, {len(tracker.get('failed', {}))} failed")
    except Exception as e:
        scan_logger.error(f"Failed to save tracker: {e}", exc_info=True)

def reset_blog(blog_name):
    scan_logger.info(f"Resetting tracking for blog: {blog_name}")
    tracker = load_tracker()
    
    if blog_name in tracker["processed"]:
        del tracker["processed"][blog_name]
        scan_logger.info(f"Reset processed blog: {blog_name}")
        print(f"✅ Reset tracking for {blog_name}")
    elif blog_name in tracker["failed"]:
        del tracker["failed"][blog_name]
        scan_logger.info(f"Reset failed blog: {blog_name}")
        print(f"✅ Reset tracking for {blog_name} (was failed)")
    else:
        scan_logger.warning(f"Blog not found in tracker: {blog_name}")
        print(f"❌ Blog '{blog_name}' not found in tracker")
    
    save_tracker(tracker)

def list_tracked_blogs():
    tracker = load_tracker()
    print("\n📊 Processed blogs:")
    for blog in tracker["processed"]:
        print(f"   ✅ {blog} (processed at: {tracker['processed'][blog][:19] if tracker['processed'][blog] else 'unknown'})")
    print("\n❌ Failed blogs:")
    for blog in tracker["failed"]:
        print(f"   ❌ {blog} (failed at: {tracker['failed'][blog][:19] if tracker['failed'][blog] else 'unknown'})")

def reset_all_blogs():
    scan_logger.warning("Resetting ALL blog tracking")
    confirm = input("⚠️ Reset ALL blogs? This will force re-scan of all blogs. (y/n): ").strip()
    if confirm.lower() == 'y':
        save_tracker({"processed": {}, "failed": {}})
        scan_logger.info("All blog tracking reset")
        print("✅ Reset all blog tracking")
    else:
        scan_logger.debug("Reset cancelled by user")
        print("Cancelled.")

if __name__ == "__main__":
    print("\n🔄 Blog Tracking Reset Tool")
    print("=" * 40)
    print("1. List tracked blogs")
    print("2. Reset specific blog")
    print("3. Reset ALL blogs")
    print("4. Exit")
    
    choice = input("\nChoice (1/2/3/4): ").strip()
    
    if choice == "1":
        list_tracked_blogs()
    elif choice == "2":
        blog_name = input("Blog name to reset: ").strip()
        if blog_name:
            reset_blog(blog_name)
        else:
            print("No blog name provided.")
    elif choice == "3":
        reset_all_blogs()
    elif choice == "4":
        print("Goodbye!")
    else:
        print("Invalid choice")