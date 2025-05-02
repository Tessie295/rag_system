"""
Main application file for the Shakers AI Support System.
"""

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.helpers import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    # Import here to avoid circular imports
    from app.api.endpoints import rag_service, recommendation_service, search_engine

    # Initialize RAG service
    logger.info("Initializing RAG service...")
    await rag_service.initialize()

    # Initialize recommendation service with documents from RAG service
    logger.info("Initializing recommendation service...")
    await recommendation_service.initialize(rag_service.documents)

    # Initialize search engine
    logger.info("Initializing search engine...")
    search_engine.initialize(rag_service.documents)

    logger.info("All services initialized successfully")

    yield

    # Cleanup on shutdown if needed
    logger.info("Shutting down services...")
    # Any cleanup code would go here


# Create FastAPI app
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router - import here to avoid circular imports
from app.api.endpoints import router as api_router

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    # Import here to avoid circular imports
    from app.api.endpoints import rag_service

    return {
        "message": "Welcome to the Shakers AI Support System",
        "documentation": "/docs",
        "status": "online" if rag_service.initialized else "initializing",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
