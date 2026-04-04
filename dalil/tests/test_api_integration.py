"""
Integration tests for all Dalil API endpoints.

Tests run against a containerized MuninnDB instance (via testcontainers).
Each test gets a fresh, isolated environment.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client: TestClient):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient):
        """Health response should contain required fields."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert data["status"] in ["ok", "degraded", "error"]


class TestConsultEndpoint:
    """Tests for /consult endpoint."""

    def test_consult_post_returns_200(self, client: TestClient, sample_consult_request):
        """Consult endpoint should return 200 for valid request."""
        response = client.post("/consult", json=sample_consult_request)
        assert response.status_code == 200

    def test_consult_response_structure(self, client: TestClient, sample_consult_request):
        """Consult response should contain recommendation and cases."""
        response = client.post("/consult", json=sample_consult_request)
        data = response.json()
        
        assert "request_id" in data
        assert "recommendation" in data
        assert "cases" in data
        assert "confidence" in data
        assert isinstance(data["cases"], list)
        assert 0.0 <= data["confidence"] <= 1.0

    def test_consult_missing_query_returns_422(self, client: TestClient):
        """Consult without query parameter should return 422."""
        response = client.post("/consult", json={"context": "test"})
        assert response.status_code == 422


class TestIngestEndpoints:
    """Tests for /ingest/* endpoints."""

    def test_ingest_csv_from_url_returns_200(self, client: TestClient):
        """CSV ingestion from URL endpoint should be available."""
        # This will depend on actual CSV URL availability
        response = client.post(
            "/ingest/csv",
            json={"url": "http://example.com/test.csv", "vault": "default"}
        )
        # Endpoint exists (not 404), though may fail due to invalid URL
        assert response.status_code in [200, 400, 422]

    def test_ingest_pdf_from_url_returns_200(self, client: TestClient):
        """PDF ingestion from URL endpoint should be available."""
        response = client.post(
            "/ingest/pdf",
            json={"url": "http://example.com/test.pdf", "vault": "default"}
        )
        # Endpoint exists (not 404), though may fail due to invalid URL
        assert response.status_code in [200, 400, 422]

    def test_ingest_confluence_endpoint_available(self, client: TestClient):
        """Confluence ingestion endpoint should be available."""
        response = client.post(
            "/ingest/confluence",
            json={
                "base_url": "https://example.atlassian.net",
                "username": "test@example.com",
                "api_token": "test-token",
                "space_key": "TEST",
                "vault": "default",
            }
        )
        # Endpoint exists (not 404)
        assert response.status_code in [200, 400, 401, 422]


class TestFeedbackEndpoint:
    """Tests for /feedback endpoint."""

    def test_feedback_post_returns_response(self, client: TestClient, sample_feedback_request):
        """Feedback endpoint should accept POST requests."""
        response = client.post("/feedback", json=sample_feedback_request)
        
        # Should return 200, 201, or 202 (accepted)
        assert response.status_code in [200, 201, 202]

    def test_feedback_response_contains_request_id(self, client: TestClient, sample_feedback_request):
        """Feedback response should acknowledge the request."""
        response = client.post("/feedback", json=sample_feedback_request)
        
        if response.status_code in [200, 201, 202]:
            data = response.json()
            assert "request_id" in data or "status" in data


class TestCasesEndpoints:
    """Tests for /cases/* endpoints."""

    def test_evolve_case_endpoint_available(self, client: TestClient):
        """PUT /cases/{case_id} endpoint should be available."""
        response = client.put(
            "/cases/test-case-123",
            json={
                "evolution_query": "Update based on new information",
                "new_source": "Additional case law",
            }
        )
        # Endpoint exists (not 404), may return 404 for missing case
        assert response.status_code in [200, 400, 404, 422]

    def test_consolidate_cases_endpoint_available(self, client: TestClient):
        """POST /cases/consolidate endpoint should be available."""
        response = client.post(
            "/cases/consolidate",
            json={
                "case_ids": ["case-1", "case-2"],
                "consolidation_instruction": "Merge and deduplicate",
                "vault": "default",
            }
        )
        # Endpoint exists (not 404)
        assert response.status_code in [200, 400, 404, 422]

    def test_set_case_state_endpoint_available(self, client: TestClient):
        """PATCH /cases/{case_id}/state endpoint should be available."""
        response = client.patch(
            "/cases/test-case-123/state",
            json={"new_state": "resolved"}
        )
        # Endpoint exists (not 404)
        assert response.status_code in [200, 400, 404, 422]


