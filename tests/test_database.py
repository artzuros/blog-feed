"""Tests for the database layer (storage/database.py)."""
import os
import sqlite3
import pytest
from storage.database import save_article, article_exists, get_articles_by_blog, init_db, get_db_conn


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


class TestArticleEvaluations:
    """Tests for the article_evaluations table (CrewAI evaluations)."""

    def test_table_created(self, test_db_path):
        init_db()
        conn = sqlite3.connect(test_db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "article_evaluations" in tables

    def test_get_db_conn_returns_connection(self, test_db_path):
        conn = get_db_conn()
        assert conn is not None
        # Should create the file if missing
        assert os.path.exists(test_db_path)
        conn.close()

    def test_get_db_conn_has_row_factory(self, test_db_path):
        conn = get_db_conn()
        assert conn.row_factory is sqlite3.Row
        conn.close()

    def test_indexes_created(self, test_db_path):
        init_db()
        conn = sqlite3.connect(test_db_path)
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_eval%'"
        ).fetchall()}
        conn.close()
        for idx in ("idx_eval_score", "idx_eval_depth", "idx_eval_type"):
            assert idx in indexes, f"Missing index: {idx}"

    def test_insert_and_read(self, conn, test_db_path):
        conn.execute("""
            INSERT INTO article_evaluations
            (article_id, content_type, technical_depth, marketing_bias,
             originality, practical_value, has_code_examples,
             has_performance_data, is_practitioner, overall_score,
             reasoning, tags_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, "tutorial", 8, 2, 6, 7, 1, 1, 1, 0.85,
              "Great technical depth with code examples", '["python","api"]'))
        conn.commit()

        row = conn.execute("SELECT * FROM article_evaluations WHERE article_id = 1").fetchone()
        assert row["content_type"] == "tutorial"
        assert row["technical_depth"] == 8
        assert row["overall_score"] == 0.85
        assert row["has_code_examples"] == 1

    def test_replace_existing(self, conn):
        conn.execute("""
            INSERT INTO article_evaluations
            (article_id, content_type, technical_depth, overall_score, reasoning)
            VALUES (2, 'announcement', 2, 0.3, 'Marketing fluff')
        """)
        conn.commit()
        conn.execute("""
            INSERT OR REPLACE INTO article_evaluations
            (article_id, content_type, technical_depth, overall_score, reasoning)
            VALUES (2, 'tutorial', 7, 0.8, 'Much better on second look')
        """)
        conn.commit()

        row = conn.execute(
            "SELECT content_type, overall_score FROM article_evaluations WHERE article_id = 2"
        ).fetchone()
        assert row["content_type"] == "tutorial"
        assert row["overall_score"] == 0.8
