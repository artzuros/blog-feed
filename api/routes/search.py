from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from api.dependencies import get_db
from api.models.schemas import SearchResponse, ArticleResponse

router = APIRouter()

@router.get("/search", response_model=SearchResponse)
def search_articles(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Results limit"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum combined score"),
    source: Optional[str] = Query(None, regex="^(rss|reddit)$", description="Filter by source")
):
    """Search articles by title, keywords, or blog name."""
    conn = get_db()
    
    # Build query
    query = """
        SELECT url, title, blog_name, score, llm_score, combined_score, 
               reason, keywords, source, added_by, fetched_at
        FROM articles 
        WHERE (title LIKE ? OR keywords LIKE ? OR blog_name LIKE ?)
    """
    params = [f'%{q}%', f'%{q}%', f'%{q}%']
    
    if min_score is not None:
        query += " AND combined_score >= ?"
        params.append(min_score)
    
    if source:
        query += " AND source = ?"
        params.append(source)
    
    query += " ORDER BY combined_score DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return SearchResponse(
        query=q,
        total=len(results),
        results=[ArticleResponse(**r) for r in results]
    )

@router.get("/articles/recent")
def get_recent_articles(limit: int = Query(20, ge=1, le=100)):
    """Get most recent articles."""
    conn = get_db()
    cursor = conn.execute("""
        SELECT url, title, blog_name, combined_score, source, fetched_at
        FROM articles 
        ORDER BY fetched_at DESC 
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"total": len(results), "results": results}

@router.get("/articles/top")
def get_top_articles(limit: int = Query(20, ge=1, le=100)):
    """Get highest scored articles."""
    conn = get_db()
    cursor = conn.execute("""
        SELECT url, title, blog_name, combined_score, source, fetched_at
        FROM articles 
        ORDER BY combined_score DESC 
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"total": len(results), "results": results}

@router.get("/articles/by-blog/{blog_name}")
def get_articles_by_blog(blog_name: str, limit: int = Query(50, ge=1, le=200)):
    """Get articles from a specific blog."""
    conn = get_db()
    cursor = conn.execute("""
        SELECT url, title, combined_score, source, fetched_at
        FROM articles 
        WHERE blog_name = ? 
        ORDER BY fetched_at DESC 
        LIMIT ?
    """, (blog_name, limit))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"blog": blog_name, "total": len(results), "results": results}