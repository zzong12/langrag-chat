"""Document registry with persistence."""
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import settings


class DocumentRegistry:
    """Persistent document registry."""
    
    def __init__(self):
        """Initialize registry with persistence."""
        self.registry_file = settings.UPLOAD_DIR / "document_registry.json"
        self.registry: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self):
        """Load registry from file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert date strings back to datetime objects
                    for doc_id, doc_data in data.items():
                        if isinstance(doc_data.get('upload_date'), str):
                            try:
                                doc_data['upload_date'] = datetime.fromisoformat(doc_data['upload_date'])
                            except:
                                pass
                    self.registry = data
            except Exception as e:
                print(f"Error loading registry: {e}")
                self.registry = {}
        else:
            self.registry = {}
    
    def _save(self):
        """Save registry to file."""
        try:
            # Convert datetime to ISO format for JSON
            data = {}
            for doc_id, doc_data in self.registry.items():
                data[doc_id] = doc_data.copy()
                if isinstance(doc_data.get('upload_date'), datetime):
                    data[doc_id]['upload_date'] = doc_data['upload_date'].isoformat()
            
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving registry: {e}")
    
    def add(self, document_id: str, document_data: Dict[str, Any]):
        """Add or update a document."""
        self.registry[document_id] = document_data
        self._save()
    
    def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        return self.registry.get(document_id)
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all documents."""
        return self.registry.copy()
    
    def delete(self, document_id: str):
        """Delete a document."""
        if document_id in self.registry:
            del self.registry[document_id]
            self._save()
    
    def restore_from_vectorstore(self, vectorstore_manager):
        """Restore registry from vectorstore metadata and upload directory."""
        # Get all unique document IDs from vectorstore chunk metadata
        chunk_metadata = vectorstore_manager._chunk_metadata
        document_ids = set()
        # Map document_id to filename from chunk metadata
        doc_id_to_filename = {}
        
        for chunk_id, metadata in chunk_metadata.items():
            doc_id = metadata.get('document_id')
            if doc_id:
                document_ids.add(doc_id)
                # Store filename mapping
                if doc_id not in doc_id_to_filename:
                    filename = metadata.get('filename')
                    if filename and filename != 'unknown':
                        doc_id_to_filename[doc_id] = filename
        
        # Also try to get filenames from Pinecone fields by searching
        # This helps recover filenames even if local metadata is lost
        try:
            from app.config import settings
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            index = pc.Index(settings.PINECONE_INDEX_NAME)
            
            # Search for a few records to get field information
            search_params = {
                'inputs': {'text': 'test'},
                'top_k': 100  # Get some records to extract filenames
            }
            results = index.search(namespace='__default__', query=search_params)
            
            if results:
                matches = None
                if isinstance(results, dict) and 'result' in results:
                    matches = results['result'].get('hits', [])
                elif hasattr(results, 'matches') and results.matches:
                    matches = results.matches
                elif hasattr(results, 'result') and hasattr(results.result, 'hits'):
                    matches = results.result.hits
                
                if matches:
                    for match in matches:
                        if isinstance(match, dict):
                            chunk_id = match.get('_id') or match.get('id')
                            fields = match.get('fields', {})
                        else:
                            chunk_id = getattr(match, 'id', None) or getattr(match, '_id', None)
                            fields = getattr(match, 'fields', {})
                        
                        if chunk_id and fields:
                            filename = fields.get('filename') if isinstance(fields, dict) else getattr(fields, 'filename', None)
                            doc_id = fields.get('document_id') if isinstance(fields, dict) else getattr(fields, 'document_id', None)
                            
                            if filename and doc_id:
                                document_ids.add(doc_id)
                                if doc_id not in doc_id_to_filename:
                                    doc_id_to_filename[doc_id] = filename
        except Exception as e:
            print(f"Warning: Could not extract filenames from Pinecone fields: {e}")
        
        # Also check upload directory for files that might not be in metadata
        upload_dir = settings.UPLOAD_DIR
        if upload_dir.exists():
            for file_path in upload_dir.glob('*'):
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.docx', '.doc', '.txt']:
                    # Try to find matching document_id by checking if file was processed
                    # We'll create a document entry for files that exist but aren't in registry
                    filename = file_path.name
                    # Check if we already have this file
                    existing = None
                    for doc_id, doc_data in self.registry.items():
                        if doc_data.get('filename') == filename:
                            existing = doc_id
                            break
                    
                    if not existing:
                        # Create a new document entry for this file
                        # Generate a document_id based on filename hash
                        import hashlib
                        doc_id = hashlib.md5(filename.encode()).hexdigest()[:16]
                        
                        # Count chunks that might belong to this file
                        chunks_count = sum(
                            1 for meta in chunk_metadata.values()
                            if meta.get('filename') == filename
                        )
                        
                        self.registry[doc_id] = {
                            "filename": filename,
                            "upload_date": datetime.fromtimestamp(file_path.stat().st_mtime),
                            "chunks_count": chunks_count if chunks_count > 0 else 1,  # At least 1
                            "file_size": file_path.stat().st_size,
                            "file_type": file_path.suffix[1:] if file_path.suffix else "unknown",
                            "file_path": str(file_path),
                        }
        
        # Restore documents that exist in vectorstore but not in registry
        for doc_id in document_ids:
            if doc_id not in self.registry:
                # Get metadata from chunks
                chunks_for_doc = [
                    meta for meta in chunk_metadata.values()
                    if meta.get('document_id') == doc_id
                ]
                
                if chunks_for_doc:
                    first_chunk = chunks_for_doc[0]
                    # Use filename from mapping if available, otherwise from chunk metadata
                    filename = doc_id_to_filename.get(doc_id) or first_chunk.get('filename', f"document_{doc_id[:8]}")
                    
                    # Try to find file in upload directory
                    found_file = None
                    upload_dir = settings.UPLOAD_DIR
                    if upload_dir.exists():
                        # First try exact match
                        for file_path in upload_dir.glob('*'):
                            if file_path.is_file() and file_path.name == filename:
                                found_file = file_path
                                break
                        # If not found, try partial match
                        if not found_file:
                            for file_path in upload_dir.glob('*'):
                                if file_path.is_file() and filename in file_path.name:
                                    found_file = file_path
                                    filename = file_path.name  # Update to actual filename
                                    break
                    
                    self.registry[doc_id] = {
                        "filename": filename,
                        "upload_date": datetime.now(),  # We don't have original date
                        "chunks_count": len(chunks_for_doc),
                        "file_size": found_file.stat().st_size if found_file and found_file.exists() else 0,
                        "file_type": first_chunk.get('file_type', 'unknown'),
                        "file_path": str(found_file) if found_file else "",
                    }
        
        self._save()


# Global registry instance
document_registry = DocumentRegistry()

