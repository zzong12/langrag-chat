"""Chat API routes."""
import uuid
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncGenerator

from app.models import ChatRequest, ChatResponse, ErrorResponse
from app.rag.chain import rag_chain

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory conversation storage (in production, use a database)
conversations: Dict[str, list] = {}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat request with RAG.
    
    Args:
        request: Chat request with user message
        
    Returns:
        Chat response with assistant answer and sources
    """
    try:
        # Generate or use existing conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Query RAG chain
        result = rag_chain.query(request.message, return_sources=True)
        
        # Store conversation (optional, for history)
        if conversation_id not in conversations:
            conversations[conversation_id] = []
        
        conversations[conversation_id].append({
            "role": "user",
            "content": request.message
        })
        conversations[conversation_id].append({
            "role": "assistant",
            "content": result["answer"]
        })
        
        return ChatResponse(
            response=result["answer"],
            conversation_id=conversation_id,
            sources=result.get("sources", [])
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Handle streaming chat request with RAG.
    
    Args:
        request: Chat request with user message
        
    Returns:
        Streaming response with chunks of text and citations
    """
    async def generate_stream() -> AsyncGenerator[str, None]:
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        try:
            # Store user message
            if conversation_id not in conversations:
                conversations[conversation_id] = []
            conversations[conversation_id].append({
                "role": "user",
                "content": request.message
            })
            
            # Stream response from RAG chain
            full_answer = ""
            async for chunk in rag_chain.stream_query(request.message, return_sources=True):
                # Ensure chunk is properly formatted
                chunk_str = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {chunk_str}\n\n"
                
                if chunk.get("type") == "text":
                    full_answer += chunk.get("content", "")
            
            # Store assistant response
            conversations[conversation_id].append({
                "role": "assistant",
                "content": full_answer
            })
            
            # Send final message with conversation ID
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Stream error: {error_msg}")
            print(traceback.format_exc())
            error_chunk = {
                "type": "error",
                "content": f"Error: {error_msg}"
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    """
    Get conversation history.
    
    Args:
        conversation_id: Conversation identifier
        
    Returns:
        List of messages in the conversation
    """
    if conversation_id not in conversations:
        return {"messages": []}
    
    return {"messages": conversations[conversation_id]}

