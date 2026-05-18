import requests
import feedparser
import urllib3
from config.settings import USER_AGENT
from storage.cache import save_cache

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_articles_via_rss(rss_url, limit=3):
    """Fetch articles from RSS feed with SSL fallback."""
    try:
        # Try with SSL verification first
        resp = requests.get(rss_url, timeout=15, headers={'User-Agent': USER_AGENT})
        feed = feedparser.parse(resp.content)
        if feed.entries:
            return [(entry.title, entry.link) for entry in feed.entries[:limit]]
    except requests.exceptions.SSLError:
        print(f"    ⚠️ SSL error, trying without verification...")
        try:
            resp = requests.get(rss_url, timeout=15, headers={'User-Agent': USER_AGENT}, verify=False)
            feed = feedparser.parse(resp.content)
            if feed.entries:
                return [(entry.title, entry.link) for entry in feed.entries[:limit]]
        except Exception as e:
            print(f"    ⚠️ RSS fetch failed: {e}")
    except Exception as e:
        print(f"    ⚠️ RSS fetch failed: {e}")
    
    return []