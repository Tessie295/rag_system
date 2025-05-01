"""
Test module for evaluation utilities to improve coverage.
"""
import os
import sys
import pytest
import asyncio
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
import json

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.evaluation import (
    evaluate_answer,
    evaluate_factual_correctness,
    evaluate_lexical_correctness,
    evaluate_relevance,
    evaluate_completeness,
    evaluate_bleu_score,
    generate_evaluation_feedback,
    evaluate_source_relevance,
    evaluate_recommendation_quality
)
from app.models.schemas import QueryEvaluation

class TestEvaluation:
    """Tests for the evaluation utilities."""

    @pytest.mark.asyncio
    async def test_evaluate_answer(self):
        """Test the evaluate_answer function."""
        # Mock the dependency functions to avoid actual computation
        with patch('app.utils.evaluation.evaluate_factual_correctness') as mock_correctness, \
             patch('app.utils.evaluation.evaluate_relevance') as mock_relevance, \
             patch('app.utils.evaluation.evaluate_completeness') as mock_completeness:
            
            # Set up mock return values
            mock_correctness.return_value = 0.8
            mock_relevance.return_value = 0.7
            mock_completeness.return_value = 0.9
            
            # Test inputs
            query = "How do payments work on Shakers?"
            answer = "Shakers uses an escrow system for payments."
            sources = ["Shakers provides a secure payment system using escrow."]
            
            # Call the function
            evaluation = await evaluate_answer(query, answer, sources)
            
            # Verify the output structure and types
            assert isinstance(evaluation, QueryEvaluation)
            assert evaluation.correctness_score == 0.8
            assert evaluation.relevance_score == 0.7
            assert evaluation.completeness_score == 0.9
            assert 0 <= evaluation.overall_score <= 1
            assert isinstance(evaluation.feedback, str)

    @pytest.mark.asyncio
    async def test_evaluate_factual_correctness_with_llm(self):
        """Test the evaluate_factual_correctness with LLM setting."""
        answer = "Shakers uses an escrow system for payments."
        sources = ["Shakers provides a secure payment system using escrow."]

        with patch('app.utils.evaluation.settings') as mock_settings, \
             patch('app.utils.evaluation.ChatOpenAI') as mock_chatgpt, \
             patch('app.utils.evaluation.ChatPromptTemplate') as mock_template, \
             patch('app.utils.evaluation.LLMChain') as mock_chain:
            
            # Set up the mocks
            mock_settings.USE_LLM_FOR_EVALUATION = True
            mock_chain_instance = AsyncMock()
            mock_chain_instance.arun.return_value = "0.85"
            mock_chain.return_value = mock_chain_instance
            
            # Call the function
            score = await evaluate_factual_correctness(answer, sources)
            
            # Verify the output
            assert 0 <= score <= 1
            assert mock_chain_instance.arun.called

    @pytest.mark.asyncio
    async def test_evaluate_factual_correctness_without_llm(self):
        """Test the evaluate_factual_correctness without LLM."""
        answer = "Shakers uses an escrow system for payments."
        sources = ["Shakers provides a secure payment system using escrow."]

        with patch('app.utils.evaluation.settings') as mock_settings:
            # Set up the mock
            mock_settings.USE_LLM_FOR_EVALUATION = False
            
            # Call the function
            score = await evaluate_factual_correctness(answer, sources)
            
            # Verify the output
            assert 0 <= score <= 1

    @pytest.mark.asyncio
    async def test_evaluate_factual_correctness_timeout(self):
        """Test the evaluate_factual_correctness with timeout."""
        answer = "Shakers uses an escrow system for payments."
        sources = ["Shakers provides a secure payment system using escrow."]

        with patch('app.utils.evaluation.settings') as mock_settings, \
             patch('app.utils.evaluation.ChatOpenAI') as mock_chatgpt, \
             patch('app.utils.evaluation.ChatPromptTemplate') as mock_template, \
             patch('app.utils.evaluation.LLMChain') as mock_chain, \
             patch('app.utils.evaluation.evaluate_lexical_correctness') as mock_lexical:
            
            # Set up the mocks to simulate a timeout
            mock_settings.USE_LLM_FOR_EVALUATION = True
            mock_chain_instance = AsyncMock()
            mock_chain_instance.arun.side_effect = asyncio.TimeoutError()
            mock_chain.return_value = mock_chain_instance
            mock_lexical.return_value = 0.7
            
            # Call the function
            score = await evaluate_factual_correctness(answer, sources)
            
            # Verify the output
            assert 0 <= score <= 1
            assert mock_lexical.called

    def test_evaluate_lexical_correctness(self):
        """Test the evaluate_lexical_correctness function."""
        # Test with normal inputs
        answer = "Shakers uses an escrow system for payments."
        sources = ["Shakers provides a secure payment system using escrow."]
        score = evaluate_lexical_correctness(answer, sources)
        assert 0 <= score <= 1
        
        # Test with empty strings
        score_empty = evaluate_lexical_correctness("", sources)
        assert score_empty == 0.5
        
        score_empty_sources = evaluate_lexical_correctness(answer, [])
        assert score_empty_sources == 0.5
        
        # Test with completely different content
        score_diff = evaluate_lexical_correctness(
            "The weather is nice today.", 
            ["Shakers provides a secure payment system."]
        )
        assert score_diff < 0.5

    def test_evaluate_relevance(self):
        """Test the evaluate_relevance function."""
        # Use patch to control the TfidfVectorizer and cosine_similarity
        with patch('app.utils.evaluation.TfidfVectorizer') as mock_tfidf, \
             patch('app.utils.evaluation.cosine_similarity') as mock_cosine:
            
            # Configure mocks to return controlled values
            mock_vectorizer = MagicMock()
            mock_tfidf.return_value = mock_vectorizer
            
            mock_matrix = MagicMock()
            mock_vectorizer.fit_transform.return_value = mock_matrix
            
            # Make cosine_similarity return 0.7 for high relevance
            mock_cosine.return_value = np.array([[0.7]])
            
            # Test with highly relevant answer
            query = "How does the payment system work?"
            answer = "The payment system works through escrow."
            
            score = evaluate_relevance(query, answer)
            
            # With a similarity of 0.7, the score should be above 0.5
            assert 0.5 <= score <= 1.0
            
            # Test with error handling
            mock_tfidf.side_effect = Exception("Simulated error")
            
            score_error = evaluate_relevance(query, answer)
            assert score_error == 0.5  # Default on error

    def test_evaluate_completeness(self):
        """Test the evaluate_completeness function."""
        # Test with highly complete answer
        query = "How do payments and escrow work on Shakers?"
        answer = "Shakers uses an escrow payment system to protect both clients and freelancers. Clients fund projects upfront, and payments are released when milestones are completed."
        sources = ["Shakers provides a secure payment system with escrow protection."]
        score = evaluate_completeness(query, answer, sources)
        assert 0.5 <= score <= 1
        
        # Test with incomplete answer (missing key terms)
        query = "How do payments and escrow work on Shakers?"
        answer = "The platform ensures transactions are secure."
        score_incomplete = evaluate_completeness(query, answer, sources)
        assert score_incomplete < 0.5
        
        # Test with empty sources
        score_no_sources = evaluate_completeness(query, answer, [])
        assert score_no_sources == 0.5

    def test_evaluate_bleu_score(self):
        """Test the evaluate_bleu_score function."""
        answer = "Shakers uses an escrow system for payments."
        references = ["Shakers provides a secure payment system using escrow."]
        score = evaluate_bleu_score(answer, references)
        assert 0 <= score <= 1
        
        # Test with empty references
        score_empty_refs = evaluate_bleu_score(answer, [])
        assert score_empty_refs == 0.5
        
        # Test with empty strings
        score_empty_refs = evaluate_bleu_score(answer, [""])
        assert score_empty_refs == 0.5
        
        # Test error handling
        with patch('app.utils.evaluation.word_tokenize') as mock_tokenize:
            mock_tokenize.side_effect = Exception("Simulated error")
            score_error = evaluate_bleu_score(answer, references)
            assert score_error == 0.5

    def test_generate_evaluation_feedback(self):
        """Test the generate_evaluation_feedback function."""
        # Test high quality feedback
        high_feedback = generate_evaluation_feedback(0.9, 0.9, 0.9, 0.9)
        assert "high quality" in high_feedback.lower()
        
        # Test medium quality feedback
        medium_feedback = generate_evaluation_feedback(0.7, 0.7, 0.7, 0.7)
        assert "adequate" in medium_feedback.lower()
        
        # Test low quality feedback
        low_feedback = generate_evaluation_feedback(0.4, 0.4, 0.4, 0.4)
        assert "needs" in low_feedback.lower()
        assert "improvement" in low_feedback.lower()
        
        # Test mixed scores feedback
        mixed_feedback = generate_evaluation_feedback(0.9, 0.4, 0.9, 0.7)
        assert "relevant" in mixed_feedback.lower() or "relevance" in mixed_feedback.lower()

    def test_evaluate_source_relevance(self):
        """Test the evaluate_source_relevance function."""
        # Mock TfidfVectorizer and cosine_similarity
        with patch('app.utils.evaluation.TfidfVectorizer') as mock_tfidf, \
             patch('app.utils.evaluation.cosine_similarity') as mock_cosine:
            
            # Configure mocks
            mock_vectorizer = MagicMock()
            mock_tfidf.return_value = mock_vectorizer
            
            mock_matrix = MagicMock()
            mock_vectorizer.fit_transform.return_value = mock_matrix
            
            # Make cosine_similarity return controlled values
            mock_cosine.return_value = np.array([[0.8, 0.2, 0.6]])
            
            query = "How does payment work on Shakers?"
            sources = [
                "Shakers provides a secure payment system using escrow.",
                "Freelancers on Shakers have diverse skills and backgrounds.",
                "The payment process involves milestone-based releases."
            ]
            
            scores = evaluate_source_relevance(query, sources)
            
            # Check output
            assert len(scores) == len(sources)
            for score in scores:
                assert 0 <= score <= 1
                
            # The first and third sources should have higher relevance scores based on our mock
            assert scores[0] > 0.2  # First source score (0.8)
            assert scores[2] > 0.2  # Third source score (0.6)
            
            # Test empty sources
            empty_scores = evaluate_source_relevance(query, [])
            assert empty_scores == []
            
            # Test error handling
            mock_tfidf.side_effect = Exception("Simulated error")
            error_scores = evaluate_source_relevance(query, sources)
            assert all(score == 0.5 for score in error_scores)

    @pytest.mark.asyncio
    async def test_evaluate_recommendation_quality(self):
        """Test the evaluate_recommendation_quality function."""
        query = "I need help finding a React developer"
        recommendations = [
            {
                "document_id": "doc1",
                "title": "Finding React Developers on Shakers",
                "explanation": "Guide to hiring React experts",
                "tags": ["react", "hiring"]
            },
            {
                "document_id": "doc2",
                "title": "Top Frontend Developers",
                "explanation": "Profiles of top React and Angular developers",
                "tags": ["frontend", "developers"]
            }
        ]
        
        evaluation = await evaluate_recommendation_quality(query, recommendations)
        
        # Check output structure
        assert "relevance_score" in evaluation
        assert "diversity_score" in evaluation
        assert "overall_score" in evaluation
        assert 0 <= evaluation["relevance_score"] <= 1
        assert 0 <= evaluation["diversity_score"] <= 1
        assert 0 <= evaluation["overall_score"] <= 1
        
        # Test error in TF-IDF calculation
        with patch('app.utils.evaluation.TfidfVectorizer') as mock_tfidf:
            mock_tfidf.side_effect = Exception("Simulated error")
            evaluation_error = await evaluate_recommendation_quality(query, recommendations)
            assert 0 <= evaluation_error["relevance_score"] <= 1
            assert 0 <= evaluation_error["diversity_score"] <= 1
            
        # Test empty recommendations
        evaluation_empty = await evaluate_recommendation_quality(query, [])
        assert evaluation_empty["relevance_score"] == 0.0
        assert evaluation_empty["diversity_score"] == 0.0
        assert evaluation_empty["overall_score"] == 0.0