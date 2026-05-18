#!/usr/bin/env python3
"""Discover good engineering blogs from Reddit, suggest them for addition to blogs.csv."""
import sys
import os
import json
import time
import requests
import feedparser
from urllib.parse import urlparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fetcher import fetch_article_text
from quality.slop_detector import is_likely_ai_slop
from core.llm_scorer import score_with_llm
from config.blogs_loader import load_blogs
from config.settings import USER_AGENT

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
SUBREDDITS = [
    "programming",
    "devops",
    "ExperiencedDevs",
    "sre",
    "engineering",
    "rust",
    "golang",
    "webdev",
    "databases"
]

SCORE_THRESHOLD = 0.45         # Suggest if heuristic score <= this (0=excellent, 1=slop)
VERBOSE = True
MAX_ARTICLES_PER_SUBREDDIT = 15
REQUEST_DELAY = 2              # seconds between article fetches

SUGGESTIONS_FILE = "data/reddit_suggestions.json"
TRACKING_FILE = "data/reddit_tracked_urls.json"

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def load_tracked_urls():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    return {}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def load_suggestions():
    if os.path.exists(SUGGESTIONS_FILE):
        try:
            with open(SUGGESTIONS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    return []
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_tracked_urls(tracked):
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracked, f, indent=2)

def save_suggestions(suggestions):
    os.makedirs(os.path.dirname(SUGGESTIONS_FILE), exist_ok=True)
    with open(SUGGESTIONS_FILE, 'w') as f:
        json.dump(suggestions, f, indent=2)

def is_domain_in_blogs(domain, blogs):
    """Check if domain (e.g., tailscale.com) is already in our curated list."""
    for _, url, _ in blogs:
        parsed = urlparse(url)
        if parsed.netloc == domain or domain in parsed.netloc:
            return True
    return False

def extract_domain_from_url(url):
    parsed = urlparse(url)
    return parsed.netloc

def fetch_reddit_posts(subreddit, limit=25):
    """Fetch top posts from Reddit using JSON API (more reliable than RSS)."""
    json_url = f"https://www.reddit.com/r/{subreddit}/top.json?t=month&limit={limit}"
    headers = {'User-Agent': USER_AGENT}
    
    try:
        resp = requests.get(json_url, headers=headers, timeout=15)
        data = resp.json()
        entries = []
        
        for post in data['data']['children']:
            post_data = post['data']
            url = post_data.get('url', '')
            title = post_data.get('title', '')
            score = post_data.get('score', 0)
            num_comments = post_data.get('num_comments', 0)
            created_utc = post_data.get('created_utc', 0)
            
            # Skip self-posts and reddit-internal links
            if not url or 'reddit.com' in url or url.startswith('/'):
                if VERBOSE:
                    print(f"    ⏭️ Skipping self-post: {title[:50]}...")
                continue
            
            # Skip domains that are almost always low-quality
            skip_domains = ['medium.com', 'towardsdatascience.com', 'dev.to', 'hashnode.com', 'youtube.com', 'github.com']
            if any(skip in url for skip in skip_domains):
                if VERBOSE:
                    print(f"    ⏭️ Skipping known low-quality domain: {urlparse(url).netloc}")
                continue
            
            entries.append({
                'title': title,
                'url': url,
                'score': score,
                'num_comments': num_comments,
                'published': datetime.fromtimestamp(created_utc).isoformat(),
                'subreddit': subreddit
            })
            
            if VERBOSE:
                print(f"    ✅ Found external: {title[:60]}... ({urlparse(url).netloc}) [{score} upvotes]")
        
        return entries
    except Exception as e:
        print(f"  ⚠️ Failed to fetch r/{subreddit} via JSON: {e}")
        return []

