from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
import sqlite3
import json
import os
from datetime import datetime
from api.dependencies import get_db
from api.logger import api_logger
from config.settings import RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class VoteRequest(BaseModel):
    vote: int  # 1 for upvote, -1 for downvote

@router.get("/suggestions")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
async def get_suggestions(
    request: Request, 
    limit: int = 50,
    sort_by: str = Query("discovered_at", regex="^(discovered_at|net_votes|reddit_score)$")
):
    """Get pending suggestions from Reddit with sorting."""
    api_logger.info(f"Fetching suggestions (limit={limit}, sort_by={sort_by}) from {request.client.host}")
    
    suggestions_file = "data/reddit_suggestions.json"
    if not os.path.exists(suggestions_file):
        api_logger.warning("Suggestions file not found")
        return {"suggestions": []}
    
    try:
        with open(suggestions_file, 'r') as f:
            all_suggestions = json.load(f)
        
        # Filter pending suggestions (not accepted)
        pending = [s for s in all_suggestions if not s.get('accepted', False)]
        
        # Get vote counts for each suggestion
        conn = get_db()
        if conn:
            for suggestion in pending:
                cursor = conn.execute(
                    "SELECT SUM(vote) as score, COUNT(*) as votes, SUM(CASE WHEN vote=1 THEN 1 ELSE 0 END) as upvotes, SUM(CASE WHEN vote=-1 THEN 1 ELSE 0 END) as downvotes FROM suggestion_reviews WHERE suggestion_url = ?",
                    (suggestion['url'],)
                )
                result = cursor.fetchone()
                suggestion['upvotes'] = result[2] if result[2] else 0
                suggestion['downvotes'] = result[3] if result[3] else 0
                suggestion['net_votes'] = result[0] if result[0] else 0
                suggestion['total_votes'] = result[1] if result[1] else 0
            conn.close()
        
        # Apply sorting
        if sort_by == "net_votes":
            pending.sort(key=lambda x: x.get('net_votes', 0), reverse=True)
        elif sort_by == "reddit_score":
            pending.sort(key=lambda x: x.get('reddit_score', 0), reverse=True)
        else:  # discovered_at
            pending.sort(key=lambda x: x.get('discovered_at', ''), reverse=True)
        
        api_logger.info(f"Returning {len(pending[:limit])} suggestions sorted by {sort_by}")
        return pending[:limit]  # Return array directly as frontend expects
        
    except Exception as e:
        api_logger.error(f"Error loading suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggestions/{suggestion_url}/vote")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
async def vote_suggestion(
    request: Request, 
    suggestion_url: str, 
    vote_data: VoteRequest
):
    """Vote on a suggestion (upvote/downvote)."""
    import base64
    
    # Decode URL
    try:
        url = base64.b64decode(suggestion_url).decode()
        api_logger.info(f"Vote on suggestion: {url[:100]}... vote={vote_data.vote} from {request.client.host}")
    except:
        api_logger.warning(f"Invalid suggestion URL encoding: {suggestion_url}")
        raise HTTPException(status_code=400, detail="Invalid suggestion URL")
    
    if vote_data.vote not in (1, -1):
        api_logger.warning(f"Invalid vote value: {vote_data.vote}")
        raise HTTPException(status_code=400, detail="Vote must be 1 or -1")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Get client IP (handle proxy headers)
        client_ip = request.headers.get('X-Forwarded-For', request.client.host)
        
        # Insert or update vote
        conn.execute(
            """INSERT INTO suggestion_reviews (suggestion_url, vote, ip_address, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(suggestion_url, ip_address) 
               DO UPDATE SET vote = ?, created_at = ?""",
            (url, vote_data.vote, client_ip, datetime.now(), vote_data.vote, datetime.now())
        )
        conn.commit()
        
        # Get updated vote stats
        cursor = conn.execute(
            "SELECT SUM(vote) as score, COUNT(*) as votes FROM suggestion_reviews WHERE suggestion_url = ?",
            (url,)
        )
        stats = cursor.fetchone()
        conn.close()
        
        api_logger.debug(f"Vote recorded for {url[:100]}: new score={stats[0]}, votes={stats[1]}")
        
        # Return the full suggestion object for the frontend
        suggestions_file = "data/reddit_suggestions.json"
        suggestion = None
        if os.path.exists(suggestions_file):
            with open(suggestions_file, 'r') as f:
                all_suggestions = json.load(f)
                for s in all_suggestions:
                    if s['url'] == url:
                        suggestion = s
                        break
        
        return {
            "success": True,
            "vote_score": stats[0] if stats[0] else 0,
            "total_votes": stats[1] if stats[1] else 0,
            "upvotes": vote_data.vote if vote_data.vote == 1 else 0,
            "downvotes": vote_data.vote if vote_data.vote == -1 else 0,
            "suggestion": suggestion
        }
    except Exception as e:
        api_logger.error(f"Error recording vote for {url}: {e}", exc_info=True)
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))