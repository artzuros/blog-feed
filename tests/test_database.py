"""Tests for the database layer (storage/database.py)."""
import sqlite3
import pytest
from storage.database import save_article, article_exists, get_articles_by_blog, init_db


class TestInitDB:
    """init_db() should create all tables and indexes."""

    def test_tables_created(self, test_db_path):
        init_db()
        conn = sqlite3.connect(test_db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','virtual')"
        ).fetchall()}
        conn.close()
        assert "articles" in tables
        assert "articles_fts" in tables
        assert "suggestion_reviews" in tables

    def test_indexes_created(self, test_db_path):
        init_db()
        conn = sqlite3.connect(test_db_path)
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_auto%'"
        ).fetchall()}
        conn.close()
        for idx in ("idx_source", "idx_added_by", "idx_combined_score", "idx_fetched_at"):
            assert idx in indexes, f"Missing index: {idx}"


class TestSaveArticle:
    """save_article() should persist articles and sync FTS5."""

    def test_save_and_retrieve(self, conn, test_db_path):
        save_article(
            url="https://a.com/1",
            title="Test Title",
            blog_name="Blog",
            score=0.5,
            llm_score=None,
            combined_score=0.5,
            reason="decent",
            keywords="test, blog",
            text_content="Hello world",
        )

        row = conn.execute("SELECT url, title, blog_name, score, combined_score, reason, keywords, text_content FROM articles").fetchone()
        assert row["url"] == "https://a.com/1"
        assert row["title"] == "Test Title"
        assert row["text_content"] == "Hello world"

    def test_save_without_text_content(self, conn):
        save_article(
            url="https://a.com/2",
            title="No Text",
            blog_name="Blog",
            score=0.5,
            llm_score=None,
            combined_score=0.5,
            reason="ok",
            keywords="",
        )
        row = conn.execute("SELECT text_content FROM articles WHERE url='https://a.com/2'").fetchone()
        assert row["text_content"] is None

    def test_replace_existing(self, conn):
        save_article(
            url="https://a.com/3",
            title="Original",
            blog_name="Blog",
            score=0.5,
            llm_score=None,
            combined_score=0.5,
            reason="first",
            keywords="a",
        )
        save_article(
            url="https://a.com/3",
            title="Replaced",
            blog_name="Blog",
            score=0.9,
            llm_score=0.8,
            combined_score=0.85,
            reason="updated",
            keywords="b",
        )
        rows = conn.execute("SELECT COUNT(*) as cnt FROM articles WHERE url='https://a.com/3'").fetchone()
        assert rows["cnt"] == 1
        row = conn.execute("SELECT title, score, reason FROM articles WHERE url='https://a.com/3'").fetchone()
        assert row["title"] == "Replaced"
        assert row["score"] == 0.9

    def test_fts5_indexed(self, conn, test_db_path):
        """FTS5 index should be populated after save."""
        save_article(
            url="https://a.com/fts",
            title="Kubernetes deployment guide",
            blog_name="Tech",
            score=0.3,
            llm_score=0.7,
            combined_score=0.55,
            reason="good",
            keywords="kubernetes, deployment",
            text_content="This article covers Kubernetes pod deployment strategies.",
        )
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM articles_fts WHERE articles_fts MATCH 'kubernetes*'"
        ).fetchone()
        assert row["cnt"] == 1

    def test_fts5_snippet(self, conn):
        """FTS5 should find the article by full-text match."""
        save_article(
            url="https://a.com/snippet",
            title="Docker compose guide",
            blog_name="Dev",
            score=0.4,
            llm_score=None,
            combined_score=0.4,
            reason="ok",
            keywords="docker, compose",
            text_content="Using Docker Compose for multi-container applications is essential.",
        )
        row = conn.execute(
            "SELECT snippet(articles_fts, -1, '<mark>', '</mark>', '…', 32) as snip FROM articles_fts WHERE articles_fts MATCH 'docker*'"
        ).fetchone()
        assert row is not None
        assert "<mark>" in row["snip"] or "Docker" in row["snip"]


class TestArticleExists:
    def test_exists(self):
        save_article(
            url="https://exists.test/1",
            title="Exists",
            blog_name="Test",
            score=0.5,
            llm_score=None,
            combined_score=0.5,
            reason="",
            keywords="",
        )
        assert article_exists("https://exists.test/1") is True

    def test_not_exists(self):
        assert article_exists("https://does-not-exist.test/99") is False


class TestGetArticlesByBlog:
    def test_returns_articles_for_blog(self):
        save_article(
            url="https://blog.test/a",
            title="A",
            blog_name="MyBlog",
            score=0.5,
            llm_score=None,
            combined_score=0.5,
            reason="",
            keywords="",
        )
        save_article(
            url="https://blog.test/b",
            title="B",
            blog_name="MyBlog",
            score=0.6,
            llm_score=None,
            combined_score=0.6,
            reason="",
            keywords="",
        )
        results = get_articles_by_blog("MyBlog")
        assert len(results) == 2

    def test_empty_for_unknown_blog(self):
        results = get_articles_by_blog("NonExistent")
        assert results == []

    def test_limit(self):
        for i in range(5):
            save_article(
                url=f"https://blog.test/{i}",
                title=f"Art{i}",
                blog_name="LimitBlog",
                score=0.5,
                llm_score=None,
                combined_score=0.5,
                reason="",
                keywords="",
            )
        results = get_articles_by_blog("LimitBlog", limit=2)
        assert len(results) == 2