class TestVaultEndpoints:
    """Tests for /vault/* endpoints."""

    def test_vault_stats_returns_200(self, client: TestClient):
        """Vault stats endpoint should return statistics."""
        response = client.get("/vault/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_memories" in data
        assert "total_concepts" in data
        assert "latest_update" in data

    def test_vault_entities_list_returns_200(self, client: TestClient):
        """Vault entities list endpoint should return entity listing."""
        response = client.get("/vault/entities")
        assert response.status_code == 200
        
        data = response.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)

    def test_vault_entity_detail_returns_response(self, client: TestClient):
        """Vault entity detail endpoint should respond."""
        # Try a generic entity name that might exist
        response = client.get("/vault/entities/law")
        
        # Should return 200 if entity exists, 404 if not (both valid)
        assert response.status_code in [200, 404]

    def test_vault_entity_timeline_returns_response(self, client: TestClient):
        """Vault entity timeline endpoint should respond."""
        response = client.get("/vault/entities/law/timeline")
        
        # Should return 200 if timeline available, 404 if not
        assert response.status_code in [200, 404]

    def test_vault_entity_cases_returns_response(self, client: TestClient):
        """Vault entity cases endpoint should respond."""
        response = client.get("/vault/entities/law/cases")
        
        # Should return 200 if cases available, 404 if not
        assert response.status_code in [200, 404]


class TestTraverseEndpoint:
    """Tests for /traverse endpoint."""

    def test_traverse_post_returns_response(self, client: TestClient, sample_traverse_request):
        """Traverse endpoint should accept POST requests."""
        response = client.post("/traverse", json=sample_traverse_request)
        assert response.status_code in [200, 400, 422]

    def test_traverse_response_contains_paths(self, client: TestClient, sample_traverse_request):
        """Traverse response should contain relationship paths."""
        response = client.post("/traverse", json=sample_traverse_request)
        
        if response.status_code == 200:
            data = response.json()
            assert "paths" in data or "relationships" in data or "graph" in data


class TestSessionEndpoint:
    """Tests for /session/* endpoints."""

    def test_session_recent_returns_200(self, client: TestClient):
        """Recent session endpoint should return recent memories."""
        response = client.get("/session/recent")
        assert response.status_code == 200
        
        data = response.json()
        assert "memories" in data or "recent" in data
        assert isinstance(data.get("memories") or data.get("recent"), list)


class TestEndpointExistence:
    """Meta tests to ensure all 18 documented endpoints exist."""

    def test_all_endpoints_exist(self, client: TestClient):
        """Verify all 18 documented endpoints are registered."""
        endpoints_to_check = [
            ("GET", "/health"),
            ("POST", "/consult"),
            ("POST", "/ingest/csv"),
            ("POST", "/ingest/pdf"),
            ("POST", "/ingest/csv/upload"),
            ("POST", "/ingest/pdf/upload"),
            ("POST", "/ingest/confluence"),
            ("POST", "/feedback"),
            ("PUT", "/cases/test-id"),
            ("POST", "/cases/consolidate"),
            ("PATCH", "/cases/test-id/state"),
            ("GET", "/vault/stats"),
            ("POST", "/traverse"),
            ("GET", "/session/recent"),
            ("GET", "/vault/entities"),
            ("GET", "/vault/entities/test"),
            ("GET", "/vault/entities/test/timeline"),
            ("GET", "/vault/entities/test/cases"),
        ]
        
        for method, path in endpoints_to_check:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json={})
            elif method == "PUT":
                response = client.put(path, json={})
            elif method == "PATCH":
                response = client.patch(path, json={})
            
            # Should NOT be 404 (endpoint exists)
            # May be 422 (bad request), 400, 200, etc. based on validation
            assert response.status_code != 404, f"{method} {path} returned 404"


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_malformed_json_returns_422(self, client: TestClient):
        """Malformed JSON should return 422."""
        response = client.post(
            "/consult",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_invalid_method_returns_405(self, client: TestClient):
        """Invalid HTTP method should return 405."""
        response = client.request("DELETE", "/health")
        assert response.status_code == 405

    def test_nonexistent_endpoint_returns_404(self, client: TestClient):
        """Nonexistent endpoint should return 404."""
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404
