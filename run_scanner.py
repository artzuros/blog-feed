#!/usr/bin/env python3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.blogs import BLOGS
from config.settings import DATA_DIR
from storage.database import init_db
from storage.cache import load_cache, save_cache
from core.scorer import score_blog

def main():
    print("🚀 Starting Blog Scout Scanner")
    print(f"📁 Data directory: {DATA_DIR}")
    print("-" * 50)
    
    # Initialize
    init_db()
    cache = load_cache()
    
    # Process each blog
    for name, url, rss_override in BLOGS:
        score_blog(name, url, rss_override, cache)
        print()
    
    # Save cache
    save_cache(cache)
    
    print("-" * 50)
    print(f"✅ Discovery cache saved")
    print(f"✅ Article database saved")
    print("🎉 Scanner completed!")

if __name__ == "__main__":
    main()