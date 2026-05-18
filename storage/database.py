import sqlite3
from datetime import datetime
from config.settings import DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            url TEXT PRIMARY KEY,
            title TEXT,
            blog_name TEXT,
            score REAL,
            llm_score REAL,
            combined_score REAL,
            reason TEXT,
            keywords TEXT,
            source TEXT DEFAULT 'rss',  -- 'rss', 'reddit', 'manual'
            reddit_suggestion_id TEXT,  -- reference to reddit_suggestions.json
            added_by TEXT,               -- 'automated', 'manual_review'
            fetched_at TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON articles(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_added_by ON articles(added_by)")
    conn.close()

def save_article(url, title, blog_name, score, llm_score, combined_score, reason, keywords, 
                 source='rss', reddit_suggestion_id=None, added_by='automated'):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT OR REPLACE INTO articles 
        (url, title, blog_name, score, llm_score, combined_score, reason, keywords, 
         source, reddit_suggestion_id, added_by, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (url, title, blog_name, score, llm_score, combined_score, reason, keywords,
          source, reddit_suggestion_id, added_by, datetime.now()))
    conn.commit()
    conn.close()

def get_articles_by_blog(blog_name, limit=50):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.execute("""
        SELECT url, title, score, reason, fetched_at 
        FROM articles 
        WHERE blog_name = ? 
        ORDER BY fetched_at DESC 
        LIMIT ?
    """, (blog_name, limit))
    results = cursor.fetchall()
    conn.close()
    return results

def article_exists(url):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists