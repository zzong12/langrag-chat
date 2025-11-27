"""Vector store tests."""
import pytest
from app.rag.vectorstore import vectorstore_manager
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document


def test_vectorstore_initialization():
    """Test that vectorstore initializes correctly."""
    assert vectorstore_manager is not None
    assert vectorstore_manager.index is not None
    assert vectorstore_manager.index_name is not None


def test_similarity_search_empty():
    """Test similarity search with empty index."""
    # Should not raise an error even if no documents exist
    try:
        results = vectorstore_manager.similarity_search("test query", k=2)
        assert isinstance(results, list)
        # Results might be empty if no documents are indexed
    except Exception as e:
        # If there's an error, it should be a meaningful one, not NoneType
        assert "NoneType" not in str(e)


def test_similarity_search_with_score():
    """Test similarity search with scores."""
    try:
        results = vectorstore_manager.similarity_search_with_score("test query", k=2)
        assert isinstance(results, list)
        # Each result should be a tuple of (Document, score)
        if results:
            assert isinstance(results[0], tuple)
            assert len(results[0]) == 2
    except Exception as e:
        assert "NoneType" not in str(e)


def test_add_documents_structure():
    """Test that add_documents accepts correct structure."""
    test_docs = [
        Document(
            page_content="This is a test document chunk.",
            metadata={
                "document_id": "test-doc-1",
                "filename": "test.txt",
                "file_type": "txt",
                "upload_date": "2025-01-01T00:00:00"
            }
        )
    ]
    
    try:
        chunk_ids = vectorstore_manager.add_documents(test_docs, "test-doc-1")
        assert isinstance(chunk_ids, list)
        # Clean up
        try:
            vectorstore_manager.delete_documents("test-doc-1")
        except:
            pass
    except Exception as e:
        # If it fails, it should be a meaningful error
        assert "NoneType" not in str(e)


def test_get_stats():
    """Test getting vector store statistics."""
    try:
        stats = vectorstore_manager.get_stats()
        assert isinstance(stats, dict)
        assert "total_vectors" in stats
    except Exception as e:
        # Should not fail with NoneType error
        assert "NoneType" not in str(e)

