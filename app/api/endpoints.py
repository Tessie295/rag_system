from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.models.schemas import QueryRequest, QueryResponse, RAGResponse, Recommendation
from app.services.rag import RAGService
from app.services.recommendations import RecommendationService
from app.utils.helpers import logger

router = APIRouter()

# Create service instances
rag_service = RAGService()
recommendation_service = RecommendationService()  # Fixed: proper initialization

async def get_rag_service() -> RAGService:
    """Dependency to get the RAG service."""
    if not rag_service.initialized:
        await rag_service.initialize()
    return rag_service

async def get_recommendation_service() -> RecommendationService:
    """Dependency to get the recommendation service."""
    if not recommendation_service.initialized:
        await recommendation_service.initialize(rag_service.documents)
    return recommendation_service

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Process a user query and return an answer with recommendations."""
    try:
        # Process query with RAG
        rag_response, processing_time = await rag_service.process_query(request.query)
        
        # Save the chat message with both user query and assistant response
        await recommendation_service.add_chat_to_user_history(
            user_id=request.user_id,
            user_message=request.query,
            assistant_message=rag_response.answer
        )

        # Generate recommendations
        recommendations = await recommendation_service.generate_recommendations(
            request.user_id, request.query
        )
        
        # Mark documents from RAG response as viewed
        for source in rag_response.sources:
            await recommendation_service.mark_document_as_viewed(
                request.user_id, source.document_id
            )
        
        # Create the full response
        response = QueryResponse(
            answer=rag_response.answer,
            sources=rag_response.sources,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your query: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}