"""
Enhanced search module for finding documents and talent profiles.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import spacy

# Download NLTK data
try:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
except:
    pass  # Handle offline scenarios

# Try to load spaCy model for NER
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None  # Will fall back to simpler methods if spaCy not available

from app.utils.helpers import logger
from app.models.schemas import Document


class SearchEngine:
    """Enhanced search engine for knowledge base and talent profiles."""

    def __init__(self):
        """Initialize the search engine."""
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),  # Include bigrams
            max_features=5000,
        )
        self.document_vectors = None
        self.documents = []
        self.tech_skills = [
            "python",
            "javascript",
            "typescript",
            "java",
            "c#",
            "c++",
            "go",
            "golang",
            "rust",
            "react",
            "angular",
            "vue",
            "node",
            "express",
            "django",
            "flask",
            "spring",
            "aws",
            "azure",
            "gcp",
            "cloud",
            "docker",
            "kubernetes",
            "devops",
            "machine learning",
            "ai",
            "data science",
            "nlp",
            "computer vision",
            "android",
            "ios",
            "mobile",
            "web",
            "frontend",
            "backend",
            "fullstack",
            "ui",
            "ux",
            "design",
            "figma",
            "sketch",
            "adobe",
            "sql",
            "nosql",
            "postgresql",
            "mysql",
            "mongodb",
            "database",
            "terraform",
            "ansible",
            "jenkins",
            "cicd",
            "security",
        ]

    def initialize(self, documents: List[Document]):
        """
        Initialize the search engine with documents.

        Args:
            documents: List of Document objects
        """
        self.documents = documents

        # Create document texts for vectorization
        doc_texts = []
        for doc in documents:
            # For talent profiles, emphasize skills and title
            if "freelancer-profiles" in doc.path or "freelancers" in doc.path:
                # Add extra weight to skills by repeating them
                # Extract skills from content
                skills = self._extract_skills_from_text(doc.content)
                skills_text = " ".join(skills)

                # Create weighted text with skills repeated
                weighted_text = f"{doc.title} {doc.title} {skills_text} {skills_text} {skills_text} {doc.content}"
                doc_texts.append(weighted_text)
            else:
                doc_texts.append(f"{doc.title} {doc.content}")

        # Create document vectors
        self.document_vectors = self.vectorizer.fit_transform(doc_texts)
        logger.info(f"Search engine initialized with {len(documents)} documents")

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """
        Extract technical skills from text.

        Args:
            text: Text to analyze

        Returns:
            List of detected skills
        """
        skills = []
        text_lower = text.lower()

        # Look for skill sections
        skill_section_match = re.search(
            r"(?:skills?|expertise)[:\s]*(.*?)(?:\n\n|\n\*\*|\Z)", text_lower, re.DOTALL
        )

        if skill_section_match:
            skill_section = skill_section_match.group(1)

            # Look for list items in the skills section
            list_items = re.findall(r"[-*•]\s*([^-*•\n]+)", skill_section)
            if list_items:
                for item in list_items:
                    item = item.strip().lower()
                    # Keep only if it's a known tech skill
                    if any(
                        skill == item or skill in item for skill in self.tech_skills
                    ):
                        skills.append(item)

            # If no list items found, just split the section by commas
            if not skills and "," in skill_section:
                items = [item.strip().lower() for item in skill_section.split(",")]
                skills = [
                    item
                    for item in items
                    if any(skill == item or skill in item for skill in self.tech_skills)
                ]

        # If no skills section found, check for mentions in the whole text
        if not skills:
            for skill in self.tech_skills:
                if skill in text_lower:
                    skills.append(skill)

        # Deduplicate
        return list(set(skills))

    def search(self, query: str, limit: int = 5) -> List[Tuple[Document, float]]:
        """
        Search for documents matching the query.

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of (document, similarity_score) tuples
        """
        # Check if engine is initialized
        if self.document_vectors is None or len(self.documents) == 0:
            logger.warning("Search engine not initialized")
            return []

        # Vectorize the query
        query_vector = self.vectorizer.transform([query])

        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.document_vectors)[0]

        # Sort by similarity
        sorted_indices = np.argsort(similarities)[::-1]

        # Return top results
        results = []
        for idx in sorted_indices[:limit]:
            if similarities[idx] > 0:  # Only include non-zero similarity
                results.append((self.documents[idx], float(similarities[idx])))

        return results

    def search_talent(self, query: str, limit: int = 3) -> List[Tuple[Document, float]]:
        """
        Search specifically for talent profiles matching the query.

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of (document, similarity_score) tuples
        """
        # Enhance query with skill detection
        enhanced_query = self._enhance_talent_query(query)

        # Filter to only talent profile documents
        talent_docs = [
            doc
            for doc in self.documents
            if "freelancer-profiles" in doc.path or "freelancers" in doc.path
        ]
        talent_indices = [
            i for i, doc in enumerate(self.documents) if doc in talent_docs
        ]

        if not talent_docs:
            logger.warning("No talent profiles found in documents")
            return []

        # Vectorize the enhanced query
        query_vector = self.vectorizer.transform([enhanced_query])

        # Get the document vectors for talent profiles only
        talent_vectors = self.document_vectors[talent_indices]

        # Calculate similarities
        similarities = cosine_similarity(query_vector, talent_vectors)[0]

        # Sort by similarity
        sorted_indices = np.argsort(similarities)[::-1]

        # Return top results
        results = []
        for i, idx in enumerate(sorted_indices[:limit]):
            if similarities[idx] > 0:  # Only include non-zero similarity
                results.append((talent_docs[idx], float(similarities[idx])))

        return results

    def _enhance_talent_query(self, query: str) -> str:
        """
        Enhance a talent search query by identifying skills and requirements.

        Args:
            query: Original user query

        Returns:
            Enhanced query for better matching
        """
        # Extract skills from query
        extracted_skills = []
        query_lower = query.lower()

        # Look for skills in the query
        for skill in self.tech_skills:
            if skill in query_lower:
                extracted_skills.append(skill)

        # Use spaCy for better Named Entity Recognition if available
        if nlp:
            doc = nlp(query)
            for ent in doc.ents:
                if ent.label_ in ["PRODUCT", "ORG", "GPE"]:
                    # These might be technology names or skills
                    candidate = ent.text.lower()
                    if any(skill in candidate for skill in self.tech_skills):
                        extracted_skills.append(candidate)

        # Detect experience requirements
        experience_match = re.search(r"(\d+)\s*(?:years?|yrs?)", query_lower)
        experience_term = ""
        if experience_match:
            years = experience_match.group(1)
            if int(years) <= 3:
                experience_term = "beginner junior"
            elif int(years) <= 6:
                experience_term = "intermediate experienced"
            else:
                experience_term = "senior expert experienced"

        # Detect job roles
        job_roles = [
            "developer",
            "programmer",
            "engineer",
            "designer",
            "writer",
            "marketer",
            "consultant",
            "manager",
            "expert",
            "specialist",
        ]

        detected_roles = []
        for role in job_roles:
            if role in query_lower:
                detected_roles.append(role)

        # Combine the enhanced terms
        enhanced_terms = []
        enhanced_terms.extend(extracted_skills)
        enhanced_terms.extend(detected_roles)
        if experience_term:
            enhanced_terms.append(experience_term)

        # Create enhanced query with repetition for emphasis
        if enhanced_terms:
            enhanced_query = (
                f"{query} {' '.join(enhanced_terms)} {' '.join(enhanced_terms)}"
            )
            return enhanced_query

        return query

    def analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze the intent of a query to determine if it's talent-related.

        Args:
            query: User query

        Returns:
            Dict with intent analysis
        """
        query_lower = query.lower()

        # Check for talent-related keywords
        talent_keywords = [
            "find",
            "looking for",
            "hire",
            "need",
            "search",
            "freelancer",
            "developer",
            "designer",
            "writer",
            "expert",
        ]

        # Count talent keywords
        talent_score = sum(1 for keyword in talent_keywords if keyword in query_lower)

        # Check for skills mention
        skills_mentioned = [skill for skill in self.tech_skills if skill in query_lower]

        # Determine if it's a talent search query
        is_talent_search = (talent_score >= 1 or len(skills_mentioned) >= 1) and (
            "?" not in query or "how" not in query_lower
        )

        return {
            "is_talent_search": is_talent_search,
            "talent_score": talent_score / len(talent_keywords),
            "skills_mentioned": skills_mentioned,
            "enhanced_query": (
                self._enhance_talent_query(query) if is_talent_search else query
            ),
        }
