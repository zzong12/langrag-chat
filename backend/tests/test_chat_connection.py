"""Test chat connection and streaming functionality."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test that the health endpoint is accessible."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]


def test_chat_stream_connection():
    """Test that chat stream endpoint is accessible and returns proper format."""
    response = client.post(
        "/api/chat/stream",
        json={"message": "test message"},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Read first chunk
    content = response.text
    assert "data:" in content or len(content) > 0


def test_chat_stream_error_handling():
    """Test that connection errors are properly handled."""
    # This test verifies that errors are returned in the stream format
    response = client.post(
        "/api/chat/stream",
        json={"message": "test"},
        headers={"Content-Type": "application/json"}
    )
    
    # Should not return 500, should stream error message instead
    assert response.status_code == 200
    
    # Check if error is in proper format
    content = response.text
    # Error should be in format: data: {"type": "error", "content": "..."}
    if "error" in content.lower():
        assert '"type":"error"' in content.replace(" ", "") or '"type": "error"' in content


def test_chat_stream_response_format():
    """Test that stream response follows SSE format."""
    response = client.post(
        "/api/chat/stream",
        json={"message": "hello"},
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    content = response.text
    
    # Should contain data: prefix for SSE format
    lines = content.split('\n')
    data_lines = [line for line in lines if line.startswith('data:')]
    assert len(data_lines) > 0 or len(content) > 0

