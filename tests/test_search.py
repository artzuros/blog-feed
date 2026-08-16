"""Tests for the search endpoint and FTS5 utilities."""
import pytest
from api.routes.search import _sanitize_fts5_query


class TestSanitizeFTS5Query:
    def test_basic_query(self):
        assert _sanitize_fts5_query("kubernetes") == "kubernetes*"

    def test_multi_word(self):
        assert _sanitize_fts5_query("kubernetes deploy") == "kubernetes deploy*"

    def test_strips_special_chars(self):
        result = _sanitize_fts5_query('kube*netes "deploy" (test)')
        assert '"' not in result
        assert "(" not in result
        assert ")" not in result
        # Last word should have prefix wildcard
        assert result.endswith("*")

    def test_strips_plus_minus(self):
        result = _sanitize_fts5_query("+kubernetes -docker compose")
        assert "+" not in result
        assert "-" not in result
        assert result.endswith("*")

    def test_empty_string(self):
        assert _sanitize_fts5_query("") is None

    def test_only_special_chars(self):
        assert _sanitize_fts5_query('*"()+-') is None

    def test_prefix_on_last_word_only(self):
        result = _sanitize_fts5_query("kubernetes docker compose")
        parts = result.split()
        assert parts[-1].endswith("*")
        assert not parts[0].endswith("*")
        assert not parts[1].endswith("*")


class TestSearchEndpoint:
    """Test the /api/search endpoint via TestClient."""

    def test_search_returns_results(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/search?q=kubernetes&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["search_type"] == "fts5"
        assert data["count"] >= 1
        assert data["articles"][0]["title"] == "Test Article About Kubernetes"

    def test_search_returns_snippet(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/search?q=deployment&limit=10")
        data = resp.json()
        assert len(data["articles"]) > 0
        assert "snippet" in data["articles"][0]

    def test_search_min_score_filter(self, client, insert_sample_article):
        insert_sample_article({"combined_score": 0.2})
        resp = client.get("/api/search?q=kubernetes&min_score=0.5&limit=10")
        data = resp.json()
        assert data["count"] == 0

    def test_search_source_filter(self, client, insert_sample_article):
        insert_sample_article({"source": "rss"})
        resp = client.get("/api/search?q=kubernetes&source=rss&limit=10")
        data = resp.json()
        assert data["count"] >= 1

    def test_search_source_filter_excludes(self, client, insert_sample_article):
        insert_sample_article({"source": "rss"})
        resp = client.get("/api/search?q=kubernetes&source=reddit&limit=10")
        data = resp.json()
        assert data["count"] == 0

    def test_search_no_results(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/search?q=zzzznotfoundxxxx&limit=10")
        data = resp.json()
        assert data["count"] == 0

    def test_search_semantic_fallback(self, client, conn, insert_sample_article, monkeypatch):
        """A 0-result FTS5 search falls back to semantic search."""
        insert_sample_article()
        rowid = conn.execute("SELECT rowid FROM articles LIMIT 1").fetchone()[0]

        import core.embeddings
        monkeypatch.setattr(core.embeddings, "semantic_search",
                            lambda q, limit: ([rowid], [0.9]))

        resp = client.get("/api/search?q=netowrk&limit=10")
        data = resp.json()
        assert data["search_type"] == "semantic"
        assert data["fallback"] is True
        assert data["count"] >= 1
        assert data["articles"][0]["semantic_relevance"] == 0.9

    def test_search_semantic_fallback_respects_source(self, client, conn, insert_sample_article, monkeypatch):
        """Semantic fallback still applies the source filter."""
        insert_sample_article({"source": "rss"})
        rowid = conn.execute("SELECT rowid FROM articles LIMIT 1").fetchone()[0]

        import core.embeddings
        monkeypatch.setattr(core.embeddings, "semantic_search",
                            lambda q, limit: ([rowid], [0.9]))

        resp = client.get("/api/search?q=netowrk&source=reddit&limit=10")
        data = resp.json()
        assert data["count"] == 0

    def test_search_pagination_offset(self, client, insert_sample_article):
        insert_sample_article({"url": "https://example.com/a1", "title": "Kubernetes A"})
        insert_sample_article({"url": "https://example.com/a2", "title": "Kubernetes B"})
        resp = client.get("/api/search?q=kubernetes&limit=1&offset=1")
        data = resp.json()
        assert data["count"] == 1

    def test_search_type_field_present(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/search?q=kubernetes&limit=10")
        data = resp.json()
        assert "search_type" in data

    def test_search_requires_query(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 422

    def test_search_query_min_length(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/search?q=a")
        assert resp.status_code == 422


class TestArticlesEndpoint:
    """Test the /api/articles endpoint."""

    def test_list_articles(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/articles?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["articles"]) >= 1

    def test_list_articles_sorted_by_score(self, client, insert_sample_article):
        insert_sample_article({"url": "https://ex.com/low", "title": "Low Score", "combined_score": 0.2})
        insert_sample_article({"url": "https://ex.com/high", "title": "High Score", "combined_score": 0.9})
        resp = client.get("/api/articles?limit=10&sort=combined_score")
        data = resp.json()
        scores = [a["combined_score"] for a in data["articles"]]
        assert scores == sorted(scores, reverse=True)

    def test_list_articles_pagination(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/articles?limit=1&offset=0")
        data = resp.json()
        assert len(data["articles"]) == 1


class TestSemanticSearch:
    """Test the /api/semantic-search endpoint."""

    def test_semantic_search_empty_result(self, client):
        # With no embeddings, semantic search should return empty
        resp = client.get("/api/semantic-search?q=kubernetes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["search_type"] == "semantic"
