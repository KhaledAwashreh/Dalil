"""
Pytest configuration and fixtures for integration tests.

Tests run against Docker Compose environment (MuninnDB + FastAPI).
"""

import os

import pytest
from fastapi.testclient import TestClient

from dalil.api.main import app
from dalil.config.settings import Settings, MuninnSettings, LLMSettings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Provide test settings with MuninnDB pointing to Docker Compose instance.
    
    Assumes: docker-compose up -d is already running
    """
    return Settings(
        muninn=MuninnSettings(
            base_url="http://127.0.0.1:8475",
            mcp_url="http://127.0.0.1:8750/mcp",
            token="",
        ),
        llm=LLMSettings(
            api_key="test-key",
            base_url="http://localhost:8000",
            model="test-model",
        ),
    )


@pytest.fixture
def client(test_settings) -> TestClient:
    """
    Provide a FastAPI TestClient for making requests to endpoints.
    
    Uses the Docker Compose MuninnDB instance.
    """
    # Override settings for test environment
    os.environ["MUNINN_URL"] = "http://127.0.0.1:8475"
    os.environ["MUNINN_TOKEN"] = ""
    
    return TestClient(app)


@pytest.fixture
def sample_consult_request():
    """Sample request data for /consult endpoint."""
    return {
        "query": "What are the key legal precedents in recent case law?",
        "context": "Corporate compliance",
        "prefer_recent": False,
    }


@pytest.fixture
def sample_feedback_request():
    """Sample request data for /feedback endpoint."""
    return {
        "request_id": "req-test-001",
        "case_id": "case-test-001",
        "rating": 5,
        "comment": "This was very helpful",
        "tags": ["accurate", "relevant"],
    }


@pytest.fixture
def sample_traverse_request():
    """Sample request data for /traverse endpoint."""
    return {
        "start_concepts": ["law", "precedent"],
        "depth": 2,
        "relation_filter": ["cites", "contradicts"],
        "max_results": 10,
    }

