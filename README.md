# Blog Feed

**A high-signal engineering reading list — searched, scored, and surfaced.**

Blog Feed discovers, ranks, and serves the best technical content from company engineering blogs, incident reports, and deep dives — while filtering out AI slop, SEO spam, and superficial tutorials.

**Live:** [blog-hub.pranav-bansal.com](https://blog-hub.pranav-bansal.com)

---

## Core Philosophy

The modern internet is flooded with:

- AI-generated blogs
- SEO-optimized content farms
- shallow Medium tutorials
- repetitive LLM summaries

Blog Feed indexes blogs that actually matter:

- **depth** — implementation specifics, not overviews
- **originality** — unique insights, not rewrites
- **technical density** — code, benchmarks, architecture
- **operational wisdom** — incidents, migrations, war stories

---

## Features

### 🔍 Search

- Full‑text search across articles (title, keywords, blog name)
- Filter by source (curated RSS / Reddit‑suggested)
- Sort by combined quality score

### 📊 Ranking

- **Heuristic scoring** — technical density, weasel words, repetition (fast, offline)
- **LLM scoring** — optional Ollama integration for deeper semantic judgement
- **Combined score** — weighted average for final ranking

### 🗳️ Community Suggestions

- Users discover and submit engineering blog posts via Reddit integration
- Upvote/downvote system for community validation
- LLM‑assisted pre‑screening before admin review

### 🔧 Admin Interface

- Approve/reject suggestions (with API key authentication)
- Add curated RSS feeds manually
- Trigger manual article scans
- Monitor discovery cache and processed blogs

### 📡 Automated Discovery

- Daily scheduled scans of curated RSS feeds
- Weekly Reddit discovery for new high‑signal domains
- Auto‑extraction of article text with Playwright fallback

---

## Tech Stack

### Backend

| Component     | Technology                                      |
| ------------- | ----------------------------------------------- |
| API           | FastAPI                                         |
| Database      | SQLite (with full‑text search)                  |
| Crawler       | feedparser, trafilatura, Playwright, requests   |
| Ranking       | Custom heuristic + optional Ollama              |
| Authentication | API key (X‑API‑Key header)                     |
| Rate Limiting | slowapi                                         |
| Metrics       | Prometheus (/metrics endpoint)                  |

### Frontend

| Component  | Technology                       |
| ---------- | -------------------------------- |
| Framework  | React (via lovable.dev)          |
| Styling    | Tailwind CSS                     |
| Deployment | Cloudflare Pages                 |

### Infrastructure

| Component     | Technology                        |
| ------------- | --------------------------------- |
| Hosting       | Home server / localhost           |
| Reverse Proxy | Cloudflare Tunnel                 |
| Scheduling    | Cron (daily/weekly scans)         |
| Monitoring    | Logging (api.log) + Prometheus    |

---

## API Endpoints

### Public (read‑only, rate‑limited)

| Method | Endpoint                                | Description                       |
| ------ | --------------------------------------- | --------------------------------- |
| GET    | `/api/search?q={query}`                 | Search articles                   |
| GET    | `/api/articles/top`                     | Highest scored articles           |
| GET    | `/api/articles/recent`                  | Most recent articles              |
| GET    | `/api/articles/by-blog/{blog_name}`     | Articles from specific blog       |
| GET    | `/api/suggestions`                      | List pending suggestions          |
| POST   | `/api/suggestions/{id}/review`          | Upvote/downvote suggestion        |
| GET    | `/api/blogs`                            | List curated RSS feeds            |
| GET    | `/api/stats`                            | System statistics                 |
| GET    | `/api/health`                           | Health check                      |
| GET    | `/metrics`                              | Prometheus metrics                |

### Admin (API key required)

| Method | Endpoint                                | Description                       |
| ------ | --------------------------------------- | --------------------------------- |
| POST   | `/api/suggestions/accept`               | Approve suggestion (adds to feed) |
| POST   | `/api/blogs`                            | Add RSS feed manually             |
| DELETE | `/api/blogs/{blog_name}`                | Remove RSS feed                   |
| POST   | `/api/blogs/refresh`                    | Trigger manual article scan       |
| POST   | `/api/suggestions/import-accepted`      | Bulk import accepted suggestions  |

---

## Ranking Formula

Articles are scored using heuristic + optional LLM:

### Heuristic Score (0–1, 0 = best)

- **Technical density** — code indicators, numbers, technical terms
- **Weasel words** — marketing phrases ("revolutionize", "unlock the power")
- **Repetition** — sentence similarity penalties
- **Readability** — oversimplified text penalty

### LLM Score (0–1, 1 = best)

- Local Ollama model (Mistral / TinyLlama)
- Rates articles on technical depth and originality

### Combined Score

```python
combined_score = (heuristic_score * 0.6) + (llm_score * 0.4)  # if LLM available
# Falls back to heuristic_score if LLM not used
```

**Penalties applied for:**

- AI‑generated content detection
- Keyword stuffing
- Generic advice without specifics
- Missing code/architecture details

---

## Source Configuration

### Default RSS Feeds (curated)

- Netflix TechBlog
- Cloudflare Blog
- Stripe Engineering (via HTML fallback)
- Tailscale
- Fly.io
- Supabase
- Temporal
- PostHog
- Dagster
- Neon
- Warp
- Pulumi
- Convex (HTML extraction)

### Add Your Own

Admin endpoint: `POST /api/blogs` with `{name, url, rss}` (requires API key)

---

## Deployment

### Backend (Home Server)

```bash
# Clone repository
git clone https://github.com/artzuros/blog-feed
cd blog-feed

# Install dependencies
pip install -r requirements.txt

# Set environment variable for admin API key
export BLOG_SCOUT_API_KEY="your-secure-key"

# Run the API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Set up cron jobs
# Daily: python scripts/scheduled_scan.py
# Weekly: python scripts/reddit_discovery.py --auto
```

### Frontend (Cloudflare Pages)

1. Push frontend code (from lovable.dev) to GitHub
2. Connect to Cloudflare Pages
3. Set build command: `npm run build` (if applicable)
4. Set output directory: `dist` or `build`
5. Add environment variable: `VITE_API_BASE=https://your-api-domain.com/api`

### Cloudflare Tunnel

```bash
cloudflared tunnel create blog-feed
cloudflared tunnel route dns blog-feed api.yourdomain.com
cloudflared tunnel run blog-feed
```

---

## Development Roadmap

### ✅ Phase 1 (Complete)

- RSS ingestion pipeline
- SQLite storage with full‑text search
- Heuristic slop detection
- Basic search (keyword)
- Admin approval workflow (API key auth)
- Reddit discovery integration
- Community voting system

### 🚧 Phase 2 (Current)

- LLM scoring (Ollama integration)
- Suggestion acceptance workflow (Reddit → review → approve → fetch)
- Prometheus metrics and logging
- Scheduled automation (cron)

### 📅 Phase 3 (Planned)

- Full‑text search index optimization (FTS5)
- User accounts + saved articles
- Email digests for new articles
- Browser extension

### 🔮 Phase 4 (Future)

- Collaborative filtering recommendations
- Source reputation scoring over time
- Semantic search with embeddings (pgvector)
- Federated sharing of curated lists

---

## Project Structure

```
blog-feed/
├── api/              # FastAPI backend (routes, auth, models)
├── apps/frontend/    # Static frontend (lovable.dev output)
├── config/           # Settings, blog list (blogs.csv)
├── core/             # Fetcher, extractor, RSS reader, scorer
├── quality/          # Slop detection heuristics
├── scripts/          # Scheduled scans, Reddit discovery, imports
├── storage/          # Database, cache management
└── data/             # SQLite DB, JSON caches, logs
```

---

## Contributing

We welcome contributions! Especially:

- New RSS feed sources (add to `config/blogs.csv`)
- Ranking algorithm improvements (heuristics or prompts)
- Bug fixes and performance tweaks
- Frontend UI/UX enhancements

**How to contribute:**

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

**Report issues or suggest features:**  
GitHub Issues: [artzuros/blog-feed/issues](https://github.com/artzuros/blog-feed/issues)

---

## License

MIT © Pranav Bansal

---

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/)
- [TanStack Start](https://tanstack.com/start) (frontend)
- [Tailwind CSS](https://tailwindcss.com/)
- [Ollama](https://ollama.ai/) (optional LLM scoring)
- [Playwright](https://playwright.dev/) (JavaScript fallback)
- [lovable.dev](https://lovable.dev) (frontend generation)

---

## Related Projects

- [Signal Engine](https://github.com/artzuros/signal-engine) — Original concept (this project's predecessor)
- [Marginalia Search](https://search.marginalia.nu/) — Inspiration for ranking over engagement
- [Kagi Small Web](https://blog.kagi.com/small-web) — Curated small internet

---

## Environment Variables

| Variable                | Default                     | Description                    |
| ----------------------- | --------------------------- | ------------------------------ |
| `BLOG_SCOUT_API_KEY`    | `change-me-in-production`   | Admin API key                  |
| `RATE_LIMIT_REQUESTS`   | `20`                        | Requests per time period       |
| `RATE_LIMIT_PERIOD`     | `60`                        | Time period in seconds         |
| `LOG_LEVEL`             | `INFO`                      | Logging level                  |
| `LOG_FILE`              | `logs/api.log`              | Log file path                  |
