"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import create_app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    app = create_app()
    return TestClient(app)


@patch('src.config.validate_required_settings')
@patch('src.database.connection.get_database_health')
def test_health_endpoint(mock_db_health, mock_validate_settings, client):
    """Test basic health check endpoint."""
    # Mock the database health check
    mock_db_health.return_value = AsyncMock(return_value={"healthy": True})
    mock_validate_settings.return_value = None
    
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "dipc-api"
    assert data["version"] == "1.3.0"
    assert "timestamp" in data


def test_cors_headers(client):
    """Test CORS headers are properly configured."""
    response = client.options("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_api_versioning_structure(client):
    """Test that API versioning structure is properly set up."""
    # Test that v1 endpoints are accessible (even if not implemented)
    response = client.post("/v1/tasks", json={})
    # Should return 422 (validation error) or 501 (not implemented), not 404
    assert response.status_code in [422, 501]
    
    response = client.post("/v1/upload/presigned-url", json={})
    # Should return 422 (validation error) or 501 (not implemented), not 404
    assert response.status_code in [422, 501]


def test_request_validation_error_handling(client):
    """Test that request validation errors are properly handled."""
    # Send invalid JSON to trigger validation error
    response = client.post("/v1/tasks", json={"invalid": "data"})
    
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert data["error_message"] == "Request validation failed"
    assert "details" in data
    assert "request_id" in data
    assert "timestamp" in data


def test_request_logging_middleware(client):
    """Test that request logging middleware adds request ID."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    
    # Verify request ID is a valid UUID format
    request_id = response.headers["X-Request-ID"]
    import uuid
    try:
        uuid.UUID(request_id)
    except ValueError:
        pytest.fail("Request ID is not a valid UUID")


@patch('src.config.validate_required_settings')
@patch('src.database.connection.get_database_health')
def test_detailed_health_check(mock_db_health, mock_validate_settings, client):
    """Test detailed health check endpoint."""
    # Mock the database health check
    mock_db_health.return_value = {
        "healthy": True,
        "response_time": 0.001,
        "database": "postgresql"
    }
    mock_validate_settings.return_value = None
    
    response = client.get("/v1/health/detailed")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "dipc-api"
    assert "components" in data
    assert "database" in data["components"]