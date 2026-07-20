"""Tests for API endpoints (health, stats, article detail)."""
import base64


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert isinstance(data["database"], bool)


class TestStats:
    def test_stats_structure(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_articles" in data
        assert "total_blogs" in data
        assert "avg_combined_score" in data
        assert data["total_articles"] >= 1

    def test_stats_empty(self, client):
        resp = client.get("/api/stats")
        data = resp.json()
        assert data["total_articles"] == 0


class TestArticleDetail:
    def test_get_by_rowid(self, client, insert_sample_article):
        insert_sample_article()
        resp = client.get("/api/articles/1")
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert data["title"] == "Test Article About Kubernetes"

    def test_get_by_base64_url(self, client, insert_sample_article):
        insert_sample_article()
        encoded = base64.urlsafe_b64encode(b"https://example.com/test-article").decode()
        resp = client.get(f"/api/articles/{encoded}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Article About Kubernetes"

    def test_get_404(self, client):
        resp = client.get("/api/articles/99999")
        assert resp.status_code == 404

    def test_get_with_invalid_id(self, client):
        resp = client.get("/api/articles/invalid")
        # Should 404, not crash
        assert resp.status_code == 404
