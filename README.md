# Blog Feed

**A high-signal engineering reading list — searched, scored, and surfaced.**

Blog Feed discovers, ranks, and serves the best technical content from company engineering blogs, incident reports, and deep dives — while filtering out AI slop, SEO spam, and superficial tutorials.

**Live:** [blog-feed.pranav-bansal.com](https://blog-feed.pranav-bansal.com)

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
| Scheduling    | Cron (daily/weekly scans) # Not yet implemented        | 
| Monitoring    | Logging (api.log) + Prometheus    |

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
- Rates articles on technical depth and originality # Very simple prompt given right now.

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

### RSS Feeds (curated)

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
- to add a whole lot more

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

```

### Frontend (Cloudflare Pages)

1. Fork https://github.com/artzuros/blog-feed-hub 
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

---
