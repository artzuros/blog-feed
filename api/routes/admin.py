from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
import os
import csv
import subprocess
from datetime import datetime
from api.auth import verify_admin_key
from api.dependencies import get_db
from api.logger import api_logger, scan_logger
from config.settings import DB_FILE, BLOGS_CSV, CACHE_FILE
from config.blogs_loader import load_blogs, save_blogs, remove_blog, add_blog
from storage.cache import load_cache, save_cache
from core.scorer import score_blog
from core.llm_scorer import score_with_llm
from core.fetcher import fetch_article_text
from quality.content_classifier import is_marketing_or_news

router = APIRouter(dependencies=[Depends(verify_admin_key)])

# ---------- Pydantic Models ----------
class BlogCreate(BaseModel):
    name: str
    url: str
    rss: Optional[str] = None

class BlogResponse(BaseModel):
    name: str
    url: str
    rss: Optional[str]
    article_count: int
    last_fetched: Optional[str] = None

class ScoreUpdate(BaseModel):
    heuristic_score: Optional[float] = None
    llm_score: Optional[float] = None
    combined_score: Optional[float] = None

class ArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    heuristic_score: float
    llm_score: Optional[float]
    combined_score: float
    fetched_at: str

# ---------- Blog Management ----------
@router.get("/blogs", response_model=List[BlogResponse])
async def list_blogs(request: Request):
    """List all blogs with article counts and last fetched date."""
    api_logger.info(f"Admin listing blogs from {request.client.host}")

    # Load blogs from CSV
    blogs = []
    if os.path.exists(BLOGS_CSV):
        with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                blogs.append(row)

    # Get article counts and last fetched
    conn = get_db()
    if conn:
        for blog in blogs:
            cursor = conn.execute(
                "SELECT COUNT(*), MAX(fetched_at) FROM articles WHERE blog_name = ?",
                (blog['name'],)
            )
            row = cursor.fetchone()
            blog['article_count'] = row[0] if row[0] else 0
            blog['last_fetched'] = row[1] if row[1] else None
        conn.close()

    api_logger.info(f"Returning {len(blogs)} blogs")
    return blogs

@router.post("/blogs")
async def add_blog(request: Request, blog: BlogCreate):
    """Add a new blog."""
    api_logger.info(f"Admin adding blog: {blog.name} ({blog.url}) from {request.client.host}")

    # Load existing blogs
    blogs = []
    if os.path.exists(BLOGS_CSV):
        with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            blogs = list(reader)

    # Check if exists
    if any(b['name'] == blog.name for b in blogs):
        api_logger.warning(f"Attempt to add duplicate blog: {blog.name}")
        raise HTTPException(status_code=400, detail="Blog already exists")

    # Add new blog
    blogs.append({
        'name': blog.name,
        'url': blog.url,
        'rss': blog.rss or ''
    })

    # Save back to CSV
    with open(BLOGS_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'url', 'rss'])
        writer.writeheader()
        writer.writerows(blogs)

    api_logger.info(f"Blog added successfully: {blog.name}")

    return {"success": True, "message": f"Added {blog.name}"}

@router.delete("/blogs/{blog_name}")
async def delete_blog(request: Request, blog_name: str):
    """Delete a blog."""
    api_logger.warning(f"Admin deleting blog: {blog_name} from {request.client.host}")

    if not os.path.exists(BLOGS_CSV):
        raise HTTPException(status_code=404, detail="Blogs file not found")

    blogs = []
    with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        blogs = list(reader)

    original_count = len(blogs)
    blogs = [b for b in blogs if b['name'] != blog_name]

    if len(blogs) == original_count:
        api_logger.warning(f"Blog not found for deletion: {blog_name}")
        raise HTTPException(status_code=404, detail="Blog not found")

    with open(BLOGS_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'url', 'rss'])
        writer.writeheader()
        writer.writerows(blogs)

    api_logger.info(f"Blog deleted: {blog_name}")

    return {"success": True, "message": f"Deleted {blog_name}"}

@router.post("/blogs/{blog_name}/refresh")
async def refresh_blog(
    request: Request, 
    blog_name: str, 
    background_tasks: BackgroundTasks
):
    """Trigger a rescan of a specific blog."""
    api_logger.info(f"Refreshing blog: {blog_name} from {request.client.host}")

    # Find the blog
    blogs = load_blogs()
    blog = next((b for b in blogs if b[0] == blog_name), None)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    # Run in background
    background_tasks.add_task(
        score_blog,
        blog_name,
        blog[1],  # url
        blog[2],  # rss
        load_cache()
    )

    return {"success": True, "message": f"Refresh queued for {blog_name}"}

@router.get("/blogs/{blog_name}/articles", response_model=List[ArticleResponse])
async def get_blog_articles(request: Request, blog_name: str, limit: int = 50):
    """List articles for a specific blog."""
    api_logger.info(f"Fetching articles for blog: {blog_name} (limit={limit})")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")

    cursor = conn.execute(
        """SELECT rowid, url, title, score, llm_score, combined_score, fetched_at 
           FROM articles 
           WHERE blog_name = ? 
           ORDER BY fetched_at DESC 
           LIMIT ?""",
        (blog_name, limit)
    )

    articles = []
    for row in cursor:
        articles.append({
            "id": row[0],
            "url": row[1],
            "title": row[2],
            "heuristic_score": row[3],
            "llm_score": row[4],
            "combined_score": row[5],
            "fetched_at": row[6]
        })

    conn.close()
    api_logger.debug(f"Returned {len(articles)} articles for {blog_name}")
    return articles

