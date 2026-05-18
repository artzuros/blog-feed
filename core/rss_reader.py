import requests
import feedparser
from config.settings import USER_AGENT
from storage.cache import save_cache

def get_articles_via_rss(rss_url, limit=3):
    """Fetch articles from RSS feed."""
    try:
        resp = requests.get(rss_url, timeout=15, headers={'User-Agent': USER_AGENT})
        feed = feedparser.parse(resp.content)
        if feed.entries:
            return [(entry.title, entry.link) for entry in feed.entries[:limit]]
        else:
            print(f"    ⚠️ RSS feed has no entries")
            return []
    except Exception as e:
        print(f"    ⚠️ RSS fetch failed: {e}")
        return []