from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import List, Optional
from datetime import datetime
import urllib.parse
import json
import os
from api.dependencies import load_suggestions, get_db
from api.models.schemas import SuggestionReview
from api.auth import verify_admin_key
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.logger import root_logger

router = APIRouter()
SUGGESTIONS_FILE = "data/reddit_suggestions.json"
limiter = Limiter(key_func=get_remote_address)

def save_suggestions(suggestions):
    os.makedirs(os.path.dirname(SUGGESTIONS_FILE), exist_ok=True)
    with open(SUGGESTIONS_FILE, 'w') as f:
        json.dump(suggestions, f, indent=2)
    root_logger.debug(f"Saved {len(suggestions)} suggestions to {SUGGESTIONS_FILE}")

def get_vote_counts(suggestion_url):
    conn = get_db()
    if not conn:
        return {"upvotes": 0, "downvotes": 0, "net": 0}
    cur = conn.execute(
        "SELECT vote, COUNT(*) FROM suggestion_reviews WHERE suggestion_url = ? GROUP BY vote",
        (suggestion_url,)
    )
    votes = {"upvotes": 0, "downvotes": 0}
    for vote, count in cur.fetchall():
        if vote == 1:
            votes["upvotes"] = count
        elif vote == -1:
            votes["downvotes"] = count
    conn.close()
    votes["net"] = votes["upvotes"] - votes["downvotes"]
    root_logger.debug(f"Vote counts for {suggestion_url}: {votes}")
    return votes

@router.get("/suggestions", response_model=List[dict])
def get_suggestions(
    status: Optional[str] = Query(None, pattern="^(pending|llm|manual)$"),
    accepted: Optional[bool] = None,
    sort_by: Optional[str] = Query("discovered_at", pattern="^(discovered_at|net_votes|reddit_score)$")
):
    root_logger.info(f"GET /suggestions called with status={status}, accepted={accepted}, sort_by={sort_by}")
    suggestions = load_suggestions()
    if not suggestions:
        root_logger.info("No suggestions found")
        return []
    if status:
        suggestions = [s for s in suggestions if s.get('reviewed') == status]
    if accepted is not None:
        suggestions = [s for s in suggestions if s.get('accepted', False) == accepted]
    
    for s in suggestions:
        votes = get_vote_counts(s['url'])
        s['upvotes'] = votes['upvotes']
        s['downvotes'] = votes['downvotes']
        s['net_votes'] = votes['net']
        if 'discovered_at' in s and isinstance(s['discovered_at'], str):
            s['discovered_at'] = datetime.fromisoformat(s['discovered_at'])
        if 'reviewed_at' in s and isinstance(s['reviewed_at'], str):
            s['reviewed_at'] = datetime.fromisoformat(s['reviewed_at'])
        if 'accepted_at' in s and isinstance(s['accepted_at'], str):
            s['accepted_at'] = datetime.fromisoformat(s['accepted_at'])
    
    if sort_by == "net_votes":
        suggestions.sort(key=lambda x: x.get('net_votes', 0), reverse=True)
    elif sort_by == "reddit_score":
        suggestions.sort(key=lambda x: x.get('reddit_score', 0), reverse=True)
    else:
        suggestions.sort(key=lambda x: x.get('discovered_at', datetime.min), reverse=True)
    
    root_logger.info(f"Returning {len(suggestions)} suggestions")
    return suggestions

@router.post("/suggestions/{suggestion_id:path}/review")
@limiter.limit("5/minute")
def submit_review(request: Request, suggestion_id: str, review: SuggestionReview):
    root_logger.info(f"POST /suggestions/{suggestion_id}/review with action={review.action}")
    
    decoded_url = urllib.parse.unquote(suggestion_id)
    root_logger.debug(f"Decoded URL: {decoded_url}")
    
    if review.action not in ["upvote", "downvote"]:
        root_logger.warning(f"Invalid action: {review.action}")
        raise HTTPException(status_code=400, detail="Invalid action")
    vote_value = 1 if review.action == "upvote" else -1
    
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    root_logger.debug(f"Client IP: {client_ip}, vote_value: {vote_value}")
    
    conn = get_db()
    if not conn:
        root_logger.error("Database unavailable")
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    cur = conn.execute(
        "SELECT vote FROM suggestion_reviews WHERE suggestion_url = ? AND ip_address = ?",
        (decoded_url, client_ip)
    )
    existing = cur.fetchone()
    
    if existing:
        if existing[0] == vote_value:
            conn.close()
            root_logger.info(f"User already voted {review.action} on {decoded_url}")
            return {"message": "Already voted this way"}
        else:
            conn.execute(
                "UPDATE suggestion_reviews SET vote = ?, created_at = CURRENT_TIMESTAMP WHERE suggestion_url = ? AND ip_address = ?",
                (vote_value, decoded_url, client_ip)
            )
            root_logger.info(f"Updated vote from {existing[0]} to {vote_value} for {decoded_url}")
    else:
        conn.execute(
            "INSERT INTO suggestion_reviews (suggestion_url, vote, ip_address) VALUES (?, ?, ?)",
            (decoded_url, vote_value, client_ip)
        )
        root_logger.info(f"Inserted new vote {vote_value} for {decoded_url}")
    
    conn.commit()
    conn.close()
    
    votes = get_vote_counts(decoded_url)
    return {"message": "Vote recorded", "upvotes": votes["upvotes"], "downvotes": votes["downvotes"], "net": votes["net"]}

@router.post("/suggestions/accept", dependencies=[Depends(verify_admin_key)])
def accept_suggestion(suggestion_url: str):
    root_logger.info(f"POST /suggestions/accept called for {suggestion_url}")
    suggestions = load_suggestions()
    suggestion = next((s for s in suggestions if s['url'] == suggestion_url), None)
    if not suggestion:
        root_logger.warning(f"Suggestion not found: {suggestion_url}")
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion['accepted'] = True
    suggestion['accepted_at'] = datetime.now().isoformat()
    suggestion['reviewed'] = 'manual'
    save_suggestions(suggestions)
    root_logger.info(f"Accepted suggestion: {suggestion['domain']}")
    
    from config.blogs_loader import add_blog
    add_blog(suggestion['domain'], f"https://{suggestion['domain']}", None)
    root_logger.info(f"Added {suggestion['domain']} to blogs.csv")
    
    return {"message": f"Accepted {suggestion['domain']}"}