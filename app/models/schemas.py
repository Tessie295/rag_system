from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union, Set
from datetime import datetime

class Query(BaseModel):
    """User query model."""
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str
    detected_language: Optional[str] = None
    detected_intent: Optional[str] = None
    
    class Config:
        orm_mode = True

class Document(BaseModel):
    """Enhanced knowledge base document model."""
    id: str
    title: str
    content: str
    path: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    category: Optional[str] = None
    tags: List[str] = []

class QueryEvaluation(BaseModel):
    """Model for evaluating the quality of responses."""
    correctness_score: float  # 0-1 rating of factual correctness
    relevance_score: float    # 0-1 rating of relevance to query
    completeness_score: float # 0-1 rating of answer completeness
    overall_score: float      # Combined quality score
    feedback: Optional[str] = None
    
class Source(BaseModel):
    """Enhanced source reference for responses."""
    document_id: str
    title: str
    path: str
    relevance_score: float
    snippet: Optional[str] = None  # Short excerpt from document
    
    @validator('relevance_score')
    def check_relevance_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Relevance score must be between 0 and 1')
        return v
        
class RAGResponse(BaseModel):
    """Enhanced response from the RAG system."""
    query: str
    answer: str
    sources: List[Source]
    processing_time: float  # in seconds
    query_type: str = "normal"  # normal, ambiguous, out_of_scope
    evaluation: Optional[QueryEvaluation] = None
    
class UserInterest(BaseModel):
    """Model to track user interests for better recommendations."""
    topic: str
    document_id: str
    category: str
    strength: float = 1.0  # Higher values indicate stronger interest
    first_mentioned: datetime = Field(default_factory=datetime.now)
    last_mentioned: datetime = Field(default_factory=datetime.now)
    
    @validator('strength')
    def check_strength(cls, v):
        if v < 0:
            return 0
        return v
        
class ChatMessage(BaseModel):
    """Enhanced chat message model."""
    user_message: str
    assistant_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    feedback: Optional[str] = None  # User feedback (positive/negative)
    sources_used: List[str] = []  # Document IDs of sources used
    
class Recommendation(BaseModel):
    """Enhanced recommendation model."""
    document_id: str
    title: str
    path: str
    explanation: str
    relevance_score: float
    category: Optional[str] = None
    tags: List[str] = []
    
    @validator('relevance_score')
    def check_relevance_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Relevance score must be between 0 and 1')
        return v
        
class UserProfile(BaseModel):
    """Enhanced user profile model for personalized recommendations."""
    user_id: str
    viewed_documents: List[str] = []  # List of document IDs
    chat_history: List[ChatMessage] = []
    interests: List[UserInterest] = []
    last_active: datetime = Field(default_factory=datetime.now)
    preferences: Dict[str, Any] = {}
    recent_recommendations: List[Recommendation] = []  # Track recently recommended docs
    
class QueryRequest(BaseModel):
    """Enhanced query request from the API."""
    query: str
    user_id: str
    context: Dict[str, Any] = {}  # Additional context for the query
    
class QueryResponse(BaseModel):
    """Enhanced full response to a user query."""
    answer: str
    sources: List[Source]
    recommendations: List[Recommendation]
    processing_time: float
    evaluation: Optional[QueryEvaluation] = None
    
class PerformanceMetrics(BaseModel):
    """Model for system performance tracking."""
    rag_metrics: Dict[str, Any]
    recommendation_metrics: Dict[str, Any]
    user_metrics: Dict[str, Any]
    system_health: Dict[str, Any]