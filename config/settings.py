import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "blog_discovery_cache.json")
DB_FILE = os.path.join(DATA_DIR, "blog_scout.db")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Fetch settings
REQUEST_TIMEOUT = 20
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Article settings
ARTICLES_PER_BLOG = 3
MIN_ARTICLE_LENGTH = 200
SLOP_THRESHOLD = 0.6

# Delay between requests (seconds)
REQUEST_DELAY = 1