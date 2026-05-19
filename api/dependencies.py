import sqlite3
import csv
import os
import json
from api.logger import root_logger
from config.settings import DB_FILE, BLOGS_CSV

def get_db():
    """Get database connection."""
    if not os.path.exists(DB_FILE):
        root_logger.warning(f"Database file not found: {DB_FILE}")
        return None
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    root_logger.debug(f"Database connection established")
    return conn

def load_blogs_csv():
    """Load blogs from CSV file."""
    blogs = []
    if not os.path.exists(BLOGS_CSV):
        root_logger.warning(f"Blogs CSV not found: {BLOGS_CSV}")
        return blogs
    
    with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            blogs.append({
                'name': row['name'],
                'url': row['url'],
                'rss': row['rss'] if row.get('rss') and row['rss'].strip() else None
            })
    root_logger.debug(f"Loaded {len(blogs)} blogs from CSV")
    return blogs

def load_suggestions():
    """Load Reddit suggestions."""
    suggestions_file = "data/reddit_suggestions.json"
    if not os.path.exists(suggestions_file):
        root_logger.debug(f"Suggestions file not found: {suggestions_file}")
        return []
    try:
        with open(suggestions_file, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            suggestions = json.loads(content)
            root_logger.debug(f"Loaded {len(suggestions)} suggestions")
            return suggestions
    except (json.JSONDecodeError, FileNotFoundError) as e:
        root_logger.error(f"Failed to load suggestions: {e}")
        return []