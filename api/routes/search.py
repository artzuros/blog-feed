from fastapi import APIRouter, Request, Query, HTTPException
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.dependencies import get_db
from api.logger import api_logger
from config.settings import RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _sanitize_fts5_query(query: str) -> str:
    """Make a user query safe for FTS5 MATCH, with prefix matching on last word."""
    # Strip FTS5 special characters that cause syntax errors
    for char in '*"()+-':
        query = query.replace(char, ' ')
    words = query.split()
    if not words:
        return None
    # Prefix match on the last word so "kubernetes deploy" matches "deployment"
    words[-1] = words[-1] + '*'
    return ' '.join(words)

def _fts5_available(conn) -> bool:
    """Check if the FTS5 index table exists and has data."""
    try:
        count = conn.execute("SELECT COUNT(*) FROM articles_fts").fetchone()[0]
        return count > 0
    except Exception:
        return False


# Relevance threshold for the semantic fallback. Slightly more lenient than the
# /semantic-search endpoint's default (0.5) so a typo or odd phrasing is more
# likely to get rescued than to still return nothing.
SEMANTIC_FALLBACK_MIN_RELEVANCE = 0.4


def _semantic_fallback(query: str, limit: int, offset: int,
                       min_score: float, source: Optional[str]):
    """When FTS5/LIKE finds nothing, retry via embedding search.

    Returns article dicts in the same shape as FTS5 results (with
    ``semantic_relevance`` instead of ``snippet``/``fts_rank``), or None when
    nothing passes the relevance / score / source filters.
    """
    from core.embeddings import semantic_search

    try:
        article_ids, similarities = semantic_search(query, limit + offset + 20)
    except Exception as e:
        api_logger.warning(f"Semantic fallback failed for '{query}': {e}")
        return None
    if not article_ids:
        return None

    conn = get_db()
    if not conn:
        return None
    try:
        placeholders = ",".join("?" * len(article_ids))
        cursor = conn.execute(
            f"""
            SELECT rowid, url, title, blog_name, score, llm_score, combined_score,
                   reason, keywords, source, fetched_at
            FROM articles
            WHERE rowid IN ({placeholders})
            """,
            list(article_ids),
        )
        rows = {r[0]: r for r in cursor.fetchall()}
    except Exception as e:
        api_logger.warning(f"Semantic fallback DB lookup failed for '{query}': {e}")
        return None
    finally:
        conn.close()

    matched = []
    for article_id, sim in zip(article_ids, similarities):
        if sim < SEMANTIC_FALLBACK_MIN_RELEVANCE:
            continue
        row = rows.get(article_id)
        if not row:
            continue
        if min_score > 0 and (row[6] or 0) < min_score:
            continue
        if source and row[9] != source:
            continue
        matched.append((row, sim))

    matched = matched[offset:offset + limit]
    if not matched:
        return None

    return [
        {
            "url": row[1],
            "title": row[2],
            "blog_name": row[3],
            "score": row[4],
            "llm_score": row[5],
            "combined_score": row[6],
            "reason": row[7],
            "keywords": row[8],
            "source": row[9],
            "fetched_at": row[10],
            "snippet": None,
            "fts_rank": None,
            "semantic_relevance": round(sim, 4),
        }
        for (row, sim) in matched
    ]


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
    offset: int = Query(0, ge=0),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum combined score"),
    source: Optional[str] = Query(None, regex="^(rss|reddit)$", description="Filter by source")
):
    """Full-text search articles with hybrid BM25 + quality ranking."""
    api_logger.info(f"Search: query='{q}', limit={limit}, offset={offset}, "
                    f"min_score={min_score}, source={source} from {request.client.host}")

    conn = get_db()
    if not conn:
        api_logger.error("Database connection failed during search")
        raise HTTPException(status_code=500, detail="Database not initialized")

    fts5_query = _sanitize_fts5_query(q)
    use_fts5 = _fts5_available(conn) and fts5_query

    def _execute_search(use_fts5_flag):
        """Build and execute the search query."""
        clauses = []
        params = []

        if use_fts5_flag:
            clauses.append("articles_fts MATCH ?")
            params.append(fts5_query)
        else:
            clauses.append("(a.title LIKE ? OR a.keywords LIKE ?)")
            params.extend([f'%{q}%', f'%{q}%'])

        if min_score > 0:
            clauses.append("a.combined_score >= ?")
            params.append(min_score)

        if source:
            clauses.append("a.source = ?")
            params.append(source)

        where_sql = " AND ".join(clauses)

        if use_fts5_flag:
            sql = f"""
                SELECT a.url, a.title, a.blog_name, a.score, a.llm_score,
                       a.combined_score, a.reason, a.keywords, a.source,
                       a.fetched_at,
                       snippet(articles_fts, 2, '<mark>', '</mark>', '…', 32) AS snippet,
                       rank AS fts_rank
                FROM articles a
                JOIN articles_fts ON a.rowid = articles_fts.rowid
                WHERE {where_sql}
                ORDER BY (a.combined_score * 100) - rank DESC
                LIMIT ? OFFSET ?
            """
        else:
            sql = f"""
                SELECT a.url, a.title, a.blog_name, a.score, a.llm_score,
                       a.combined_score, a.reason, a.keywords, a.source,
                       a.fetched_at,
                       NULL AS snippet, NULL AS fts_rank
                FROM articles a
                WHERE {where_sql}
                ORDER BY a.combined_score DESC
                LIMIT ? OFFSET ?
            """

        params.extend([limit, offset])
        return conn.execute(sql, params).fetchall()

    try:
        if use_fts5:
            try:
                results = _execute_search(use_fts5_flag=True)
                search_type = "fts5"
            except Exception as fts5_err:
                api_logger.warning(f"FTS5 query failed, falling back to LIKE: {fts5_err}")
                results = _execute_search(use_fts5_flag=False)
                search_type = "like"
        else:
            results = _execute_search(use_fts5_flag=False)
            search_type = "like"

        conn.close()

        api_logger.info(f"Search for '{q}' returned {len(results)} results (type={search_type})")

        if not results:
            fallback_articles = _semantic_fallback(q, limit, offset, min_score, source)
            if fallback_articles:
                api_logger.info(f"Semantic fallback for '{q}' returned {len(fallback_articles)} results")
                return {
                    "query": q,
                    "count": len(fallback_articles),
                    "limit": limit,
                    "offset": offset,
                    "min_score": min_score,
                    "search_type": "semantic",
                    "fallback": True,
                    "articles": fallback_articles,
                }

        return {
            "query": q,
            "count": len(results),
            "limit": limit,
            "offset": offset,
            "min_score": min_score,
            "search_type": search_type,
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
                    "fetched_at": r[9],
                    "snippet": r[10],
                    "fts_rank": r[11],
                }
                for r in results
            ],
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