import sqlite3
from config.settings import DB_FILE, BLOGS_CSV
import json

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def load_blogs_csv():
    """Load blogs from CSV file."""
    import csv
    blogs = []
    with open(BLOGS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            blogs.append({
                'name': row['name'],
                'url': row['url'],
                'rss': row['rss'] if row.get('rss') else None
            })
    return blogs

def load_suggestions():
    """Load Reddit suggestions."""
    suggestions_file = "data/reddit_suggestions.json"
    if not os.path.exists(suggestions_file):
        return []
    with open(suggestions_file, 'r') as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)