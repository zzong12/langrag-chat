"""Pydantic models for API requests and responses."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for history")
    stream: bool = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant response")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    sources: Optional[List[dict]] = Field(default_factory=list, description="Source documents used")


class DocumentInfo(BaseModel):
    """Document information model."""
    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    upload_date: datetime = Field(..., description="Upload timestamp")
    chunks_count: int = Field(..., description="Number of text chunks")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File type (pdf, docx, txt)")


class DocumentList(BaseModel):
    """List of documents."""
    documents: List[DocumentInfo] = Field(default_factory=list, description="List of documents")
    total: int = Field(0, description="Total number of documents")


class UploadResponse(BaseModel):
    """Response model for document upload."""
    success: bool = Field(..., description="Upload success status")
    document_id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Uploaded filename")
    chunks_count: int = Field(..., description="Number of chunks created")
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")

