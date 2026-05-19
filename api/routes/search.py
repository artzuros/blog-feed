from fastapi import APIRouter, Request, Query, HTTPException
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.dependencies import get_db
from api.logger import api_logger
from config.settings import RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.get("/articles")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
async def list_articles(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("fetched_at", regex="^(fetched_at|combined_score)$")
):
    """List articles with pagination."""
    api_logger.info(f"Listing articles: limit={limit}, offset={offset}, sort={sort} from {request.client.host}")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Get total count
        total_cursor = conn.execute("SELECT COUNT(*) FROM articles")
        total_count = total_cursor.fetchone()[0]
        
        # Order by specified column
        order_by = "fetched_at DESC" if sort == "fetched_at" else "combined_score DESC"
        
        cursor = conn.execute(
            f"""SELECT rowid, url, title, blog_name, score, llm_score, combined_score, 
                      reason, keywords, source, fetched_at 
               FROM articles 
               ORDER BY {order_by}
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        results = cursor.fetchall()
        conn.close()
        
        api_logger.debug(f"Returning {len(results)} articles (total: {total_count})")
        
        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "articles": [
                {
                    "id": r[0],
                    "url": r[1],
                    "title": r[2],
                    "domain": r[3],
                    "score": r[4],
                    "llm_score": r[5],
                    "combined_score": r[6],
                    "reason": r[7],
                    "keywords": r[8],
                    "source": r[9],
                    "published_at": r[10],
                    "llm_review_status": "completed" if r[5] is not None else "pending"
                }
                for r in results
            ]
        }
    except Exception as e:
        api_logger.error(f"Failed to list articles: {e}", exc_info=True)
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
async def search_articles(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum combined score"),
    source: Optional[str] = Query(None, regex="^(rss|reddit)$", description="Filter by source")
):
    """Search articles by title or keywords."""
    api_logger.info(f"Search: query='{q}', limit={limit}, min_score={min_score}, source={source} from {request.client.host}")
    
    conn = get_db()
    if not conn:
        api_logger.error("Database connection failed during search")
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build query based on source filter
        if source:
            cursor = conn.execute(
                """SELECT url, title, blog_name, score, llm_score, combined_score, 
                          reason, keywords, source, fetched_at 
                   FROM articles 
                   WHERE (title LIKE ? OR keywords LIKE ?) 
                   AND combined_score >= ?
                   AND source = ?
                   ORDER BY combined_score DESC
                   LIMIT ?""",
                (f'%{q}%', f'%{q}%', min_score, source, limit)
            )
        else:            
            cursor = conn.execute(
                """SELECT url, title, blog_name, score, llm_score, combined_score, 
                          reason, keywords, source, fetched_at 
                   FROM articles 
                   WHERE (title LIKE ? OR keywords LIKE ?) 
                   AND combined_score >= ?
                   ORDER BY combined_score DESC
                   LIMIT ?""",
                (f'%{q}%', f'%{q}%', min_score, limit)
            )
        
        results = cursor.fetchall()
        conn.close()
        
        api_logger.info(f"Search for '{q}' returned {len(results)} results")
        
        return {
            "query": q,
            "count": len(results),
            "min_score": min_score,
            "articles": [
                {
                    "url": r[0],
                    "title": r[1],
                    "blog_name": r[2],
                    "score": r[3],
                    "llm_score": r[4],
                    "combined_score": r[5],
                    "reason": r[6],
                    "keywords": r[7],
                    "source": r[8],
                    "fetched_at": r[9]
                }
                for r in results
            ]
        }
    except Exception as e:
        api_logger.error(f"Search failed for query '{q}': {e}", exc_info=True)
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/articles/{article_identifier}")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
async def get_article(request: Request, article_identifier: str):
    """
    Get single article by ID (numeric) or base64-encoded URL.
    
    Examples:
    - /api/articles/1 (numeric ID)
    - /api/articles/aHR0cHM6Ly9leGFtcGxlLmNvbS9hcnRpY2xl (base64 URL)
    """
    import base64
    
    api_logger.info(f"Fetching article with identifier: {article_identifier[:50]}...")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    article = None
    
    # Try as numeric ID first
    if article_identifier.isdigit():
        api_logger.debug(f"Trying numeric ID: {article_identifier}")
        cursor = conn.execute(
            "SELECT rowid, * FROM articles WHERE rowid = ?",
            (int(article_identifier),)
        )
        article = cursor.fetchone()
        
        if article:
            api_logger.info(f"Found article by numeric ID: {article_identifier}")
    
    # If not found, try as base64 encoded URL
    if not article:
        try:
            # Try to decode as base64
            url = base64.b64decode(article_identifier).decode('utf-8')
            api_logger.debug(f"Trying base64 decoded URL: {url[:100]}...")
            
            cursor = conn.execute(
                "SELECT rowid, * FROM articles WHERE url = ?",
                (url,)
            )
            article = cursor.fetchone()
            
            if article:
                api_logger.info(f"Found article by base64 URL")
        except Exception as e:
            api_logger.debug(f"Not a valid base64 string: {e}")
    
    conn.close()
    
    if not article:
        api_logger.warning(f"Article not found for identifier: {article_identifier[:50]}...")
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Convert to dict (rowid becomes 'id')
    result = dict(article)
    result['id'] = result.pop('rowid')
    
    return result

@router.get("/semantic-search")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
async def semantic_search_articles(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    min_relevance: float = Query(0.5, ge=0.0, le=1.0, description="Minimum relevance score (0-1)")
):
    """
    Search articles by semantic similarity using embeddings.
    Only returns results with relevance >= min_relevance (default 0.5).
    """
    api_logger.info(f"Semantic search: query='{q}', limit={limit}, min_relevance={min_relevance} from {request.client.host}")
    
    from core.embeddings import semantic_search
    
    # Get semantic search results
    article_ids, similarities = semantic_search(q, limit * 2)  # Get extra to filter
    
    if not article_ids:
        api_logger.debug(f"No semantic results for '{q}'")
        return {
            "query": q,
            "count": 0,
            "articles": [],
            "search_type": "semantic"
        }
    
    # Filter by min_relevance and take top limit
    filtered_results = []
    for idx, (article_id, sim) in enumerate(zip(article_ids, similarities)):
        if sim >= min_relevance:
            filtered_results.append((article_id, sim))
            if len(filtered_results) >= limit:
                break
    
    if not filtered_results:
        api_logger.debug(f"No results above {min_relevance} relevance for '{q}'")
        return {
            "query": q,
            "count": 0,
            "articles": [],
            "search_type": "semantic",
            "min_relevance": min_relevance
        }
    
    # Fetch full article details from SQLite
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    placeholders = ','.join('?' * len(filtered_results))
    article_ids_filtered = [id for id, _ in filtered_results]
    cursor = conn.execute(f"""
        SELECT url, title, blog_name, score, llm_score, combined_score, 
               reason, source, fetched_at 
        FROM articles 
        WHERE rowid IN ({placeholders})
    """, article_ids_filtered)
    
    results = cursor.fetchall()
    conn.close()
    
    # Map results with similarity scores (NO keywords!)
    articles = []
    for (article_id, sim), row in zip(filtered_results, results):
        articles.append({
            "url": row[0],
            "title": row[1],
            "blog_name": row[2],
            "score": row[3],
            "llm_score": row[4],
            "combined_score": row[5],
            "reason": row[6],
            "source": row[7],
            "fetched_at": row[8],
            "semantic_relevance": round(sim, 4)  # Keep relevance score
            # keywords intentionally omitted
        })
    
    api_logger.info(f"Semantic search for '{q}' returned {len(articles)} results (filtered from {len(article_ids)})")
    
    return {
        "query": q,
        "count": len(articles),
        "articles": articles,
        "search_type": "semantic",
        "min_relevance": min_relevance
    }