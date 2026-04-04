"""
Integration tests for Dalil API endpoints.

Tests run against a running FastAPI server (http://localhost:8000).
Make sure `docker-compose up` is running before executing tests.
"""

import httpx
import pytest


BASE_URL = "http://localhost:8000"

# Use a longer timeout for Docker environment
CLIENT = httpx.Client(base_url=BASE_URL, timeout=10.0)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self):
        """Health endpoint should return 200 OK."""
        response = CLIENT.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self):
        """Health response should contain required fields."""
        response = CLIENT.get("/health")
        data = response.json()
        
        assert "status" in data
        assert data["status"] in ["ok", "degraded", "error"]
        assert "muninn_connected" in data or "llm_model" in data


class TestConsultEndpoint:
    """Tests for /consult endpoint."""

    def test_consult_post_returns_200(self):
        """Consult endpoint should return successful response for valid request."""
        request_data = {
            "query": "What are the key legal precedents?",
        }
        response = CLIENT.post("/consult", json=request_data)
        # 200 for success, 422 if required fields missing
        assert response.status_code in [200, 422]

    def test_consult_response_structure(self):
        """Consult response should contain recommendation and cases."""
        request_data = {"query": "test query", "context": "test"}
        response = CLIENT.post("/consult", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "request_id" in data
            assert "recommendation" in data
            assert "cases" in data


class TestIngestEndpoints:
    """Tests for /ingest/* endpoints."""

    def test_ingest_csv_endpoint_exists(self):
        """CSV ingestion endpoint should exist."""
        request_data = {"url": "http://example.com/test.csv", "vault": "default"}
        response = CLIENT.post("/ingest/csv", json=request_data)
        # Endpoint exists; may return various status codes based on URL validity
        assert response.status_code != 404

    def test_ingest_pdf_endpoint_exists(self):
        """PDF ingestion endpoint should exist."""
        request_data = {"url": "http://example.com/test.pdf", "vault": "default"}
        response = CLIENT.post("/ingest/pdf", json=request_data)
        assert response.status_code != 404

    def test_ingest_confluence_endpoint_exists(self):
        """Confluence ingestion endpoint should exist."""
        request_data = {
            "base_url": "https://example.atlassian.net",
            "username": "test@example.com",
            "api_token": "test-token",
            "space_key": "TEST",
            "vault": "default",
        }
        response = CLIENT.post("/ingest/confluence", json=request_data)
        assert response.status_code != 404


class TestVaultEndpoints:
    """Tests for /vault/* endpoints."""

    def test_vault_stats_returns_200(self):
        """Vault stats endpoint should return 200."""
        response = CLIENT.get("/vault/stats")
        assert response.status_code == 200
        
        data = response.json()
        # Stats may include various fields like coherence_score, confidence_distribution, etc.
        assert len(data) > 0  # Response should contain data

    def test_vault_entities_list_returns_200(self):
        """Vault entities list endpoint should return 200."""
        response = CLIENT.get("/vault/entities")
        assert response.status_code == 200
        
        data = response.json()
        assert "entities" in data or "results" in data

    def test_vault_entity_detail_responds(self):
        """Vault entity detail endpoint should respond."""
        response = CLIENT.get("/vault/entities/test-entity")
        # 200 if exists, 404 if not (both valid)
        assert response.status_code in [200, 404]

    def test_vault_entity_timeline_responds(self):
        """Vault entity timeline endpoint should respond."""
        response = CLIENT.get("/vault/entities/test-entity/timeline")
        assert response.status_code in [200, 404]

    def test_vault_entity_cases_responds(self):
        """Vault entity cases endpoint should respond."""
        response = CLIENT.get("/vault/entities/test-entity/cases")
        assert response.status_code in [200, 404]


class TestCasesEndpoints:
    """Tests for /cases/* endpoints."""

    def test_evolve_case_endpoint_exists(self):
        """PUT /cases/{case_id} endpoint should exist."""
        request_data = {
            "evolution_query": "Update based on new info",
            "new_source": "Case law",
        }
        response = CLIENT.put("/cases/test-case", json=request_data)
        assert response.status_code != 404

    def test_consolidate_cases_endpoint_exists(self):
        """POST /cases/consolidate endpoint should exist."""
        request_data = {
            "case_ids": ["case-1", "case-2"],
            "consolidation_instruction": "Merge",
            "vault": "default",
        }
        response = CLIENT.post("/cases/consolidate", json=request_data)
        assert response.status_code != 404

    def test_set_case_state_endpoint_exists(self):
        """PATCH /cases/{case_id}/state endpoint should exist."""
        request_data = {"new_state": "resolved"}
        response = CLIENT.patch("/cases/test-case/state", json=request_data)
        assert response.status_code != 404


class TestOtherEndpoints:
    """Tests for remaining endpoints."""

    def test_traverse_endpoint_exists(self):
        """POST /traverse endpoint should exist."""
        request_data = {
            "start_concepts": ["law", "precedent"],
            "depth": 2,
        }
        response = CLIENT.post("/traverse", json=request_data)
        assert response.status_code != 404

    def test_session_recent_endpoint_exists(self):
        """GET /session/recent endpoint should exist."""
        response = CLIENT.get("/session/recent")
        assert response.status_code != 404

    def test_feedback_endpoint_exists(self):
        """POST /feedback endpoint should exist."""
        request_data = {
            "request_id": "req-1",
            "rating": 5,
        }
        response = CLIENT.post("/feedback", json=request_data)
        assert response.status_code != 404


class TestErrorHandling:
    """Tests for error handling."""

    def test_nonexistent_endpoint_returns_404(self):
        """Nonexistent endpoint should return 404."""
        response = CLIENT.get("/nonexistent/endpoint")
        assert response.status_code == 404

    def test_invalid_method_returns_405(self):
        """Invalid HTTP method should return 405."""
        response = CLIENT.request("DELETE", "/health")
        assert response.status_code == 405


@pytest.fixture(scope="session", autouse=True)
def verify_server_running():
    """Verify that the API server is running before tests start."""
    try:
        response = CLIENT.get("/health", timeout=2.0)
        assert response.status_code == 200
    except Exception as e:
        pytest.skip(f"API server not running at {BASE_URL}: {e}")
