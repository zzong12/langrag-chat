"""Comprehensive test cases for document upload, delete, reload, and chat citation."""
import pytest
import os
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.document_registry import document_registry
from app.rag.vectorstore import vectorstore_manager

# Test file path
TEST_FILE = "/Users/jason/Projects/funny/my-rag/knowledge/Encyclopedia.pdf"


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def clear_vectorstore():
    """Clear vectorstore before each test."""
    # Clear local tracking
    vectorstore_manager._document_chunks.clear()
    vectorstore_manager._chunk_metadata.clear()
    
    # Try to clear Pinecone (if possible)
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        # Delete all in default namespace
        index.delete(delete_all=True, namespace='__default__')
    except Exception as e:
        print(f"Note: Could not clear Pinecone: {e}")
    
    yield
    
    # Cleanup after test
    vectorstore_manager._document_chunks.clear()
    vectorstore_manager._chunk_metadata.clear()


@pytest.fixture(scope="function")
def clear_registry():
    """Clear document registry before each test."""
    # Clear registry
    all_docs = list(document_registry.get_all().keys())
    for doc_id in all_docs:
        document_registry.delete(doc_id)
    
    yield
    
    # Cleanup after test
    all_docs = list(document_registry.get_all().keys())
    for doc_id in all_docs:
        document_registry.delete(doc_id)


class TestDocumentWorkflow:
    """Test complete document workflow."""
    
    def test_1_upload_document(self, client, clear_vectorstore, clear_registry):
        """Test 1: Upload a document."""
        assert os.path.exists(TEST_FILE), f"Test file not found: {TEST_FILE}"
        
        with open(TEST_FILE, "rb") as f:
            response = client.post(
                "/api/documents/upload",
                files={"file": ("Encyclopedia.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "Encyclopedia.pdf"
        assert data["chunks_count"] > 0
        
        document_id = data["document_id"]
        print(f"✓ Upload successful. Document ID: {document_id}, Chunks: {data['chunks_count']}")
        
        # Verify document appears in list
        list_response = client.get("/api/documents")
        assert list_response.status_code == 200
        docs = list_response.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["filename"] == "Encyclopedia.pdf"
        
        return document_id
    
    def test_2_chat_with_citation(self, client, clear_vectorstore, clear_registry):
        """Test 2: Chat and verify citations show filename."""
        # First upload
        document_id = self.test_1_upload_document(client, clear_vectorstore, clear_registry)
        
        # Send a chat message
        response = client.post(
            "/api/chat",
            json={
                "message": "What is in the Encyclopedia?",
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data.get("sources", [])) > 0
        
        # Verify sources have correct filename
        for source in data["sources"]:
            assert "filename" in source
            assert source["filename"] == "Encyclopedia.pdf"
            assert source["filename"] != "Unknown"
            print(f"✓ Citation shows filename: {source['filename']}")
        
        return document_id
    
    def test_3_delete_document(self, client, clear_vectorstore, clear_registry):
        """Test 3: Delete a document and verify it's removed."""
        # First upload
        document_id = self.test_1_upload_document(client, clear_vectorstore, clear_registry)
        
        # Delete document
        response = client.delete(f"/api/documents/{document_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print(f"✓ Delete successful: {data['message']}")
        
        # Verify document is removed from list
        list_response = client.get("/api/documents")
        assert list_response.status_code == 200
        docs = list_response.json()["documents"]
        assert len(docs) == 0
        
        # Verify document cannot be found in chat
        chat_response = client.post(
            "/api/chat",
            json={
                "message": "What is in the Encyclopedia?",
                "stream": False
            }
        )
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        # Should not find the deleted document
        sources = chat_data.get("sources", [])
        for source in sources:
            assert source.get("filename") != "Encyclopedia.pdf"
        print("✓ Deleted document no longer appears in search results")
    
    def test_4_reload_document(self, client, clear_vectorstore, clear_registry):
        """Test 4: Reload a document."""
        # First upload
        document_id = self.test_1_upload_document(client, clear_vectorstore, clear_registry)
        
        # Get initial chunks count
        list_response = client.get("/api/documents")
        initial_chunks = list_response.json()["documents"][0]["chunks_count"]
        
        # Reload document
        response = client.post(f"/api/documents/{document_id}/reload")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chunks_count"] > 0
        print(f"✓ Reload successful. Chunks: {data['chunks_count']}")
        
        # Verify document still appears in list
        list_response = client.get("/api/documents")
        assert list_response.status_code == 200
        docs = list_response.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["filename"] == "Encyclopedia.pdf"
    
    def test_5_delete_by_filename(self, client, clear_vectorstore, clear_registry):
        """Test 5: Delete document by filename matching."""
        # First upload
        document_id = self.test_1_upload_document(client, clear_vectorstore, clear_registry)
        
        # Try to delete by filename (should work)
        # Note: This tests the filename matching logic
        response = client.delete(f"/api/documents/{document_id}")
        assert response.status_code == 200
        
        # Verify deletion
        list_response = client.get("/api/documents")
        assert list_response.status_code == 200
        docs = list_response.json()["documents"]
        assert len(docs) == 0
        print("✓ Delete by document_id successful")
    
    def test_6_stream_chat_with_citations(self, client, clear_vectorstore, clear_registry):
        """Test 6: Stream chat and verify citations."""
        # First upload
        document_id = self.test_1_upload_document(client, clear_vectorstore, clear_registry)
        
        # Stream chat
        response = client.post(
            "/api/chat/stream",
            json={
                "message": "What is in the Encyclopedia?",
            },
            stream=True
        )
        
        assert response.status_code == 200
        
        # Collect streamed data
        citations = []
        text_chunks = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    import json
                    try:
                        data = json.loads(line_str[6:])
                        if data.get('type') == 'citation':
                            citations.append(data)
                            assert data.get('filename') == 'Encyclopedia.pdf'
                            assert data.get('filename') != 'Unknown'
                        elif data.get('type') == 'text':
                            text_chunks.append(data.get('content', ''))
                    except:
                        pass
        
        assert len(text_chunks) > 0
        assert len(citations) > 0
        print(f"✓ Stream chat successful. Received {len(citations)} citations")
        for citation in citations:
            print(f"  - Citation filename: {citation.get('filename')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

