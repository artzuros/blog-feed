import time
from config.settings import ARTICLES_PER_BLOG, SLOP_THRESHOLD, REQUEST_DELAY
from storage.database import save_article
from core.fetcher import fetch_article_text
from core.rss_reader import get_articles_via_rss
from core.extractor import extract_articles_from_html
from storage.cache import save_cache
from core.llm_scorer import score_with_llm
from core.keywords import extract_keywords
from api.logger import root_logger
from core.embeddings import init_embeddings
from quality.content_classifier import is_marketing_or_news

HEURISTIC_WEIGHT = 0.6
LLM_WEIGHT = 0.4

# Initialize embeddings when module loads
try:
    init_embeddings()
except Exception as e:
    root_logger.warning(f"Could not initialize embeddings: {e}")

def get_articles(blog_name, base_url, rss_override, cache, limit=ARTICLES_PER_BLOG):
    """Get articles via RSS or HTML extraction."""
    root_logger.info(f"Scanning {blog_name} (limit: {limit})")
    
    # Force HTML extraction for Convex
    if 'convex' in blog_name.lower() or 'stack.convex' in base_url:
        root_logger.debug(f"Forcing HTML extraction for {blog_name} (Convex has no RSS)")
        return extract_articles_from_html(base_url, blog_name, limit, cache)
    
    # Try RSS if available
    if rss_override:
        root_logger.debug(f"Using RSS for {blog_name}: {rss_override}")
        articles = get_articles_via_rss(rss_override, limit)
        if articles:
            root_logger.info(f"Found {len(articles)} articles via RSS for {blog_name}")
            # Cache for next time
            if base_url not in cache:
                cache[base_url] = {}
            cache[base_url]['rss_url'] = rss_override
            save_cache(cache)
            return articles
        else:
            root_logger.warning(f"No articles found via RSS for {blog_name}")
    
    # Fallback to HTML
    root_logger.info(f"Falling back to HTML extraction for {blog_name}")
    return extract_articles_from_html(base_url, blog_name, limit, cache)

def score_blog(blog_name, base_url, rss_override, cache):
    """Score all articles for a blog."""
    root_logger.info(f"Scoring blog: {blog_name}")
    articles = get_articles(blog_name, base_url, rss_override, cache)
    
    if not articles:
        root_logger.warning(f"No articles found for {blog_name}")
        return
    
    success_count = 0
    for title, url in articles:
        # Skip known non-article URLs
        if any(skip in url for skip in ['/sessions/', '/industry', '/product']):
            root_logger.debug(f"Skipping non-article URL: {url}")
            continue
        
        root_logger.debug(f"Processing article: {title[:70]}...")
        text = fetch_article_text(url)
        if text and len(text) > 200:
            # Check if it's marketing/news
            marketing_score, marketing_reason = is_marketing_or_news(title, text)
            if marketing_score > 0.7:  # threshold, adjust as needed
                root_logger.info(f"⏭️ Skipping marketing/news article: {title[:50]}... (score: {marketing_score:.2f}, reason: {marketing_reason})")
                continue  # Don't save this article
            from quality.slop_detector import is_likely_ai_slop
            score, reason = is_likely_ai_slop(text)
            
            # LLM scoring for substantial articles
            llm_score = None
            combined = score
            if text and len(text) > 500:
                root_logger.debug(f"Running LLM scoring for {url}")
                llm_score = score_with_llm(text)
                if llm_score is not None:
                    combined = (score * HEURISTIC_WEIGHT) + (llm_score * LLM_WEIGHT)
                    root_logger.debug(f"LLM score: {llm_score:.2f}, Combined: {combined:.2f}")
                else:
                    root_logger.warning(f"LLM scoring failed for {url}")
            else:
                root_logger.debug(f"Skipping LLM scoring (text length: {len(text)})")
            
            # Save with new fields
            keywords = extract_keywords(text)
            save_article(url, title, blog_name, score, llm_score, combined, reason, keywords, text_content=text)
            success_count += 1
            verdict = "SLOP" if score > SLOP_THRESHOLD else "GOOD"
            root_logger.info(f"Article scored: {verdict} (heuristic: {score:.2f}, combined: {combined:.2f}) - {title[:50]}")
        else:
            root_logger.warning(f"Could not extract enough text from {url} (text length: {len(text) if text else 0})")
        
        time.sleep(REQUEST_DELAY)
    
    root_logger.info(f"Completed scoring for {blog_name}: {success_count}/{len(articles)} articles processed")