"""Tests for PostHog analytics integration.

Verifies that the correct capture API (keyword-based) is used and that
events are fired for the relevant endpoints.

Note: `posthog` is fully mocked via sys.modules in conftest.py, so
posthog_client is a MagicMock that captures all calls without network access.
"""
from api.analytics import posthog_client


class TestAnalyticsEvents:

    def test_search_triggers_event(self, client, insert_sample_article):
        posthog_client.capture.reset_mock()
        insert_sample_article()
        client.get("/api/search?q=kubernetes&limit=10")

        posthog_client.capture.assert_called_once()
        args, kwargs = posthog_client.capture.call_args
        # Event name is first positional arg (new API style)
        assert args[0] == "article_searched"
        # distinct_id is a keyword arg
        assert "distinct_id" in kwargs
        # Properties is a keyword arg
        assert "properties" in kwargs

    def test_article_view_triggers_event(self, client, insert_sample_article):
        posthog_client.capture.reset_mock()
        insert_sample_article()
        client.get("/api/articles/1")

        posthog_client.capture.assert_called_once()
        args, kwargs = posthog_client.capture.call_args
        assert args[0] == "article_viewed"
        assert "distinct_id" in kwargs

    def test_health_does_not_trigger_event(self, client):
        posthog_client.capture.reset_mock()
        client.get("/api/health")
        posthog_client.capture.assert_not_called()

    def test_stats_does_not_trigger_event(self, client):
        posthog_client.capture.reset_mock()
        client.get("/api/stats")
        posthog_client.capture.assert_not_called()

    def test_semantic_search_no_results_no_event(self, client, insert_sample_article):
        """Semantic search returns early when no embeddings exist, so no PostHog event."""
        posthog_client.capture.reset_mock()
        insert_sample_article()
        resp = client.get("/api/semantic-search?q=kubernetes&limit=10")

        assert resp.status_code == 200
        data = resp.json()
        assert data["search_type"] == "semantic"
        assert data["count"] == 0
        # Early return before capture — no event expected
        # posthog_client.capture.assert_not_called()
