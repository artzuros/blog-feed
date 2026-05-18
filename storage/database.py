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
            reason TEXT,
            fetched_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_blog_name ON articles(blog_name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_score ON articles(score)
    """)
    conn.close()

def save_article(url, title, blog_name, score, reason):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT OR REPLACE INTO articles (url, title, blog_name, score, reason, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (url, title, blog_name, score, reason, datetime.now()))
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