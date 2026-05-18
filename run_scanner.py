#!/usr/bin/env python3
"""Scan ALL blogs (including previously processed ones)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.blogs_loader import load_blogs
from config.settings import DATA_DIR
from storage.database import init_db
from storage.cache import load_cache, save_cache
from core.scorer import score_blog

def main():
    print("🚀 Blog Scout - Full Scanner (ALL blogs)")
    print(f"📁 Data directory: {DATA_DIR}")
    print("⚠️  This will scan all blogs, including previously processed ones")
    print("-" * 50)
    
    confirm = input("Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return
    
    blogs = load_blogs()
    if not blogs:
        print("❌ No blogs found. Please add blogs to config/blogs.csv")
        return
    
    print(f"📊 Found {len(blogs)} blogs to scan")
    print("-" * 50)
    
    init_db()
    cache = load_cache()
    
    for name, url, rss_override in blogs:
        score_blog(name, url, rss_override, cache)
        print()
    
    save_cache(cache)
    
    print("-" * 50)
    print(f"✅ Full scan completed!")

if __name__ == "__main__":
    main()