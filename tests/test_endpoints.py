"""
Test module for API endpoints to improve coverage.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, create_autospec
import json

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import bare minimum dependencies for patching
from app.api.endpoints import (
    router,
    process_query,
    health_check,
    get_performance_metrics,
    update_knowledge_base,
    get_documents,
    get_user_profile,
    mark_document_viewed,
    search_documents,
    evaluate_recommendations,
    _mark_documents_as_viewed,
)

# Manual dependency tests
from app.api.endpoints import (
    get_rag_service,
    get_recommendation_service,
    get_search_engine,
)

from app.models.schemas import (
    Document,
    UserProfile,
    Recommendation,
    Source,
    RAGResponse,
    QueryEvaluation,
)


class TestEndpoints:
    """Tests for the API endpoints."""

    @pytest.mark.asyncio
    async def test_process_query(self):
        """Test the process_query function directly."""
        # Create mock objects
        mock_rag_service = AsyncMock()
        mock_recommendation_service = AsyncMock()

        # Configure mock RAG service response
        mock_rag_response = MagicMock(spec=RAGResponse)
        mock_rag_response.answer = "Test answer"
        mock_rag_response.sources = [
            Source(
                document_id="doc1",
                title="Test Doc",
                path="/test/path",
                relevance_score=0.8,
            )
        ]
        mock_rag_response.processing_time = 0.5
        mock_rag_response.query_type = "normal"
        mock_rag_response.evaluation = None

        mock_rag_service.process_query.return_value = (mock_rag_response, 0.5)
        mock_rag_service.initialized = True

        # Configure mock recommendations
        mock_recommendation_service.initialized = True
        mock_recommendation_service.generate_recommendations.return_value = [
            {
                "document_id": "rec1",
                "title": "Recommended Doc 1",
                "path": "/rec/path1",
                "explanation": "This is relevant to your query",
                "relevance_score": 0.9,
                "tags": ["recommended", "relevant"],
            }
        ]

        # Create mock request and background tasks
        mock_request = MagicMock()
        mock_request.query = "How do payments work?"
        mock_request.user_id = "user1"
        mock_request.context = {}

        mock_bg_tasks = MagicMock()

        # Replace the dependency injection functions
        with patch(
            "app.api.endpoints.get_rag_service", return_value=mock_rag_service
        ), patch(
            "app.api.endpoints.get_recommendation_service",
            return_value=mock_recommendation_service,
        ):

            # Call the function directly
            response = await process_query(mock_request, mock_bg_tasks)

            # Check the response
            assert response.answer == "Test answer"
            assert len(response.sources) == 1
            assert len(response.recommendations) > 0

            # Verify that the services were called
            assert mock_rag_service.process_query.called
            assert mock_recommendation_service.generate_recommendations.called
            assert mock_bg_tasks.add_task.called

    @pytest.mark.asyncio
    async def test_process_query_service_not_ready(self):
        """Test the process_query function when services are not ready."""
        # Create mock objects with initialized=False
        mock_rag_service = AsyncMock()
        mock_rag_service.initialized = False

        # Create mock request and background tasks
        mock_request = MagicMock()
        mock_request.query = "Test query"
        mock_request.user_id = "user1"

        mock_bg_tasks = MagicMock()

        # Replace the dependency injection function
        with patch("app.api.endpoints.get_rag_service", return_value=mock_rag_service):
            # Call the function and expect an error response
            with pytest.raises(Exception) as excinfo:
                await process_query(mock_request, mock_bg_tasks)

            # Check that the error message contains 'initializing'
            assert "initializing" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_process_query_error(self):
        """Test the process_query function with an error."""
        # Create mock objects
        mock_rag_service = AsyncMock()
        mock_recommendation_service = AsyncMock()

        # Configure mock to raise an exception
        mock_rag_service.process_query.side_effect = Exception("Test error")
        mock_rag_service.initialized = True
        mock_recommendation_service.initialized = True

        # Create mock request and background tasks
        mock_request = MagicMock()
        mock_request.query = "Test query"
        mock_request.user_id = "user1"
        mock_request.context = {}

        mock_bg_tasks = MagicMock()

        # Replace the dependency injection functions
        with patch(
            "app.api.endpoints.get_rag_service", return_value=mock_rag_service
        ), patch(
            "app.api.endpoints.get_recommendation_service",
            return_value=mock_recommendation_service,
        ):

            # Call the function and expect an error response
            with pytest.raises(Exception) as excinfo:
                await process_query(mock_request, mock_bg_tasks)

            # Check that the error message contains 'error'
            assert "error" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test the health_check function."""
        # Create mock services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.recommendation_service"
        ) as mock_rec, patch("app.api.endpoints.search_engine") as mock_search:

            # Configure mocks
            mock_rag.initialized = True
            mock_rec.initialized = True
            mock_search.document_vectors = MagicMock()

            # Setup performance metrics
            mock_rag.get_performance_metrics = AsyncMock()
            mock_rag.get_performance_metrics.return_value = {
                "total_queries": 10,
                "answered_ratio": 0.9,
                "avg_processing_time": 0.5,
                "processing_times": [0.4, 0.5, 0.6],
            }

            # Call the function
            response = await health_check()

            # Check response structure
            assert "status" in response
            assert response["status"] == "ok"
            assert "rag_status" in response
            assert response["rag_status"] == "online"

            # If metrics are included, check their structure
            if "metrics" in response:
                assert "total_queries" in response["metrics"]
                assert "avg_processing_time" in response["metrics"]

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self):
        """Test health_check when services are not initialized."""
        # Create mock services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.recommendation_service"
        ) as mock_rec, patch("app.api.endpoints.search_engine") as mock_search:

            # Configure mocks as not initialized
            mock_rag.initialized = False
            mock_rec.initialized = False
            mock_search.document_vectors = None

            # Call the function
            response = await health_check()

            # Check response structure
            assert "status" in response
            assert "rag_status" in response
            assert response["rag_status"] == "initializing"

    @pytest.mark.asyncio
    async def test_get_performance_metrics(self):
        """Test the get_performance_metrics function."""
        # Create mock services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.recommendation_service"
        ) as mock_rec:

            # Configure mocks
            mock_rag.initialized = True
            mock_rec.initialized = True

            # Setup metrics
            mock_rag.get_performance_metrics = AsyncMock()
            mock_rag.get_performance_metrics.return_value = {
                "total_queries": 10,
                "answered_ratio": 0.9,
                "avg_processing_time": 0.5,
            }

            mock_rec.get_performance_metrics = AsyncMock()
            mock_rec.get_performance_metrics.return_value = {
                "total_recommendations": 20,
                "user_interactions": 5,
                "interaction_rate": 0.25,
            }

            # Call the function
            response = await get_performance_metrics()

            # Check response structure
            assert "rag_metrics" in response
            assert "recommendation_metrics" in response
            assert "user_metrics" in response
            assert "system_health" in response

    @pytest.mark.asyncio
    async def test_get_performance_metrics_not_initialized(self):
        """Test get_performance_metrics when services are not initialized."""
        # Create mock services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.recommendation_service"
        ) as mock_rec:

            # Configure mocks as not initialized
            mock_rag.initialized = False
            mock_rec.initialized = False

            # Call the function and expect an error
            with pytest.raises(Exception) as excinfo:
                await get_performance_metrics()

            # Check error message
            assert "initializing" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_update_knowledge_base(self):
        """Test the update_knowledge_base function."""
        # Create mock RAG service
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.get_rag_service"
        ) as mock_get_rag:

            # Configure mock
            mock_rag.initialized = True
            mock_rag.update_knowledge_base = AsyncMock()
            mock_rag.update_knowledge_base.return_value = True

            # Set up dependency injection
            mock_get_rag.return_value = mock_rag

            # Call the function
            response = await update_knowledge_base()

            # Check response
            assert "status" in response
            assert response["status"] == "success"
            assert mock_rag.update_knowledge_base.called

    @pytest.mark.asyncio
    async def test_update_knowledge_base_not_initialized(self):
        """Test update_knowledge_base when service is not initialized."""
        # Create mock RAG service
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.get_rag_service"
        ) as mock_get_rag:

            # Configure mock as not initialized
            mock_rag.initialized = False
            mock_rag._initializing = False

            # Set up dependency injection
            mock_get_rag.return_value = mock_rag

            # Call the function
            response = await update_knowledge_base()

            # Check response
            assert "status" in response
            assert response["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_get_documents(self):
        """Test the get_documents function."""
        # Create mock RAG service
        with patch("app.api.endpoints.rag_service") as mock_rag:

            # Configure mock
            mock_rag.initialized = True

            # Create sample documents
            mock_rag.documents = [
                Document(
                    id="doc1",
                    title="Test Doc 1",
                    content="Test content",
                    path="/test/path1",
                    metadata={},
                    category="test",
                    tags=["test", "sample"],
                ),
                Document(
                    id="doc2",
                    title="Test Doc 2",
                    content="More test content",
                    path="/test/path2",
                    metadata={},
                    category="other",
                    tags=["other"],
                ),
            ]

            # Call the function
            response = await get_documents()

            # Check response
            assert len(response) == 2
            assert response[0].id == "doc1"
            assert response[1].id == "doc2"

            # Test with category filter
            response = await get_documents(category="test")

            # Check filtered response
            assert len(response) == 1
            assert response[0].id == "doc1"

            # Test with tag filter
            response = await get_documents(tag="other")

            # Check filtered response
            assert len(response) == 1
            assert response[0].id == "doc2"

    @pytest.mark.asyncio
    async def test_get_documents_not_initialized(self):
        """Test get_documents when service is not initialized."""
        # Create mock RAG service
        with patch("app.api.endpoints.rag_service") as mock_rag:

            # Configure mock as not initialized
            mock_rag.initialized = False

            # Call the function and expect an error
            with pytest.raises(Exception) as excinfo:
                await get_documents()

            # Check error message
            assert "initializing" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_get_user_profile(self):
        """Test the get_user_profile function."""
        # Create mock recommendation service
        with patch("app.api.endpoints.recommendation_service") as mock_rec:

            # Configure mock
            mock_rec.initialized = True

            # Create sample user
            mock_rec.users = {
                "user1": UserProfile(
                    user_id="user1",
                    viewed_documents=["doc1"],
                    chat_history=[],
                    interests=[],
                    last_active=None,
                    preferences={},
                    recent_recommendations=[],
                )
            }

            # Call the function
            response = await get_user_profile("user1")

            # Check response
            assert response.user_id == "user1"
            assert "doc1" in response.viewed_documents

            # Test with non-existent user
            with pytest.raises(Exception) as excinfo:
                await get_user_profile("nonexistent")

            # Check error message
            assert "not found" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_get_user_profile_not_initialized(self):
        """Test get_user_profile when service is not initialized."""
        # Create mock recommendation service
        with patch("app.api.endpoints.recommendation_service") as mock_rec:

            # Configure mock as not initialized
            mock_rec.initialized = False

            # Call the function and expect an error
            with pytest.raises(Exception) as excinfo:
                await get_user_profile("user1")

            # Check error message
            assert "initializing" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_mark_document_viewed(self):
        """Test the mark_document_viewed function."""
        # Create mock services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.recommendation_service"
        ) as mock_rec:

            # Configure mocks
            mock_rag.initialized = True
            mock_rec.initialized = True

            # Create sample document
            mock_rag.documents = [
                Document(
                    id="doc1",
                    title="Test Doc",
                    content="Test content",
                    path="/test/path",
                    metadata={},
                    category="test",
                    tags=["test"],
                )
            ]

            # Mock the mark method
            mock_rec.mark_document_as_viewed = AsyncMock()

            # Call the function
            request = {"user_id": "user1"}
            response = await mark_document_viewed("doc1", request)

            # Check response
            assert "status" in response
            assert response["status"] == "success"
            assert mock_rec.mark_document_as_viewed.called

            # Test with missing user_id
            with pytest.raises(Exception) as excinfo:
                await mark_document_viewed("doc1", {})

            # Check error message
            assert "user id" in str(excinfo.value).lower()

            # Test with non-existent document
            with pytest.raises(Exception) as excinfo:
                await mark_document_viewed("nonexistent", {"user_id": "user1"})

            # Check error message
            assert "not found" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_search_documents(self):
        """Test the search_documents function."""
        # Create mock search engine
        with patch("app.api.endpoints.search_engine") as mock_search:

            # Configure mock
            mock_search.document_vectors = MagicMock()

            # Mock search methods
            mock_search.analyze_intent = MagicMock()
            mock_search.analyze_intent.return_value = {
                "is_talent_search": False,
                "skills_mentioned": [],
                "enhanced_query": "test query",
            }

            mock_search.search = MagicMock()
            mock_search.search.return_value = [
                (
                    Document(
                        id="doc1",
                        title="Test Doc",
                        content="Test content",
                        path="/test/path",
                        metadata={},
                        category="test",
                        tags=["test"],
                    ),
                    0.8,
                )
            ]

            # Call the function
            response = await search_documents(q="test query")

            # Check response
            assert "query" in response
            assert "results" in response
            assert len(response["results"]) > 0
            assert mock_search.search.called

            # Test talent search
            mock_search.analyze_intent.return_value = {
                "is_talent_search": True,
                "skills_mentioned": ["react"],
                "enhanced_query": "test query",
            }

            mock_search.search_talent = MagicMock()
            mock_search.search_talent.return_value = [
                (
                    Document(
                        id="talent1",
                        title="Developer Profile",
                        content="React developer",
                        path="/profile/path",
                        metadata={},
                        category="talent",
                        tags=["developer", "react"],
                    ),
                    0.9,
                )
            ]

            response = await search_documents(q="find react developer")

            # Check response
            assert "query" in response
            assert "results" in response
            assert len(response["results"]) > 0
            assert mock_search.search_talent.called

    @pytest.mark.asyncio
    async def test_search_documents_not_initialized(self):
        """Test search_documents when engine is not initialized."""
        # Create mock search engine
        with patch("app.api.endpoints.search_engine") as mock_search:

            # Configure mock as not initialized
            mock_search.document_vectors = None

            # Call the function and expect an error
            with pytest.raises(Exception) as excinfo:
                await search_documents(q="test query")

            # Check error message
            assert "initializing" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_evaluate_recommendations(self):
        """Test the evaluate_recommendations function."""
        # Mock the evaluation function
        with patch(
            "app.api.endpoints.evaluate_recommendation_quality"
        ) as mock_evaluate:

            # Configure mock
            mock_evaluate.return_value = {
                "relevance_score": 0.8,
                "diversity_score": 0.7,
                "overall_score": 0.75,
            }

            # Call the function
            request = {
                "query": "test query",
                "recommendations": [
                    {
                        "document_id": "rec1",
                        "title": "Rec 1",
                        "path": "/path1",
                        "relevance_score": 0.9,
                    }
                ],
            }
            response = await evaluate_recommendations(request)

            # Check response
            assert "status" in response
            assert response["status"] == "success"
            assert "metrics" in response
            assert mock_evaluate.called

            # Test with empty recommendations
            request = {"query": "test query", "recommendations": []}
            response = await evaluate_recommendations(request)

            # Should return warning
            assert response["status"] == "warning"

            # Test with missing query
            with pytest.raises(Exception) as excinfo:
                await evaluate_recommendations({"recommendations": []})

            # Check error message
            assert (
                "required" in str(excinfo.value).lower()
                or "query" in str(excinfo.value).lower()
            )

    @pytest.mark.asyncio
    async def test_mark_documents_as_viewed(self):
        """Test the _mark_documents_as_viewed helper function."""
        # Mock the recommendation service
        with patch("app.api.endpoints.recommendation_service") as mock_rec:

            # Configure mock
            mock_rec.mark_document_as_viewed = AsyncMock()

            # Call the function
            user_id = "user1"
            document_ids = ["doc1", "doc2"]
            await _mark_documents_as_viewed(user_id, document_ids)

            # Check that mark_document_as_viewed was called for each document
            assert mock_rec.mark_document_as_viewed.call_count == 2

            # Test error handling
            mock_rec.mark_document_as_viewed.side_effect = Exception("Test error")

            # Should not raise exception
            await _mark_documents_as_viewed(user_id, document_ids)

    @pytest.mark.asyncio
    async def test_get_rag_service_dependency(self):
        """Test the get_rag_service dependency."""
        # Mock the rag_service
        with patch("app.api.endpoints.rag_service") as mock_rag:

            # Configure mock as initialized
            mock_rag.initialized = True
            mock_rag._initializing = False

            # For creating an async task
            mock_initialize = AsyncMock()
            mock_rag.initialize = mock_initialize

            # Call the dependency function
            result = await get_rag_service()

            # Should return the service
            assert result is mock_rag

            # Should not have called initialize
            assert not mock_initialize.called

            # Test when service is not initialized
            mock_rag.initialized = False
            mock_rag._initializing = False

            # Call the dependency function
            result = await get_rag_service()

            # Should return the service
            assert result is mock_rag

            # Should have created a task to initialize
            # (we can't verify this directly since we're using create_task)

    @pytest.mark.asyncio
    async def test_get_recommendation_service_dependency(self):
        """Test the get_recommendation_service dependency."""
        # Mock the services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.recommendation_service"
        ) as mock_rec:

            # Configure mocks
            mock_rag.initialized = True
            mock_rec.initialized = True
            mock_rec._initializing = False

            # For creating an async task
            mock_initialize = AsyncMock()
            mock_rec.initialize = mock_initialize

            # Call the dependency function
            result = await get_recommendation_service()

            # Should return the service
            assert result is mock_rec

            # Should not have called initialize
            assert not mock_initialize.called

            # Test when service is not initialized but RAG is
            mock_rec.initialized = False
            mock_rec._initializing = False

            # Call the dependency function
            result = await get_recommendation_service()

            # Should return the service
            assert result is mock_rec

            # Should have created a task to initialize
            # (we can't verify this directly since we're using create_task)

    @pytest.mark.asyncio
    async def test_get_search_engine_dependency(self):
        """Test the get_search_engine dependency."""
        # Mock the services
        with patch("app.api.endpoints.rag_service") as mock_rag, patch(
            "app.api.endpoints.search_engine"
        ) as mock_search:

            # Configure mocks
            mock_rag.initialized = True
            mock_search.document_vectors = MagicMock()

            # Call the dependency function
            result = await get_search_engine()

            # Should return the engine
            assert result is mock_search

            # Should not have called initialize
            assert (
                not hasattr(mock_search, "initialize")
                or not mock_search.initialize.called
            )

            # Test when engine is not initialized
            mock_search.document_vectors = None
            mock_search.initialize = MagicMock()

            # Call the dependency function
            result = await get_search_engine()

            # Should return the engine
            assert result is mock_search

            # Should have called initialize
            assert mock_search.initialize.called
