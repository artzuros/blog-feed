"""Tests for the CrewAI multi-agent evaluator (quality/crew_evaluator.py)."""
import json
import sqlite3
import pytest

from quality.crew_evaluator import (
    EvaluationResult,
    parse_json_output,
    save_evaluation,
    get_evaluation,
    list_evaluations,
)


class TestEvaluationResult:
    """EvaluationResult data class."""

    def test_defaults(self):
        r = EvaluationResult({})
        assert r.content_type == "other"
        assert r.technical_depth == 0
        assert r.marketing_bias == 5
        assert r.overall_score == 0.0
        assert r.tags == []

    def test_from_dict(self):
        r = EvaluationResult({
            "content_type": "tutorial",
            "technical_depth": 8,
            "marketing_bias": 2,
            "originality": 6,
            "practical_value": 7,
            "has_code_examples": True,
            "has_performance_data": False,
            "is_practitioner": True,
            "overall_score": 0.85,
            "reasoning": "Solid tutorial with code",
            "tags": ["python", "api"],
        })
        assert r.content_type == "tutorial"
        assert r.technical_depth == 8
        assert r.marketing_bias == 2
        assert r.has_code_examples is True
        assert r.has_performance_data is False
        assert r.is_practitioner is True
        assert r.overall_score == 0.85

    def test_to_dict(self):
        r = EvaluationResult({"content_type": "case_study", "technical_depth": 5, "overall_score": 0.5})
        d = r.to_dict()
        assert d["content_type"] == "case_study"
        assert d["technical_depth"] == 5
        assert d["overall_score"] == 0.5

    def test_repr(self):
        r = EvaluationResult({"content_type": "tutorial", "technical_depth": 7, "overall_score": 0.72})
        text = repr(r)
        assert "tutorial" in text
        assert "7" in text
        assert "0.72" in text


class TestParseJsonOutput:
    """parse_json_output edge cases."""

    def test_plain_json(self):
        result = parse_json_output('{"content_type": "tutorial", "tags": ["a", "b"]}')
        assert result == {"content_type": "tutorial", "tags": ["a", "b"]}

    def test_json_in_text(self):
        result = parse_json_output(
            'Here is my analysis:\n{"depth": 7, "code": true}\nHope that helps.'
        )
        assert result == {"depth": 7, "code": True}

    def test_invalid_string(self):
        result = parse_json_output("not json at all")
        assert result is None

    def test_empty_string(self):
        result = parse_json_output("")
        assert result is None


class TestSaveEvaluation:
    """save_evaluation() with a real test DB."""

    def test_save_and_read(self, conn):
        result = EvaluationResult({
            "content_type": "research",
            "technical_depth": 9,
            "marketing_bias": 1,
            "originality": 8,
            "practical_value": 5,
            "has_code_examples": True,
            "has_performance_data": True,
            "is_practitioner": True,
            "overall_score": 0.78,
            "reasoning": "Deep research with benchmarks",
            "tags": ["kubernetes", "scalability", "benchmarks"],
        })
        ok = save_evaluation(42, result)
        assert ok is True

        # Verify with raw SQL
        c = sqlite3.connect(conn.execute("SELECT 'dummy'").connection.execute("PRAGMA database_list").fetchone()[2])
        # Actually just use the conn fixture
        row = conn.execute("SELECT * FROM article_evaluations WHERE article_id = 42").fetchone()
        assert row is not None
        assert row["content_type"] == "research"
        assert row["technical_depth"] == 9
        assert row["overall_score"] == 0.78
        assert row["has_code_examples"] == 1
        assert row["has_performance_data"] == 1

    def test_replace_existing(self, conn):
        r1 = EvaluationResult({"content_type": "opinion", "technical_depth": 3, "overall_score": 0.3})
        r2 = EvaluationResult({"content_type": "tutorial", "technical_depth": 8, "overall_score": 0.85})

        save_evaluation(99, r1)
        save_evaluation(99, r2)

        row = conn.execute(
            "SELECT content_type, overall_score FROM article_evaluations WHERE article_id = 99"
        ).fetchone()
        assert row["content_type"] == "tutorial"
        assert row["overall_score"] == 0.85


class TestGetEvaluation:
    """get_evaluation() with test DB."""

    def test_get_existing(self, conn):
        result = EvaluationResult({"content_type": "case_study", "overall_score": 0.65})
        save_evaluation(7, result)

        ev = get_evaluation(7)
        assert ev is not None
        assert ev["content_type"] == "case_study"
        assert ev["article_id"] == 7
        assert ev["overall_score"] == 0.65

    def test_get_missing(self):
        ev = get_evaluation(99999)
        assert ev is None


class TestListEvaluations:
    """list_evaluations() with test DB."""

    @pytest.fixture(autouse=True)
    def _seed(self, conn):
        for i, (ctype, score) in enumerate([
            ("tutorial", 0.9), ("announcement", 0.2),
            ("research", 0.8), ("opinion", 0.4),
        ], start=1):
            conn.execute("""
                INSERT INTO article_evaluations
                (article_id, content_type, technical_depth, overall_score, reasoning)
                VALUES (?, ?, ?, ?, ?)
            """, (i, ctype, int(score * 10), score, f"Test {ctype}"))
        conn.commit()

    def test_list_all(self):
        evs = list_evaluations(limit=10)
        assert len(evs) == 4

    def test_limit(self):
        evs = list_evaluations(limit=2)
        assert len(evs) == 2

    def test_offset(self):
        all_evs = list_evaluations(limit=10)
        offset_evs = list_evaluations(limit=10, offset=2)
        assert len(offset_evs) == 2
        assert offset_evs[0]["article_id"] == all_evs[2]["article_id"]

    def test_min_score_filter(self):
        evs = list_evaluations(limit=10, min_score=0.7)
        assert len(evs) == 2
        ids = {e["article_id"] for e in evs}
        assert 1 in ids  # tutorial 0.9
        assert 3 in ids  # research 0.8

    def test_content_type_filter(self):
        evs = list_evaluations(limit=10, content_type="tutorial")
        assert len(evs) == 1
        assert evs[0]["article_id"] == 1

    def test_content_type_no_match(self):
        evs = list_evaluations(limit=10, content_type="documentation")
        assert len(evs) == 0

    def test_sort_by_depth(self):
        evs = list_evaluations(limit=10, sort_by="technical_depth")
        # Highest technical_depth first
        assert evs[0]["technical_depth"] >= evs[1]["technical_depth"]

    def test_invalid_sort_falls_back(self):
        evs = list_evaluations(limit=10, sort_by="nonexistent")
        # Should not crash, should sort by default (overall_score)
        assert len(evs) == 4


class TestRunEvaluation:
    """run_evaluation() surface-level tests (no mocking needed)."""

    def test_returns_none_for_short_text(self):
        from quality.crew_evaluator import run_evaluation
        result = run_evaluation("Short", "Hi")
        assert result is None

    def test_returns_none_without_long_enough_text(self):
        from quality.crew_evaluator import run_evaluation
        result = run_evaluation("Test", "x" * 250)
        assert result is None

    def test_run_evaluation_is_callable(self):
        from quality.crew_evaluator import run_evaluation
        assert callable(run_evaluation)
