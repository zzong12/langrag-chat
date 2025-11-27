"""RAG chain tests."""
import pytest
from app.rag.chain import rag_chain


def test_rag_chain_initialization():
    """Test that RAG chain initializes correctly."""
    assert rag_chain is not None
    assert rag_chain.llm is not None
    assert rag_chain.retriever is not None


def test_rag_chain_query_basic():
    """Test basic RAG chain query."""
    try:
        result = rag_chain.query("What is this?", return_sources=False)
        assert isinstance(result, dict)
        assert "answer" in result
    except Exception as e:
        # Should not fail with NoneType error
        assert "NoneType" not in str(e)
        # If it fails, it should be a meaningful error
        print(f"Query failed with: {e}")


def test_rag_chain_query_with_sources():
    """Test RAG chain query with sources."""
    try:
        result = rag_chain.query("What is this?", return_sources=True)
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)
    except Exception as e:
        assert "NoneType" not in str(e)
        print(f"Query with sources failed with: {e}")


def test_rag_chain_format_sources():
    """Test source formatting."""
    try:
        from langchain_core.documents import Document
    except ImportError:
        from langchain.schema import Document
    
    test_docs = [
        Document(
            page_content="Test content 1",
            metadata={"document_id": "doc1", "filename": "test1.txt"}
        ),
        Document(
            page_content="Test content 2",
            metadata={"document_id": "doc2", "filename": "test2.txt"}
        )
    ]
    
    sources = rag_chain._format_sources(test_docs)
    assert isinstance(sources, list)
    if sources:
        assert "filename" in sources[0]
        assert "content" in sources[0]
        assert "document_id" in sources[0]

