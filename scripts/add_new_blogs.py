#!/usr/bin/env python3
"""Utility to add new blogs to the configuration."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.blogs import BLOGS

def add_blog():
    print("Add a new engineering blog")
    print("-" * 40)
    
    name = input("Blog name: ").strip()
    url = input("Blog URL (e.g., https://example.com/blog): ").strip()
    rss = input("RSS URL (or press Enter if unknown): ").strip()
    
    if not rss:
        rss = None
    
    # Append to BLOGS list in file
    with open("config/blogs.py", "a") as f:
        f.write(f'    ("{name}", "{url}", {repr(rss)}),\n')
    
    print(f"\n✅ Added {name} to config/blogs.py")
    print("Run run_scanner.py to fetch articles.")

if __name__ == "__main__":
    add_blog()