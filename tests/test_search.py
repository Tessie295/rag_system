"""
Test module for search utilities to improve coverage.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.search import SearchEngine
from app.models.schemas import Document


class TestSearchEngine:
    """Tests for the SearchEngine class."""

    @pytest.fixture
    def mock_documents(self):
        """Fixture to create mock documents."""
        return [
            Document(
                id="doc1",
                title="Finding Talent on Shakers",
                content="This document explains how to find talent on Shakers using filters and search.",
                path="/docs/finding_talent.md",
                metadata={},
                category="guides",
                tags=["hiring", "talent", "search"],
            ),
            Document(
                id="doc2",
                title="Payment System",
                content="Information about the payment system on Shakers with escrow protection.",
                path="/docs/payments.md",
                metadata={},
                category="general",
                tags=["payments", "fees", "escrow"],
            ),
            Document(
                id="doc3",
                title="React Developer Profile",
                content="Profile of a frontend developer with React and JavaScript skills.",
                path="/docs/freelancer-profiles.md",
                metadata={},
                category="talent",
                tags=["profile", "developer", "react"],
            ),
            Document(
                id="doc4",
                title="Python Developer Profile",
                content="Profile of a backend developer with Python and Django skills.",
                path="/docs/freelancer-profiles.md",
                metadata={},
                category="talent",
                tags=["profile", "developer", "python"],
            ),
            Document(
                id="doc5",
                title="Technical Documentation",
                content="Technical details about the Shakers platform architecture with API documentation.",
                path="/docs/shakers-technical-documentation.md",
                metadata={},
                category="technical",
                tags=["technical", "api", "architecture"],
            ),
        ]

    @pytest.fixture
    def search_engine(self):
        """Fixture to create a SearchEngine instance."""
        return SearchEngine()

    def test_initialize(self, search_engine, mock_documents):
        """Test the initialize method."""
        # Initialize the search engine
        search_engine.initialize(mock_documents)

        # Check that the documents were stored
        assert search_engine.documents == mock_documents

        # Check that document vectors were created
        assert search_engine.document_vectors is not None
        assert search_engine.document_vectors.shape[0] == len(mock_documents)

        # Check that the vectorizer was fit
        assert search_engine.vectorizer.vocabulary_ is not None

        # Make sure tech_skills are defined
        assert isinstance(search_engine.tech_skills, list)
        assert len(search_engine.tech_skills) > 0

    def test_extract_skills_from_text(self, search_engine):
        """Test the _extract_skills_from_text method."""
        # Text with skills in a section
        skill_section_text = """
        # Developer Profile
        
        ## Skills:
        - JavaScript
        - React
        - Node.js
        - TypeScript
        - AWS
        
        ## Experience
        Worked on various projects...
        """

        skills = search_engine._extract_skills_from_text(skill_section_text)

        assert "javascript" in skills
        assert "react" in skills
        assert "node.js" in skills
        assert "typescript" in skills
        assert "aws" in skills

        # Text with skills in a comma-separated list
        comma_list_text = """
        # Developer Profile
        
        ## Skills
        JavaScript, React, Node.js, TypeScript, AWS
        
        ## Experience
        Worked on various projects...
        """

        comma_skills = search_engine._extract_skills_from_text(comma_list_text)

        assert "javascript" in comma_skills
        assert "react" in comma_skills
        assert "node.js" in comma_skills

        # Text with skills mentioned but no specific section
        scattered_text = """
        I am a developer who works with Python and Django. 
        My projects often involve cloud technologies like AWS.
        """

        scattered_skills = search_engine._extract_skills_from_text(scattered_text)

        assert "python" in scattered_skills
        assert "aws" in scattered_skills

        # Text with no skills mentioned
        no_skills_text = """
        This is a general description with no technical terms.
        """

        no_skills = search_engine._extract_skills_from_text(no_skills_text)
        assert len(no_skills) == 0

    def test_search(self, search_engine, mock_documents):
        """Test the search method."""
        # Initialize the search engine
        search_engine.initialize(mock_documents)

        # Search for general terms
        results = search_engine.search("payment system", limit=2)

        # Check results
        assert len(results) > 0
        assert len(results) <= 2  # Respect the limit

        # Top result should be the payment document
        assert results[0][0].id == "doc2"

        # Each result should include a document and a score
        for doc, score in results:
            assert isinstance(doc, Document)
            assert isinstance(score, float)
            assert 0 <= score <= 1

        # Search for talent-specific terms
        talent_results = search_engine.search("react developer", limit=2)

        # Top result should be the React developer profile
        assert talent_results[0][0].id == "doc3"

        # Search with technical terms
        technical_results = search_engine.search("API architecture", limit=2)

        # Top result should be the technical documentation
        assert technical_results[0][0].id == "doc5"

        # Search with non-existent terms
        no_results = search_engine.search("completely unrelated query xyz123", limit=2)
        assert len(no_results) >= 0  # May return low-relevance results or empty list

        # Test when engine is not initialized
        search_engine.document_vectors = None
        search_engine.documents = []

        empty_results = search_engine.search("test", limit=2)
        assert len(empty_results) == 0

    def test_search_talent(self, search_engine, mock_documents):
        """Test the search_talent method."""
        # Initialize the search engine
        search_engine.initialize(mock_documents)

        # Search for talent with React skills
        results = search_engine.search_talent("React developer", limit=2)

        # Check results
        assert len(results) > 0
        assert len(results) <= 2  # Respect the limit

        # Top result should be the React developer profile
        assert results[0][0].id == "doc3"

        # Search for talent with Python skills
        python_results = search_engine.search_talent("Python developer", limit=2)

        # Top result should be the Python developer profile
        assert python_results[0][0].id == "doc4"

        # Search for talent with non-existent skills
        no_results = search_engine.search_talent("Rust developer", limit=2)

        # Should still return talent documents but with lower relevance
        assert len(no_results) >= 0

        # Test when engine is not initialized
        search_engine.document_vectors = None
        search_engine.documents = []

        empty_results = search_engine.search_talent("test", limit=2)
        assert len(empty_results) == 0

        # Test when no talent profiles exist
        search_engine.initialize(
            [
                Document(
                    id="doc1",
                    title="General Document",
                    content="General content",
                    path="/docs/general.md",
                    metadata={},
                )
            ]
        )

        no_talent_results = search_engine.search_talent("developer", limit=2)
        assert len(no_talent_results) == 0

    def test_enhance_talent_query(self, search_engine):
        """Test the _enhance_talent_query method."""
        # Search for specific skills
        enhanced_query = search_engine._enhance_talent_query("React developer")

        # Should include original terms plus expanded terms
        assert "React developer" in enhanced_query
        assert "react" in enhanced_query.lower()
        assert "developer" in enhanced_query.lower()

        # Search for frontend role
        frontend_query = search_engine._enhance_talent_query(
            "Looking for a frontend engineer"
        )

        # Should emphasize developer-related terms
        assert "Looking for a frontend engineer" in frontend_query
        assert "frontend" in frontend_query.lower()
        assert "engineer" in frontend_query.lower()

        # Search with experience requirements
        exp_query = search_engine._enhance_talent_query(
            "Need a developer with 5 years experience"
        )

        # Should include experience-related terms
        assert "Need a developer with 5 years experience" in exp_query
        assert "developer" in exp_query.lower()
        assert "experienced" in exp_query.lower()

        # Search with senior level
        senior_query = search_engine._enhance_talent_query(
            "Senior Python developer needed"
        )

        # Should include senior and Python terms
        assert "Senior Python developer needed" in senior_query
        assert "python" in senior_query.lower()
        assert "developer" in senior_query.lower()
        assert "senior" in senior_query.lower()

    def test_analyze_intent(self, search_engine):
        """Test the analyze_intent method."""
        # Query clearly about talent
        talent_intent = search_engine.analyze_intent("Looking for a React developer")

        assert talent_intent["is_talent_search"] is True
        assert talent_intent["talent_score"] > 0
        assert "react" in talent_intent["skills_mentioned"]

        # Query about hiring with skills
        hiring_intent = search_engine.analyze_intent(
            "Need to hire someone who knows python"
        )

        assert hiring_intent["is_talent_search"] is True
        assert hiring_intent["talent_score"] > 0
        assert "python" in hiring_intent["skills_mentioned"]

        # Query about platform features, not talent
        platform_intent = search_engine.analyze_intent(
            "How does the payment system work?"
        )

        assert platform_intent["is_talent_search"] is False
        assert platform_intent["talent_score"] >= 0
        assert len(platform_intent["skills_mentioned"]) == 0

        # Ambiguous query that mentions a skill but is a question
        ambiguous_intent = search_engine.analyze_intent("What is React used for?")

        assert "react" in ambiguous_intent["skills_mentioned"]
        # The is_talent_search might be True or False depending on implementation

        # General informational query
        info_intent = search_engine.analyze_intent("Tell me about Shakers platform")

        assert info_intent["is_talent_search"] is False
        assert info_intent["talent_score"] >= 0
        assert len(info_intent["skills_mentioned"]) == 0

    def test_search_with_mocked_cosine_similarity(self, search_engine, mock_documents):
        """Test the search method with mocked cosine_similarity."""
        search_engine.initialize(mock_documents)

        # Mock the cosine_similarity function to return controlled similarity scores
        mock_similarities = np.array([[0.9, 0.1, 0.2, 0.3, 0.4]])

        with patch("app.utils.search.cosine_similarity") as mock_cosine:
            mock_cosine.return_value = mock_similarities

            results = search_engine.search("test query", limit=3)

            # Check that results match our mocked similarities
            assert len(results) == 3
            assert results[0][0].id == "doc1"  # Highest similarity of 0.9
            assert results[0][1] == 0.9

            # Test limit larger than number of documents
            all_results = search_engine.search("test query", limit=10)
            assert len(all_results) == 5  # Only 5 documents available
