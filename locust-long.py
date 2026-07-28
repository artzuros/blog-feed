"""Extended load test with staged user ramps over 1 hour.

Simulates a full day's traffic pattern in miniature:
  - Warm-up crawl  (0-5m)   — gradual ramp, find baseline
  - Normal traffic (5-15m)  — steady moderate load
  - Peak traffic   (15-25m) — busy hours, max concurrency
  - Sustained mid  (25-35m) — post-peak plateau
  - Stress burst   (35-45m) — push to find breaking point
  - Cool-down      (45-55m) — ease off
  - Tail           (55-60m) — wind down to zero

Usage:
    locust --host=https://blog-feed-aws.pranav-bansal.com \
      -f locust-long.py --headless --run-time 1h \
      --csv=reports/locust-long --html=reports/locust-long.html

    # Auto-stop when all users finish
    locust --host=https://blog-feed-aws.pranav-bansal.com \
      -f locust-long.py --headless --run-time 1h \
      --csv=reports/locust-long --html=reports/locust-long.html \
      --stop-timeout 30
"""
from locust import HttpUser, task, between, tag, events, LoadTestShape
import random
import logging
from urllib.request import Request, urlopen
from urllib.parse import quote
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = "a47c17c565c5582eb8116c6cf4c97965a66312c79fbc44870efa0ef1d3afc9ee"
SEARCH_QUERIES = [
    "kubernetes", "docker", "aws", "python", "react",
    "machine learning", "database", "api design", "microservices",
    "devops", "typescript", "rust", "go", "postgresql", "redis",
    "sre", "observability", "distributed systems", "serverless",
    "ci/cd", "testing", "security", "performance", "llm", "rag",
]
BLOG_NAMES: list[str] = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Fetch live blog names from the API on startup."""
    url = f"{environment.host}/api/blogs"
    req = Request(url)
    req.add_header("X-API-Key", API_KEY)
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            blogs = data if isinstance(data, list) else data.get("blogs", [])
            BLOG_NAMES.extend(b.get("name", "") for b in blogs if b.get("name"))
            logger.info("Fetched %d blog names from API", len(BLOG_NAMES))
    except Exception as exc:
        logger.warning("Could not fetch blog names: %s", exc)
        BLOG_NAMES.extend([
            "Tailscale", "Fly.io", "Supabase", "PostHog", "Temporal",
            "Dagster", "Prefect", "Neon", "Convex", "Warp",
        ])


class LongRunUser(HttpUser):
    """User behaviour during the 1-hour sustained test."""
    wait_time = between(3.5, 5.5)

    def _get(self, path, name=None, auth=False):
        headers = {"X-API-Key": API_KEY} if auth else {}
        with self.client.get(
            path, headers=headers, name=name or path, catch_response=True,
        ) as resp:
            if resp.status_code == 429:
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"Server error: {resp.status_code}")

    # -- core endpoints --
    @task(4)
    @tag("search")
    def search(self):
        q = random.choice(SEARCH_QUERIES)
        self._get(f"/api/search?q={q}&limit=10", name="/api/search?q=...")

    @task(3)
    @tag("health")
    def health_check(self):
        self._get("/api/health", name="/api/health")

    @task(2)
    @tag("search")
    def search_with_filter(self):
        q = random.choice(SEARCH_QUERIES)
        source = random.choice(["rss", "reddit"])
        self._get(
            f"/api/search?q={q}&source={source}&limit=5",
            name="/api/search?q=...&source=...",
        )

    @task(2)
    @tag("blogs")
    def list_blogs(self):
        self._get("/api/blogs", auth=True, name="/api/blogs")

    @task(2)
    @tag("blogs")
    def blog_articles(self):
        if not BLOG_NAMES:
            return
        blog = random.choice(BLOG_NAMES)
        self._get(
            f"/api/blogs/{quote(blog)}/articles?limit=10",
            auth=True,
            name="/api/blogs/{name}/articles",
        )

    @task(1)
    @tag("stats")
    def stats(self):
        self._get("/api/stats", name="/api/stats")

    @task(1)
    @tag("article")
    def article_detail(self):
        self._get(
            f"/api/articles/{random.randint(1, 900)}",
            name="/api/articles/{id}",
        )

    @task(1)
    @tag("semantic")
    def semantic_search(self):
        self._get(
            f"/api/semantic-search?q={random.choice(SEARCH_QUERIES)}&limit=5",
            name="/api/semantic-search?q=...",
        )

    @task(1)
    @tag("suggestions")
    def suggestions(self):
        self._get(
            "/api/reddit/suggestions", auth=True,
            name="/api/reddit/suggestions",
        )


class HourlyTrafficShape(LoadTestShape):
    """
    60-minute staged traffic pattern.

    Stage   Time     Users  Description
    ─────── ───────  ─────  ───────────────────────────
    1       0-5m      1→5   Warm-up crawl
    2       5-15m     5→8   Normal business traffic
    3      15-25m     8→12  Peak hours
    4      25-35m    12→8   Post-peak plateau
    5      35-45m     8→15  Stress burst (find limit)
    6      45-55m    15→5   Cool-down
    7      55-60m     5→0   Tail to zero
    """
    def tick(self):
        run_time = self.get_run_time()

        # Stage 1: Warm-up (0-5 min) — linear ramp 1→5
        if run_time < 300:
            users = int(1 + (run_time / 300) * 4)
            return max(1, users), 1

        # Stage 2: Normal load (5-15 min) — 5→8
        if run_time < 900:
            t = (run_time - 300) / 600
            users = int(5 + t * 3)
            return max(users, 5), 2

        # Stage 3: Peak (15-25 min) — 8→12
        if run_time < 1500:
            t = (run_time - 900) / 600
            users = int(8 + t * 4)
            spawn = 2
            return users, spawn

        # Stage 4: Post-peak plateau (25-35 min) — 12→8
        if run_time < 2100:
            t = (run_time - 1500) / 600
            users = int(12 - t * 4)
            return max(users, 8), 2

        # Stage 5: Stress burst (35-45 min) — 8→15
        if run_time < 2700:
            t = (run_time - 2100) / 600
            users = int(8 + t * 7)
            spawn = 3
            return users, spawn

        # Stage 6: Cool-down (45-55 min) — 15→5
        if run_time < 3300:
            t = (run_time - 2700) / 600
            users = int(15 - t * 10)
            return max(users, 5), 2

        # Stage 7: Tail (55-60 min) — 5→0
        if run_time < 3600:
            t = (run_time - 3300) / 300
            users = int(5 - t * 5)
            return max(users, 0), 1

        return None  # stop
