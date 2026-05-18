from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import search, suggestions, blogs
from api.dependencies import get_db
import os

app = FastAPI(
    title="Blog Scout API",
    description="Search engine for engineering blog posts",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create an API router for all endpoints
api_router = APIRouter(prefix="/api")

# Include the existing routers
api_router.include_router(search.router, tags=["search"])
api_router.include_router(suggestions.router, tags=["suggestions"])
api_router.include_router(blogs.router, tags=["blogs"])

# Add stats and health to the API router
@api_router.get("/stats")
def get_stats():
    """Get overall statistics."""
    conn = get_db()
    if not conn:
        return {"error": "Database not initialized"}
    
    # Total articles
    total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    
    # By source
    by_source = dict(conn.execute(
        "SELECT source, COUNT(*) FROM articles GROUP BY source"
    ).fetchall())
    
    # Average scores
    avg_scores = conn.execute(
        "SELECT AVG(combined_score), AVG(score) FROM articles"
    ).fetchone()
    
    conn.close()
    
    # Suggestions stats
    import json
    suggestions_file = "data/reddit_suggestions.json"
    pending = 0
    accepted = 0
    if os.path.exists(suggestions_file):
        with open(suggestions_file, 'r') as f:
            suggestions = json.load(f)
            pending = len([s for s in suggestions if s.get('accepted') != True])
            accepted = len([s for s in suggestions if s.get('accepted') == True])
    
    # Blogs count
    from api.dependencies import load_blogs_csv
    blogs = load_blogs_csv()
    
    return {
        "total_articles": total_articles,
        "total_blogs": len(blogs),
        "pending_suggestions": pending,
        "accepted_suggestions": accepted,
        "articles_by_source": by_source,
        "avg_heuristic_score": avg_scores[1] if avg_scores[1] else 0,
        "avg_combined_score": avg_scores[0] if avg_scores[0] else 0
    }

@api_router.get("/health")
def health_check():
    return {"status": "healthy", "database": os.path.exists("data/blog_scout.db")}

# Mount the API router
app.include_router(api_router)

# Serve static frontend if it exists
frontend_dir = "apps/frontend"
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)