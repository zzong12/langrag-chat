"""RAG chain implementation using LangChain."""
from typing import List, Dict, Any, AsyncGenerator
import re
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.documents import Document
except ImportError:
    from langchain.prompts import ChatPromptTemplate
    from langchain.schema import Document
from langchain_openai import ChatOpenAI

from app.config import settings
from app.rag.vectorstore import vectorstore_manager


class RAGChain:
    """RAG chain for question answering with document retrieval."""
    
    def __init__(self):
        """Initialize RAG chain with LLM and prompt template."""
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE_URL,
            temperature=0.7,
        )
        
        # Custom prompt template for RAG
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant that answers questions based on the provided context documents.

Context information:
{context}

Based on the context above, please answer the following question. If the answer cannot be found in the context, please say so and provide a general answer if possible."""),
            ("human", "{question}")
        ])
        
        # Create retriever
        self.retriever = vectorstore_manager.as_retriever(
            search_kwargs={"k": settings.TOP_K_RESULTS}
        )
    
    def query(
        self,
        question: str,
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Query the RAG chain with a question.
        
        Args:
            question: User question
            return_sources: Whether to return source documents
            
        Returns:
            Dictionary with answer and optionally sources
        """
        # Retrieve relevant documents
        source_docs = self.retriever.invoke(question)
        
        # Combine context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in source_docs])
        
        # Format prompt with context and question
        messages = self.prompt.format_messages(context=context, question=question)
        
        # Generate response
        response = self.llm.invoke(messages)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        result = {
            "answer": answer,
        }
        
        if return_sources:
            sources = self._format_sources(source_docs)
            result["sources"] = sources
        
        return result
    
    async def stream_query(
        self,
        question: str,
        return_sources: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream query results with citations.
        
        Args:
            question: User question
            return_sources: Whether to return source documents
            
        Yields:
            Dictionary chunks with text and citation information
        """
        # Retrieve relevant documents
        source_docs = self.retriever.invoke(question)
        
        # Format sources for citation
        sources = self._format_sources(source_docs) if return_sources else []
        
        # Combine context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in source_docs])
        
        # Format prompt with context and question
        messages = self.prompt.format_messages(context=context, question=question)
        
        # Stream response from LLM
        full_answer = ""
        citation_index = 0
        sentence_buffer = ""
        
        try:
            # Use stream method for ChatOpenAI
            async for chunk in self.llm.astream(messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    full_answer += content
                    sentence_buffer += content
                    
                    # Send text chunk immediately for typing effect
                    yield {
                        "type": "text",
                        "content": content
                    }
                    
                    # Check for sentence endings to insert citations
                    # Only check if we have accumulated some text
                    if len(sentence_buffer) > 10:  # Minimum sentence length
                        sentence_endings = ['.', '。', '!', '?', '！', '？']
                        if any(sentence_buffer.rstrip().endswith(ending) for ending in sentence_endings):
                            # Insert citation after sentence if we have sources
                            if sources and citation_index < len(sources):
                                source = sources[citation_index]
                                yield {
                                    "type": "citation",
                                    "index": citation_index,
                                    "filename": source["filename"],
                                    "document_id": source["document_id"],
                                    "content": source["content"],
                                    "preview": source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                                }
                                citation_index += 1
                            sentence_buffer = ""
        except Exception as e:
            # If astream doesn't work, fall back to regular invoke and simulate streaming
            response = self.llm.invoke(messages)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # Simulate streaming by sending chunks
            words = answer.split(' ')
            for i, word in enumerate(words):
                yield {
                    "type": "text",
                    "content": word + (" " if i < len(words) - 1 else "")
                }
                
                # Insert citations periodically
                if sources and (i + 1) % 10 == 0 and citation_index < len(sources):
                    source = sources[citation_index]
                    yield {
                        "type": "citation",
                        "index": citation_index,
                        "filename": source["filename"],
                        "document_id": source["document_id"],
                        "content": source["content"],
                        "preview": source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                    }
                    citation_index += 1
        
        # Send all remaining sources at the end
        if return_sources and sources:
            for idx in range(citation_index, len(sources)):
                source = sources[idx]
                yield {
                    "type": "citation",
                    "index": idx,
                    "filename": source["filename"],
                    "document_id": source["document_id"],
                    "content": source["content"],
                    "preview": source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                }
    
    def _format_sources(self, source_docs: List[Document]) -> List[Dict[str, Any]]:
        """Format source documents for API response."""
        from app.services.document_registry import document_registry
        
        sources = []
        seen_chunks = set()
        
        for doc in source_docs:
            # Create unique identifier for chunk
            chunk_id = f"{doc.metadata.get('document_id', 'unknown')}_{doc.page_content[:50]}"
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            
            document_id = doc.metadata.get("document_id", "unknown")
            filename = doc.metadata.get("filename", "Unknown")
            
            # Try to get filename from document registry if not in metadata
            if filename == "Unknown" and document_id != "unknown":
                doc_data = document_registry.get(document_id)
                if doc_data:
                    filename = doc_data.get("filename", "Unknown")
                else:
                    # If document_id doesn't match, try to find by checking all documents
                    # This handles cases where document_id format differs (UUID vs hash)
                    # We'll search for documents that might match
                    all_docs = document_registry.get_all()
                    # If there's only one document, use it
                    if len(all_docs) == 1:
                        filename = list(all_docs.values())[0].get("filename", "Unknown")
                    else:
                        # Try to match by checking if document_id appears in any chunk
                        # For now, we'll use a fallback
                        filename = "Unknown"
            
            sources.append({
                "filename": filename,
                "content": doc.page_content,  # Full content for citation details
                "document_id": document_id,
            })
        
        return sources


# Global RAG chain instance
rag_chain = RAGChain()

