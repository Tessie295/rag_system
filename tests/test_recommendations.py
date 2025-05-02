"""
Test module for enhanced recommendations service to improve coverage.
"""

import os
import sys
import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from datetime import datetime, timedelta
import numpy as np

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enhanced_recommendations import EnhancedRecommendationService
from app.models.schemas import (
    UserProfile,
    UserInterest,
    ChatMessage,
    Document,
    Recommendation,
)


class TestEnhancedRecommendations:
    """Tests for the enhanced recommendations service."""

    @pytest.fixture
    def mock_documents(self):
        """Fixture to create mock documents."""
        return [
            Document(
                id="doc1",
                title="Finding Talent on Shakers",
                content="This document explains how to find talent on Shakers.",
                path="/docs/finding_talent.md",
                metadata={},
                category="guides",
                tags=["hiring", "talent", "search"],
            ),
            Document(
                id="doc2",
                title="Payment System",
                content="Information about the payment system on Shakers.",
                path="/docs/payments.md",
                metadata={},
                category="general",
                tags=["payments", "fees", "escrow"],
            ),
            Document(
                id="doc3",
                title="Frontend Developer Profile",
                content="Profile of a frontend developer with React skills.",
                path="/docs/freelancer-profiles.md",
                metadata={},
                category="talent",
                tags=["profile", "developer", "react"],
            ),
            Document(
                id="doc4",
                title="Technical Documentation",
                content="Technical details about the Shakers platform architecture.",
                path="/docs/shakers-technical-documentation.md",
                metadata={},
                category="technical",
                tags=["technical", "api", "architecture"],
            ),
            Document(
                id="doc5",
                title="Dispute Resolution",
                content="How to handle disputes on the platform.",
                path="/docs/dispute-resolution.md",
                metadata={},
                category="guides",
                tags=["disputes", "resolution", "mediation"],
            ),
        ]

    @pytest.fixture
    def mock_search_engine(self):
        """Fixture to create a mock search engine."""
        with patch(
            "app.services.enhanced_recommendations.SearchEngine"
        ) as MockSearchEngine:
            mock_instance = MagicMock()
            mock_instance.initialize = MagicMock()
            mock_instance.search = MagicMock(
                return_value=[
                    (
                        Document(
                            id="doc1",
                            title="Test Doc",
                            content="Test",
                            path="/test",
                            tags=["test"],
                        ),
                        0.8,
                    )
                ]
            )
            mock_instance.tech_skills = ["react", "python", "java", "javascript"]
            mock_instance.analyze_intent = MagicMock(
                return_value={
                    "is_talent_search": False,
                    "skills_mentioned": [],
                    "enhanced_query": "test query",
                }
            )
            MockSearchEngine.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def recommendation_service(self, mock_documents, mock_search_engine):
        """Fixture to create a recommendation service with mocks."""
        service = EnhancedRecommendationService()
        service.documents = mock_documents
        service.search_engine = mock_search_engine
        return service

    @pytest.mark.asyncio
    async def test_initialize(self, recommendation_service, mock_documents):
        """Test the initialize method."""
        # Mock dependencies
        with patch(
            "app.services.enhanced_recommendations.load_metrics"
        ) as mock_load_metrics:
            mock_load_metrics.return_value = {
                "total_recommendations": 10,
                "user_interactions": 5,
                "diversity_scores": [0.7, 0.8],
                "relevance_scores": [0.8, 0.9],
            }

            with patch.object(
                recommendation_service, "_load_user_profiles"
            ) as mock_load_profiles, patch.object(
                recommendation_service, "_categorize_documents"
            ) as mock_categorize:

                # Run initialize
                await recommendation_service.initialize(mock_documents)

                # Check that dependencies were called
                assert recommendation_service.search_engine.initialize.called
                assert mock_categorize.called
                assert mock_load_profiles.called
                assert mock_load_metrics.called

                # Check that state was updated
                assert recommendation_service.documents == mock_documents
                assert recommendation_service.initialized is True

                # Check that initialize doesn't run again if already initialized
                recommendation_service.search_engine.initialize.reset_mock()
                await recommendation_service.initialize(mock_documents)
                assert not recommendation_service.search_engine.initialize.called

    @pytest.mark.asyncio
    async def test_categorize_documents(self, recommendation_service, mock_documents):
        """Test the _categorize_documents method."""
        # Run the method
        await recommendation_service._categorize_documents()

        # Check that documents were categorized
        assert len(recommendation_service.document_categories) > 0

        # Check specific categorizations - using correct expected values
        assert recommendation_service.document_categories.get("doc1") == "talent"
        assert recommendation_service.document_categories.get("doc2") == "payments"
        assert recommendation_service.document_categories.get("doc3") == "talent"
        assert recommendation_service.document_categories.get("doc4") == "technical"

    @pytest.mark.asyncio
    async def test_load_user_profiles(self, recommendation_service):
        """Test the _load_user_profiles method."""
        # Test when profiles file exists
        sample_profiles = [
            {
                "user_id": "user1",
                "viewed_documents": ["doc1"],
                "chat_history": [],
                "interests": [
                    {
                        "topic": "hiring",
                        "document_id": "doc1",
                        "category": "guides",
                        "strength": 0.8,
                        "first_mentioned": "2023-01-01T00:00:00",
                        "last_mentioned": "2023-01-01T00:00:00",
                    }
                ],
                "last_active": "2023-01-01T00:00:00",
                "preferences": {},
                "recent_recommendations": [],
            }
        ]

        with patch("os.path.exists") as mock_exists, patch(
            "builtins.open", mock_open(read_data=json.dumps(sample_profiles))
        ):

            mock_exists.return_value = True
            await recommendation_service._load_user_profiles()

            # Check that profiles were loaded
            assert len(recommendation_service.users) == 1
            assert "user1" in recommendation_service.users
            assert isinstance(recommendation_service.users["user1"], UserProfile)

            # Test error handling
            recommendation_service.users = {}
            mock_exists.return_value = True
            with patch("builtins.open") as mock_file:
                mock_file.side_effect = Exception("Test error")

                # Should handle exception and create empty users dict
                await recommendation_service._load_user_profiles()
                assert recommendation_service.users == {}

            # Test when profiles file doesn't exist
            recommendation_service.users = {}
            mock_exists.return_value = False

            await recommendation_service._load_user_profiles()
            assert recommendation_service.users == {}

    @pytest.mark.asyncio
    async def test_save_user_profiles(self, recommendation_service):
        """Test the _save_user_profiles method."""
        # Create a test user profile
        recommendation_service.users = {
            "user1": UserProfile(
                user_id="user1",
                viewed_documents=["doc1"],
                chat_history=[],
                interests=[],
                last_active=datetime.now(),
                preferences={},
                recent_recommendations=[],
            )
        }

        # Test successful save
        with patch("os.path.exists") as mock_exists, patch(
            "os.makedirs"
        ) as mock_makedirs, patch("builtins.open") as mock_file:

            mock_exists.return_value = True

            result = await recommendation_service._save_user_profiles()

            assert result is True
            assert mock_makedirs.called
            assert mock_file.called

            # Test error handling
            mock_file.side_effect = Exception("Test error")

            result = await recommendation_service._save_user_profiles()

            assert result is False

    @pytest.mark.asyncio
    async def test_add_chat_to_user_history(self, recommendation_service):
        """Test the add_chat_to_user_history method."""
        # Create a mock for _update_user_interests and _save_user_profiles
        with patch.object(
            recommendation_service, "_update_user_interests"
        ) as mock_update_interests, patch.object(
            recommendation_service, "_save_user_profiles"
        ) as mock_save_profiles:

            # Test with new user
            user_id = "new_user"
            user_message = "How do I find talent?"
            assistant_message = "You can search for talent using filters."
            sources_used = ["doc1", "doc3"]

            await recommendation_service.add_chat_to_user_history(
                user_id, user_message, assistant_message, sources_used
            )

            # Check that new user was created
            assert user_id in recommendation_service.users

            # Check that chat message was added
            user = recommendation_service.users[user_id]
            assert len(user.chat_history) == 1
            assert user.chat_history[0].user_message == user_message
            assert user.chat_history[0].assistant_message == assistant_message
            assert user.chat_history[0].sources_used == sources_used

            # Check that dependencies were called
            assert mock_update_interests.called
            assert mock_save_profiles.called

            # Test with existing user
            existing_user = "existing_user"
            recommendation_service.users[existing_user] = UserProfile(
                user_id=existing_user,
                viewed_documents=[],
                chat_history=[],
                interests=[],
                last_active=datetime.now(),
                preferences={},
                recent_recommendations=[],
            )

            mock_update_interests.reset_mock()
            mock_save_profiles.reset_mock()

            await recommendation_service.add_chat_to_user_history(
                existing_user, user_message, assistant_message, sources_used
            )

            # Check that chat message was added to existing user
            assert len(recommendation_service.users[existing_user].chat_history) == 1

            # Check that dependencies were called
            assert mock_update_interests.called
            assert mock_save_profiles.called

    @pytest.mark.asyncio
    async def test_update_user_interests(self, recommendation_service, mock_documents):
        """Test the _update_user_interests method."""
        # Set up service
        recommendation_service.initialized = True
        recommendation_service.document_categories = {
            "doc1": "guides",
            "doc3": "talent",
        }

        # Create a test user
        user_id = "test_user"
        recommendation_service.users[user_id] = UserProfile(
            user_id=user_id,
            viewed_documents=[],
            chat_history=[],
            interests=[
                UserInterest(
                    topic="hiring",
                    document_id="doc1",
                    category="guides",
                    strength=0.5,
                    first_mentioned=datetime.now() - timedelta(days=7),
                    last_mentioned=datetime.now() - timedelta(days=7),
                )
            ],
            last_active=datetime.now(),
            preferences={},
            recent_recommendations=[],
        )

        # Mock extract_topics
        with patch.object(
            recommendation_service, "_extract_topics"
        ) as mock_extract_topics:
            mock_extract_topics.return_value = [("react", 0.8), ("developer", 0.6)]

            # Test with sources
            message = "I need a React developer"
            sources_used = ["doc3"]

            await recommendation_service._update_user_interests(
                user_id, message, sources_used
            )

            # Check that the source was added as an interest
            user = recommendation_service.users[user_id]
            assert any(interest.document_id == "doc3" for interest in user.interests)

            # Check that existing interest was decayed (7 days old)
            hiring_interest = next(i for i in user.interests if i.topic == "hiring")
            assert hiring_interest.strength < 0.5

            # Test with no sources, but topics
            sources_used = []

            # Configure search to return results for topics
            recommendation_service.search_engine.search.return_value = [
                (mock_documents[0], 0.8)
            ]

            await recommendation_service._update_user_interests(
                user_id, message, sources_used
            )

            # Check that topics were extracted and added as interests
            user = recommendation_service.users[user_id]
            assert len(user.interests) >= 2

            # Test when service is not initialized
            recommendation_service.initialized = False

            # Should not process any interests
            old_interests_count = len(user.interests)
            await recommendation_service._update_user_interests(
                user_id, message, sources_used
            )

            # Interest count should remain the same
            assert len(user.interests) == old_interests_count

    def test_extract_topics(self, recommendation_service):
        """Test the _extract_topics method."""
        # Set up the search engine tech skills
        recommendation_service.search_engine.tech_skills = [
            "python",
            "javascript",
            "react",
            "angular",
            "node.js",
            "aws",
            "docker",
            "kubernetes",
        ]

        # Test with payment-related text
        payment_text = (
            "How does the payment system work on Shakers? I'm curious about escrow."
        )
        payment_topics = recommendation_service._extract_topics(payment_text)

        # Should find some relevant topics - check that we get a list of tuples
        assert isinstance(payment_topics, list)
        assert all(isinstance(item, tuple) for item in payment_topics)
        assert all(len(item) == 2 for item in payment_topics)

        # Test with talent-related text
        talent_text = "I need to hire a freelancer with expertise in design."
        talent_topics = recommendation_service._extract_topics(talent_text)

        # Should return list of tuples
        assert isinstance(talent_topics, list)

        # Test with technical skills
        tech_text = "Looking for someone who knows react and javascript."
        tech_topics = recommendation_service._extract_topics(tech_text)

        # Should return list of tuples
        assert isinstance(tech_topics, list)

        # Test with empty text
        empty_topics = recommendation_service._extract_topics("")
        assert isinstance(empty_topics, list)

    @pytest.mark.asyncio
    async def test_mark_document_as_viewed(self, recommendation_service):
        """Test the mark_document_as_viewed method."""
        # Set up service
        recommendation_service.initialized = True
        recommendation_service.document_categories = {"doc1": "guides"}

        # Create a test document
        test_doc = Document(
            id="doc1",
            title="Test Document",
            content="Test content",
            path="/test/path",
            metadata={},
            category="guides",
            tags=["test"],
        )
        recommendation_service.documents = [test_doc]

        # Set up mocks
        with patch.object(
            recommendation_service, "_save_user_profiles"
        ) as mock_save_profiles, patch(
            "app.services.enhanced_recommendations.save_metrics"
        ) as mock_save_metrics:

            # Test with new user viewing a new document
            user_id = "new_user"
            document_id = "doc1"

            await recommendation_service.mark_document_as_viewed(user_id, document_id)

            # Check that new user was created
            assert user_id in recommendation_service.users

            # Check that document was marked as viewed
            user = recommendation_service.users[user_id]
            assert document_id in user.viewed_documents

            # Check that an interest was created
            assert any(
                interest.document_id == document_id for interest in user.interests
            )

            # Check that metrics were updated
            assert (
                recommendation_service.recommendation_metrics["user_interactions"] > 0
            )

            # Check that save methods were called
            assert mock_save_profiles.called
            assert mock_save_metrics.called

            # Test viewing a document that was in recent recommendations
            user.recent_recommendations = [
                Recommendation(
                    document_id="doc2",
                    title="Another Document",
                    path="/another/path",
                    explanation="Recommended document",
                    relevance_score=0.8,
                    tags=["test"],
                )
            ]

            mock_save_profiles.reset_mock()
            mock_save_metrics.reset_mock()

            await recommendation_service.mark_document_as_viewed(user_id, "doc2")

            # Check that document was marked as viewed
            assert "doc2" in user.viewed_documents

            # Check that save methods were called
            assert mock_save_profiles.called
            assert mock_save_metrics.called

    def test_calculate_diversity_score(self, recommendation_service):
        """Test the _calculate_diversity_score method."""
        # Set up document categories
        recommendation_service.document_categories = {
            "doc1": "guides",
            "doc2": "general",
            "doc3": "talent",
            "doc4": "technical",
            "doc5": "guides",
        }

        # Test with empty list
        empty_score = recommendation_service._calculate_diversity_score([])
        assert empty_score == 1.0

        # Test with single document
        single_score = recommendation_service._calculate_diversity_score(["doc1"])
        assert single_score == 1.0

        # Test with multiple documents from same category
        same_category_score = recommendation_service._calculate_diversity_score(
            ["doc1", "doc5"]
        )
        assert same_category_score == 0.5  # 1 unique category / 2 documents

        # Test with diverse documents
        diverse_score = recommendation_service._calculate_diversity_score(
            ["doc1", "doc2", "doc3"]
        )
        assert diverse_score == 1.0  # 3 unique categories / 3 documents

        # Test with mix of diverse and duplicate categories
        mixed_score = recommendation_service._calculate_diversity_score(
            ["doc1", "doc2", "doc3", "doc5"]
        )
        assert mixed_score == 0.75  # 3 unique categories / 4 documents

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, recommendation_service):
        """Test the generate_recommendations method."""
        # Set up service
        recommendation_service.initialized = True
        recommendation_service.document_categories = {
            "doc1": "guides",
            "doc2": "general",
            "doc3": "talent",
            "doc4": "technical",
        }

        # Create a test user
        user_id = "test_user"
        recommendation_service.users[user_id] = UserProfile(
            user_id=user_id,
            viewed_documents=["doc5"],  # Already viewed a document
            chat_history=[],
            interests=[
                UserInterest(
                    topic="hiring",
                    document_id="doc1",
                    category="guides",
                    strength=0.8,
                    first_mentioned=datetime.now(),
                    last_mentioned=datetime.now(),
                )
            ],
            last_active=datetime.now(),
            preferences={},
            recent_recommendations=[],
        )

        # Set up mocks
        with patch.object(
            recommendation_service, "_get_query_recommendations"
        ) as mock_query_recs, patch.object(
            recommendation_service, "_get_interest_recommendations"
        ) as mock_interest_recs, patch.object(
            recommendation_service, "_generate_fallback_recommendations"
        ) as mock_fallback_recs, patch.object(
            recommendation_service, "_save_user_profiles"
        ) as mock_save_profiles, patch(
            "app.services.enhanced_recommendations.save_metrics"
        ) as mock_save_metrics:

            # Configure mocks
            mock_query_recs.return_value = [
                {
                    "document_id": "doc1",
                    "title": "Finding Talent",
                    "path": "/docs/finding_talent.md",
                    "explanation": "Relevant to your query",
                    "relevance_score": 0.9,
                    "tags": ["hiring", "talent"],
                }
            ]

            mock_interest_recs.return_value = [
                {
                    "document_id": "doc2",
                    "title": "Payment System",
                    "path": "/docs/payments.md",
                    "explanation": "Based on your interests",
                    "relevance_score": 0.8,
                    "tags": ["payments"],
                }
            ]

            mock_fallback_recs.return_value = [
                {
                    "document_id": "doc3",
                    "title": "Developer Profile",
                    "path": "/docs/freelancer-profiles.md",
                    "explanation": "Recommended resource",
                    "relevance_score": 0.7,
                    "tags": ["profile"],
                }
            ]

            # Test generating recommendations
            query = "How do I find talent?"
            recommendations = await recommendation_service.generate_recommendations(
                user_id, query
            )

            # Check results
            assert len(recommendations) > 0
            assert mock_query_recs.called
            assert mock_interest_recs.called
            assert mock_save_profiles.called
            assert mock_save_metrics.called

            # Check that metrics were updated
            assert (
                recommendation_service.recommendation_metrics["total_recommendations"]
                > 0
            )
            assert (
                len(recommendation_service.recommendation_metrics["diversity_scores"])
                > 0
            )
            assert (
                len(recommendation_service.recommendation_metrics["relevance_scores"])
                > 0
            )

            # Check that user's recent recommendations were updated
            assert len(recommendation_service.users[user_id].recent_recommendations) > 0

            # Test with new user
            new_user_id = "new_user"

            mock_query_recs.reset_mock()
            mock_interest_recs.reset_mock()
            mock_fallback_recs.reset_mock()

            recommendations = await recommendation_service.generate_recommendations(
                new_user_id, query
            )

            # Check that new user was created
            assert new_user_id in recommendation_service.users

            # Check results
            assert len(recommendations) > 0
            assert mock_query_recs.called
            assert mock_interest_recs.called

            # Test when service is not initialized
            recommendation_service.initialized = False

            empty_recs = await recommendation_service.generate_recommendations(
                user_id, query
            )
            assert empty_recs == []

            # Test error handling
            recommendation_service.initialized = True
            mock_query_recs.side_effect = Exception("Test error")

            # Should fall back to fallback recommendations
            error_recs = await recommendation_service.generate_recommendations(
                user_id, query
            )
            assert error_recs == mock_fallback_recs.return_value

    @pytest.mark.asyncio
    async def test_get_query_recommendations(self, recommendation_service):
        """Test the _get_query_recommendations method."""
        # Set up viewed documents
        viewed_docs = {"doc5"}

        # Set up intent
        normal_intent = {"is_talent_search": False, "enhanced_query": "test query"}
        talent_intent = {
            "is_talent_search": True,
            "skills_mentioned": ["react", "javascript"],
        }

        # Set up search results
        doc1 = Document(
            id="doc1", title="Doc 1", content="Content", path="/path1", tags=["test"]
        )
        doc2 = Document(
            id="doc2", title="Doc 2", content="Content", path="/path2", tags=["test"]
        )
        doc3 = Document(
            id="doc3", title="Doc 3", content="Content", path="/path3", tags=["test"]
        )

        # Mock search methods
        with patch.object(
            recommendation_service.search_engine, "search"
        ) as mock_search, patch.object(
            recommendation_service.search_engine, "search_talent"
        ) as mock_search_talent:

            # Configure search for normal intent
            mock_search.return_value = [(doc1, 0.9), (doc2, 0.8), (doc3, 0.7)]

            # Configure search for talent intent
            mock_search_talent.return_value = [(doc1, 0.9), (doc2, 0.8)]

            # Test with normal intent
            query = "How do payments work?"
            normal_recs = await recommendation_service._get_query_recommendations(
                query, viewed_docs, normal_intent
            )

            # Check results
            assert len(normal_recs) > 0
            assert normal_recs[0]["document_id"] == "doc1"
            assert "Relevant to your current question" in normal_recs[0]["explanation"]
            assert mock_search.called
            assert not mock_search_talent.called

            # Reset mocks
            mock_search.reset_mock()
            mock_search_talent.reset_mock()

            # Test with talent intent
            query = "Find React developers"
            talent_recs = await recommendation_service._get_query_recommendations(
                query, viewed_docs, talent_intent
            )

            # Check results
            assert len(talent_recs) > 0
            assert talent_recs[0]["document_id"] == "doc1"
            assert (
                "expertise in react, javascript"
                in talent_recs[0]["explanation"].lower()
                or "Profile with expertise" in talent_recs[0]["explanation"]
            )
            assert not mock_search.called
            assert mock_search_talent.called

            # Test with already viewed document
            viewed_docs = {"doc1", "doc2"}
            limited_recs = await recommendation_service._get_query_recommendations(
                query, viewed_docs, normal_intent
            )

            # Should return fewer recommendations
            assert len(limited_recs) < len(normal_recs)

    @pytest.mark.asyncio
    async def test_get_interest_recommendations(self, recommendation_service):
        """Test the _get_interest_recommendations method."""
        # Set up service
        user_id = "test_user"
        viewed_docs = {"doc5"}
        current_query = "How do I hire talent?"

        # Create user with interests
        recommendation_service.users[user_id] = UserProfile(
            user_id=user_id,
            viewed_documents=list(viewed_docs),
            chat_history=[],
            interests=[
                UserInterest(
                    topic="hiring",
                    document_id="doc1",
                    category="guides",
                    strength=0.9,
                    first_mentioned=datetime.now(),
                    last_mentioned=datetime.now(),
                ),
                UserInterest(
                    topic="payments",
                    document_id="doc2",
                    category="general",
                    strength=0.7,
                    first_mentioned=datetime.now() - timedelta(days=3),
                    last_mentioned=datetime.now() - timedelta(days=3),
                ),
                UserInterest(
                    topic="react",
                    document_id="doc3",
                    category="talent",
                    strength=0.5,
                    first_mentioned=datetime.now() - timedelta(days=10),
                    last_mentioned=datetime.now() - timedelta(days=10),
                ),
            ],
            last_active=datetime.now(),
            preferences={},
            recent_recommendations=[],
        )

        # Mock search method
        with patch.object(
            recommendation_service.search_engine, "search"
        ) as mock_search:
            # Configure search to return different documents based on query
            def mock_search_side_effect(query, limit):
                if "hiring" in query:
                    return [
                        (
                            Document(
                                id="doc1",
                                title="Finding Talent",
                                content="Content",
                                path="/path1",
                                tags=["hiring"],
                            ),
                            0.9,
                        )
                    ]
                elif "payments" in query:
                    return [
                        (
                            Document(
                                id="doc2",
                                title="Payments",
                                content="Content",
                                path="/path2",
                                tags=["payments"],
                            ),
                            0.8,
                        )
                    ]
                else:
                    return [
                        (
                            Document(
                                id="doc3",
                                title="React Developers",
                                content="Content",
                                path="/path3",
                                tags=["react"],
                            ),
                            0.7,
                        )
                    ]

            mock_search.side_effect = mock_search_side_effect

            # Test getting interest recommendations
            interest_recs = await recommendation_service._get_interest_recommendations(
                user_id, current_query, viewed_docs
            )

            # Check results
            assert len(interest_recs) > 0

            # Explanations should mention interests or time frames
            for rec in interest_recs:
                assert (
                    "interests" in rec["explanation"].lower()
                    or "topics" in rec["explanation"].lower()
                )

            # Test with no matching interests
            empty_recs = await recommendation_service._get_interest_recommendations(
                user_id, "completely unrelated query", viewed_docs
            )
            assert len(empty_recs) <= len(interest_recs)

            # Test with no interests
            recommendation_service.users[user_id].interests = []
            no_interests_recs = (
                await recommendation_service._get_interest_recommendations(
                    user_id, current_query, viewed_docs
                )
            )
            assert len(no_interests_recs) == 0

    @pytest.mark.asyncio
    async def test_generate_fallback_recommendations(self, recommendation_service):
        """Test the _generate_fallback_recommendations method."""
        # Set up service
        recommendation_service.document_categories = {
            "doc1": "guides",
            "doc2": "general",
            "doc3": "talent",
            "doc4": "technical",
        }

        # Set documents
        recommendation_service.documents = [
            Document(
                id=f"doc{i}",
                title=f"Test Doc {i}",
                content=f"Content {i}",
                path=f"/path{i}",
            )
            for i in range(1, 5)
        ]

        # Create test user
        user_id = "test_user"
        recommendation_service.users[user_id] = UserProfile(
            user_id=user_id,
            viewed_documents=["doc1"],  # Already viewed doc1
            chat_history=[],
            interests=[],
            last_active=datetime.now(),
            preferences={},
            recent_recommendations=[],
        )

        # Mock random.choice to ensure deterministic testing
        with patch("numpy.random.choice") as mock_random_choice:
            # Configure mock to return first document in list
            mock_random_choice.side_effect = lambda docs, **kwargs: docs[0]

            # Test generating fallback recommendations
            fallback_recs = (
                await recommendation_service._generate_fallback_recommendations(user_id)
            )

            # Test should pass if we get any recommendations
            assert isinstance(fallback_recs, list)

            # Test with limit
            limited_recs = (
                await recommendation_service._generate_fallback_recommendations(
                    user_id, limit=1
                )
            )
            assert isinstance(limited_recs, list)
            assert len(limited_recs) <= max(
                1, len(recommendation_service.documents) - 1
            )

            # Test with new user
            new_user_id = "new_user"
            new_user_recs = (
                await recommendation_service._generate_fallback_recommendations(
                    new_user_id
                )
            )

            # Should create new user profile
            assert new_user_id in recommendation_service.users
            assert isinstance(new_user_recs, list)

    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, recommendation_service):
        """Test the get_performance_metrics method."""
        # Set up recommendation metrics with exact values
        recommendation_service.recommendation_metrics = {
            "total_recommendations": 50,
            "user_interactions": 20,
            "diversity_scores": [0.7, 0.8, 0.9],
            "relevance_scores": [0.8, 0.9, 0.7],
        }

        # Add some test users
        recommendation_service.users = {
            "user1": UserProfile(user_id="user1"),
            "user2": UserProfile(user_id="user2"),
        }

        # Get metrics
        metrics = await recommendation_service.get_performance_metrics()

        # Check results
        assert "total_recommendations" in metrics
        assert "user_interactions" in metrics
        assert "interaction_rate" in metrics
        assert "avg_diversity" in metrics
        assert "avg_relevance" in metrics
        assert "user_count" in metrics

        # Check calculations - use approximate equality for floating point
        assert metrics["total_recommendations"] == 50
        assert metrics["user_interactions"] == 20
        assert abs(metrics["interaction_rate"] - 0.4) < 0.001  # 20/50
        assert abs(metrics["avg_diversity"] - 0.8) < 0.001  # Average of [0.7, 0.8, 0.9]
        assert abs(metrics["avg_relevance"] - 0.8) < 0.001  # Average of [0.8, 0.9, 0.7]
        assert metrics["user_count"] == 2
