"""Locust load testing for Blog Feed API.

Simulates realistic traffic with respect for the server's rate limits
(20 req / 60s per IP).  Fetches live blog names from the API on startup
so all endpoints get valid input, and classifies 429 (rate-limit) hits
as successes rather than failures so the report shows real errors only.

Usage:
    pip install locust

    # Web UI (manual control — CSV & HTML saved automatically)
    locust --host=https://blog-feed-aws.pranav-bansal.com \
      --csv=reports/locust-web --html=reports/locust-web.html

    # Quick smoke test: 10 users, spawn 2/s, run 90s
    locust --host=https://blog-feed-aws.pranav-bansal.com \
      --headless -u 10 -r 2 --run-time 90s \
      --html=reports/locust-smoke.html

    # Staged ramp-up: 5→15 users over 4 min (find breaking point)
    locust --host=https://blog-feed-aws.pranav-bansal.com \
      --headless -u 15 -r 1 --run-time 5m \
      --csv=reports/locust-full --html=reports/locust-full.html

    # Heavy burst: 30 users, fast spawn, short duration
    locust --host=https://blog-feed-aws.pranav-bansal.com \
      --headless -u 30 -r 5 --run-time 60s \
      --csv=reports/locust-burst --html=reports/locust-burst.html
"""
from locust import HttpUser, task, between, tag, events
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = "a47c17c565c5582eb8116c6cf4c97965a66312c79fbc44870efa0ef1d3afc9ee"

# Rate-limit-aware pacing: 20 req / 60s per IP ≈ 1 req / 3s minimum.
# We use 3.5-5.5s so a few users stay under the limit without being
# unrealistically slow.
DEFAULT_WAIT = between(3.5, 5.5)

SEARCH_QUERIES = [
    "kubernetes", "docker", "aws", "python", "react",
    "machine learning", "database", "api design", "microservices",
    "devops", "typescript", "rust", "go", "postgresql", "redis",
    "sre", "observability", "distributed systems", "serverless",
    "ci/cd", "testing", "security", "performance",
]

# Populated from the live API on startup so all admin endpoints
# resolve against actual blog names.
BLOG_NAMES: list[str] = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Fetch live blog names from the API when the test starts."""
    import json
    import urllib.request

    url = f"{environment.host}/api/blogs"
    req = urllib.request.Request(url)
    req.add_header("X-API-Key", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            blogs = data if isinstance(data, list) else data.get("blogs", [])
            names = [b.get("name", "") for b in blogs if b.get("name")]
            BLOG_NAMES.extend(names)
            logger.info("Fetched %d blog names from API", len(BLOG_NAMES))
    except Exception as exc:
        logger.warning("Could not fetch blog names, using defaults: %s", exc)
        BLOG_NAMES.extend([
            "Tailscale", "Fly.io", "Supabase", "PostHog", "Temporal",
            "Dagster", "Prefect", "Neon", "Convex", "Warp",
        ])


class BlogFeedUser(HttpUser):
    wait_time = DEFAULT_WAIT

    def _get(self, path, name=None, auth=False):
        """GET with optional auth; treat 429 (rate-limited) as success."""
        headers = {"X-API-Key": API_KEY} if auth else {}
        with self.client.get(
            path,
            headers=headers,
            name=name or path,
            catch_response=True,
        ) as resp:
            if resp.status_code == 429:
                resp.success()  # rate-limited != real failure
            elif resp.status_code >= 500:
                resp.failure(f"Server error: {resp.status_code}")
            # 2xx, 3xx, 4xx (except 429) → default (success)
        return resp

    # --- tasks ordered by frequency ---

    @task(3)
    @tag("health")
    def health_check(self):
        """GET /api/health — no auth, lightweight."""
        self._get("/api/health", name="/api/health")

    @task(4)
    @tag("search")
    def search(self):
        """GET /api/search — FTS5 full-text search."""
        q = random.choice(SEARCH_QUERIES)
        self._get(f"/api/search?q={q}&limit=10", name="/api/search?q=...")

    @task(2)
    @tag("search")
    def search_with_filter(self):
        """GET /api/search with source filter."""
        q = random.choice(SEARCH_QUERIES)
        source = random.choice(["rss", "reddit"])
        self._get(
            f"/api/search?q={q}&source={source}&limit=5",
            name="/api/search?q=...&source=...",
        )

    @task(2)
    @tag("blogs")
    def list_blogs(self):
        """GET /api/blogs — blog list with article counts (auth)."""
        self._get("/api/blogs", auth=True, name="/api/blogs")

    @task(1)
    @tag("blogs")
    def blog_articles(self):
        """GET /api/admin/blogs/{name}/articles (auth)."""
        if not BLOG_NAMES:
            return
        blog = random.choice(BLOG_NAMES)
        self._get(
            f"/api/blogs/{blog}/articles?limit=10",
            auth=True,
            name="/api/blogs/{name}/articles",
        )

    @task(1)
    @tag("stats")
    def stats(self):
        """GET /api/stats — aggregate counts."""
        self._get("/api/stats", name="/api/stats")

    @task(1)
    @tag("article")
    def article_detail(self):
        """GET /api/articles/{id} — single article."""
        article_id = random.randint(1, 900)
        self._get(
            f"/api/articles/{article_id}",
            name="/api/articles/{id}",
        )

    @task(1)
    @tag("semantic")
    def semantic_search(self):
        """GET /api/semantic-search — embedding-based (hits ML model)."""
        q = random.choice(SEARCH_QUERIES)
        self._get(
            f"/api/semantic-search?q={q}&limit=5",
            name="/api/semantic-search?q=...",
        )

    @task(1)
    @tag("suggestions")
    def suggestions(self):
        """GET /api/reddit/suggestions (auth)."""
        self._get(
            "/api/reddit/suggestions",
            auth=True,
            name="/api/reddit/suggestions",
        )
