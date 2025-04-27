import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.endpoints import router as api_router
from app.services.rag import RAGService
from app.services.recommendations import RecommendationService

# Create RAG and Recommendation services
rag_service = RAGService()
recommendation_service = RecommendationService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    # Initialize RAG service
    await rag_service.initialize()
    
    # Initialize recommendation service with documents from RAG service
    await recommendation_service.initialize(rag_service.documents)
    
    yield
    
    # Cleanup on shutdown if needed
    pass

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to the Shakers AI Support System",
        "documentation": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)