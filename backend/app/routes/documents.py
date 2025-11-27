"""Document management API routes."""
import shutil
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.models import DocumentInfo, DocumentList, UploadResponse, ErrorResponse
from app.config import settings
from app.services.document_processor import document_processor
from app.services.document_registry import document_registry
from app.rag.vectorstore import vectorstore_manager

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_all_documents() -> List[DocumentInfo]:
    """Get all registered documents."""
    # Try to restore from vectorstore if registry is empty
    all_docs = document_registry.get_all()
    if not all_docs:
        try:
            document_registry.restore_from_vectorstore(vectorstore_manager)
            all_docs = document_registry.get_all()
        except Exception as e:
            print(f"Error restoring from vectorstore: {e}")
    
    documents = []
    for doc_id, doc_data in all_docs.items():
        # Convert datetime if needed
        upload_date = doc_data.get("upload_date")
        if isinstance(upload_date, str):
            from datetime import datetime
            try:
                upload_date = datetime.fromisoformat(upload_date)
            except:
                upload_date = datetime.now()
        
        documents.append(DocumentInfo(
            id=doc_id,
            filename=doc_data["filename"],
            upload_date=upload_date,
            chunks_count=doc_data.get("chunks_count", 0),
            file_size=doc_data.get("file_size", 0),
            file_type=doc_data.get("file_type", "unknown"),
        ))
    return documents


