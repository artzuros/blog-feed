from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from api.dependencies import load_suggestions
from api.models.schemas import SuggestionResponse, SuggestionReview
import json
import os

router = APIRouter()
SUGGESTIONS_FILE = "data/reddit_suggestions.json"

def save_suggestions(suggestions):
    with open(SUGGESTIONS_FILE, 'w') as f:
        json.dump(suggestions, f, indent=2)

@router.get("/suggestions", response_model=List[SuggestionResponse])
def get_suggestions(
    status: Optional[str] = Query(None, regex="^(pending|llm|manual)$"),
    accepted: Optional[bool] = None
):
    """Get Reddit suggestions with optional filters."""
    suggestions = load_suggestions()
    
    # Apply filters
    if status:
        suggestions = [s for s in suggestions if s.get('reviewed') == status]
    if accepted is not None:
        suggestions = [s for s in suggestions if s.get('accepted', False) == accepted]
    
    # Convert datetime strings
    for s in suggestions:
        if 'discovered_at' in s:
            s['discovered_at'] = datetime.fromisoformat(s['discovered_at'])
    
    return suggestions

@router.post("/suggestions/{suggestion_id}/review")
def review_suggestion(suggestion_id: str, review: SuggestionReview):
    """Review a suggestion (accept/reject/llm_review)."""
    suggestions = load_suggestions()
    
    # Find suggestion by URL
    suggestion = None
    for s in suggestions:
        if s.get('url') == suggestion_id:
            suggestion = s
            break
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if review.action == 'accept':
        suggestion['accepted'] = True
        suggestion['accepted_at'] = datetime.now().isoformat()
        suggestion['reviewed'] = 'manual'
        suggestion['reviewed_at'] = datetime.now().isoformat()
        message = f"Accepted {suggestion['domain']}"
    
    elif review.action == 'reject':
        suggestion['accepted'] = False
        suggestion['reviewed'] = 'manual'
        suggestion['reviewed_at'] = datetime.now().isoformat()
        message = f"Rejected {suggestion['domain']}"
    
    elif review.action == 'llm_review':
        # Trigger LLM review (async or background task)
        from core.llm_scorer import score_with_llm
        from core.fetcher import fetch_article_text
        
        text = fetch_article_text(suggestion['url'])
        if text and len(text) > 200:
            llm_score = score_with_llm(text)
            if llm_score:
                suggestion['llm_score'] = llm_score
                suggestion['combined_score'] = (suggestion['heuristic_score'] * 0.6) + (llm_score * 0.4)
                suggestion['reviewed'] = 'llm'
                suggestion['reviewed_at'] = datetime.now().isoformat()
                message = f"LLM reviewed {suggestion['domain']} (score: {llm_score:.2f})"
            else:
                raise HTTPException(status_code=500, detail="LLM review failed")
        else:
            raise HTTPException(status_code=400, detail="Could not fetch article text")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    save_suggestions(suggestions)
    return {"message": message, "suggestion": suggestion}

@router.post("/suggestions/import-accepted")
def import_accepted_suggestions():
    """Import accepted suggestions to blogs.csv."""
    import subprocess
    result = subprocess.run(
        ['python', 'scripts/import_reddit_to_curated.py'],
        capture_output=True,
        text=True
    )
    return {
        "message": "Import completed",
        "stdout": result.stdout,
        "stderr": result.stderr
    }