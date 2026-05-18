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
            score REAL,                -- heuristic score
            llm_score REAL,            -- LLM score (0-1)
            combined_score REAL,       -- weighted combination
            reason TEXT,
            keywords TEXT,             -- comma-separated
            fetched_at TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_blog_name ON articles(blog_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_combined_score ON articles(combined_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fetched_at ON articles(fetched_at)")
    conn.close()

def save_article(url, title, blog_name, score, llm_score, combined_score, reason, keywords):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT OR REPLACE INTO articles 
        (url, title, blog_name, score, llm_score, combined_score, reason, keywords, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (url, title, blog_name, score, llm_score, combined_score, reason, keywords, datetime.now()))
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