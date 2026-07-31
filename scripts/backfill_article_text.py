#!/usr/bin/env python3
"""One-time backfill: fetch full article bodies for articles missing text_content.

Articles imported via RSS never had their full body fetched, so they have
text_content = NULL/empty. This script fetches the body for each one and
updates both the articles table and the FTS index.

Usage:
    conda run -n blog python scripts/backfill_article_text.py

Flags:
    --limit N    Only process the first N articles (dry-run-ish, default: all)
    --min-len N  Minimum body length to accept (default: 300)
"""
import argparse
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from config.settings import DB_FILE, REQUEST_DELAY
from core.fetcher import fetch_article_text
from api.logger import root_logger


def backfill_article_text(limit=None, min_len=300):
    """Fetch and store article bodies for all articles with empty text_content."""
    root_logger.info(f"Starting article text backfill (min_len={min_len})...")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT rowid, url, title, text_content
        FROM articles
        WHERE text_content IS NULL OR length(text_content) < ?
    """
    params = [min_len]
    if limit:
        query += " ORDER BY rowid ASC LIMIT ?"
        params.append(limit)

    articles = conn.execute(query, params).fetchall()
    root_logger.info(f"Found {len(articles)} articles to backfill")

    success_count = 0
    fail_count = 0
    for row in articles:
        rowid = row["rowid"]
        url = row["url"]
        title = row["title"] or "Untitled"

        root_logger.info(f"[{rowid}] Fetching: {title[:60]}...")
        text = fetch_article_text(url)

        if text and len(text) >= min_len:
            try:
                conn.execute(
                    "UPDATE articles SET text_content = ? WHERE rowid = ?",
                    (text, rowid)
                )
                conn.execute(
                    "UPDATE articles_fts SET text_content = ? WHERE rowid = ?",
                    (text, rowid)
                )
                conn.commit()
                success_count += 1
                root_logger.info(f"[{rowid}] Saved {len(text)} chars")
            except Exception as e:
                conn.execute("ROLLBACK")
                fail_count += 1
                root_logger.error(f"[{rowid}] DB error: {e}", exc_info=True)
        else:
            fail_count += 1
            root_logger.warning(f"[{rowid}] Could not extract >= {min_len} chars "
                                f"(got {len(text) if text else 0})")

        # Respect the same politeness delay as the scorer
        time.sleep(REQUEST_DELAY)

    conn.close()
    root_logger.info(
        f"Backfill complete: {success_count} saved, {fail_count} failed/insufficient"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill article full text")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process the first N articles")
    parser.add_argument("--min-len", type=int, default=300,
                        help="Minimum body length to accept (default: 300)")
    args = parser.parse_args()
    backfill_article_text(limit=args.limit, min_len=args.min_len)
