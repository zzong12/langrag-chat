"""Document processor tests."""
import pytest
import tempfile
from pathlib import Path
from app.services.document_processor import document_processor


def test_text_splitter_initialization():
    """Test that text splitter is initialized."""
    assert document_processor.text_splitter is not None


def test_process_txt_file():
    """Test processing a TXT file."""
    # Create a temporary text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document. " * 50)  # Create enough content to chunk
        temp_path = Path(f.name)
    
    try:
        doc_id, chunks, file_size = document_processor.process_file(
            temp_path, "test.txt"
        )
        assert doc_id is not None
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert file_size > 0
    finally:
        # Clean up
        temp_path.unlink()


def test_extract_txt_text():
    """Test TXT text extraction."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content for extraction")
        temp_path = Path(f.name)
    
    try:
        text = document_processor._extract_txt_text(temp_path)
        assert isinstance(text, str)
        assert "Test content" in text
    finally:
        temp_path.unlink()

