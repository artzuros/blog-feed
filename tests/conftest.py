"""Test fixtures and configuration."""
import os
import sys
import types
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock heavy external deps BEFORE any project modules are imported.
# These are imported at module level in api/main.py and core/embeddings.py.
# ---------------------------------------------------------------------------
_sent_t = MagicMock()
_sent_t.SentenceTransformer = MagicMock()
sys.modules["sentence_transformers"] = _sent_t

_chroma = types.ModuleType("chromadb")
_chroma.__path__ = ["chromadb"]
_chroma.PersistentClient = MagicMock()

_chroma_utils = types.ModuleType("chromadb.utils")
_chroma_utils.__path__ = ["chromadb/utils"]
_chroma.utils = _chroma_utils

_chroma_utils_ef = types.ModuleType("chromadb.utils.embedding_functions")
_chroma_utils_ef.__path__ = ["chromadb/utils/embedding_functions"]
_chroma_utils.embedding_functions = _chroma_utils_ef

_chroma_oef = types.ModuleType("chromadb.utils.embedding_functions.openai_embedding_function")
_chroma_utils_ef.openai_embedding_function = _chroma_oef

sys.modules["chromadb"] = _chroma
sys.modules["chromadb.utils"] = _chroma_utils
sys.modules["chromadb.utils.embedding_functions"] = _chroma_utils_ef
sys.modules["chromadb.utils.embedding_functions.openai_embedding_function"] = _chroma_oef

_posthog = MagicMock()
_posthog.Posthog = MagicMock()
_posthog.Posthog.return_value.shutdown = MagicMock()
sys.modules["posthog"] = _posthog

# Now safe to import project code.
import sqlite3
from fastapi.testclient import TestClient

from config import settings
import storage.database as db_mod
import api.dependencies as deps_mod

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db_path():
    """Create a temporary SQLite database file.

    Patches DB_FILE in every module that imports it so they all point to
    the same temp file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Patch settings so new imports get the right value (belt & suspenders)
    original_settings = settings.DB_FILE
    settings.DB_FILE = db_path

    # Patch module-level references that were imported at module load time
    original_db = db_mod.DB_FILE
    db_mod.DB_FILE = db_path
    original_deps = deps_mod.DB_FILE
    deps_mod.DB_FILE = db_path

    yield db_path

    # Restore everything
    settings.DB_FILE = original_settings
    db_mod.DB_FILE = original_db
    deps_mod.DB_FILE = original_deps
    os.unlink(db_path)


@pytest.fixture(autouse=True)
def _db(test_db_path):
    """Initialize the database schema and FTS5 index."""
    from storage.database import init_db
    init_db()
    yield


@pytest.fixture
def conn(test_db_path):
    """Provide a raw SQLite connection (row_factory = sqlite3.Row)."""
    c = sqlite3.connect(test_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.fixture
def client():
    """FastAPI TestClient connected to the real app."""
    from api.main import app
    return TestClient(app)



# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

SAMPLE_ARTICLE = {
    "url": "https://example.com/test-article",
    "title": "Test Article About Kubernetes",
    "blog_name": "Example Blog",
    "score": 0.3,
    "llm_score": 0.8,
    "combined_score": 0.55,
    "reason": "good technical content",
    "keywords": "kubernetes, deployment, docker",
    "text_content": (
        "This is a detailed technical article about Kubernetes deployment strategies. "
        "We cover cluster management, pod scheduling, and service meshes. "
        "The article includes code examples and architecture diagrams."
    ),
}


@pytest.fixture
def insert_sample_article():
    """Insert one sample article via save_article() into the test DB.

    Usage: inject as a fixture, then call insert_sample_article().
    Optionally pass overrides dict, e.g. insert_sample_article({"url": "...", "score": 0.9})
    """
    def _insert(overrides=None):
        from storage.database import save_article
        data = {**SAMPLE_ARTICLE, **(overrides or {})}
        save_article(
            url=data["url"],
            title=data["title"],
            blog_name=data["blog_name"],
            score=data["score"],
            llm_score=data["llm_score"],
            combined_score=data["combined_score"],
            reason=data["reason"],
            keywords=data["keywords"],
            text_content=data["text_content"],
        )
        return data
    return _insert
