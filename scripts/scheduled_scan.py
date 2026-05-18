#!/usr/bin/env python3
"""Check all blogs for new articles and process only new ones."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.blogs_loader import load_blogs
from storage.database import init_db, article_exists, save_article
from storage.cache import load_cache, save_cache
from core.scorer import score_blog  # we'll refactor
from core.fetcher import fetch_article_text
from core.rss_reader import get_articles_via_rss
from core.extractor import extract_articles_from_html
from quality.slop_detector import is_likely_ai_slop
from core.llm_scorer import score_with_llm
from core.keywords import extract_keywords

HEURISTIC_WEIGHT = 0.6
LLM_WEIGHT = 0.4

def process_article(url, title, blog_name):
    if article_exists(url):
        print(f"  ⏭️ Already processed: {title[:50]}...")
        return
    print(f"  🆕 New article: {title[:70]}...")
    text = fetch_article_text(url)
    if text and len(text) > 200:
        heuristic_score, reason = is_likely_ai_slop(text)
        llm_score = None
        if len(text) > 500:
            llm_score = score_with_llm(text)
        combined = heuristic_score
        if llm_score is not None:
            combined = heuristic_score * HEURISTIC_WEIGHT + llm_score * LLM_WEIGHT
        keywords = extract_keywords(text)
        save_article(url, title, blog_name, heuristic_score, llm_score, combined, reason, keywords)
        print(f"    ✅ Heuristic: {heuristic_score:.2f}, LLM: {llm_score or 'N/A'}, Combined: {combined:.2f}")
    else:
        print(f"    ⚠️ Could not extract enough text")

def main():
    init_db()
    cache = load_cache()
    blogs = load_blogs()
    
    for name, url, rss_url in blogs:
        print(f"\n📡 Checking {name}...")
        articles = []
        if rss_url:
            articles = get_articles_via_rss(rss_url, limit=5)
        if not articles:
            articles = extract_articles_from_html(url, name, limit=3, cache=cache)
        for title, article_url in articles:
            process_article(article_url, title, name)
    
    save_cache(cache)
    print("\n✅ Scheduled scan complete.")

if __name__ == "__main__":
    main()