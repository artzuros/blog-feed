import json
import os
from config.settings import CACHE_FILE
from api.logger import db_logger

def load_cache():
    """Load blog discovery cache from JSON file."""
    db_logger.debug(f"Loading cache from {CACHE_FILE}")
    
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    db_logger.warning("Cache file is empty")
                    return {}
                cache = json.loads(content)
                db_logger.info(f"Cache loaded with {len(cache)} entries")
                return cache
        except json.JSONDecodeError as e:
            db_logger.error(f"Cache file corrupted: {e}", exc_info=True)
            # Backup corrupted file
            backup_file = f"{CACHE_FILE}.corrupted"
            try:
                os.rename(CACHE_FILE, backup_file)
                db_logger.warning(f"Backed up corrupted cache to {backup_file}")
            except:
                pass
            return {}
        except Exception as e:
            db_logger.error(f"Error loading cache: {e}", exc_info=True)
            return {}
    else:
        db_logger.debug("No cache file found, creating new cache")
        return {}

def save_cache(cache):
    """Save blog discovery cache to JSON file."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        # Validate cache is serializable
        if not isinstance(cache, dict):
            db_logger.error(f"Cache is not a dict: {type(cache)}")
            return False
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        
        db_logger.debug(f"Cache saved with {len(cache)} entries")
        return True
    except Exception as e:
        db_logger.error(f"Error saving cache: {e}", exc_info=True)
        return False

def clear_cache():
    """Clear the cache file."""
    db_logger.warning("Clearing cache")
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            db_logger.info("Cache cleared successfully")
            return True
        else:
            db_logger.debug("Cache file doesn't exist, nothing to clear")
            return True
    except Exception as e:
        db_logger.error(f"Error clearing cache: {e}", exc_info=True)
        return False

def get_cached_blog(blog_url):
    """Get a specific blog from cache."""
    cache = load_cache()
    result = cache.get(blog_url)
    if result:
        db_logger.debug(f"Cache hit for {blog_url}")
    else:
        db_logger.debug(f"Cache miss for {blog_url}")
    return result

def update_cached_blog(blog_url, data):
    """Update a specific blog in cache."""
    cache = load_cache()
    cache[blog_url] = data
    success = save_cache(cache)
    if success:
        db_logger.debug(f"Updated cache for {blog_url}")
    return success