def review_with_llm(suggestion):
    """Review a suggestion using LLM and update its status."""
    print(f"\n🤖 Reviewing with LLM: {suggestion['domain']}")
    print(f"   Article: {suggestion['title'][:70]}...")
    
    # Fetch full article text
    text = fetch_article_text(suggestion['url'])
    if not text or len(text) < 200:
        print(f"   ❌ Cannot review - insufficient text extracted")
        return None
    
    # Get LLM score
    llm_score = score_with_llm(text)
    if llm_score is None:
        print(f"   ❌ LLM scoring failed")
        return None
    
    print(f"   📊 LLM score: {llm_score:.2f}")
    
    # Update suggestion with LLM review
    suggestion['llm_score'] = llm_score
    suggestion['combined_score'] = (suggestion['heuristic_score'] * 0.6) + (llm_score * 0.4)
    suggestion['reviewed'] = 'llm'
    suggestion['reviewed_at'] = datetime.now().isoformat()
    
    return suggestion

def process_reddit_posts():
    blogs = load_blogs()
    tracked_urls = load_tracked_urls()
    suggestions = load_suggestions()
    new_suggestions = []
    total_tested = 0
    
    print("\n🔍 Scanning Reddit for high-quality engineering links...")
    print(f"Score threshold: {SCORE_THRESHOLD} (lower = better content)")
    print("-" * 60)
    
    for subreddit in SUBREDDITS:
        print(f"\n📡 r/{subreddit}")
        posts = fetch_reddit_posts(subreddit, MAX_ARTICLES_PER_SUBREDDIT)
        if not posts:
            print(f"    No external links found in r/{subreddit}")
            continue
        
        for post in posts:
            url = post['url']
            total_tested += 1
            
            # Skip if already tracked
            if url in tracked_urls:
                if VERBOSE:
                    print(f"    ⏭️ Already tracked: {post['title'][:50]}...")
                continue
            
            domain = extract_domain_from_url(url)
            
            # Skip if domain already in our curated list
            if is_domain_in_blogs(domain, blogs):
                if VERBOSE:
                    print(f"    ⏭️ Domain already curated: {domain}")
                tracked_urls[url] = {'skipped': 'already_curated', 'domain': domain, 'timestamp': datetime.now().isoformat()}
                continue
            
            print(f"\n  🧪 Testing [{domain}]: {post['title'][:70]}...")
            print(f"     Reddit score: {post['score']} upvotes, {post['num_comments']} comments")
            
            # Fetch and score the article (heuristic only for speed)
            text = fetch_article_text(url)
            if not text or len(text) < 200:
                print(f"      ❌ Failed to extract text (too short or blocked)")
                tracked_urls[url] = {'skipped': 'no_extractable_text', 'domain': domain, 'timestamp': datetime.now().isoformat()}
                continue
            
            heuristic_score, reason = is_likely_ai_slop(text)
            print(f"      📊 Heuristic score: {heuristic_score:.2f} – {reason}")
            
            # If good enough, suggest it
            if heuristic_score <= SCORE_THRESHOLD:
                suggestion = {
                    'url': url,
                    'domain': domain,
                    'title': post['title'],
                    'subreddit': subreddit,
                    'reddit_score': post['score'],
                    'reddit_comments': post['num_comments'],
                    'heuristic_score': heuristic_score,
                    'heuristic_reason': reason,
                    'discovered_at': datetime.now().isoformat(),
                    'reviewed': 'pending'  # pending, llm, manual
                }
                # Avoid duplicate suggestions
                if not any(s['url'] == url for s in suggestions):
                    new_suggestions.append(suggestion)
                    print(f"      ✅ ** SUGGESTION: Consider adding {domain} (heuristic score {heuristic_score:.2f})")
                    print(f"         URL: {url}")
                else:
                    print(f"      ℹ️ Already suggested previously")
            else:
                print(f"      ❌ Score {heuristic_score:.2f} > threshold {SCORE_THRESHOLD} – not suggesting (likely slop)")
            
            tracked_urls[url] = {
                'domain': domain,
                'heuristic_score': heuristic_score,
                'reason': reason,
                'reddit_score': post['score'],
                'timestamp': datetime.now().isoformat()
            }
            
            time.sleep(REQUEST_DELAY)  # Be polite
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Summary: Tested {total_tested} external links from Reddit")
    print(f"   - Already curated: {sum(1 for v in tracked_urls.values() if v.get('skipped') == 'already_curated')}")
    print(f"   - Failed to extract: {sum(1 for v in tracked_urls.values() if v.get('skipped') == 'no_extractable_text')}")
    print(f"   - New suggestions: {len(new_suggestions)}")
    
    # Save new suggestions
    if new_suggestions:
        suggestions.extend(new_suggestions)
        save_suggestions(suggestions)
        print(f"\n✨ Added {len(new_suggestions)} new suggestion(s) to {SUGGESTIONS_FILE}")
    else:
        print("\n📭 No new suggestions. Try running again later or adjust SCORE_THRESHOLD.")
    
    save_tracked_urls(tracked_urls)
    print(f"✅ Tracking saved to {TRACKING_FILE}")

