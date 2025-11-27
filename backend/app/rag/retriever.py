"""Pinecone retriever for LangChain compatibility."""
from typing import List, Dict, Any, Optional
try:
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    from pydantic import Field
except ImportError:
    from langchain.schema import Document
    from langchain.schema import BaseRetriever
    from pydantic import Field


class PineconeRetriever(BaseRetriever):
    """Retriever wrapper for Pinecone vector store."""
    
    vectorstore: Any = Field(description="Pinecone vector store manager")
    search_kwargs: Dict[str, Any] = Field(default_factory=dict, description="Search parameters")
    
    class Config:
        from pydantic import ConfigDict
        model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Get relevant documents for a query."""
        k = self.search_kwargs.get("k", 4)
        filter_dict = self.search_kwargs.get("filter")
        namespace = self.search_kwargs.get("namespace")
        
        return self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter_dict,
            namespace=namespace
        )
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version of get relevant documents."""
        return self._get_relevant_documents(query)

