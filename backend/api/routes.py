"""
FastAPI routes for the OmniPro 220 Expert Agent backend.

Endpoints:
- POST /api/chat: Main chat endpoint (streams response via SSE)
- GET /api/images/{image_id}: Serve manual images
- GET /api/health: Health check with knowledge base stats
"""
import json
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from api.models import ChatRequest, HealthResponse
from agent.client import chat
from knowledge.store import store
from config import MODEL

router = APIRouter(prefix="/api")


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint. Streams response via Server-Sent Events (SSE).
    
    Frontend sends full conversation history.
    We extract the last user message and stream Claude's response back.
    """
    messages = request.messages
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    # Convert ChatMessage objects to dicts for the agent
    anthropic_messages = []
    for msg in messages[:-1]:
        anthropic_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    last_msg = messages[-1]
    
    async def generate():
        """Stream response as Server-Sent Events."""
        try:
            chat_generator = chat(
                anthropic_messages,
                last_msg.content,
                last_msg.images or ([last_msg.image] if last_msg.image else None)
            )
            
            async for event_type, data in chat_generator:
                yield f"data: {json.dumps({'type': event_type, 'content': data})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    """
    Serve a manual image by ID.
    
    Returns the image file from the knowledge base.
    """
    try:
        path = store.get_image_path(image_id)
        if not path or not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Image '{image_id}' not found"
            )
        
        return FileResponse(path, media_type="image/png")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving image: {str(e)}"
        )


@router.get("/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint with knowledge base statistics.
    
    Used by frontend to verify backend is running and ready.
    """
    return HealthResponse(
        status="ok",
        knowledge_loaded=store.is_loaded,
        chunks_count=len(store.chunks),
        images_count=len(store.image_catalog),
        models={
            "chat_model": MODEL,
            "embedding_model": "keyword-matching"
        }
    )
