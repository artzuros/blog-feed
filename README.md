# Signal Engine

A high-signal engineering knowledge search engine.

Signal Engine discovers, extracts, ranks, embeds, and indexes
high-quality software engineering content while filtering out
AI slop, SEO spam, and superficial tutorials.

The goal is to build:
- a search engine for implementation knowledge
- an engineering intelligence system
- a curated infra/AI/devops knowledge base

---

# Core Idea

The modern internet is flooded with:
- AI-generated blogs
- SEO-optimized content farms
- shallow Medium tutorials
- repetitive LLM summaries

Meanwhile the best engineering knowledge exists in:
- company engineering blogs
- production incident reports
- migration writeups
- distributed systems deep dives
- niche infra startups

Signal Engine indexes and ranks:
- depth
- originality
- implementation quality
- technical density

instead of:
- engagement
- SEO
- virality

---

# Features

## Discovery Engine

Discovers blogs from:
- Reddit
- Hacker News
- RSS feeds
- GitHub awesome lists
- engineering blog directories

---

## Content Extraction

Extracts:
- full article text
- code snippets
- architecture discussions
- benchmarks
- metadata

using:
- trafilatura
- readability-lxml
- BeautifulSoup

---

## AI Quality Ranking

Scores content based on:
- implementation depth
- originality
- benchmark density
- operational insights
- architecture specificity

Penalizes:
- AI slop
- SEO spam
- generic tutorials
- keyword stuffing

---

## Semantic Search

Supports:
- vector search
- BM25 keyword search
- hybrid reranking

Example searches:
- kubernetes autoscaling failures
- production RAG pipelines
- kafka migration stories
- observability war stories

---

## AI Summaries

Uses local LLMs via Ollama to:
- summarize articles
- classify topics
- generate tags
- extract key insights

---

# Tech Stack

## Backend
- FastAPI
- PostgreSQL
- pgvector

## Crawling
- feedparser
- trafilatura
- Playwright

## AI
- Ollama
- bge-large embeddings
- rerankers

## Search
- pgvector
- BM25
- hybrid search

## Frontend
- Next.js
- Tailwind

## Infra
- Docker Compose
- Nginx

---

# Setup

# 1. Clone Repository

```bash
git clone https://github.com/yourname/signal-engine.git
cd signal-engine
```

---

# 2. Create Environment File

Create `.env`

```env
POSTGRES_USER=signal
POSTGRES_PASSWORD=signalpassword
POSTGRES_DB=signaldb

OLLAMA_HOST=http://localhost:11434

OPENAI_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
```

---

# 3. Install Ollama

Install:
https://ollama.com

Pull models:

```bash
ollama pull mistral
ollama pull nomic-embed-text
```

Recommended later:
- llama3
- deepseek-coder
- bge-large

---

# 4. Start PostgreSQL + pgvector

```bash
docker compose up -d postgres
```

Initialize extension:

```sql
CREATE EXTENSION vector;
```

---

# 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

# 6. Run Initial Feed Seeding

```bash
python scripts/seed_feeds.py
```

This adds:
- Netflix
- Stripe
- Cloudflare
- Tailscale
- Fly.io
- Swiggy
- OpenAI
- Anthropic
- etc.

---

# 7. Run Crawler

```bash
python apps/crawler/pipelines/crawl_pipeline.py
```

Pipeline:
1. discover feeds
2. fetch articles
3. extract content
4. score quality
5. generate embeddings
6. store database

---

# 8. Start API

```bash
uvicorn apps.api.main:app --reload
```

API:
http://localhost:8000

---

# 9. Start Frontend

```bash
cd apps/frontend

npm install
npm run dev
```

Frontend:
http://localhost:3000

---

# Search Examples

```bash
GET /search?q=distributed+systems+failures
GET /search?q=rag+architecture
GET /search?q=kafka+migration
```

---

# Ranking Strategy

Score articles based on:

```python
score =
    depth_score * 0.35 +
    originality_score * 0.25 +
    technical_density * 0.20 +
    reputation_score * 0.10 +
    freshness_score * 0.10
```

Penalties:
- AI slop
- excessive SEO
- low specificity
- generic phrasing

---

# Recommended First Milestones

## Phase 1
- RSS ingestion
- PostgreSQL storage
- basic frontend
- keyword search

## Phase 2
- embeddings
- semantic search
- AI summaries

## Phase 3
- Reddit/HN discovery
- ranking engine
- AI slop detection

## Phase 4
- user collections
- personalized feeds
- recommendation engine

---

# Long-Term Vision

Signal Engine becomes:
- a search engine for engineering depth
- a curated implementation knowledge graph
- a semantic archive of production engineering insights

Instead of:
"content"

Optimize for:
"technical insight density"

---

# Recommended Reading Sources

## Big Tech
- Netflix TechBlog
- Stripe Engineering
- Cloudflare
- Uber Engineering

## High Signal Smaller Companies
- Tailscale
- Fly.io
- Temporal
- Supabase
- PostHog
- Dagster
- Prefect

---

# License

MIT