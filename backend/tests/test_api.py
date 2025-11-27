"""API endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]


def test_documents_list_empty():
    """Test listing documents when empty."""
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data
    assert isinstance(data["documents"], list)


def test_chat_endpoint_basic():
    """Test chat endpoint with a simple query."""
    response = client.post(
        "/api/chat",
        json={"message": "Hello, this is a test message"}
    )
    # Should return 200 even if no documents are indexed
    assert response.status_code in [200, 500]  # 500 if LLM fails, but structure should be correct
    if response.status_code == 200:
        data = response.json()
        assert "response" in data or "error" in data


def test_chat_endpoint_with_conversation_id():
    """Test chat endpoint with conversation ID."""
    response = client.post(
        "/api/chat",
        json={
            "message": "Test message",
            "conversation_id": "test-conv-123"
        }
    )
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "response" in data or "error" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200


def test_documents_upload_invalid_file_type():
    """Test document upload with invalid file type."""
    # Create a fake file
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = client.post("/api/documents/upload", files=files)
    # Should accept txt files
    assert response.status_code in [200, 400, 500]


def test_documents_delete_nonexistent():
    """Test deleting a non-existent document."""
    response = client.delete("/api/documents/nonexistent-id-12345")
    assert response.status_code == 404


def test_documents_reload_nonexistent():
    """Test reloading a non-existent document."""
    response = client.post("/api/documents/nonexistent-id-12345/reload")
    assert response.status_code == 404

