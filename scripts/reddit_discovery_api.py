#!/usr/bin/env python3
"""Non-interactive Reddit discovery for API calls."""
import sys
import os
import json
import time
import requests
from urllib.parse import urlparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fetcher import fetch_article_text
from quality.slop_detector import is_likely_ai_slop
from config.blogs_loader import load_blogs
from config.settings import USER_AGENT
from api.logger import scan_logger

# Configuration
SUBREDDITS = [
    "programming", "devops", "ExperiencedDevs", "sre", 
    "engineering", "rust", "golang", "webdev", "databases"
]

SCORE_THRESHOLD = 0.45
MAX_ARTICLES_PER_SUBREDDIT = 15
REQUEST_DELAY = 2

SUGGESTIONS_FILE = "data/reddit_suggestions.json"
TRACKING_FILE = "data/reddit_tracked_urls.json"

def load_tracked_urls():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except:
            return {}
    return {}

def load_suggestions():
    if os.path.exists(SUGGESTIONS_FILE):
        try:
            with open(SUGGESTIONS_FILE, 'r') as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except:
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
    for _, url, _ in blogs:
        parsed = urlparse(url)
        if parsed.netloc == domain or domain in parsed.netloc:
            return True
    return False

def extract_domain_from_url(url):
    return urlparse(url).netloc

def fetch_reddit_posts(subreddit, limit=25):
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
            
            if not url or 'reddit.com' in url or url.startswith('/'):
                continue
            
            skip_domains = ['medium.com', 'towardsdatascience.com', 'dev.to', 'hashnode.com', 'youtube.com', 'github.com']
            if any(skip in url for skip in skip_domains):
                continue
            
            entries.append({
                'title': title,
                'url': url,
                'score': score,
                'num_comments': num_comments,
                'published': datetime.fromtimestamp(created_utc).isoformat(),
                'subreddit': subreddit
            })
        
        return entries
    except Exception as e:
        scan_logger.error(f"Failed to fetch r/{subreddit}: {e}")
        return []

def run_discovery():
    """Main discovery function (non-interactive)."""
    scan_logger.info("Starting Reddit discovery process")
    
    blogs = load_blogs()
    tracked_urls = load_tracked_urls()
    suggestions = load_suggestions()
    new_suggestions = []
    total_tested = 0
    
    for subreddit in SUBREDDITS:
        scan_logger.info(f"Scanning r/{subreddit}")
        posts = fetch_reddit_posts(subreddit, MAX_ARTICLES_PER_SUBREDDIT)
        if not posts:
            continue
        
        for post in posts:
            url = post['url']
            total_tested += 1
            
            if url in tracked_urls:
                continue
            
            domain = extract_domain_from_url(url)
            
            if is_domain_in_blogs(domain, blogs):
                tracked_urls[url] = {'skipped': 'already_curated', 'domain': domain, 'timestamp': datetime.now().isoformat()}
                continue
            
            scan_logger.debug(f"Testing {domain}: {post['title'][:50]}...")
            text = fetch_article_text(url)
            if not text or len(text) < 200:
                tracked_urls[url] = {'skipped': 'no_extractable_text', 'domain': domain, 'timestamp': datetime.now().isoformat()}
                continue
            
            heuristic_score, reason = is_likely_ai_slop(text)
            
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
                    'reviewed': 'pending'
                }
                if not any(s['url'] == url for s in suggestions):
                    new_suggestions.append(suggestion)
                    scan_logger.info(f"New suggestion: {domain} (score: {heuristic_score:.2f})")
            else:
                scan_logger.debug(f"Rejected {domain}: score {heuristic_score:.2f} > threshold")
            
            tracked_urls[url] = {
                'domain': domain,
                'heuristic_score': heuristic_score,
                'reason': reason,
                'reddit_score': post['score'],
                'timestamp': datetime.now().isoformat()
            }
            
            time.sleep(REQUEST_DELAY)
    
    if new_suggestions:
        suggestions.extend(new_suggestions)
        save_suggestions(suggestions)
        scan_logger.info(f"Added {len(new_suggestions)} new suggestions")
    
    save_tracked_urls(tracked_urls)
    scan_logger.info(f"Reddit discovery completed. Tested {total_tested} links, found {len(new_suggestions)} suggestions")
    return new_suggestions

if __name__ == "__main__":
    run_discovery()
