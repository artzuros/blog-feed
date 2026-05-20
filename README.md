# Blog Feed

**A high-signal engineering reading list — searched, scored, and surfaced.**

Blog Feed discovers, ranks, and serves the best technical content from company engineering blogs, incident reports, and deep dives — while filtering out AI slop, SEO spam, and superficial tutorials.

**Live:** [blog-feed.pranav-bansal.com](https://blog-feed.pranav-bansal.com)

---

## Table of Contents

- [Core Philosophy](#core-philosophy)
- [Tech Stack](#tech-stack)
- [Ranking Formula](#ranking-formula)
- [Source Configuration](#source-configuration)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

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

## Tech Stack

### Backend

| Component     | Technology                                      |
| ------------- | ----------------------------------------------- |
| API           | FastAPI                                         |
| Database      | SQLite + Chroma DB (semantic search)            |
| Crawler       | feedparser, trafilatura, Playwright, requests   |
| Ranking       | Custom heuristic + optional Ollama              |
| Keyword Extraction | RAKE (Rapid Automatic Keyword Extraction)  |
| Authentication | API key (X‑API‑Key header)                     |
| Rate Limiting | slowapi                                         |
| Metrics       | Prometheus (/metrics endpoint)                  |

### Frontend

| Component  | Technology                       |
| ---------- | -------------------------------- |
| Framework  | React + TanStack Router          |
| Styling    | Tailwind CSS                     |
| Deployment | Cloudflare Pages                 |

### Infrastructure

| Component     | Technology                        |
| ------------- | --------------------------------- |
| Hosting       | Ubuntu home server                |
| Reverse Proxy | Cloudflare Tunnel                 |
| Monitoring    | Logging + systemd service         |
| Vector DB     | Chroma (persistent embeddings)    |

---

## Ranking Formula

Articles are scored using heuristic + optional LLM:

### Heuristic Score (0–1, lower = better)

- **Technical density** — code indicators, numbers, technical terms
- **Weasel words** — marketing phrases ("revolutionize", "unlock the power")
- **Repetition** — sentence similarity penalties
- **Readability** — oversimplified text penalty

### LLM Score (0–1, higher = better)

- Local Ollama model (granite3.3:2b / Mistral)
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

### Semantic Search

Articles are embedded using `all-MiniLM-L6-v2` (384-dim) and stored in Chroma DB. Search queries find conceptually similar articles even without keyword matches.

---

## Source Configuration

Blogs are configured in `config/blogs.csv`:

```csv
name,url,rss
Netflix,https://netflixtechblog.com,https://netflixtechblog.com/feed
Cloudflare,https://blog.cloudflare.com,https://blog.cloudflare.com/rss
Tailscale,https://tailscale.com/blog,https://tailscale.com/blog/feed.xml
```

**Currently indexed (50+ blogs):**
- Netflix TechBlog, Cloudflare, Stripe, Uber, Spotify
- Tailscale, Fly.io, Supabase, Temporal, PostHog
- Dagster, Neon, Warp, Pulumi, Convex
- AWS, Google Cloud, GitHub, GitLab, HashiCorp
- And more being added regularly

---

## Deployment

### Backend (Ubuntu Server)

```bash
# Clone repository
git clone https://github.com/artzuros/blog-feed
cd blog-feed

# Create conda environment
conda create -n blog python=3.11
conda activate blog

# Install dependencies
pip install -r requirements.txt

# Set environment variable for admin API key
export BLOG_SCOUT_API_KEY="your-secure-key"

# Run the API
uvicorn api.main:app --host 0.0.0.0 --port 8765

# Run as systemd service (recommended)
sudo systemctl start blog-feed-api
```

### Frontend (Cloudflare Pages)

1. Fork [github.com/artzuros/blog-feed-hub](https://github.com/artzuros/blog-feed-hub)
2. Connect to Cloudflare Pages
3. Set build command: `npm run build`
4. Set output directory: `dist`
5. Add environment variable: `VITE_API_BASE=https://your-api-domain.com/api`

### Cloudflare Tunnel

```bash
cloudflared tunnel create blog-feed
cloudflared tunnel route dns blog-feed api.yourdomain.com
cloudflared tunnel run blog-feed
```

---

## API Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/health` | GET | Health check | None |
| `/api/stats` | GET | Database statistics | None |
| `/api/search` | GET | Keyword search | None |
| `/api/semantic-search` | GET | Semantic search | None |
| `/api/suggestions` | GET | Reddit suggestions | None |
| `/api/suggestions/{url}/vote` | POST | Vote on suggestion | None |
| `/api/admin/verify` | GET | Admin verification | API Key |
| `/api/blogs` | GET/POST/DELETE | Manage blogs | API Key |
| `/api/blogs/{name}/refresh` | POST | Rescan a blog | API Key |
| `/api/reddit/discover` | POST | Run Reddit discovery | API Key |
| `/api/reddit/suggestions` | GET | Pending suggestions | API Key |

Full API documentation available at `/docs` when running locally.

---

## Contributing

We welcome contributions! Especially:

- New RSS feed sources (add to `config/blogs.csv`)
- Ranking algorithm improvements (heuristics or prompts)
- Keyword extraction enhancements
- Bug fixes and performance tweaks
- Frontend UI/UX improvements

**Please read our [Contributing Guide](CONTRIBUTING.md) before submitting pull requests.**

**How to contribute:**

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

**Report issues or suggest features:**  
[GitHub Issues](https://github.com/artzuros/blog-feed/issues)


---

## License

MIT © Pranav Bansal

---

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/)
- [TanStack Router](https://tanstack.com/router)
- [Tailwind CSS](https://tailwindcss.com/)
- [Ollama](https://ollama.ai/)
- [Playwright](https://playwright.dev/)
- [Chroma DB](https://www.trychroma.com/)
- [sentence-transformers](https://www.sbert.net/)

---

**Why another search engine?** Because good engineering content shouldn't be buried under SEO spam and AI-generated fluff. Blog Feed is my attempt to fix that — one blog at a time.
