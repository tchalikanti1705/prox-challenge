"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str           # "user" or "assistant"
    content: str        # Message text
    image: Optional[str] = None  # Base64 image (legacy single)
    images: Optional[List[str]] = None  # Base64 images (multiple)


class ChatRequest(BaseModel):
    """Chat endpoint request - full conversation history."""
    messages: List[ChatMessage]
    # Latest user message is in messages[-1]


class ChatResponse(BaseModel):
    """Chat endpoint response."""
    role: str
    content: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    knowledge_loaded: bool
    chunks_count: int
    images_count: int
    models: dict = {}


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
