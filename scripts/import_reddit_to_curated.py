#!/usr/bin/env python3
"""Import accepted Reddit suggestions into curated blogs and fetch their articles."""
import sys
import os
import json
import time
from urllib.parse import urlparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.blogs_loader import add_blog, load_blogs
from core.fetcher import fetch_article_text
from core.rss_reader import get_articles_via_rss
from quality.slop_detector import is_likely_ai_slop
from core.llm_scorer import score_with_llm
from core.keywords import extract_keywords
from storage.database import save_article, init_db
from core.extractor import extract_articles_from_html

SUGGESTIONS_FILE = "data/reddit_suggestions.json"
PROCESSED_FILE = "data/reddit_accepted_processed.json"

def load_suggestions():
    if not os.path.exists(SUGGESTIONS_FILE):
        print(f"\n❌ No suggestions file found at {SUGGESTIONS_FILE}")
        return []
    
    with open(SUGGESTIONS_FILE, 'r') as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)

def save_suggestions(suggestions):
    os.makedirs(os.path.dirname(SUGGESTIONS_FILE), exist_ok=True)
    with open(SUGGESTIONS_FILE, 'w') as f:
        json.dump(suggestions, f, indent=2)

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_processed(processed):
    os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(processed, f, indent=2)

def auto_discover_rss(domain):
    """Try to discover RSS feed for a domain."""
    common_paths = [
        "/rss.xml",
        "/feed.xml", 
        "/index.xml",
        "/rss",
        "/feed",
        "/blog/rss.xml",
        "/blog/feed.xml"
    ]
    
    for path in common_paths:
        test_url = f"https://{domain}{path}"
        try:
            import requests
            resp = requests.head(test_url, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                return test_url
        except:
            continue
    return None

def fetch_article_from_suggestion(suggestion, limit=3):
    """Fetch articles from a Reddit-suggested blog."""
    domain = suggestion['domain']
    base_url = f"https://{domain}"
    
    print(f"\n📡 Processing suggested blog: {domain}")
    print(f"   Original post: {suggestion['title'][:70]}...")
    print(f"   Reddit score: {suggestion['reddit_score']} upvotes")
    
    # First try to find RSS feed
    rss_url = auto_discover_rss(domain)
    
    articles = []
    if rss_url:
        print(f"   ✅ Found RSS: {rss_url}")
        articles = get_articles_via_rss(rss_url, limit)
    
    if not articles:
        print(f"   🔍 No RSS found, trying HTML extraction")
        # Try to find blog homepage
        blog_url = suggestion.get('blog_url', base_url)
        articles = extract_articles_from_html(blog_url, domain, limit)
    
    return articles

def process_accepted_suggestion(suggestion, processed_list):
    """Process a single accepted suggestion and add articles to database."""
    domain = suggestion['domain']
    
    # Check if domain already in blogs.csv
    existing_blogs = load_blogs()
    for name, url, _ in existing_blogs:
        if domain in url:
            print(f"   ⚠️ Domain {domain} already exists in blogs.csv, skipping...")
            return True  # Count as success, don't add duplicate
    
    # Add to blogs.csv
    add_blog(suggestion['domain'], f"https://{domain}", None)
    print(f"   ✅ Added {domain} to blogs.csv")
    
    # Fetch articles from this blog
    articles = fetch_article_from_suggestion(suggestion)
    
    if not articles:
        print(f"   ⚠️ No articles found for {domain}")
        return False
    
    # Score and save each article
    articles_added = 0
    for title, url in articles[:3]:
        print(f"   📄 Fetching: {title[:60]}...")
        text = fetch_article_text(url)
        
        if text and len(text) > 200:
            heuristic_score, reason = is_likely_ai_slop(text)
            llm_score = None
            if len(text) > 500:
                llm_score = score_with_llm(text)
            
            combined = heuristic_score
            if llm_score:
                combined = (heuristic_score * 0.6) + (llm_score * 0.4)
            
            keywords = extract_keywords(text)
            
            save_article(
                url=url,
                title=title,
                blog_name=suggestion['domain'],
                score=heuristic_score,
                llm_score=llm_score,
                combined_score=combined,
                reason=reason,
                keywords=keywords,
                source='reddit',
                reddit_suggestion_id=suggestion.get('url', ''),
                added_by='manual_review'
            )
            print(f"      ✅ Added (combined score: {combined:.2f})")
            articles_added += 1
        else:
            print(f"      ⚠️ Could not extract text")
        
        time.sleep(1)
    
    return articles_added > 0

def main():
    print("=" * 60)
    print("Import Accepted Reddit Suggestions to Curated Blogs")
    print("=" * 60)
    
    suggestions = load_suggestions()
    if not suggestions:
        return
    
    processed = load_processed()
    
    # Get suggestions that are accepted and not yet processed
    ready_suggestions = []
    for s in suggestions:
        suggestion_id = s.get('url')
        if suggestion_id not in processed:
            if s.get('accepted') == True:  # Only accepted suggestions
                ready_suggestions.append(s)
    
    if not ready_suggestions:
        print("\n📭 No accepted suggestions ready for import.")
        print("\nTo accept suggestions:")
        print("   1. Run 'python scripts/accept_reddit_suggestion.py'")
        print("   2. Mark suggestions as 'accepted'")
        print("\nThen run this script again.")
        return
    
    print(f"\n📊 Found {len(ready_suggestions)} accepted suggestion(s):")
    for i, s in enumerate(ready_suggestions, 1):
        score = s.get('combined_score', s.get('heuristic_score', 0))
        reviewed_by = s.get('reviewed', 'unknown')
        print(f"   {i}. {s['domain']:35} | score: {score:.2f} | reviewed: {reviewed_by}")
    
    print("\n" + "-" * 60)
    confirm = input("\nAdd these blogs to your curated list and fetch articles? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Cancelled.")
        return
    
    # Process each suggestion
    success_count = 0
    for suggestion in ready_suggestions:
        print(f"\n{'=' * 50}")
        try:
            if process_accepted_suggestion(suggestion, processed):
                processed.append(suggestion.get('url'))
                success_count += 1
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Save processed tracking
    save_processed(processed)
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully imported {success_count}/{len(ready_suggestions)} blogs")
    
    if success_count > 0:
        print("\n📝 Next steps:")
        print("   1. Run 'python scripts/scheduled_scan.py' to fetch all articles from your updated blog list")
        print("   2. Or wait for the daily cron job to pick them up")
    
    # Show what was added
    if success_count > 0:
        print("\n📋 Updated blogs.csv now contains:")
        blogs = load_blogs()
        for name, url, rss in blogs[-success_count:]:
            print(f"   - {name}: {url}")

if __name__ == "__main__":
    main()