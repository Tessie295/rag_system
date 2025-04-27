from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Query(BaseModel):
    """User query model."""
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str

class Document(BaseModel):
    """Knowledge base document model."""
    id: str
    title: str
    content: str
    path: str
    metadata: Dict[str, Any] = {}

class Source(BaseModel):
    """Source reference for responses."""
    document_id: str
    title: str
    path: str
    relevance_score: float
    
class RAGResponse(BaseModel):
    """Response from the RAG system."""
    query: str
    answer: str
    sources: List[Source]
    processing_time: float  # in seconds

class Recommendation(BaseModel):
    """Recommendation model."""
    document_id: str
    title: str
    path: str
    explanation: str
    relevance_score: float

class ChatMessage(BaseModel):
    user_message: str
    assistant_message: str
    timestamp: Optional[datetime] = None

class UserProfile(BaseModel):
    user_id: str
    viewed_documents: List[str] = [] # List of document IDs
    chat_history: List[ChatMessage] = []

class QueryRequest(BaseModel):
    """Query request from the API."""
    query: str
    user_id: str

class QueryResponse(BaseModel):
    """Full response to a user query."""
    answer: str
    sources: List[Source]
    recommendations: List[Recommendation]
    processing_time: float