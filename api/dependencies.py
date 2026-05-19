import sqlite3
import csv
import os
import json
from api.logger import db_logger, api_logger
from config.settings import DB_FILE, BLOGS_CSV

def get_db():
    """Get database connection."""
    db_logger.debug(f"Attempting to connect to database: {DB_FILE}")
    
    if not os.path.exists(DB_FILE):
        db_logger.warning(f"Database file not found: {DB_FILE}")
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        db_logger.debug(f"Database connection established successfully")
        return conn
    except Exception as e:
        db_logger.error(f"Failed to connect to database: {e}", exc_info=True)
        return None

def load_blogs_csv():
    """Load blogs from CSV file."""
    blogs = []
    api_logger.debug(f"Loading blogs from CSV: {BLOGS_CSV}")
    
    if not os.path.exists(BLOGS_CSV):
        api_logger.warning(f"Blogs CSV not found: {BLOGS_CSV}")
        return blogs
    
    try:
        with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                blogs.append({
                    'name': row['name'],
                    'url': row['url'],
                    'rss': row['rss'] if row.get('rss') and row['rss'].strip() else None
                })
        api_logger.info(f"Loaded {len(blogs)} blogs from CSV")
        return blogs
    except Exception as e:
        api_logger.error(f"Failed to load blogs CSV: {e}", exc_info=True)
        return []

def load_suggestions():
    """Load Reddit suggestions."""
    suggestions_file = "data/reddit_suggestions.json"
    api_logger.debug(f"Loading suggestions from {suggestions_file}")
    
    if not os.path.exists(suggestions_file):
        api_logger.debug(f"Suggestions file not found: {suggestions_file}")
        return []
    
    try:
        with open(suggestions_file, 'r') as f:
            content = f.read().strip()
            if not content:
                api_logger.debug("Suggestions file is empty")
                return []
            suggestions = json.loads(content)
            api_logger.info(f"Loaded {len(suggestions)} suggestions")
            return suggestions
    except json.JSONDecodeError as e:
        api_logger.error(f"Failed to parse suggestions JSON: {e}", exc_info=True)
        return []
    except Exception as e:
        api_logger.error(f"Failed to load suggestions: {e}", exc_info=True)
        return []

def close_db(conn):
    """Close database connection safely."""
    if conn:
        try:
            conn.close()
            db_logger.debug("Database connection closed")
        except Exception as e:
            db_logger.error(f"Error closing database connection: {e}")