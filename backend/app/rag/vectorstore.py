"""Pinecone vector store integration with hosted embedding model."""
import uuid
from typing import List, Dict, Any, Optional
from pinecone import Pinecone
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

from app.config import settings


class VectorStoreManager:
    """Manager for Pinecone vector store operations with hosted embedding model."""
    
    def __init__(self):
        """Initialize Pinecone client and index."""
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.index = self.pc.Index(self.index_name)
        # Store chunk IDs for each document to enable deletion
        self._document_chunks: Dict[str, List[str]] = {}
        # Store metadata for chunks (since Pinecone hosted embedding doesn't support metadata)
        self._chunk_metadata: Dict[str, Dict[str, Any]] = {}
    
    def add_documents(
        self,
        documents: List[Document],
        document_id: str,
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        Add documents to the vector store using hosted embedding model.
        
        Args:
            documents: List of Document objects with text content
            document_id: Document identifier
            namespace: Optional namespace
            
        Returns:
            List of chunk IDs
        """
        # Prepare records for upsert
        records = []
        chunk_ids = []
        
        for i, doc in enumerate(documents):
            # Generate unique chunk ID
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # For Pinecone hosted embedding models, metadata is not supported in upsert_records
            # We'll store metadata separately in our application registry
            # The text content is stored in the 'text' field and Pinecone will auto-embed it
            
            # Create record with text (Pinecone will auto-embed)
            # According to Pinecone docs, additional fields are stored as metadata
            # The field name for text must match the field_map in the index (usually 'text' or 'chunk_text')
            # Additional fields like 'filename' and 'document_id' are stored as metadata
            filename = doc.metadata.get("filename", "unknown")
            file_type = doc.metadata.get("file_type", "unknown")
            
            record = {
                "_id": chunk_id,  # Use _id as per Pinecone docs (id is also accepted as alias)
                "text": doc.page_content,  # Text field for embedding (field name depends on index field_map)
                "filename": filename,  # Stored as metadata, can be returned in search results
                "document_id": document_id,  # Stored as metadata
                "file_type": file_type,  # Stored as metadata
            }
            records.append(record)
            
            # Store metadata separately in our application (since Pinecone doesn't support it)
            self._chunk_metadata[chunk_id] = {
                "document_id": document_id,
                "filename": doc.metadata.get("filename", "unknown"),
                "file_type": doc.metadata.get("file_type", "unknown"),
                "upload_date": doc.metadata.get("upload_date", ""),
                "text": doc.page_content,  # Store full text for retrieval
            }
        
        # Upsert records using hosted embedding model
        # namespace is required, use "__default__" for default namespace
        namespace = namespace if namespace is not None else "__default__"
        
        # Pinecone has payload size limits and rate limits
        # Rate limit: 250,000 tokens per minute for llama-text-embed-v2
        # We need to be conservative with batch size and add delays
        # Estimate tokens: roughly 1 token = 4 characters for English, 1.5-2 for Chinese
        # We'll use a smaller batch size and add delays to respect rate limits
        BATCH_SIZE = 20  # Reduced batch size to avoid rate limits (was 96)
        MAX_BATCH_SIZE_BYTES = 1 * 1024 * 1024  # 1MB per batch (more conservative)
        MAX_TOKENS_PER_BATCH = 20000  # Conservative estimate to stay under 250k/min limit
        DELAY_BETWEEN_BATCHES = 2.0  # 2 seconds delay between batches
        
        # Split records into batches with token and size limits
        batches = []
        current_batch = []
        current_batch_size = 0
        current_batch_tokens = 0
        
        def estimate_tokens(text: str) -> int:
            """Estimate token count for text (rough approximation)."""
            # For mixed content, use average: ~1.5 tokens per character
            # This is conservative to avoid rate limits
            return int(len(text) * 1.5)
        
        for record in records:
            text = record.get('text', '')
            record_id = record.get('_id', '') or record.get('id', '')  # Support both _id and id
            record_size = len(record_id) + len(text)
            record_tokens = estimate_tokens(text)
            
            # Check if adding this record would exceed limits
            would_exceed_size = (current_batch_size + record_size) > MAX_BATCH_SIZE_BYTES
            would_exceed_count = len(current_batch) >= BATCH_SIZE
            would_exceed_tokens = (current_batch_tokens + record_tokens) > MAX_TOKENS_PER_BATCH
            
            if would_exceed_size or would_exceed_count or would_exceed_tokens:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [record]
                current_batch_size = record_size
                current_batch_tokens = record_tokens
            else:
                current_batch.append(record)
                current_batch_size += record_size
                current_batch_tokens += record_tokens
        
        # Add the last batch if it has records
        if current_batch:
            batches.append(current_batch)
        
        # Upload batches sequentially with rate limiting and retry
        import time
        import random
        
        for i, batch in enumerate(batches):
            max_retries = 5  # Increased retries for rate limit issues
            base_retry_delay = 5  # Base delay in seconds (increased)
            
            for attempt in range(max_retries):
                try:
                    self.index.upsert_records(namespace=namespace, records=batch)
                    
                    # Calculate estimated tokens for this batch
                    batch_tokens = sum(int(len(r.get('text', '')) * 1.5) for r in batch)
                    print(f"Uploaded batch {i+1}/{len(batches)} ({len(batch)} records, ~{batch_tokens} tokens)")
                    
                    # Add delay between batches to avoid rate limiting
                    # Use longer delay to respect 250k tokens/min limit
                    if i < len(batches) - 1:  # Don't delay after last batch
                        # Calculate delay based on tokens used
                        # Target: stay under 250k tokens/min = ~4166 tokens/sec
                        # Add buffer: use ~3000 tokens/sec max
                        tokens_per_second = 3000
                        calculated_delay = max(DELAY_BETWEEN_BATCHES, batch_tokens / tokens_per_second)
                        # Add small random jitter to avoid thundering herd
                        jitter = random.uniform(0.1, 0.5)
                        delay = calculated_delay + jitter
                        print(f"  Waiting {delay:.2f}s before next batch (rate limiting)...")
                        time.sleep(delay)
                    break
                    
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'rate limit' in error_str.lower():
                        if attempt < max_retries - 1:
                            # Exponential backoff with jitter
                            # Formula: base_delay * (2^attempt) + random_jitter
                            exponential_delay = base_retry_delay * (2 ** attempt)
                            jitter = random.uniform(1, 3)  # Random jitter 1-3 seconds
                            wait_time = exponential_delay + jitter
                            
                            # Cap maximum wait time at 60 seconds
                            wait_time = min(wait_time, 60)
                            
                            print(f"Rate limit hit (batch {i+1}/{len(batches)}), waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}...")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(
                                f"Rate limit exceeded after {max_retries} retries. "
                                f"Pinecone limit: 250,000 tokens/minute. "
                                f"Please wait a few minutes and try again, or upload smaller files."
                            )
                    else:
                        # For non-rate-limit errors, retry with shorter delay
                        if attempt < max_retries - 1:
                            wait_time = 2 * (attempt + 1)  # Linear backoff for other errors
                            print(f"Error uploading batch {i+1}/{len(batches)}, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"Failed to upload batch {i+1}/{len(batches)}: {str(e)}")
        
        # Track chunk IDs for this document
        if document_id not in self._document_chunks:
            self._document_chunks[document_id] = []
        self._document_chunks[document_id].extend(chunk_ids)
        
        return chunk_ids
    
    def similarity_search(
        self,
        query: str,
        k: int = None,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[Document]:
        """
        Perform similarity search using hosted embedding model.
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            namespace: Optional namespace (default: empty string for default namespace)
            
        Returns:
            List of Document objects
        """
        k = k or settings.TOP_K_RESULTS
        
        # Build search query
        search_params = {
            "inputs": {"text": query},
            "top_k": k
        }
        
        if filter:
            search_params["filter"] = filter
        
        # Perform search - namespace is required, use "__default__" for default namespace
        namespace = namespace if namespace is not None else "__default__"
        results = self.index.search(namespace=namespace, query=search_params)
        
        # Convert results to Document objects
        documents = []
        # Handle different Pinecone response formats
        matches = None
        if results:
            # Check if results can be accessed as dict (SearchRecordsResponse)
            try:
                if hasattr(results, 'result'):
                    result = results.result
                    if isinstance(result, dict) and 'hits' in result:
                        matches = result['hits']
                    elif hasattr(result, 'hits'):
                        matches = result.hits
            except:
                pass
            
            # Check for dictionary format (Pinecone hosted embedding returns dict)
            if not matches and isinstance(results, dict):
                if 'result' in results and isinstance(results['result'], dict):
                    hits = results['result'].get('hits', [])
                    if hits:
                        matches = hits
                elif 'hits' in results:
                    matches = results['hits']
                elif 'matches' in results:
                    matches = results['matches']
            
            # Check for standard format (results.matches)
            if not matches and hasattr(results, 'matches') and results.matches:
                matches = results.matches
            
            # Check for alternative format (results.result.hits)
            if not matches and hasattr(results, 'result'):
                result = results.result
                if isinstance(result, dict):
                    hits = result.get('hits', [])
                    if hits:
                        matches = hits
                elif hasattr(result, 'hits'):
                    matches = result.hits
        
        if matches:
            for match in matches:
                # Extract match ID - handle different formats
                match_id = None
                if isinstance(match, dict):
                    match_id = match.get('_id') or match.get('id')
                else:
                    match_id = getattr(match, 'id', None) or getattr(match, '_id', None)
                
                # Extract text and metadata fields - handle different formats
                # According to Pinecone docs, additional fields are returned directly in the match object
                text = ''
                filename_from_record = None
                document_id_from_record = None
                file_type_from_record = None
                
                if isinstance(match, dict):
                    # Format: {'_id': '...', 'text': '...', 'filename': '...', 'document_id': '...', ...}
                    # Text field
                    text = match.get('text', '')
                    if not text and 'fields' in match:
                        fields = match['fields']
                        if isinstance(fields, dict):
                            text = fields.get('text', '')
                        elif hasattr(fields, 'text'):
                            text = fields.text
                    if not text and 'metadata' in match and isinstance(match['metadata'], dict):
                        text = match['metadata'].get('text', '')
                    
                    # Metadata fields directly from record (as per Pinecone docs)
                    filename_from_record = match.get('filename')
                    document_id_from_record = match.get('document_id')
                    file_type_from_record = match.get('file_type')
                    
                else:
                    # Object format
                    text = getattr(match, 'text', None) or ''
                    if not text and hasattr(match, 'fields'):
                        fields = match.fields
                        if isinstance(fields, dict):
                            text = fields.get('text', '')
                        elif hasattr(fields, 'text'):
                            text = fields.text
                    if not text and hasattr(match, 'metadata') and isinstance(match.metadata, dict):
                        text = match.metadata.get('text', '')
                    
                    # Metadata fields from object
                    filename_from_record = getattr(match, 'filename', None)
                    document_id_from_record = getattr(match, 'document_id', None)
                    file_type_from_record = getattr(match, 'file_type', None)
                
                # Get metadata - prioritize fields from Pinecone record, then local storage
                metadata = {}
                
                # First, use metadata fields directly from Pinecone record (most reliable)
                # These fields are stored as metadata in Pinecone and returned in search results
                if filename_from_record:
                    metadata['filename'] = filename_from_record
                if document_id_from_record:
                    metadata['document_id'] = document_id_from_record
                if file_type_from_record:
                    metadata['file_type'] = file_type_from_record
                
                # Get additional metadata from local storage
                if match_id:
                    local_metadata = self._chunk_metadata.get(match_id, {}).copy()
                    # Merge local metadata, but don't override Pinecone fields
                    for key, value in local_metadata.items():
                        if key not in metadata or not metadata[key]:
                            metadata[key] = value
                    if text and not metadata.get('text'):
                        metadata['text'] = text
                
                # If still no text, try to fetch from local storage
                if not text and match_id:
                    if not metadata:
                        metadata = self._chunk_metadata.get(match_id, {}).copy()
                    text = metadata.get('text', '')
                
                # Extract document_id from match if not already set
                if match_id and not metadata.get('document_id'):
                    # Try to extract from chunk ID pattern: {doc_id}_chunk_{i}
                    if '_chunk_' in str(match_id):
                        metadata['document_id'] = str(match_id).split('_chunk_')[0]
                
                # Fallback: Try to get filename from document registry if not in metadata
                if not metadata.get('filename') and metadata.get('document_id'):
                    from app.services.document_registry import document_registry
                    doc_data = document_registry.get(metadata['document_id'])
                    if doc_data:
                        metadata['filename'] = doc_data.get('filename', 'Unknown')
                        if not metadata.get('file_type'):
                            metadata['file_type'] = doc_data.get('file_type', 'unknown')
                
                # Final fallback: Try to get from chunk metadata
                if not metadata.get('filename') and match_id:
                    chunk_meta = self._chunk_metadata.get(match_id, {})
                    if chunk_meta.get('filename') and chunk_meta.get('filename') != 'unknown':
                        metadata['filename'] = chunk_meta['filename']
                
                # Final fallback
                if not text:
                    text = f"[Document ID: {match_id or 'unknown'}]"
                
                # Ensure metadata has required fields
                if not metadata:
                    metadata = {
                        "document_id": "unknown",
                        "filename": "Unknown",
                        "file_type": "unknown",
                        "upload_date": "",
                    }
                elif not metadata.get('filename') or metadata.get('filename') == 'unknown':
                    metadata['filename'] = 'Unknown'
                elif not metadata.get('filename'):
                    metadata['filename'] = 'Unknown'
                
                doc = Document(
                    page_content=text,
                    metadata=metadata
                )
                documents.append(doc)
        
        return documents
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = None,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            namespace: Optional namespace (default: empty string for default namespace)
            
        Returns:
            List of tuples (Document, score)
        """
        k = k or settings.TOP_K_RESULTS
        
        # Build search query
        search_params = {
            "inputs": {"text": query},
            "top_k": k
        }
        
        if filter:
            search_params["filter"] = filter
        
        # Perform search - namespace is required, use "__default__" for default namespace
        namespace = namespace if namespace is not None else "__default__"
        results = self.index.search(namespace=namespace, query=search_params)
        
        # Convert results to Document objects with scores
        documents_with_scores = []
        if results and hasattr(results, 'matches') and results.matches:
            for match in results.matches:
                score = getattr(match, 'score', 0.0)
                match_id = getattr(match, 'id', '')
                
                # Get metadata from our local storage
                metadata = self._chunk_metadata.get(match_id, {})
                
                # Get text from our local storage or try to fetch from Pinecone
                text = metadata.get('text', '')
                
                # If not in local storage, try to fetch from Pinecone
                if not text:
                    try:
                        fetch_result = self.index.fetch(ids=[match_id], namespace=namespace)
                        if fetch_result and hasattr(fetch_result, 'vectors') and match_id in fetch_result.vectors:
                            record = fetch_result.vectors[match_id]
                            if hasattr(record, 'text'):
                                text = record.text
                    except Exception:
                        pass
                
                # Fallback if we still don't have text
                if not text:
                    text = f"[Document ID: {match_id}]"
                
                # Ensure metadata has required fields
                if not metadata:
                    metadata = {
                        "document_id": "unknown",
                        "filename": "Unknown",
                        "file_type": "unknown",
                        "upload_date": "",
                    }
                
                doc = Document(
                    page_content=text,
                    metadata=metadata
                )
                documents_with_scores.append((doc, score))
        
        return documents_with_scores
    
    def delete_documents(self, document_id: str, namespace: Optional[str] = None):
        """
        Delete all documents with the given document_id.
        
        Args:
            document_id: Document identifier
            namespace: Optional namespace
        """
        namespace = namespace if namespace is not None else "__default__"
        
        # Collect all chunk IDs from multiple sources
        chunk_ids = set()
        
        # 1. Get from tracked chunks
        tracked_chunks = self._document_chunks.get(document_id, [])
        chunk_ids.update(tracked_chunks)
        
        # 2. Find chunks by searching metadata
        for chunk_id, metadata in list(self._chunk_metadata.items()):
            if metadata.get('document_id') == document_id:
                chunk_ids.add(chunk_id)
        
        # 3. Find chunks by ID pattern
        for chunk_id in list(self._chunk_metadata.keys()):
            if str(chunk_id).startswith(f"{document_id}_chunk_"):
                chunk_ids.add(chunk_id)
        
        # Convert to list for deletion
        chunk_ids = list(chunk_ids)
        
        # Delete by IDs
        if chunk_ids:
            try:
                # Pinecone delete supports batch deletion
                # Delete in batches if there are many chunks
                BATCH_SIZE = 1000  # Pinecone can handle large batches
                for i in range(0, len(chunk_ids), BATCH_SIZE):
                    batch = chunk_ids[i:i + BATCH_SIZE]
                    self.index.delete(ids=batch, namespace=namespace)
                    print(f"Deleted batch {i//BATCH_SIZE + 1} ({len(batch)} chunks)")
                
                # Remove from tracking and metadata storage
                if document_id in self._document_chunks:
                    del self._document_chunks[document_id]
                
                # Remove chunk metadata
                for chunk_id in chunk_ids:
                    if chunk_id in self._chunk_metadata:
                        del self._chunk_metadata[chunk_id]
                
                print(f"Successfully deleted {len(chunk_ids)} chunks for document_id: {document_id}")
            except Exception as e:
                error_msg = f"Failed to delete documents from Pinecone: {str(e)}"
                print(f"Error: {error_msg}")
                # Still try to clean up local tracking even if Pinecone deletion fails
                if document_id in self._document_chunks:
                    del self._document_chunks[document_id]
                for chunk_id in chunk_ids:
                    if chunk_id in self._chunk_metadata:
                        del self._chunk_metadata[chunk_id]
                raise Exception(error_msg)
        else:
            # If no chunks found in local tracking, try alternative methods
            # This handles cases where tracking was lost (e.g., after service restart)
            print(f"Warning: No chunks found in local tracking for document_id {document_id}")
            print("Attempting to find chunks using alternative methods...")
            
            # Method 1: Try to find chunks by searching Pinecone with a meaningful query
            # This is a fallback when local tracking is lost
            found_chunk_ids = []
            
            try:
                # Search with a meaningful query to get some results
                # Use a common word that's likely to appear in documents
                # Avoid empty or whitespace-only queries which cause embedding errors
                search_params = {
                    'inputs': {'text': 'the'},  # Common word query (not empty)
                    'top_k': 1000  # Get many results to find matching chunks
                }
                results = self.index.search(namespace=namespace, query=search_params)
                
                # Extract chunk IDs that match our document_id pattern
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
                            else:
                                chunk_id = getattr(match, 'id', None) or getattr(match, '_id', None)
                            
                            if chunk_id and str(chunk_id).startswith(f"{document_id}_chunk_"):
                                found_chunk_ids.append(chunk_id)
                
                if found_chunk_ids:
                    print(f"Found {len(found_chunk_ids)} chunks in Pinecone for document_id: {document_id}")
            except Exception as search_error:
                # If search fails (e.g., empty index, embedding error), skip this method
                print(f"Note: Could not search Pinecone for chunks: {search_error}")
                # Don't fail here, try other methods or just clean up local tracking
            
            # Method 2: Try to find chunks by checking all metadata entries
            # This is more reliable when we have local metadata
            if not found_chunk_ids:
                for chunk_id, metadata in list(self._chunk_metadata.items()):
                    if metadata.get('document_id') == document_id:
                        found_chunk_ids.append(chunk_id)
                
                if found_chunk_ids:
                    print(f"Found {len(found_chunk_ids)} chunks in local metadata for document_id: {document_id}")
            
            # Delete found chunks
            if found_chunk_ids:
                BATCH_SIZE = 1000
                total_deleted = 0
                for i in range(0, len(found_chunk_ids), BATCH_SIZE):
                    batch = found_chunk_ids[i:i + BATCH_SIZE]
                    try:
                        self.index.delete(ids=batch, namespace=namespace)
                        total_deleted += len(batch)
                        print(f"Deleted batch {i//BATCH_SIZE + 1} ({len(batch)} chunks)")
                    except Exception as batch_error:
                        print(f"Error deleting batch {i//BATCH_SIZE + 1}: {batch_error}")
                        # Continue with next batch even if one fails
                
                # Clean up local tracking
                if document_id in self._document_chunks:
                    del self._document_chunks[document_id]
                
                for chunk_id in found_chunk_ids:
                    if chunk_id in self._chunk_metadata:
                        del self._chunk_metadata[chunk_id]
                
                print(f"Successfully deleted {total_deleted} chunks for document_id: {document_id}")
            else:
                print(f"No chunks found for document_id: {document_id}")
                # Still clean up local tracking if document_id exists
                if document_id in self._document_chunks:
                    del self._document_chunks[document_id]
                # Don't raise error - document may already be deleted or never existed
                print(f"Document {document_id} appears to be already deleted or never existed")
                # Return silently - this is not necessarily an error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        stats = self.index.describe_index_stats()
        return {
            "total_vectors": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 0),
            "index_fullness": stats.get("index_fullness", 0),
        }
    
    # Compatibility method for LangChain retriever
    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        """Create a retriever compatible with LangChain."""
        from app.rag.retriever import PineconeRetriever
        return PineconeRetriever(
            vectorstore=self,
            search_kwargs=search_kwargs or {}
        )


# Global vector store manager instance
vectorstore_manager = VectorStoreManager()

