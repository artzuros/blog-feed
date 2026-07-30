"""Tests for API endpoints (health, stats, article detail)."""
import base64
from unittest.mock import MagicMock, patch

from config import settings


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


class TestEvaluateEndpoint:
    """POST /api/admin/evaluate/{article_id} endpoint."""

    API_KEY = settings.API_KEY

    def test_evaluate_missing_article(self, client):
        resp = client.post(
            "/api/admin/evaluate/99999",
            headers={"X-API-Key": self.API_KEY},
        )
        assert resp.status_code == 404

    def test_evaluate_no_auth(self, client):
        resp = client.post("/api/admin/evaluate/1")
        assert resp.status_code == 403

    def test_evaluate_success(self, client, insert_sample_article):
        insert_sample_article()

        with patch("api.routes.admin.run_evaluation") as mock_run:
            mock_result = MagicMock()
            mock_result.content_type = "tutorial"
            mock_result.technical_depth = 7
            mock_result.marketing_bias = 2
            mock_result.originality = 5
            mock_result.practical_value = 6
            mock_result.has_code_examples = True
            mock_result.has_performance_data = False
            mock_result.is_practitioner = True
            mock_result.overall_score = 0.72
            mock_result.reasoning = "Good tutorial with code"
            mock_result.tags = ["python", "api"]
            mock_result.to_dict.return_value = {
                "content_type": "tutorial",
                "technical_depth": 7,
                "marketing_bias": 2,
                "originality": 5,
                "practical_value": 6,
                "has_code_examples": True,
                "has_performance_data": False,
                "is_practitioner": True,
                "overall_score": 0.72,
                "reasoning": "Good tutorial with code",
                "tags": ["python", "api"],
            }
            mock_run.return_value = mock_result

            resp = client.post(
                "/api/admin/evaluate/1",
                headers={"X-API-Key": self.API_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["article_id"] == 1
        assert data["evaluation"]["overall_score"] == 0.72
        assert data["evaluation"]["content_type"] == "tutorial"
        assert data["evaluation"]["technical_depth"] == 7

    def test_evaluate_cached(self, client, insert_sample_article):
        insert_sample_article()

        with patch("api.routes.admin.run_evaluation") as mock_run:
            mock_result = MagicMock()
            mock_result.content_type = "tutorial"
            mock_result.overall_score = 0.72
            mock_result.to_dict.return_value = {
                "content_type": "tutorial", "overall_score": 0.72,
            }
            mock_result.technical_depth = 7
            mock_result.marketing_bias = 2
            mock_result.originality = 5
            mock_result.practical_value = 6
            mock_result.has_code_examples = True
            mock_result.has_performance_data = False
            mock_result.is_practitioner = True
            mock_result.reasoning = "Good"
            mock_result.tags = ["python"]
            mock_run.return_value = mock_result

            # First call
            client.post("/api/admin/evaluate/1", headers={"X-API-Key": self.API_KEY})
            # Second call — should return cached
            resp2 = client.post(
                "/api/admin/evaluate/1",
                headers={"X-API-Key": self.API_KEY},
            )

        assert resp2.status_code == 200
        assert resp2.json()["cached"] is True


class TestEvaluationsListEndpoint:
    """GET /api/admin/evaluations endpoint."""

    API_KEY = settings.API_KEY

    def test_list_no_auth(self, client):
        resp = client.get("/api/admin/evaluations")
        assert resp.status_code == 403

    def test_list_empty(self, client):
        resp = client.get(
            "/api/admin/evaluations",
            headers={"X-API-Key": self.API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["evaluations"] == []

    def test_list_with_data(self, client):
        # Insert an evaluation directly via DB
        from storage.database import get_db_conn
        conn = get_db_conn()
        conn.execute("""
            INSERT INTO article_evaluations
            (article_id, content_type, technical_depth, overall_score, reasoning)
            VALUES (1, 'tutorial', 8, 0.85, 'Great')
        """)
        conn.commit()
        conn.close()

        resp = client.get(
            "/api/admin/evaluations",
            headers={"X-API-Key": self.API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert any(e["article_id"] == 1 for e in data["evaluations"])
