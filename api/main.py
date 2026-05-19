from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import os
from datetime import datetime
from api.routes import search, suggestions, blogs
from api.dependencies import get_db
from api.auth import verify_admin_key
from config.settings import API_KEY, RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD, LOG_LEVEL, LOG_FILE

# ---------- Logging ----------
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blog-feed")

# ---------- Rate Limiting ----------
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second"])
app = FastAPI(
    title="Blog Scout API",
    description="Search engine for engineering blog posts",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------- CORS & Security ----------
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["192.168.0.18:8080", "https://blog-hub.pranav-bansal.com/"],  # Replace with your domain in production
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Restrict in production

# ---------- Prometheus Metrics ----------
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ---------- Request Logging Middleware ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response

# ---------- API Router ----------
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# Include route modules
api_router.include_router(search.router, tags=["search"])
api_router.include_router(suggestions.router, tags=["suggestions"])
api_router.include_router(blogs.router, tags=["blogs"])

# ---------- Public endpoints (no auth, but rate limited) ----------
@api_router.get("/stats")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
def get_stats(request: Request):
    conn = get_db()
    if not conn:
        return {"error": "Database not initialized"}
    
    total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    by_source = dict(conn.execute("SELECT source, COUNT(*) FROM articles GROUP BY source").fetchall())
    avg_scores = conn.execute("SELECT AVG(combined_score), AVG(score) FROM articles").fetchone()
    conn.close()
    
    import json
    suggestions_file = "data/reddit_suggestions.json"
    pending = accepted = 0
    if os.path.exists(suggestions_file):
        with open(suggestions_file, 'r') as f:
            suggestions = json.load(f)
            pending = len([s for s in suggestions if not s.get('accepted')])
            accepted = len([s for s in suggestions if s.get('accepted')])
    
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
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
def health_check(request: Request):
    return {"status": "healthy", "database": os.path.exists("data/blog_scout.db")}

# ---------- Admin endpoints (require API key) ----------
# The blogs routes already require admin key – we'll add dependency in blogs.py

app.include_router(api_router)

# ---------- Static Frontend ----------
frontend_dir = "apps/frontend"
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)