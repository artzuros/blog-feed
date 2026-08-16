import os
from dotenv import load_dotenv
from api.logger import root_logger

load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
BLOGS_CSV = os.path.join(CONFIG_DIR, "blogs.csv")
CACHE_FILE = os.path.join(DATA_DIR, "blog_discovery_cache.json")
DB_FILE = os.path.join(DATA_DIR, "blog_scout.db")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

root_logger.debug(f"Settings loaded: DB_FILE={DB_FILE}, BLOGS_CSV={BLOGS_CSV}")

# Fetch settings
REQUEST_TIMEOUT = 20
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# Article settings
ARTICLES_PER_BLOG = 3
MIN_ARTICLE_LENGTH = 200
SLOP_THRESHOLD = 0.6

# Delay between requests (seconds)
REQUEST_DELAY = 1

# API settings
API_KEY = os.getenv("BLOG_SCOUT_API_KEY", "your-secret-key")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/api.log")

# LLM API (DeepSeek)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# Validate critical settings
if API_KEY == "your-secret-key":
    root_logger.warning("Using default API key! Please set BLOG_SCOUT_API_KEY in .env")