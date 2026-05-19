from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import List, Optional
from datetime import datetime
from api.dependencies import load_suggestions, get_db
from api.models.schemas import SuggestionResponse, SuggestionReview
from api.auth import verify_admin_key
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import os

router = APIRouter()
SUGGESTIONS_FILE = "data/reddit_suggestions.json"
limiter = Limiter(key_func=get_remote_address)

def save_suggestions(suggestions):
    os.makedirs(os.path.dirname(SUGGESTIONS_FILE), exist_ok=True)
    with open(SUGGESTIONS_FILE, 'w') as f:
        json.dump(suggestions, f, indent=2)

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
    return votes

@router.get("/suggestions", response_model=List[dict])
def get_suggestions(
    status: Optional[str] = Query(None, pattern="^(pending|llm|manual)$"),
    accepted: Optional[bool] = None,
    sort_by: Optional[str] = Query("discovered_at", pattern="^(discovered_at|net_votes|reddit_score)$")
):
    suggestions = load_suggestions()
    if not suggestions:
        return []
    if status:
        suggestions = [s for s in suggestions if s.get('reviewed') == status]
    if accepted is not None:
        suggestions = [s for s in suggestions if s.get('accepted', False) == accepted]
    
    # Attach vote counts
    for s in suggestions:
        votes = get_vote_counts(s['url'])
        s['upvotes'] = votes['upvotes']
        s['downvotes'] = votes['downvotes']
        s['net_votes'] = votes['net']
        # Convert datetime strings
        if 'discovered_at' in s and isinstance(s['discovered_at'], str):
            s['discovered_at'] = datetime.fromisoformat(s['discovered_at'])
        if 'reviewed_at' in s and isinstance(s['reviewed_at'], str):
            s['reviewed_at'] = datetime.fromisoformat(s['reviewed_at'])
        if 'accepted_at' in s and isinstance(s['accepted_at'], str):
            s['accepted_at'] = datetime.fromisoformat(s['accepted_at'])
    
    # Sorting
    if sort_by == "net_votes":
        suggestions.sort(key=lambda x: x.get('net_votes', 0), reverse=True)
    elif sort_by == "reddit_score":
        suggestions.sort(key=lambda x: x.get('reddit_score', 0), reverse=True)
    else:
        suggestions.sort(key=lambda x: x.get('discovered_at', datetime.min), reverse=True)
    
    return suggestions

@router.post("/suggestions/{suggestion_id}/review")
@limiter.limit("5/minute")
def submit_review(request: Request, suggestion_id: str, review: SuggestionReview):
    """Public endpoint to upvote/downvote a suggestion."""
    if review.action not in ["upvote", "downvote"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    vote_value = 1 if review.action == "upvote" else -1
    
    # Get client IP (respects proxy headers)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    # Check if already voted
    cur = conn.execute(
        "SELECT vote FROM suggestion_reviews WHERE suggestion_url = ? AND ip_address = ?",
        (suggestion_id, client_ip)
    )
    existing = cur.fetchone()
    if existing:
        if existing[0] == vote_value:
            conn.close()
            return {"message": "Already voted this way"}
        else:
            # Update vote
            conn.execute(
                "UPDATE suggestion_reviews SET vote = ?, created_at = CURRENT_TIMESTAMP WHERE suggestion_url = ? AND ip_address = ?",
                (vote_value, suggestion_id, client_ip)
            )
    else:
        conn.execute(
            "INSERT INTO suggestion_reviews (suggestion_url, vote, ip_address) VALUES (?, ?, ?)",
            (suggestion_id, vote_value, client_ip)
        )
    conn.commit()
    conn.close()
    
    # Recalculate vote counts
    votes = get_vote_counts(suggestion_id)
    return {"message": "Vote recorded", "upvotes": votes["upvotes"], "downvotes": votes["downvotes"], "net": votes["net"]}

@router.post("/suggestions/accept", dependencies=[Depends(verify_admin_key)])
def accept_suggestion(suggestion_url: str):
    """Admin endpoint to mark a suggestion as accepted."""
    suggestions = load_suggestions()
    suggestion = next((s for s in suggestions if s['url'] == suggestion_url), None)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion['accepted'] = True
    suggestion['accepted_at'] = datetime.now().isoformat()
    suggestion['reviewed'] = 'manual'
    save_suggestions(suggestions)
    
    # Add to blogs.csv
    from config.blogs_loader import add_blog
    add_blog(suggestion['domain'], f"https://{suggestion['domain']}", None)
    
    return {"message": f"Accepted {suggestion['domain']}"}