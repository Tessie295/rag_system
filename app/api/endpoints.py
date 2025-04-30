"""
API endpoints for the Shakers AI Support System.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import asyncio
import traceback
from starlette.concurrency import run_in_threadpool

from app.models.schemas import (
    QueryRequest, 
    QueryResponse, 
    RAGResponse, 
    Recommendation,
    PerformanceMetrics,
    UserProfile,
    Document
)
from app.services.rag import RAGService
from app.services.enhanced_recommendations import EnhancedRecommendationService
from app.utils.helpers import logger, time_function, cache_result
from app.utils.search import SearchEngine
from app.utils.evaluation import evaluate_recommendation_quality
from app.config import settings

router = APIRouter()

# Create service instances here instead of importing from main
rag_service = RAGService()
recommendation_service = EnhancedRecommendationService()
search_engine = SearchEngine()

# Cache for frequently requested endpoints
response_cache = {}

async def get_rag_service() -> RAGService:
    """Dependency to get the RAG service."""
    if not rag_service.initialized:
        # Don't block the request with initialization
        # Instead, start initialization in background if not already running
        if not getattr(rag_service, '_initializing', False):
            rag_service._initializing = True
            asyncio.create_task(rag_service.initialize())
    return rag_service

async def get_recommendation_service() -> EnhancedRecommendationService:
    """Dependency to get the recommendation service."""
    if not recommendation_service.initialized:
        # Only initialize if RAG service is ready
        if rag_service.initialized:
            if not getattr(recommendation_service, '_initializing', False):
                recommendation_service._initializing = True
                asyncio.create_task(recommendation_service.initialize(rag_service.documents))
    return recommendation_service

async def get_search_engine() -> SearchEngine:
    """Dependency to get the search engine."""
    # Use the locally created search_engine instance
    if search_engine.document_vectors is None:
        # Initialize search engine if RAG service is ready
        if rag_service.initialized:
            search_engine.initialize(rag_service.documents)
    return search_engine

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    rag_svc: RAGService = Depends(get_rag_service),
    recommendation_svc: EnhancedRecommendationService = Depends(get_recommendation_service)
):
    """Process a user query with optimized performance."""
    start_time = time.time()
    
    # Check if services are initialized
    if not rag_svc.initialized:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Service is initializing. Please try again in a few seconds.",
                "status": "initializing"
            }
        )
    
    try:
        # Set a timeout for the entire process
        if settings.ENABLE_RESPONSE_TIMEOUT:
            timeout = settings.RESPONSE_TIMEOUT
        else:
            timeout = None
            
        # Process query with enhanced RAG system
        try:
            # First, check if it's a talent search query
            intent = search_engine.analyze_intent(request.query)
            
            # Process with RAG
            response, processing_time = await asyncio.wait_for(
                rag_svc.process_query(
                    request.query, 
                    user_id=request.user_id
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # If we timeout, create a basic response
            logger.warning(f"Query processing timed out after {timeout}s: {request.query}")
            response = RAGResponse(
                query=request.query,
                answer="I'm sorry, but it's taking longer than expected to process your query. Could you try asking a more specific question about Shakers?",
                sources=[],
                processing_time=timeout,
                query_type="timeout"
            )
            processing_time = timeout
        
        # Extract source document IDs
        source_ids = [source.document_id for source in response.sources]
        
        # Save chat history in background so it doesn't delay response
        background_tasks.add_task(
            recommendation_svc.add_chat_to_user_history,
            user_id=request.user_id,
            user_message=request.query,
            assistant_message=response.answer,
            sources_used=source_ids
        )
        
        # Generate recommendations
        logger.info("Generating recommendations")
        recommendations = await recommendation_svc.generate_recommendations(
            request.user_id, request.query
        )
        
        logger.info(f"Got {len(recommendations)} recommendations")
        
        # Mark documents as viewed in background
        background_tasks.add_task(
            _mark_documents_as_viewed,
            request.user_id,
            source_ids
        )
        
        # Create the full response
        response_obj = QueryResponse(
            answer=response.answer,
            sources=response.sources,
            recommendations=recommendations,
            processing_time=processing_time,
            evaluation=response.evaluation
        )
        
        # Log total response time
        total_time = time.time() - start_time
        logger.info(f"Total query response time: {total_time:.4f}s")
        
        return response_obj
    
    except Exception as e:
        # Log the error
        logger.error(f"Error processing query: {e}")
        logger.error(traceback.format_exc())
        
        # If error occurs after certain time, return a partial response instead of error
        elapsed_time = time.time() - start_time
        if elapsed_time > 2.0:  # We've already invested significant time
            # Create a fallback response
            return QueryResponse(
                answer="I apologize, but I encountered an issue while processing your query. I understand you're asking about Shakers. Could you try rephrasing your question?",
                sources=[],
                recommendations=[],
                processing_time=elapsed_time,
                evaluation=None
            )
        else:
            # For quick failures, return proper error
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while processing your query: {str(e)}"
            )

async def _mark_documents_as_viewed(user_id: str, document_ids: List[str]):
    """Background task to mark documents as viewed."""
    for doc_id in document_ids:
        try:
            await recommendation_service.mark_document_as_viewed(user_id, doc_id)
        except Exception as e:
            logger.error(f"Error marking document {doc_id} as viewed: {e}")

@router.get("/health")
@cache_result(ttl_seconds=5)  # Cache for 5 seconds to prevent overload
async def health_check():
    """Enhanced health check endpoint with system metrics."""
    # Basic health status
    health_data = {
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "response_time_target": f"{settings.MAX_RESPONSE_TIME}s"
    }
    
    # Add initialization status
    health_data["rag_status"] = "online" if rag_service.initialized else "initializing"
    health_data["recommendation_status"] = "online" if recommendation_service.initialized else "initializing"
    health_data["search_status"] = "online" if search_engine.document_vectors is not None else "initializing"
    
    # Only add metrics if services are initialized
    if rag_service.initialized:
        try:
            # Get last few processing times for monitoring
            rag_metrics = await rag_service.get_performance_metrics()
            
            health_data["metrics"] = {
                "total_queries": rag_metrics["total_queries"],
                "answered_ratio": rag_metrics["answered_ratio"],
                "avg_processing_time": rag_metrics["avg_processing_time"],
                "recent_processing_times": rag_metrics["processing_times"][-5:] if "processing_times" in rag_metrics else []
            }
        except Exception as e:
            logger.error(f"Error getting metrics for health check: {e}")
            health_data["metrics_error"] = str(e)
    
    return health_data

@router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """Get detailed performance metrics for monitoring."""
    if not rag_service.initialized or not recommendation_service.initialized:
        raise HTTPException(
            status_code=503,
            detail="Services are still initializing, metrics not available yet"
        )
    
    try:
        rag_metrics = await rag_service.get_performance_metrics()
        rec_metrics = await recommendation_service.get_performance_metrics()
        
        # Get basic system info
        system_health = {
            "uptime": "unknown",  # Would be populated in a real system
            "memory_usage": "unknown",
            "documents_loaded": len(rag_service.documents),
            "last_knowledge_base_update": rag_service.last_update_timestamp,
            "api_status": "online"
        }
        
        # Get user metrics
        user_metrics = {
            "total_users": len(recommendation_service.users),
            "active_users_24h": 0,  # Would be calculated in a real system
            "avg_queries_per_user": (rag_metrics["total_queries"] / 
                                    max(1, len(recommendation_service.users))),
            "user_satisfaction": rec_metrics.get("user_satisfaction", {})
        }
        
        return PerformanceMetrics(
            rag_metrics=rag_metrics,
            recommendation_metrics=rec_metrics,
            user_metrics=user_metrics,
            system_health=system_health
        )
    
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )

@router.post("/knowledge-base/update")
async def update_knowledge_base():
    """Update the knowledge base with new documents."""
    if not rag_service.initialized:
        # Start initialization if not already running
        if not getattr(rag_service, '_initializing', False):
            rag_service._initializing = True
            asyncio.create_task(rag_service.initialize())
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted", 
                "message": "RAG service is initializing. Update will be performed after initialization completes."
            }
        )
    
    try:
        # Run in background to avoid blocking
        background_task = asyncio.create_task(rag_service.update_knowledge_base())
        
        # Set a timeout for the operation
        try:
            updated = await asyncio.wait_for(background_task, timeout=5.0)
            
            if updated:
                # Schedule recommendation service reinitialization
                asyncio.create_task(recommendation_service.initialize(rag_service.documents))
                return {"status": "success", "message": "Knowledge base updated successfully"}
            else:
                return {"status": "success", "message": "No new documents found to update"}
                
        except asyncio.TimeoutError:
            # Operation is taking too long, continue in background
            return JSONResponse(
                status_code=202,
                content={
                    "status": "accepted", 
                    "message": "Update is taking longer than expected and will continue in the background"
                }
            )
    
    except Exception as e:
        logger.error(f"Error updating knowledge base: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update knowledge base: {str(e)}"
        )

@router.get("/documents", response_model=List[Document])
@cache_result(ttl_seconds=60)  # Cache for 60 seconds
async def get_documents(
    category: Optional[str] = Query(None, description="Filter by document category"),
    tag: Optional[str] = Query(None, description="Filter by document tag")
):
    """Get available documents with optional filtering and caching."""
    if not rag_service.initialized:
        raise HTTPException(
            status_code=503,
            detail="RAG service is initializing. Please try again in a few seconds."
        )
    
    documents = rag_service.documents
    
    # Apply filters if provided
    if category:
        documents = [doc for doc in documents if doc.category == category]
    
    if tag:
        documents = [doc for doc in documents if tag in doc.tags]
    
    return documents

@router.get("/user/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Get a user's profile and recommendations."""
    if not recommendation_service.initialized:
        raise HTTPException(
            status_code=503,
            detail="Recommendation service is initializing. Please try again in a few seconds."
        )
    
    user = recommendation_service.users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    
    return user

