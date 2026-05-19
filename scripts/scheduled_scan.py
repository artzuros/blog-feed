#!/usr/bin/env python3
"""Check all blogs for new articles and process only new ones."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.blogs_loader import load_blogs
from storage.database import init_db, article_exists, save_article
from storage.cache import load_cache, save_cache
from core.fetcher import fetch_article_text
from core.rss_reader import get_articles_via_rss
from core.extractor import extract_articles_from_html
from quality.slop_detector import is_likely_ai_slop
from core.llm_scorer import score_with_llm
from core.keywords import extract_keywords
from api.logger import root_logger

HEURISTIC_WEIGHT = 0.6
LLM_WEIGHT = 0.4

def process_article(url, title, blog_name):
    """Process a single article if it doesn't exist."""
    if article_exists(url):
        root_logger.debug(f"Skipping existing article: {title[:50]}...")
        return
    
    root_logger.info(f"Processing new article from {blog_name}: {title[:70]}...")
    text = fetch_article_text(url)
    
    if text and len(text) > 200:
        heuristic_score, reason = is_likely_ai_slop(text)
        llm_score = None
        
        if len(text) > 500:
            root_logger.debug(f"Running LLM scoring for {url}")
            llm_score = score_with_llm(text)
        
        combined = heuristic_score
        if llm_score is not None:
            combined = heuristic_score * HEURISTIC_WEIGHT + llm_score * LLM_WEIGHT
        
        keywords = extract_keywords(text)
        save_article(url, title, blog_name, heuristic_score, llm_score, combined, reason, keywords)
        root_logger.info(f"Saved article: {title[:50]} - Heuristic: {heuristic_score:.2f}, Combined: {combined:.2f}")
    else:
        root_logger.warning(f"Could not extract enough text from {url}")

def main():
    """Main scheduled scan function."""
    root_logger.info("Starting scheduled blog scan")
    
    try:
        init_db()
        root_logger.debug("Database initialized")
        
        cache = load_cache()
        blogs = load_blogs()
        
        if not blogs:
            root_logger.warning("No blogs found to scan")
            return
        
        root_logger.info(f"Scanning {len(blogs)} blogs")
        
        for name, url, rss_url in blogs:
            root_logger.info(f"Checking blog: {name} ({url})")
            articles = []
            
            if rss_url:
                root_logger.debug(f"Trying RSS for {name}: {rss_url}")
                articles = get_articles_via_rss(rss_url, limit=5)
            
            if not articles:
                root_logger.debug(f"Falling back to HTML extraction for {name}")
                articles = extract_articles_from_html(url, name, limit=3, cache=cache)
            
            root_logger.info(f"Found {len(articles)} articles for {name}")
            
            for title, article_url in articles:
                process_article(article_url, title, name)
        
        save_cache(cache)
        root_logger.info("Scheduled scan completed successfully")
        
    except Exception as e:
        root_logger.error(f"Scheduled scan failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()