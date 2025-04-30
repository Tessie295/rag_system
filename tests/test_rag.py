"""
Test module for the RAG system with improved source detection.
"""
import os
import json
import pytest
import asyncio
import time
from typing import List, Dict, Any
import pandas as pd

from app.services.rag import RAGService
from app.utils.helpers import logger

# Test data paths
TEST_QUERIES_PATH = "tests/data/test_queries.json"
USER_PROFILES_PATH = "tests/data/user_profiles.json"

class TestRAG:
    """Test class for the RAG system."""

    @pytest.fixture
    async def rag_service(self):
        """Fixture to create and initialize a RAG service."""
        service = RAGService()
        await service.initialize()
        return service

    @pytest.fixture
    def test_queries(self):
        """Fixture to load test queries with more flexible source expectations."""
        if not os.path.exists(TEST_QUERIES_PATH):
            queries = [
                {
                    "query": "How do payments work on Shakers?",
                    "expected_sources": ["payments"],
                    "expected_topics": ["payments", "escrow", "fees"],
                    "should_be_out_of_scope": False
                },
                {
                    "query": "What payment methods does Shakers accept?",
                    "expected_sources": ["payments", "shakers-qa-dataset"],
                    "expected_topics": ["payment methods", "credit card", "paypal", "bank transfer"],
                    "should_be_out_of_scope": False
                },
                {
                    "query": "What is a freelancer on Shakers?",
                    "expected_sources": ["freelancers"],
                    "expected_topics": ["freelancer", "contractor", "professional"],
                    "should_be_out_of_scope": False
                },
                {
                    "query": "How do I become a freelancer on Shakers?",
                    "expected_sources": ["freelancers", "getting-started-guide"],
                    "expected_topics": ["freelancer", "registration", "profile"],
                    "should_be_out_of_scope": False
                },
                {
                    "query": "I need an Android developer with experience",
                    "expected_sources": ["freelancer-profiles"],
                    "expected_topics": ["android", "developer", "mobile"],
                    "should_be_out_of_scope": False
                },
                {
                    "query": "How do I cook pasta?",
                    "expected_sources": [],
                    "expected_topics": [],
                    "should_be_out_of_scope": True
                }
            ]
            os.makedirs(os.path.dirname(TEST_QUERIES_PATH), exist_ok=True)
            with open(TEST_QUERIES_PATH, 'w') as f:
                json.dump(queries, f, indent=2)
        with open(TEST_QUERIES_PATH, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def user_profiles(self):
        """Fixture to load user profiles."""
        if not os.path.exists(USER_PROFILES_PATH):
            profiles = [
                {
                    "user_id": "user1",
                    "interests": ["web development", "payments", "hiring"],
                    "viewed_documents": ["payments.md"],
                    "queries": [
                        "How do I hire a developer?",
                        "What are the payment methods?"
                    ]
                },
                {
                    "user_id": "user2",
                    "interests": ["design", "mobile development", "freelancing"],
                    "viewed_documents": ["freelancers.md"],
                    "queries": [
                        "How do I become a freelancer?",
                        "Looking for UI/UX designers"
                    ]
                }
            ]
            os.makedirs(os.path.dirname(USER_PROFILES_PATH), exist_ok=True)
            with open(USER_PROFILES_PATH, 'w') as f:
                json.dump(profiles, f, indent=2)
        with open(USER_PROFILES_PATH, 'r') as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_rag_response_time(self, rag_service, test_queries):
        """Test if the RAG system responds within the required time limit (5 seconds)."""
        # Obtener la instancia real a partir de la corutina
        service = await rag_service

        in_scope_queries = [q for q in test_queries if not q["should_be_out_of_scope"]]
        response_times = []

        for query_data in in_scope_queries:
            query = query_data["query"]
            start_time = time.time()
            response, _ = await service.process_query(query)
            end_time = time.time()

            response_time = end_time - start_time
            response_times.append(response_time)

            assert response_time < 5.0, f"Response time for query '{query}' exceeded 5 seconds: {response_time:.2f}s"

        avg_response_time = sum(response_times) / len(response_times)
        logger.info(f"Average response time: {avg_response_time:.2f}s")

        df = pd.DataFrame({
            "Query": [q["query"] for q in in_scope_queries],
            "Response Time (s)": response_times
        })
        print("\nResponse Time Results:")
        print(df)

    @pytest.mark.asyncio
    async def test_out_of_scope_detection(self, rag_service, test_queries):
        """Test if the system correctly identifies out-of-scope queries."""
        service = await rag_service

        for query_data in test_queries:
            query = query_data["query"]
            expected_out_of_scope = query_data["should_be_out_of_scope"]

            query_analysis = await service.analyze_query(query)
            is_out_of_scope = query_analysis["is_out_of_scope"]

            assert is_out_of_scope == expected_out_of_scope, (
                f"Out-of-scope detection for query '{query}' failed. "
                f"Expected: {expected_out_of_scope}, Got: {is_out_of_scope}"
            )

            if expected_out_of_scope:
                response, _ = await service.process_query(query)
                assert ("I don't have enough information" in response.answer or
                        "outside the scope" in response.answer), (
                    f"Out-of-scope response doesn't contain expected message: {response.answer}"
                )

    @pytest.mark.asyncio
    async def test_source_inclusion(self, rag_service, test_queries):
        """Test if the response includes at least one of the expected sources.
        This test is more flexible and will pass if any part of the expected source name
        appears in any returned source path."""
        service = await rag_service

        in_scope_queries = [q for q in test_queries if not q["should_be_out_of_scope"]]

        for query_data in in_scope_queries:
            query = query_data["query"]
            expected_sources = query_data["expected_sources"]

            response, _ = await service.process_query(query)

            assert len(response.sources) > 0, f"Response for query '{query}' has no sources"

            if expected_sources:
                source_paths = [source.path for source in response.sources]
                
                # More flexible source matching - check if any expected source substring appears in any path
                sources_found = []
                for expected in expected_sources:
                    for path in source_paths:
                        if expected.lower() in path.lower():
                            sources_found.append(expected)
                            break
                
                # Log actual source paths for debugging
                logger.info(f"Query: {query}")
                logger.info(f"Expected sources: {expected_sources}")
                logger.info(f"Actual source paths: {source_paths}")
                logger.info(f"Sources found: {sources_found}")
                
                assert len(sources_found) > 0, (
                    f"Response for query '{query}' does not include any expected sources.\n"
                    f"Expected at least one of: {expected_sources}\n"
                    f"Got: {source_paths}"
                )

    @pytest.mark.asyncio
    async def test_response_relevance(self, rag_service, test_queries):
        """Test if the response is relevant to the query by checking for expected topics."""
        service = await rag_service

        in_scope_queries = [q for q in test_queries if not q["should_be_out_of_scope"]]
        relevance_scores = []

        for query_data in in_scope_queries:
            query = query_data["query"]
            expected_topics = query_data["expected_topics"]

            if not expected_topics:
                continue  # Skip if no expected topics

            response, _ = await service.process_query(query)

            answer_lower = response.answer.lower()
            topic_matches = sum(1 for topic in expected_topics if topic.lower() in answer_lower)
            relevance_ratio = topic_matches / len(expected_topics) if expected_topics else 0
            relevance_scores.append(relevance_ratio)

            # Log topic matches for debugging
            logger.info(f"Query: {query}")
            logger.info(f"Expected topics: {expected_topics}")
            logger.info(f"Topics found: {[topic for topic in expected_topics if topic.lower() in answer_lower]}")
            logger.info(f"Relevance ratio: {relevance_ratio:.2f}")

            assert relevance_ratio >= 0.3, (
                f"Response for query '{query}' has low topic relevance.\n"
                f"Score: {relevance_ratio:.2f}\n"
                f"Expected topics: {expected_topics}\n"
                f"Response: {response.answer[:100]}..."
            )

        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        logger.info(f"Average response relevance: {avg_relevance:.2f}")

        df = pd.DataFrame({
            "Query": [q["query"] for q in in_scope_queries if q["expected_topics"]],
            "Relevance Score": relevance_scores
        })
        print("\nRelevance Score Results:")
        print(df)

    @pytest.mark.asyncio
    async def test_query_caching(self, rag_service, test_queries):
        """Test if the caching mechanism improves response time for repeated queries."""
        service = await rag_service

        query_data = next(q for q in test_queries if not q["should_be_out_of_scope"])
        query = query_data["query"]

        # First query - should not be cached
        start_time = time.time()
        first_response, first_time = await service.process_query(query)
        first_query_time = time.time() - start_time

        # Second query - should be cached and faster
        start_time = time.time()
        second_response, second_time = await service.process_query(query)
        second_query_time = time.time() - start_time

        # Log times for debugging
        logger.info(f"First query time: {first_query_time:.4f}s")
        logger.info(f"Second query time: {second_query_time:.4f}s")
        logger.info(f"Speed improvement: {(first_query_time/max(0.001, second_query_time)):.2f}x")

        assert second_query_time < first_query_time, (
            f"Caching doesn't improve response time.\n"
            f"First query: {first_query_time:.4f}s\n"
            f"Second query: {second_query_time:.4f}s"
        )
