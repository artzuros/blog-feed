from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from typing import List, Optional
from api.auth import verify_admin_key
from api.dependencies import get_db
from api.logger import llm_logger, api_logger
from core.llm_scorer import score_with_llm
from storage.database import save_article, get_articles_by_blog, article_exists
import sqlite3

router = APIRouter(dependencies=[Depends(verify_admin_key)])

class LLMQueueItem(BaseModel):
    article_url: str
    priority: int = 1  # 1=normal, 2=high

@router.get("/llm/queue")
async def get_llm_queue(request: Request):
    """Get articles pending LLM review."""
    api_logger.info(f"LLM queue status requested by {request.client.host}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")

    cursor = conn.execute(
        """SELECT url, title, blog_name, score, keywords, fetched_at 
           FROM articles 
           WHERE llm_score IS NULL AND score IS NOT NULL
           ORDER BY fetched_at DESC
           LIMIT 100"""
    )
    articles = [dict(row) for row in cursor.fetchall()]
    conn.close()

    llm_logger.info(f"Returning {len(articles)} articles pending LLM review")
    return {"pending_count": len(articles), "articles": articles}

@router.post("/llm/review-article/{article_id}")
async def review_article_with_llm(request: Request, article_id: str, background_tasks: BackgroundTasks):
    """Queue an article for LLM review."""
    import base64
    try:
        url = base64.b64decode(article_id).decode()
        api_logger.info(f"Queueing article for LLM review: {url[:100]}... from {request.client.host}")
    except:
        api_logger.error(f"Invalid article ID: {article_id}")
        raise HTTPException(status_code=400, detail="Invalid article ID")

    # Add to background task
    background_tasks.add_task(process_llm_review, url)

    return {"success": True, "message": "Article queued for LLM review"}

async def process_llm_review(url: str):
    """Background task to process LLM review."""
    llm_logger.info(f"Starting LLM review for {url}")

    conn = get_db()
    if not conn:
        llm_logger.error(f"Cannot review {url}: Database not available")
        return

    # Get article
    cursor = conn.execute(
        "SELECT url, title, blog_name, text FROM articles WHERE url = ?",
        (url,)
    )
    article = cursor.fetchone()

    if not article:
        llm_logger.warning(f"Article not found for LLM review: {url}")
        conn.close()
        return

    # Get article text (you'd need to fetch it or store it)
    # For now, assuming we have it stored or will fetch
    text = article[3] if len(article) > 3 else None

    if not text:
        llm_logger.warning(f"No text available for LLM review: {url}")
        conn.close()
        return

    # Score with LLM
    llm_score = score_with_llm(text)

    if llm_score is not None:
        # Update article
        conn.execute(
            "UPDATE articles SET llm_score = ?, combined_score = (score * 0.6 + ? * 0.4) WHERE url = ?",
            (llm_score, llm_score, url)
        )
        conn.commit()
        llm_logger.info(f"LLM review complete for {url}: score={llm_score:.2f}")
    else:
        llm_logger.error(f"LLM scoring failed for {url}")

    conn.close()