#!/usr/bin/env python3
"""Add new blogs to configuration with tracking."""
import sys
import os
import re
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.logger import scan_logger

PROCESSED_TRACKER = "data/processed_blogs.json"
BLOGS_FILE = "config/blogs.py"

def load_tracker():
    """Load processed blogs tracker."""
    scan_logger.debug(f"Loading tracker from {PROCESSED_TRACKER}")
    
    if os.path.exists(PROCESSED_TRACKER):
        try:
            with open(PROCESSED_TRACKER, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            scan_logger.error(f"Tracker file corrupted: {e}")
            return {"processed": {}, "failed": {}}
    return {"processed": {}, "failed": {}}

def save_tracker(tracker):
    """Save processed blogs tracker."""
    try:
        os.makedirs(os.path.dirname(PROCESSED_TRACKER), exist_ok=True)
        with open(PROCESSED_TRACKER, 'w') as f:
            json.dump(tracker, f, indent=2)
        scan_logger.debug(f"Tracker saved: {len(tracker.get('processed', {}))} processed")
    except Exception as e:
        scan_logger.error(f"Failed to save tracker: {e}", exc_info=True)

def read_existing_blogs():
    """Read existing blogs from config/blogs.py."""
    scan_logger.debug(f"Reading existing blogs from {BLOGS_FILE}")
    
    try:
        with open(BLOGS_FILE, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        scan_logger.error(f"Blogs file not found: {BLOGS_FILE}")
        return []
    
    # Find the BLOGS list
    pattern = r'BLOGS\s*=\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        scan_logger.error("Could not find BLOGS list in config/blogs.py")
        print("❌ Could not find BLOGS list in config/blogs.py")
        return []
    
    # Extract all blog names
    blogs = []
    lines = match.group(1).split('\n')
    for line in lines:
        # Match pattern: ("Name", "url", "rss")
        blog_match = re.search(r'\(\s*"([^"]+)"', line)
        if blog_match:
            blogs.append(blog_match.group(1))
    
    scan_logger.debug(f"Found {len(blogs)} existing blogs")
    return blogs

def add_blog_to_config(name, url, rss):
    """Add a new blog to the BLOGS list in config/blogs.py."""
    scan_logger.info(f"Adding blog to config: {name} ({url})")
    
    try:
        with open(BLOGS_FILE, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        scan_logger.error(f"Cannot read {BLOGS_FILE}")
        return False
    
    # Find the line where BLOGS list ends (the ']' on its own line or after last entry)
    insert_pos = -1
    for i, line in enumerate(lines):
        if line.strip() == ']' or (line.strip().startswith(']') and i > 0):
            insert_pos = i
            break
    
    if insert_pos == -1:
        scan_logger.error("Could not find end of BLOGS list")
        print("❌ Could not find end of BLOGS list")
        return False
    
    # Create the new entry with proper indentation
    new_entry = f'    ("{name}", "{url}", {repr(rss)}),\n'
    
    # Insert before the closing bracket
    lines.insert(insert_pos, new_entry)
    
    # Write back
    try:
        with open(BLOGS_FILE, 'w') as f:
            f.writelines(lines)
        scan_logger.info(f"Successfully added {name} to config")
        return True
    except Exception as e:
        scan_logger.error(f"Failed to write to {BLOGS_FILE}: {e}", exc_info=True)
        return False

def add_single_blog():
    """Add a single blog interactively."""
    print("Add a new engineering blog")
    print("-" * 40)
    
    name = input("Blog name: ").strip()
    url = input("Blog URL (e.g., https://example.com/blog): ").strip()
    rss_input = input("RSS URL (or press Enter if unknown): ").strip()
    
    rss = rss_input if rss_input else None
    
    # Check if blog already exists
    existing = read_existing_blogs()
    if name in existing:
        scan_logger.warning(f"Attempted to add duplicate blog: {name}")
        print(f"❌ Blog '{name}' already exists in config!")
        return
    
    # Add to config
    if add_blog_to_config(name, url, rss):
        scan_logger.info(f"Single blog added: {name}")
        print(f"\n✅ Added {name} to {BLOGS_FILE}")
        print(f"📝 Run 'python scripts/scan_new_blogs.py' to fetch articles.")
    else:
        scan_logger.error(f"Failed to add blog: {name}")
        print(f"❌ Failed to add {name}")

def add_multiple_blogs():
    """Add multiple blogs at once."""
    print("Add multiple engineering blogs")
    print("Enter in format: name, url, rss")
    print("Example: Netflix, https://netflixtechblog.com, https://netflixtechblog.com/feed")
    print("For no RSS, use: None or leave empty")
    print("-" * 40)
    
    blogs_to_add = []
    existing = read_existing_blogs()
    
    while True:
        entry = input("Blog (or 'done' to finish): ").strip()
        if entry.lower() == 'done':
            break
        if not entry:
            continue
        
        parts = [p.strip() for p in entry.split(',')]
        if len(parts) >= 2:
            name = parts[0]
            url = parts[1]
            rss = parts[2] if len(parts) > 2 and parts[2] not in ['None', ''] else None
            
            if name in existing:
                scan_logger.debug(f"Skipping duplicate: {name}")
                print(f"  ⚠️ Skipping {name} - already exists")
            else:
                blogs_to_add.append((name, url, rss))
                existing.append(name)  # Prevent duplicates in same batch
        else:
            print("  Invalid format. Use: Name, URL, RSS")
    
    if not blogs_to_add:
        scan_logger.debug("No new blogs to add")
        print("No new blogs to add.")
        return
    
    # Add all blogs
    for name, url, rss in blogs_to_add:
        if add_blog_to_config(name, url, rss):
            print(f"  ✅ Added {name}")
        else:
            print(f"  ❌ Failed to add {name}")
    
    scan_logger.info(f"Added {len(blogs_to_add)} new blogs")
    print(f"\n✅ Added {len(blogs_to_add)} new blog(s)")
    print(f"📝 Run 'python scripts/scan_new_blogs.py' to fetch articles.")

def show_current_blogs():
    """Display current blogs in config."""
    existing = read_existing_blogs()
    scan_logger.debug(f"Showing {len(existing)} current blogs")
    print("\n📚 Current blogs in config:")
    print("-" * 40)
    for i, blog in enumerate(existing, 1):
        print(f"  {i}. {blog}")
    print(f"\nTotal: {len(existing)} blogs")

if __name__ == "__main__":
    print("\n📝 Blog Management Script")
    print("=" * 40)
    print("1. Show current blogs")
    print("2. Add single blog")
    print("3. Add multiple blogs")
    print("4. Exit")
    
    choice = input("\nChoice (1/2/3/4): ").strip()
    
    if choice == "1":
        show_current_blogs()
    elif choice == "2":
        add_single_blog()
    elif choice == "3":
        add_multiple_blogs()
    else:
        scan_logger.info("Blog management script exited")
        print("Goodbye!")