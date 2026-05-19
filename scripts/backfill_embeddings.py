#!/usr/bin/env python3
"""Backfill embeddings for existing articles."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.dependencies import get_db
from core.embeddings import init_embeddings, update_article_embedding
from api.logger import root_logger

def backfill_embeddings():
    """Generate embeddings for all existing articles."""
    root_logger.info("Starting embedding backfill...")
    
    # Initialize embedding system
    init_embeddings()
    
    conn = get_db()
    if not conn:
        root_logger.error("Database not accessible")
        return
    
    # Get all articles
    cursor = conn.execute("""
        SELECT rowid, url, title, keywords, blog_name, source, combined_score
        FROM articles
    """)
    
    articles = cursor.fetchall()
    conn.close()
    
    root_logger.info(f"Found {len(articles)} articles to process")
    
    success_count = 0
    for row in articles:
        article_id, url, title, keywords, blog_name, source, combined_score = row
        
        article_data = {
            'title': title,
            'keywords': keywords or '',
            'blog_name': blog_name,
            'source': source or 'rss',
            'combined_score': combined_score or 0.5,
            'url': url
        }
        
        try:
            update_article_embedding(article_id, article_data)
            success_count += 1
            if success_count % 100 == 0:
                root_logger.info(f"Processed {success_count}/{len(articles)} articles")
        except Exception as e:
            root_logger.error(f"Failed for article {article_id}: {e}")
    
    root_logger.info(f"Backfill complete: {success_count}/{len(articles)} articles embedded")

if __name__ == "__main__":
    backfill_embeddings()