from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from prometheus_fastapi_instrumentator import Instrumentator
import os
from datetime import datetime

from api.routes import search, suggestions, blogs, admin, llm
from api.dependencies import get_db
from api.auth import verify_admin_key
from api.logger import root_logger, api_logger, reconfigure_logging
from api.analytics import posthog_client
from config.settings import RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD, LOG_LEVEL, LOG_FILE
from core.embeddings import init_embeddings

# Reconfigure logging with actual settings
reconfigure_logging(LOG_LEVEL, LOG_FILE)

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# ---------- Prometheus Metrics ----------
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ---------- Request Logging Middleware ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start).total_seconds()
    
    # Log based on status code
    if response.status_code >= 500:
        api_logger.error(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    elif response.status_code >= 400:
        api_logger.warning(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    else:
        api_logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    
    return response

# ---------- Startup/Shutdown Events ----------
@app.on_event("startup")
async def startup_event():
    api_logger.info("Blog Feed API starting up")
    # Initialize embedding system
    try:
        init_embeddings()
        api_logger.info("Embedding system initialized successfully")
    except Exception as e:
        api_logger.error(f"Failed to initialize embedding system: {e}", exc_info=True)
    
    # Verify database exists
    if not os.path.exists("data/blog_scout.db"):
        api_logger.warning("Database file not found, will be created on first request")
    else:
        api_logger.info("Database found")

@app.on_event("shutdown")
async def shutdown_event():
    api_logger.info("Blog Feed API shutting down")
    posthog_client.shutdown()

# ---------- API Router ----------
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# Include route modules
api_router.include_router(search.router, tags=["search"])
api_router.include_router(suggestions.router, tags=["suggestions"])
api_router.include_router(blogs.router, tags=["blogs"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(llm.router, tags=["llm"])

# ---------- Public endpoints (no auth, but rate limited) ----------
@api_router.get("/stats")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
def get_stats(request: Request):
    api_logger.info(f"Stats endpoint called from {request.client.host}")
    conn = get_db()
    if not conn:
        api_logger.error("Database not initialized for stats endpoint")
        return {"error": "Database not initialized"}
    
    try:
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
        
        api_logger.debug(f"Stats: {total_articles} articles, {len(blogs)} blogs")
        
        return {
            "total_articles": total_articles,
            "total_blogs": len(blogs),
            "pending_suggestions": pending,
            "accepted_suggestions": accepted,
            "articles_by_source": by_source,
            "avg_heuristic_score": avg_scores[1] if avg_scores[1] else 0,
            "avg_combined_score": avg_scores[0] if avg_scores[0] else 0
        }
    except Exception as e:
        api_logger.error(f"Error generating stats: {e}", exc_info=True)
        conn.close()
        return {"error": str(e)}

@api_router.get("/health")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_PERIOD} second")
def health_check(request: Request):
    api_logger.debug(f"Health check from {request.client.host}")
    db_exists = os.path.exists("data/blog_scout.db")
    return {"status": "healthy", "database": db_exists}

app.include_router(api_router)

# ---------- Static Frontend ----------
frontend_dir = "apps/frontend"
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    api_logger.info(f"Mounted static frontend from {frontend_dir}")
else:
    api_logger.warning(f"Frontend directory not found: {frontend_dir}")

if __name__ == "__main__":
    import uvicorn
    api_logger.info("Starting uvicorn server on 0.0.0.0:8765")
    uvicorn.run(app, host="0.0.0.0", port=8765, reload=True)