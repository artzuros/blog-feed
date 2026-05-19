from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from core.fetcher import fetch_html_robust
from storage.cache import save_cache
from api.logger import root_logger

def extract_articles_from_html(blog_url, blog_name, limit=3, cache=None):
    """Extract article links from blog homepage HTML."""
    root_logger.debug(f"Extracting articles from HTML for {blog_url} (limit={limit})")
    
    html = fetch_html_robust(blog_url)
    if not html:
        root_logger.warning(f"No HTML fetched for {blog_url}")
        return []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        skip_paths = {'/tag/', '/category/', '/author/', '/page/', '?page=',
                      '/sessions/', '/industry', '/product', '/about', '/privacy',
                      '/login', '/signup', '/search', '/archive'}
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(blog_url, href)
            
            # Stay on same domain
            if urlparse(full_url).netloc != urlparse(blog_url).netloc:
                continue
            
            # Skip obvious non-article paths
            if any(skip in href for skip in skip_paths):
                continue
            if href in ('/', '', '#', 'javascript:void(0)'):
                continue
            
            # Special handling for Convex
            if 'convex.dev' in blog_url or 'stack.convex' in blog_url or 'convex' in blog_name.lower():
                title = a.get_text(strip=True)
                if not title or len(title) < 15:
                    heading = a.find(['h1', 'h2', 'h3', 'h4'])
                    if heading:
                        title = heading.get_text(strip=True)
                if title and len(title) > 15 and href and len(href) > 5 and not href.startswith('/?'):
                    article_links.append((title, full_url))
            
            # Generic blog patterns
            elif any(pattern in href for pattern in ['/blog/', '/posts/', '/article/', '/202', '/20']):
                if any(bad in href for bad in ['/tag/', '/category/', '/author/', '/page']):
                    continue
                title = a.get_text(strip=True)
                if not title or len(title) < 8:
                    heading = a.find(['h1', 'h2', 'h3', 'h4'])
                    if heading:
                        title = heading.get_text(strip=True)
                if title and len(title) > 5:
                    article_links.append((title, full_url))
        
        # Deduplicate
        seen = set()
        unique = []
        for title, url in article_links:
            if url not in seen:
                seen.add(url)
                unique.append((title, url))
                if len(unique) >= limit:
                    break
        
        root_logger.info(f"Extracted {len(unique)} articles from {blog_url}")
        
        # Cache hint
        if cache and blog_url not in cache:
            cache[blog_url] = {'html_selector': 'default'}
            save_cache(cache)
        
        return unique[:limit]
        
    except Exception as e:
        root_logger.error(f"Error extracting articles from {blog_url}: {e}", exc_info=True)
        return []