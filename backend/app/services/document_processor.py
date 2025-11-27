"""Document processing service for PDF, DOCX, and TXT files."""
import os
import uuid
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

import PyPDF2
from docx import Document as DocxDocument
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document

from app.config import settings
from app.rag.vectorstore import vectorstore_manager


class DocumentProcessor:
    """Process uploaded documents and extract text chunks."""
    
    def __init__(self):
        """Initialize document processor with text splitter."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def process_file(
        self,
        file_path: Path,
        filename: str
    ) -> Tuple[str, List[Document], int]:
        """
        Process a file and return document_id, chunks, and file_size.
        
        Args:
            file_path: Path to the uploaded file
            filename: Original filename
            
        Returns:
            Tuple of (document_id, chunks, file_size)
        """
        # Determine file type
        file_ext = file_path.suffix.lower()
        file_size = file_path.stat().st_size
        
        # Extract text based on file type
        if file_ext == ".pdf":
            text = self._extract_pdf_text(file_path)
        elif file_ext in [".docx", ".doc"]:
            text = self._extract_docx_text(file_path)
        elif file_ext == ".txt":
            text = self._extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Split text into chunks
        chunks = self.text_splitter.create_documents(
            [text],
            metadatas=[{
                "document_id": document_id,
                "filename": filename,
                "file_type": file_ext[1:],  # Remove the dot
                "upload_date": datetime.now().isoformat(),
            }]
        )
        
        return document_id, chunks, file_size
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        text_parts = []
        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_parts.append(page.extract_text())
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")
        return "\n".join(text_parts)
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        try:
            doc = DocxDocument(file_path)
            text_parts = [paragraph.text for paragraph in doc.paragraphs]
            return "\n".join(text_parts)
        except Exception as e:
            raise Exception(f"Error reading DOCX file: {str(e)}")
    
    def _extract_txt_text(self, file_path: Path) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as file:
                return file.read()
        except Exception as e:
            raise Exception(f"Error reading TXT file: {str(e)}")
    
    def index_document(
        self,
        document_id: str,
        chunks: List[Document]
    ) -> int:
        """
        Index document chunks in the vector store.
        
        Args:
            document_id: Document identifier
            chunks: List of document chunks
            
        Returns:
            Number of chunks indexed
        """
        vectorstore_manager.add_documents(chunks, document_id=document_id)
        return len(chunks)
    
    def delete_document(self, document_id: str):
        """Delete a document from the vector store."""
        vectorstore_manager.delete_documents(document_id)


# Global document processor instance
document_processor = DocumentProcessor()