# ---------- Article Scoring Management ----------
@router.post("/articles/{article_id}/score")
async def update_article_score(
    request: Request, 
    article_id: int, 
    score_data: ScoreUpdate
):
    """Manually update heuristic/LLM/combined scores for an article."""
    api_logger.info(f"Updating scores for article {article_id} from {request.client.host}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")

    updates = []
    params = []

    if score_data.heuristic_score is not None:
        updates.append("score = ?")
        params.append(score_data.heuristic_score)
    if score_data.llm_score is not None:
        updates.append("llm_score = ?")
        params.append(score_data.llm_score)
    if score_data.combined_score is not None:
        updates.append("combined_score = ?")
        params.append(score_data.combined_score)

    if not updates:
        raise HTTPException(status_code=400, detail="No score fields provided")

    params.append(article_id)
    query = f"UPDATE articles SET {', '.join(updates)} WHERE rowid = ?"

    try:
        conn.execute(query, params)
        conn.commit()
        conn.close()
        api_logger.info(f"Scores updated for article {article_id}")

        return {"success": True, "message": "Score updated"}
    except Exception as e:
        api_logger.error(f"Failed to update scores: {e}", exc_info=True)
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/articles/{article_id}/review")
async def review_article(
    request: Request, 
    article_id: int, 
    background_tasks: BackgroundTasks
):
    """Trigger LLM review for a single article."""
    api_logger.info(f"Triggering LLM review for article {article_id} from {request.client.host}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")

    # Get article URL
    cursor = conn.execute("SELECT url FROM articles WHERE rowid = ?", (article_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Article not found")

    # Run in background
    background_tasks.add_task(process_article_llm_review, row[0], article_id)

    return {"success": True, "message": f"LLM review queued for article {article_id}"}

async def process_article_llm_review(url: str, article_id: int):
    """Background task to process LLM review for an article."""
    api_logger.info(f"Processing LLM review for {url}")

    text = fetch_article_text(url)
    if not text or len(text) < 200:
        api_logger.warning(f"Insufficient text for LLM review: {url}")
        return

    llm_score = score_with_llm(text)
    if llm_score is None:
        api_logger.error(f"LLM scoring failed for {url}")
        return

    conn = get_db()
    if conn:
        conn.execute(
            "UPDATE articles SET llm_score = ?, combined_score = (score * 0.6 + ? * 0.4) WHERE rowid = ?",
            (llm_score, llm_score, article_id)
        )
        conn.commit()
        conn.close()
        api_logger.info(f"LLM review completed for article {article_id}: score={llm_score:.2f}")

# ---------- Reddit Discovery Integration ----------
@router.get("/reddit/suggestions")
async def get_reddit_suggestions(request: Request, limit: int = 50):
    """Fetch pending Reddit suggestions."""
    api_logger.info(f"Fetching Reddit suggestions (limit={limit}) from {request.client.host}")

    suggestions_file = "data/reddit_suggestions.json"
    if not os.path.exists(suggestions_file):
        return []

    try:
        with open(suggestions_file, 'r') as f:
            all_suggestions = json.load(f)

        # Filter pending suggestions (not accepted)
        pending = [s for s in all_suggestions if not s.get('accepted', False)]

        # Get vote counts from database
        conn = get_db()
        if conn:
            for suggestion in pending:
                cursor = conn.execute(
                    "SELECT SUM(vote) as score, COUNT(*) as votes FROM suggestion_reviews WHERE suggestion_url = ?",
                    (suggestion['url'],)
                )
                result = cursor.fetchone()
                suggestion['vote_score'] = result[0] if result[0] else 0
                suggestion['total_votes'] = result[1] if result[1] else 0
            conn.close()

        api_logger.info(f"Returning {len(pending[:limit])} pending suggestions")
        return pending[:limit]
    except Exception as e:
        api_logger.error(f"Error loading suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reddit/discover")
async def run_reddit_discovery(request: Request, background_tasks: BackgroundTasks):
    """Run Reddit discovery script in background."""
    api_logger.info(f"Running Reddit discovery from {request.client.host}")

    background_tasks.add_task(run_reddit_discovery_script)

    return {"success": True, "message": "Reddit discovery started in background"}

async def run_reddit_discovery_script():
    """Background task to run Reddit discovery."""
    scan_logger.info("Starting Reddit discovery background task")
    try:
        # Use the non-interactive version
        result = subprocess.run(
            ["python", "scripts/reddit_discovery_api.py"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        if result.returncode == 0:
            scan_logger.info("Reddit discovery completed successfully")
            scan_logger.debug(f"Output: {result.stdout[:500]}")
        else:
            scan_logger.error(f"Reddit discovery failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        scan_logger.error("Reddit discovery timed out after 5 minutes")
    except Exception as e:
        scan_logger.error(f"Reddit discovery error: {e}", exc_info=True)

@router.post("/reddit/suggestions/accept")
async def accept_reddit_suggestion(request: Request, suggestion_url: str):
    """Mark a Reddit suggestion as accepted (without auto-adding to blogs)."""
    api_logger.info(f"Accepting Reddit suggestion: {suggestion_url} from {request.client.host}")

    suggestions_file = "data/reddit_suggestions.json"
    if not os.path.exists(suggestions_file):
        raise HTTPException(status_code=404, detail="Suggestions file not found")

    with open(suggestions_file, 'r') as f:
        suggestions = json.load(f)

    found = False
    for suggestion in suggestions:
        if suggestion['url'] == suggestion_url:
            suggestion['accepted'] = True
            suggestion['accepted_at'] = datetime.now().isoformat()
            found = True
            break

    if not found:
        api_logger.warning(f"Suggestion not found: {suggestion_url}")
        raise HTTPException(status_code=404, detail="Suggestion not found")

    with open(suggestions_file, 'w') as f:
        json.dump(suggestions, f, indent=2)

    api_logger.info(f"Suggestion accepted: {suggestion_url}")
    return {"success": True, "message": "Suggestion accepted"}

# ---------- Legacy Suggestions Accept (keep for compatibility) ----------
@router.post("/suggestions/accept")
async def accept_suggestion(request: Request, suggestion_url: str):
    """Accept a Reddit suggestion and save ONLY the specific article (not the whole blog)."""
    import base64
    try:
        url = base64.b64decode(suggestion_url).decode()
        api_logger.info(f"Accepting suggestion and saving article: {url} from {request.client.host}")
    except:
        api_logger.error(f"Invalid suggestion URL encoding: {suggestion_url}")
        raise HTTPException(status_code=400, detail="Invalid suggestion URL")

    suggestions_file = "data/reddit_suggestions.json"
    if not os.path.exists(suggestions_file):
        raise HTTPException(status_code=404, detail="Suggestions file not found")

    with open(suggestions_file, 'r') as f:
        suggestions = json.load(f)

    found_suggestion = None
    for suggestion in suggestions:
        if suggestion['url'] == url:
            suggestion['accepted'] = True
            suggestion['accepted_at'] = datetime.now().isoformat()
            found_suggestion = suggestion
            break

    if not found_suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    # Save the article directly to database
    from core.fetcher import fetch_article_text
    from quality.slop_detector import is_likely_ai_slop
    from core.keywords import extract_keywords
    from storage.database import save_article

    # Fetch full article text
    text = fetch_article_text(url)
    if not text or len(text) < 200:
        raise HTTPException(status_code=400, detail="Could not extract enough article text")

    # Re-run heuristic scoring
    heuristic_score, reason = is_likely_ai_slop(text)

    # Use LLM score if available
    llm_score = found_suggestion.get('llm_score')
    combined = heuristic_score
    if llm_score is not None:
        combined = heuristic_score * 0.6 + llm_score * 0.4

    # Extract keywords
    keywords = extract_keywords(text)

    # Save article
    try:
        save_article(
            url=url,
            title=found_suggestion.get('title', ''),
            blog_name=found_suggestion.get('domain', 'reddit-discovery'),
            score=heuristic_score,
            llm_score=llm_score,
            combined_score=combined,
            reason=reason,
            keywords=keywords,
            source='reddit',
            reddit_suggestion_id=url,
            added_by='manual_review',
            text_content=text
        )
        api_logger.info(f"Article saved from accepted suggestion: {url}")

    except Exception as e:
        api_logger.error(f"Failed to save article: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save article: {str(e)}")

    # Save updated suggestions (mark as accepted)
    with open(suggestions_file, 'w') as f:
        json.dump(suggestions, f, indent=2)

    return {"success": True, "message": "Article accepted and saved to database"}

async def scan_new_blog(blog_name, blog_url, rss_url):
    """Background task to fetch articles for a newly added blog."""
    from core.scorer import score_blog
    from storage.cache import load_cache
    cache = load_cache()
    score_blog(blog_name, blog_url, rss_url, cache)
    from storage.cache import save_cache
    save_cache(cache)
    api_logger.info(f"Completed initial scan for new blog: {blog_name}")

# ---------- Admin Verification ----------
@router.get("/verify")
async def verify_admin(request: Request):
    """Verify that the API key is valid."""
    api_logger.debug(f"Admin verification from {request.client.host}")
    return {"valid": True, "message": "API key is valid"}

# ---------- CrewAI Article Evaluation ----------
@router.post("/admin/evaluate/{article_id}")
def evaluate_article(request: Request, article_id: int):
    """Run CrewAI multi-agent evaluation on an article and store results.

    Sync (not async) so crew.kickoff() runs in a threadpool — CrewAI
    refuses synchronous agent execution from within a running event loop.
    """
    from quality.crew_evaluator import run_evaluation, save_evaluation, get_evaluation
    from quality.crew_evaluator import run_evaluation, save_evaluation, get_evaluation

    api_logger.info(f"Agentic evaluation requested for article {article_id}")

    # Check if already evaluated
    existing = get_evaluation(article_id)
    if existing:
        api_logger.info(f"Article {article_id} already evaluated, returning cached result")
        return {"cached": True, "evaluation": existing}

    # Fetch article text
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        row = conn.execute(
            "SELECT rowid, title, text_content FROM articles WHERE rowid = ?",
            (article_id,)
        ).fetchone()
        conn.close()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not row:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

    title = row["title"] or "Untitled"
    text = row["text_content"] or ""

    if not text or len(text) < 300:
        raise HTTPException(
            status_code=400,
            detail=f"Article text too short ({len(text)} chars) — need at least 300"
        )

    # Run CrewAI evaluation
    result = run_evaluation(title, text)
    if not result:
        raise HTTPException(status_code=500, detail="Agentic evaluation failed")

    # Persist
    save_evaluation(article_id, result)

    return {
        "article_id": article_id,
        "title": title,
        "evaluation": result.to_dict(),
    }

@router.get("/admin/evaluations")
async def list_article_evaluations(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    min_score: Optional[float] = None,
    content_type: Optional[str] = None,
    min_depth: Optional[int] = None,
    has_code: Optional[bool] = None,
    sort_by: str = "overall_score",
):
    """Query article evaluations with optional filters."""
    from quality.crew_evaluator import list_evaluations

    api_logger.info(f"Listing evaluations: limit={limit}, offset={offset}, "
                    f"min_score={min_score}, type={content_type}")

    results = list_evaluations(
        limit=limit,
        offset=offset,
        min_score=min_score,
        content_type=content_type,
        min_depth=min_depth,
        has_code=has_code,
        sort_by=sort_by,
    )

    return {
        "count": len(results),
        "limit": limit,
        "offset": offset,
        "evaluations": results,
    }