import time
from config.settings import ARTICLES_PER_BLOG, SLOP_THRESHOLD, REQUEST_DELAY
from storage.database import save_article
from core.fetcher import fetch_article_text
from core.rss_reader import get_articles_via_rss
from core.extractor import extract_articles_from_html
from storage.cache import save_cache
from core.llm_scorer import score_with_llm
from core.keywords import extract_keywords

HEURISTIC_WEIGHT = 0.6
LLM_WEIGHT = 0.4

def get_articles(blog_name, base_url, rss_override, cache, limit=ARTICLES_PER_BLOG):
    """Get articles via RSS or HTML extraction."""
    print(f"  📡 Scanning {blog_name}...")
    
    # Force HTML extraction for Convex
    if 'convex' in blog_name.lower() or 'stack.convex' in base_url:
        print(f"    🎯 Using HTML extraction for {blog_name} (no RSS)")
        return extract_articles_from_html(base_url, blog_name, limit, cache)
    
    # Try RSS if available
    if rss_override:
        print(f"    ✅ Using RSS: {rss_override}")
        articles = get_articles_via_rss(rss_override, limit)
        if articles:
            # Cache for next time
            if base_url not in cache:
                cache[base_url] = {}
            cache[base_url]['rss_url'] = rss_override
            save_cache(cache)
            return articles
    
    # Fallback to HTML
    print(f"    ❌ Using HTML fallback for {blog_name}")
    return extract_articles_from_html(base_url, blog_name, limit, cache)

def score_blog(blog_name, base_url, rss_override, cache):
    """Score all articles for a blog."""
    articles = get_articles(blog_name, base_url, rss_override, cache)
    if not articles:
        print(f"  ❌ No articles found for {blog_name}")
        return
    
    for title, url in articles:
        # Skip known non-article URLs
        if any(skip in url for skip in ['/sessions/', '/industry', '/product']):
            continue
        
        print(f"    📄 {title[:70]}...")
        text = fetch_article_text(url)
        
        if text and len(text) > 200:
            from quality.slop_detector import is_likely_ai_slop
            score, reason = is_likely_ai_slop(text)
            # After getting heuristic score
            llm_score = None
            combined = score
            if text and len(text) > 500:  # only use LLM for substantial articles
                llm_score = score_with_llm(text)
                if llm_score is not None:
                    combined = (score * HEURISTIC_WEIGHT) + (llm_score * LLM_WEIGHT)
                else:
                    combined = score
            else:
                combined = score

            # Save with new fields
            keywords = extract_keywords(text)
            save_article(url, title, blog_name, score, llm_score, combined, reason, keywords)
            verdict = "🔴 SLOP" if score > SLOP_THRESHOLD else "🟢 GOOD"
            print(f"      {verdict} (score: {score:.2f})")
        else:
            print(f"      ⚠️ Could not extract enough text")
        
        time.sleep(REQUEST_DELAY)