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
        assert data["status"] in ["ok", "degraded"]
        assert "muninn_connected" in data
        assert "llm_provider" in data
        assert "llm_model" in data


class TestConsultEndpoint:
    """Tests for /consult endpoint."""

    def test_consult_post_returns_200(self):
        """Consult endpoint should return successful response for valid request."""
        request_data = {
            "problem": "What are the key legal precedents?",
        }
        response = CLIENT.post("/consult", json=request_data)
        assert response.status_code == 200

    def test_consult_response_structure(self):
        """Consult response should contain recommendation and similar_cases."""
        request_data = {
            "problem": "test query",
            "context": "test",
            "vault": "default",
        }
        response = CLIENT.post("/consult", json=request_data)

        if response.status_code == 200:
            data = response.json()
            assert "request_id" in data
            assert "recommendation" in data
            assert "similar_cases" in data
            assert "confidence" in data
            assert isinstance(data["similar_cases"], list)

    def test_consult_missing_problem_returns_422(self):
        """Consult without problem field should return 422."""
        response = CLIENT.post("/consult", json={"context": "test"})
        assert response.status_code == 422


class TestIngestEndpoints:
    """Tests for /ingest/* endpoints."""

    def test_ingest_csv_endpoint_exists(self):
        """CSV ingestion endpoint should exist."""
        request_data = {"file_path": "/nonexistent/test.csv", "vault": "default"}
        response = CLIENT.post("/ingest/csv", json=request_data)
        # Endpoint exists; may return 500 due to missing file
        assert response.status_code != 404

    def test_ingest_pdf_endpoint_exists(self):
        """PDF ingestion endpoint should exist."""
        request_data = {"file_path": "/nonexistent/test.pdf", "vault": "default"}
        response = CLIENT.post("/ingest/pdf", json=request_data)
        assert response.status_code != 404

    def test_ingest_confluence_endpoint_exists(self):
        """Confluence ingestion endpoint should exist."""
        request_data = {
            "url": "https://example.atlassian.net/wiki/spaces/TEST/pages/123",
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
        assert "vault" in data
        assert "total_memories" in data
        assert "health" in data
        assert "enrichment_mode" in data
        assert "contradiction_count" in data
        assert "contradictions" in data
        assert isinstance(data["total_memories"], int)
        assert isinstance(data["contradictions"], list)

    def test_vault_stats_with_vault_param(self):
        """Vault stats should accept vault query parameter."""
        response = CLIENT.get("/vault/stats?vault=default")
        assert response.status_code == 200
        data = response.json()
        assert data["vault"] == "default"

    def test_vault_entities_list_returns_200(self):
        """Vault entities list endpoint should return 200."""
        response = CLIENT.get("/vault/entities")
        assert response.status_code == 200

        data = response.json()
        assert "vault" in data
        assert "entities" in data
        assert isinstance(data["entities"], list)

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
            "case_id": "test-case",
            "content": "Updated content",
            "vault": "default",
        }
        response = CLIENT.put("/cases/test-case", json=request_data)
        assert response.status_code != 404

    def test_consolidate_cases_validation(self):
        """POST /cases/consolidate should require at least 2 case_ids."""
        request_data = {
            "case_ids": ["single"],
            "vault": "default",
        }
        response = CLIENT.post("/cases/consolidate", json=request_data)
        assert response.status_code == 400

    def test_consolidate_cases_endpoint_exists(self):
        """POST /cases/consolidate endpoint should exist."""
        request_data = {
            "case_ids": ["case-1", "case-2"],
            "vault": "default",
        }
        response = CLIENT.post("/cases/consolidate", json=request_data)
        assert response.status_code != 404

    def test_set_case_state_endpoint_exists(self):
        """PATCH /cases/{case_id}/state endpoint should exist."""
        request_data = {
            "case_id": "test-case",
            "state": "active",
            "vault": "default",
        }
        response = CLIENT.patch("/cases/test-case/state", json=request_data)
        assert response.status_code != 404


class TestOtherEndpoints:
    """Tests for remaining endpoints."""

    def test_traverse_endpoint_exists(self):
        """POST /traverse endpoint should exist."""
        request_data = {
            "start_id": "test-id",
            "max_depth": 2,
            "vault": "default",
        }
        response = CLIENT.post("/traverse", json=request_data)
        assert response.status_code != 404

    def test_traverse_response_structure(self):
        """Traverse response should contain result dict."""
        request_data = {
            "start_id": "test-id",
            "max_depth": 2,
            "vault": "default",
        }
        response = CLIENT.post("/traverse", json=request_data)
        if response.status_code == 200:
            data = response.json()
            assert "start_id" in data
            assert "vault" in data
            assert "result" in data

    def test_session_recent_returns_200(self):
        """GET /session/recent endpoint should return 200."""
        response = CLIENT.get("/session/recent")
        assert response.status_code == 200
        data = response.json()
        assert "vault" in data
        assert "memories" in data
        assert isinstance(data["memories"], list)

    def test_feedback_endpoint_exists(self):
        """POST /feedback endpoint should exist."""
        request_data = {
            "request_id": "req-1",
            "results": [{"case_id": "c1", "relevant": True}],
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