@router.get("", response_model=DocumentList)
async def list_documents():
    """
    List all uploaded documents.
    
    Returns:
        List of document information
    """
    documents = _get_all_documents()
    return DocumentList(
        documents=documents,
        total=len(documents)
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Args:
        file: Uploaded file (PDF, DOCX, or TXT)
        
    Returns:
        Upload response with document information
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
        )
    
    try:
        # Save uploaded file
        file_path = settings.UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Process document
        document_id, chunks, file_size = document_processor.process_file(
            file_path, file.filename
        )
        
        # Index document in vector store
        chunks_count = document_processor.index_document(document_id, chunks)
        
        # Register document
        document_registry.add(document_id, {
            "filename": file.filename,
            "upload_date": datetime.now(),
            "chunks_count": chunks_count,
            "file_size": file_size,
            "file_type": file_ext[1:],
            "file_path": str(file_path),
        })
        
        return UploadResponse(
            success=True,
            document_id=document_id,
            filename=file.filename,
            chunks_count=chunks_count,
            message=f"Document uploaded and processed successfully. Created {chunks_count} chunks."
        )
    
    except Exception as e:
        # Clean up file if processing failed
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its chunks from the vector store.
    
    Args:
        document_id: Document identifier (can be document_id or filename)
        
    Returns:
        Success message
    """
    # Try to find document by ID first
    doc_data = document_registry.get(document_id)
    
    # If not found by ID, try to find by filename
    if not doc_data:
        all_docs = document_registry.get_all()
        for doc_id, data in all_docs.items():
            if data.get('filename') == document_id:
                doc_data = data
                document_id = doc_id  # Update to actual document_id
                break
    
    if not doc_data:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}"
        )
    
    filename = doc_data.get('filename', '')
    
    try:
        # First, delete from vector store (this is the most important step)
        # This must succeed to ensure data consistency
        try:
            # Try to delete by document_id
            # Note: delete_document may not find chunks if tracking is lost,
            # but it will try alternative methods and won't fail if chunks don't exist
            document_processor.delete_document(document_id)
            print(f"Delete operation completed for document_id: {document_id}")
            
            # Also try to delete by filename if document_id deletion didn't find chunks
            # This handles cases where tracking is lost but we know the filename
            # We'll search for chunks and match by checking local metadata
            if filename:
                try:
                    # Search for chunks and match by filename in local metadata
                    from app.rag.vectorstore import vectorstore_manager
                    
                    # Find chunks by searching local metadata
                    chunks_to_delete = []
                    for chunk_id, chunk_meta in list(vectorstore_manager._chunk_metadata.items()):
                        if chunk_meta.get('filename') == filename:
                            chunks_to_delete.append(chunk_id)
                    
                    if chunks_to_delete:
                        print(f"Found {len(chunks_to_delete)} additional chunks by filename matching in metadata")
                        # Delete in batches
                        BATCH_SIZE = 1000
                        from app.config import settings
                        from pinecone import Pinecone
                        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                        index = pc.Index(settings.PINECONE_INDEX_NAME)
                        
                        for i in range(0, len(chunks_to_delete), BATCH_SIZE):
                            batch = chunks_to_delete[i:i + BATCH_SIZE]
                            index.delete(ids=batch, namespace='__default__')
                            print(f"Deleted {len(batch)} chunks by filename match")
                            
                            # Clean up metadata
                            for chunk_id in batch:
                                if chunk_id in vectorstore_manager._chunk_metadata:
                                    del vectorstore_manager._chunk_metadata[chunk_id]
                except Exception as filename_delete_error:
                    print(f"Warning: Could not delete by filename: {filename_delete_error}")
                    
        except Exception as vec_error:
            # Log the error but continue with file and registry cleanup
            print(f"Warning: Error deleting from vector store: {vec_error}")
            # Re-raise to ensure user knows about the issue
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting document from vector store: {str(vec_error)}"
            )
        
        # Delete physical file
        file_path = Path(doc_data["file_path"])
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"Deleted physical file: {file_path}")
            except Exception as file_error:
                print(f"Warning: Could not delete physical file {file_path}: {file_error}")
                # Don't fail the whole operation if file deletion fails
        
        # Remove from registry (this should be last)
        try:
            document_registry.delete(document_id)
            print(f"Removed document from registry: {document_id}")
        except Exception as reg_error:
            print(f"Warning: Could not remove from registry: {reg_error}")
        
        return {
            "success": True, 
            "message": f"Document '{filename or document_id}' deleted successfully",
            "chunks_deleted": True
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting document {document_id}: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )


@router.post("/clear-index", response_model=dict)
async def clear_index():
    """
    Clear all vectors from the Pinecone index.
    This will delete all documents from the vector store but keep the document registry.
    
    Returns:
        Success message
    """
    try:
        from app.rag.vectorstore import vectorstore_manager
        from app.config import settings
        from pinecone import Pinecone
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        
        # Get stats to find all namespaces
        stats = index.describe_index_stats()
        cleared_namespaces = []
        total_vectors_cleared = 0
        
        if 'namespaces' in stats:
            for ns_name, ns_stats in stats['namespaces'].items():
                vector_count = ns_stats.get('vector_count', 0)
                if vector_count > 0:
                    try:
                        # Delete all vectors in this namespace
                        if ns_name == '':
                            # Empty string namespace
                            index.delete(delete_all=True, namespace='')
                        else:
                            index.delete(delete_all=True, namespace=ns_name)
                        
                        cleared_namespaces.append(ns_name if ns_name else '__default__')
                        total_vectors_cleared += vector_count
                        print(f"Cleared namespace '{ns_name if ns_name else '__default__'}': {vector_count} vectors")
                    except Exception as ns_error:
                        print(f"Error clearing namespace {ns_name}: {ns_error}")
        
        # Clear local tracking
        vectorstore_manager._document_chunks.clear()
        vectorstore_manager._chunk_metadata.clear()
        
        return {
            "success": True,
            "message": f"Index cleared successfully. Removed {total_vectors_cleared} vectors from {len(cleared_namespaces)} namespace(s).",
            "vectors_cleared": total_vectors_cleared,
            "namespaces_cleared": cleared_namespaces
        }
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error clearing index: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing index: {str(e)}"
        )


@router.post("/{document_id}/reload", response_model=UploadResponse)
async def reload_document(document_id: str):
    """
    Reload and re-index a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Reload response
    """
    doc_data = document_registry.get(document_id)
    if not doc_data:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    try:
        file_path = Path(doc_data["file_path"])
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Original file not found"
            )
        
        # Delete old chunks
        document_processor.delete_document(document_id)
        
        # Re-process document
        chunks = document_processor.process_file(file_path, doc_data["filename"])[1]
        
        # Re-index
        chunks_count = document_processor.index_document(document_id, chunks)
        
        # Update registry
        doc_data["chunks_count"] = chunks_count
        doc_data["upload_date"] = datetime.now()
        document_registry.add(document_id, doc_data)
        
        return UploadResponse(
            success=True,
            document_id=document_id,
            filename=doc_data["filename"],
            chunks_count=chunks_count,
            message=f"Document reloaded successfully. Created {chunks_count} chunks."
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading document: {str(e)}"
        )