def list_suggestions():
    """Display current suggestions."""
    suggestions = load_suggestions()
    if not suggestions:
        print("\n📭 No suggestions yet. Run discovery first (option 1).")
        return
    
    print(f"\n📋 Current suggestions ({len(suggestions)}):")
    print("-" * 80)
    for i, s in enumerate(suggestions, 1):
        if s.get('reviewed') == 'llm':
            status = "🤖 LLM reviewed"
        elif s.get('reviewed') == 'manual':
            status = "✅ Manual review"
        elif s.get('reviewed') == 'pending':
            status = "🆕 Pending"
        else:
            status = "🆕 New"
        
        score_info = f"heuristic: {s['heuristic_score']:.2f}"
        if s.get('llm_score'):
            score_info += f" | LLM: {s['llm_score']:.2f} | combined: {s.get('combined_score', 0):.2f}"
        
        print(f"{i:3}. {s['domain']:35} | {score_info}")
        print(f"     {status} | from r/{s['subreddit']} ({s['reddit_score']} upvotes)")
        print(f"     {s['title'][:70]}...")

def review_suggestions_with_llm():
    """Review pending suggestions using LLM."""
    suggestions = load_suggestions()
    pending = [s for s in suggestions if s.get('reviewed') == 'pending']
    
    if not pending:
        print("\n📭 No pending suggestions to review. All suggestions have been reviewed.")
        return
    
    print(f"\n🤖 LLM Review: {len(pending)} pending suggestion(s)")
    print("-" * 60)
    
    updated = 0
    for i, suggestion in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] Reviewing: {suggestion['domain']}")
        reviewed_suggestion = review_with_llm(suggestion)
        if reviewed_suggestion:
            # Update in the main list
            for idx, s in enumerate(suggestions):
                if s['url'] == suggestion['url']:
                    suggestions[idx] = reviewed_suggestion
                    updated += 1
                    break
        
        time.sleep(1)  # Be polite to Ollama
    
    if updated > 0:
        save_suggestions(suggestions)
        print(f"\n✅ Reviewed {updated} suggestion(s) with LLM")
    else:
        print("\n❌ No suggestions were successfully reviewed")

def mark_reviewed(suggestion_index, review_type='manual'):
    """Mark a suggestion as reviewed (manual or LLM)."""
    suggestions = load_suggestions()
    if 1 <= suggestion_index <= len(suggestions):
        idx = suggestion_index - 1
        suggestions[idx]['reviewed'] = review_type
        suggestions[idx]['reviewed_at'] = datetime.now().isoformat()
        save_suggestions(suggestions)
        print(f"✅ Marked suggestion #{suggestion_index} ({suggestions[idx]['domain']}) as {review_type} review.")
    else:
        print(f"❌ Invalid index. Choose 1-{len(suggestions)}")

