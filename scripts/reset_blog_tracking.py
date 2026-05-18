#!/usr/bin/env python3
"""Reset tracking for specific blogs (to force re-scan)."""
import sys
import os
import json

PROCESSED_TRACKER = "data/processed_blogs.json"

def load_tracker():
    if os.path.exists(PROCESSED_TRACKER):
        with open(PROCESSED_TRACKER, 'r') as f:
            return json.load(f)
    return {"processed": {}, "failed": {}}

def save_tracker(tracker):
    with open(PROCESSED_TRACKER, 'w') as f:
        json.dump(tracker, f, indent=2)

def reset_blog(blog_name):
    tracker = load_tracker()
    if blog_name in tracker["processed"]:
        del tracker["processed"][blog_name]
        print(f"✅ Reset tracking for {blog_name}")
    elif blog_name in tracker["failed"]:
        del tracker["failed"][blog_name]
        print(f"✅ Reset tracking for {blog_name} (was failed)")
    else:
        print(f"❌ Blog '{blog_name}' not found in tracker")
    save_tracker(tracker)

def list_tracked_blogs():
    tracker = load_tracker()
    print("\n📊 Processed blogs:")
    for blog in tracker["processed"]:
        print(f"   ✅ {blog}")
    print("\n❌ Failed blogs:")
    for blog in tracker["failed"]:
        print(f"   ❌ {blog}")

if __name__ == "__main__":
    print("1. List tracked blogs")
    print("2. Reset specific blog")
    print("3. Reset ALL blogs")
    choice = input("Choice (1/2/3): ").strip()
    
    if choice == "1":
        list_tracked_blogs()
    elif choice == "2":
        blog_name = input("Blog name to reset: ").strip()
        reset_blog(blog_name)
    elif choice == "3":
        confirm = input("Reset ALL blogs? (y/n): ").strip()
        if confirm.lower() == 'y':
            save_tracker({"processed": {}, "failed": {}})
            print("✅ Reset all blog tracking")
    else:
        print("Invalid choice")