@router.post("/documents/{document_id}/view")
async def mark_document_viewed(
    document_id: str,
    request: Dict[str, Any]
):
    """Mark a document as viewed by a user."""
    if not recommendation_service.initialized:
        raise HTTPException(
            status_code=503,
            detail="Recommendation service is initializing. Please try again in a few seconds."
        )
    
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID is required"
        )
    
    # Check if document exists
    doc = next((doc for doc in rag_service.documents if doc.id == document_id), None)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID {document_id} not found"
        )
    
    await recommendation_service.mark_document_as_viewed(user_id, document_id)
    
    return {"status": "success", "message": f"Document {document_id} marked as viewed by user {user_id}"}

@router.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Maximum number of results")
):
    """Search documents using the search engine."""
    if search_engine.document_vectors is None:
        raise HTTPException(
            status_code=503,
            detail="Search engine is initializing. Please try again in a few seconds."
        )
    
    # Analyze intent
    intent = search_engine.analyze_intent(q)
    
    if intent["is_talent_search"]:
        # This is a talent search query
        results = search_engine.search_talent(q, limit=limit)
    else:
        # General search query
        results = search_engine.search(q, limit=limit)
    
    # Format results
    formatted_results = [
        {
            "document_id": doc.id,
            "title": doc.title,
            "path": doc.path,
            "relevance": float(score),
            "category": getattr(doc, "category", None),
            "tags": getattr(doc, "tags", [])
        }
        for doc, score in results
    ]
    
    return {
        "query": q,
        "intent": intent,
        "total_results": len(formatted_results),
        "results": formatted_results
    }

@router.post("/evaluate/recommendations")
async def evaluate_recommendations(
    request: Dict[str, Any]
):
    """Evaluate the quality of recommendations."""
    query = request.get("query")
    recommendations = request.get("recommendations", [])
    user_history = request.get("user_history", [])
    
    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query is required"
        )
    
    if not recommendations:
        return {
            "status": "warning",
            "message": "No recommendations to evaluate",
            "metrics": {
                "relevance_score": 0.0,
                "diversity_score": 0.0,
                "overall_score": 0.0
            }
        }
    
    try:
        evaluation = await evaluate_recommendation_quality(query, recommendations, user_history)
        
        return {
            "status": "success",
            "message": "Recommendations evaluated successfully",
            "metrics": evaluation
        }
    except Exception as e:
        logger.error(f"Error evaluating recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate recommendations: {str(e)}"
        )