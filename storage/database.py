import sqlite3
from datetime import datetime
from config.settings import DB_FILE
from api.logger import db_logger

from core.embeddings import update_article_embedding

def init_db():
    """Initialize database with all tables."""
    db_logger.info(f"Initializing database at {DB_FILE}")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Articles table
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
                source TEXT DEFAULT 'rss',
                reddit_suggestion_id TEXT,
                added_by TEXT,
                fetched_at TIMESTAMP,
                text_content TEXT,
                content_type TEXT DEFAULT 'blog',
                embedding_updated INTEGER DEFAULT 0
            )
        """)
        
        # Ensure text_content column exists on older databases
        try:
            conn.execute("ALTER TABLE articles ADD COLUMN text_content TEXT")
            db_logger.info("Added text_content column to articles table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # FTS5 full-text search index
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title, keywords, blog_name, text_content
            )
        """)
        # Backfill FTS5 index for existing articles that aren't indexed yet
        backfill_count = conn.execute("""
            INSERT OR IGNORE INTO articles_fts(rowid, title, keywords, blog_name, text_content)
            SELECT rowid, title, COALESCE(keywords, ''), blog_name, COALESCE(text_content, '')
            FROM articles
        """).rowcount
        if backfill_count > 0:
            db_logger.info(f"FTS5 backfill: indexed {backfill_count} existing articles")

        db_logger.info("FTS5 search index ready")

        # Suggestion reviews table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suggestion_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_url TEXT NOT NULL,
                vote INTEGER NOT NULL,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(suggestion_url, ip_address)
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_review_suggestion ON suggestion_reviews(suggestion_url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON articles(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_added_by ON articles(added_by)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_combined_score ON articles(combined_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fetched_at ON articles(fetched_at)")
        
        conn.commit()
        conn.close()
        
        db_logger.info("Database initialized successfully")
    except Exception as e:
        db_logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

def save_article(url, title, blog_name, score, llm_score, combined_score, reason, keywords, 
                 source='rss', reddit_suggestion_id=None, added_by='automated', text_content=None,
                 content_type='blog'):
    """Save or update an article."""
    db_logger.debug(f"Saving article: {title[:50]}... from {blog_name}")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("""
            INSERT OR REPLACE INTO articles 
            (url, title, blog_name, score, llm_score, combined_score, reason, keywords, 
             source, reddit_suggestion_id, added_by, fetched_at, text_content, content_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (url, title, blog_name, score, llm_score, combined_score, reason, keywords,
              source, reddit_suggestion_id, added_by, datetime.now(), text_content, content_type))
        conn.commit()
        
        # Get the rowid of the inserted/updated article
        cursor = conn.execute("SELECT rowid FROM articles WHERE url = ?", (url,))
        rowid = cursor.fetchone()[0]

        # Sync to FTS5 full-text search index
        conn.execute("DELETE FROM articles_fts WHERE rowid = ?", (rowid,))
        conn.execute(
            "INSERT INTO articles_fts(rowid, title, keywords, blog_name, text_content) VALUES (?, ?, ?, ?, ?)",
            (rowid, title, keywords or '', blog_name, text_content or '')
        )

        conn.close()
        
        db_logger.info(f"Article saved: {title[:50]} (score: {combined_score:.2f})")
        
        # Generate embedding for semantic search
        if content_type != 'marketing':
            article_data = {
                'title': title,
                'keywords': keywords,
                'blog_name': blog_name,
                'source': source,
                'combined_score': combined_score,
                'url': url
            }
            update_article_embedding(rowid, article_data)
            # Mark as updated
            conn = sqlite3.connect(DB_FILE)
            conn.execute("UPDATE articles SET embedding_updated = 1 WHERE rowid = ?", (rowid,))
            conn.commit()
            conn.close()
        
    except Exception as e:
        db_logger.error(f"Failed to save article {url}: {e}", exc_info=True)

def article_exists(url):
    """Check if article already exists."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        db_logger.error(f"Error checking article existence: {e}", exc_info=True)
        return False

def get_articles_by_blog(blog_name, limit=50):
    """Get articles for a specific blog."""
    db_logger.debug(f"Fetching articles for blog: {blog_name} (limit={limit})")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.execute("""
            SELECT url, title, score, combined_score, reason, fetched_at 
            FROM articles 
            WHERE blog_name = ? 
            ORDER BY fetched_at DESC 
            LIMIT ?
        """, (blog_name, limit))
        results = cursor.fetchall()
        conn.close()
        
        db_logger.debug(f"Found {len(results)} articles for {blog_name}")
        return results
    except Exception as e:
        db_logger.error(f"Error fetching articles for {blog_name}: {e}", exc_info=True)
        return []

def update_llm_score(url, llm_score):
    """Update LLM score for an article."""
    db_logger.debug(f"Updating LLM score for {url[:50]}... to {llm_score:.2f}")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute(
            "UPDATE articles SET llm_score = ?, combined_score = (score * 0.6 + ? * 0.4) WHERE url = ?",
            (llm_score, llm_score, url)
        )
        conn.commit()
        conn.close()
        
        db_logger.info(f"LLM score updated for {url[:50]}")
        return True
    except Exception as e:
        db_logger.error(f"Failed to update LLM score: {e}", exc_info=True)
        return False