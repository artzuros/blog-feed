# Contributing to Blog Feed

First off, thank you for considering contributing to Blog Feed! 🎉

Blog Feed is an open-source search engine for high-signal engineering blog posts. We welcome contributions of all kinds:
- Adding new engineering blogs to the index
- Improving the heuristic slop detection
- Enhancing keyword extraction
- Fixing bugs
- Improving documentation

## Table of Contents

- [How Can I Contribute?](#how-can-i-contribute)
  - [Adding a Blog](#adding-a-blog)
  - [Improving Scoring](#improving-scoring)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Local Setup](#local-setup)
  - [Running the Stack](#running-the-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Style Guides](#style-guides)
  - [Python Style Guide](#python-style-guide)
  - [TypeScript Style Guide](#typescript-style-guide)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a simple principle: **be excellent to each other**. We expect all contributors to maintain a respectful and constructive environment.

## How Can I Contribute?

### Adding a Blog

The easiest way to contribute is to add an engineering blog you follow.

**How to add:**

1. Fork the repository
2. Edit `config/blogs.csv` with the following format:
   ```csv
   name,url,rss
   Blog Name,https://blog.example.com,https://blog.example.com/feed.xml
   ```
3. Submit a Pull Request

**Guidelines for blog inclusion:**
- Must be an engineering/technical blog (not marketing/news)
- Should have original content (not aggregated)
- RSS feed should contain full articles or substantial excerpts

### Improving Scoring

The quality scoring system has two components:

**1. Heuristic Slop Detection** (`quality/slop_detector.py`)
- Currently uses: technical density, weasel words, repetition, readability
- Looking for: better detection patterns for AI-generated content

**2. LLM Scoring** (`core/llm_scorer.py`)
- Currently prompts Ollama for 0-10 technical depth rating
- Looking for: better prompts, alternative models, caching strategies

**3. Keyword Extraction** (`core/keywords.py`)
- Uses RAKE (Rapid Automatic Keyword Extraction)
- Looking for: domain-specific technical term dictionaries

### Reporting Bugs

Use the GitHub issue tracker. Please include:
- Steps to reproduce
- Expected behavior vs actual behavior
- Logs if applicable (`logs/api.log`)
- Browser/OS if frontend-related

### Suggesting Features

Open an issue with the `enhancement` label. Describe:
- The problem you're solving
- Your proposed solution
- Alternatives you've considered

## Development Setup

### Prerequisites

```bash
# Python 3.11+
# Node.js 18+
# Ollama (for LLM scoring)

# Clone the repository
git clone https://github.com/yourusername/blog-feed.git
cd blog-feed
```

### Local Setup

**Backend:**

```bash
# Create conda environment (recommended)
conda create -n blog python=3.11
conda activate blog

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API key

# Initialize database
python -c "from storage.database import init_db; init_db()"
```

**Frontend:**

```bash
cd frontend
npm install
```

### Running the Stack

**Terminal 1 - Backend API:**
```bash
conda activate blog
uvicorn api.main:app --reload --port 8765
```

**Terminal 2 - Frontend:**
```bash
cd frontend
bun run dev
```

**Terminal 3 - Scheduled Scan (optional):**
```bash
conda activate blog
python scripts/scheduled_scan.py
```

The API will be available at `http://localhost:8765` with Swagger docs at `/docs`.

## Project Structure

```
blog-feed/
├── api/                    # FastAPI routes and middleware
│   ├── routes/            # API endpoints (search, suggestions, admin, blogs)
│   └── models/            # Pydantic schemas
├── config/                # Configuration and blog list
├── core/                  # Core functionality
│   ├── embeddings.py      # Semantic search with Chroma DB
│   ├── fetcher.py         # Article fetching (requests/curl/playwright)
│   ├── keywords.py        # RAKE keyword extraction
│   ├── llm_scorer.py      # Ollama integration
│   ├── rss_reader.py      # RSS feed parsing
│   └── scorer.py          # Heuristic + LLM scoring pipeline
├── quality/               # Content quality detection
│   ├── content_classifier.py  # Marketing vs technical detection
│   └── slop_detector.py   # AI slop detection
├── scripts/               # Utility scripts
│   ├── scheduled_scan.py  # Daily RSS ingestion
│   ├── reddit_discovery_api.py  # Reddit blog discovery
│   └── backfill_embeddings.py   # Generate embeddings for existing articles
├── storage/               # Database and cache
│   ├── database.py        # SQLite operations
│   └── cache.py           # Blog discovery cache
└── frontend/              # React + TanStack Router app
```

## How It Works

1. **Ingestion**: `scheduled_scan.py` runs daily, fetching articles from blogs in `config/blogs.csv`
2. **Scoring**: Each article gets:
   - Heuristic score (slop detection)
   - Keyword extraction (RAKE)
   - LLM score (if text > 500 chars)
3. **Storage**: Articles saved to SQLite, embeddings to Chroma DB
4. **Search**: 
   - Keyword: SQLite `LIKE` queries on title/keywords
   - Semantic: Vector similarity via Chroma DB
5. **Admin**: Protected endpoints for managing blogs and reviewing Reddit suggestions

## Style Guides

### Python Style Guide

- Follow PEP 8
- Use type hints for function signatures
- Use `api.logger` for logging (not `print`)
- Maximum line length: 100 characters

```python
def process_article(url: str, title: str, blog_name: str) -> None:
    """Process a single article."""
    logger.info(f"Processing: {title[:50]}...")
    # ... implementation
```

### TypeScript Style Guide

- Use functional components with hooks
- Define types/interfaces for all props and state
- Use the `API_BASE` constant from `@/lib/api`

```typescript
type Article = {
  url: string;
  title: string;
  blog_name: string;
  combined_score: number;
};
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** with clear commit messages
4. **Test your changes** locally
5. **Update documentation** if needed
6. **Push to your fork** and open a Pull Request

**PR Checklist:**
- [ ] Code follows style guides
- [ ] No new `print()` statements (use logger)
- [ ] Existing tests pass (if any)
- [ ] Documentation updated
- [ ] PR title clearly describes the change

## Getting Help

- Open an issue for bugs or feature requests
- Email: admin@pranav-bansal.com
- Check existing issues before opening a new one