def clear_all_suggestions():
    """Clear all suggestions (after adding them to blogs.csv)."""
    confirm = input("⚠️ This will delete ALL suggestions. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        save_suggestions([])
        print("✅ All suggestions cleared.")

def show_stats():
    """Show discovery statistics."""
    tracked = load_tracked_urls()
    suggestions = load_suggestions()
    
    print("\n📊 Discovery Statistics")
    print("-" * 40)
    print(f"Total URLs tracked: {len(tracked)}")
    print(f"Current suggestions: {len(suggestions)}")
    print(f"  - Pending: {sum(1 for s in suggestions if s.get('reviewed') == 'pending')}")
    print(f"  - LLM reviewed: {sum(1 for s in suggestions if s.get('reviewed') == 'llm')}")
    print(f"  - Manual review: {sum(1 for s in suggestions if s.get('reviewed') == 'manual')}")
    
    # Show average scores
    if suggestions:
        avg_heuristic = sum(s.get('heuristic_score', 0) for s in suggestions) / len(suggestions)
        avg_llm = None
        llm_scores = [s.get('llm_score', 0) for s in suggestions if s.get('llm_score')]
        if llm_scores:
            avg_llm = sum(llm_scores) / len(llm_scores)
        
        print(f"\nAverage heuristic score: {avg_heuristic:.2f}")
        if avg_llm:
            print(f"Average LLM score: {avg_llm:.2f}")
    
    # Show domains that scored well but were already curated
    curated_domains = set()
    for v in tracked.values():
        if v.get('skipped') == 'already_curated' and 'domain' in v:
            curated_domains.add(v['domain'])
    if curated_domains:
        print(f"\nDomains already in your curated list: {', '.join(sorted(curated_domains)[:5])}")

def export_suggestions():
    """Export suggestions to CSV for external review."""
    suggestions = load_suggestions()
    if not suggestions:
        print("\n📭 No suggestions to export.")
        return
    
    import csv
    export_file = f"data/reddit_suggestions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    os.makedirs('data', exist_ok=True)
    
    with open(export_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['domain', 'url', 'title', 'subreddit', 'reddit_score', 'heuristic_score', 'llm_score', 'combined_score', 'status', 'discovered_at'])
        
        for s in suggestions:
            writer.writerow([
                s.get('domain', ''),
                s.get('url', ''),
                s.get('title', ''),
                s.get('subreddit', ''),
                s.get('reddit_score', 0),
                s.get('heuristic_score', 0),
                s.get('llm_score', ''),
                s.get('combined_score', ''),
                s.get('reviewed', 'pending'),
                s.get('discovered_at', '')
            ])
    
    print(f"✅ Exported {len(suggestions)} suggestions to {export_file}")

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Reddit Engineering Blog Discovery")
    print("=" * 50)
    print("This tool scans Reddit for high-quality engineering blog posts")
    print("and suggests new domains to add to your curated blogs.csv")
    print()
    
    while True:
        print("\nOptions:")
        print("  1. Run discovery (scan Reddit, test articles, suggest new blogs)")
        print("  2. List current suggestions")
        print("  3. Review pending suggestions with LLM")
        print("  4. Mark a suggestion as manually reviewed")
        print("  5. Show statistics")
        print("  6. Export suggestions to CSV")
        print("  7. Clear all suggestions")
        print("  8. Exit")
        
        choice = input("\nChoice (1-8): ").strip()
        
        if choice == "1":
            process_reddit_posts()
        elif choice == "2":
            list_suggestions()
        elif choice == "3":
            review_suggestions_with_llm()
        elif choice == "4":
            list_suggestions()
            if load_suggestions():
                idx = input("\nEnter suggestion number to mark as manually reviewed: ").strip()
                if idx.isdigit():
                    mark_reviewed(int(idx), 'manual')
        elif choice == "5":
            show_stats()
        elif choice == "6":
            export_suggestions()
        elif choice == "7":
            clear_all_suggestions()
        elif choice == "8":
            print("\nGoodbye! Keep discovering great engineering content.")
            break
        else:
            print("Invalid choice. Please enter 1-8.")