from datetime import datetime, timedelta
import json
import os
import traceback
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import pandas as pd
from scipy.spatial.distance import pdist, squareform

from app.config import settings
from app.models.schemas import (
    UserProfile,
    Query,
    Document,
    Recommendation,
    ChatMessage,
    UserInterest,
)
from app.utils.helpers import logger, save_metrics, load_metrics


class RecommendationService:
    """Enhanced service for generating personalized content recommendations."""

    def __init__(self):
        """Initialize the recommendation service with improved capabilities."""
        self.users: Dict[str, UserProfile] = {}
        self.documents: List[Document] = []

        # Enhanced text processing for better feature extraction
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1500,
            stop_words="english",
            ngram_range=(1, 2),  # Include bigrams for better topic modeling
            min_df=2,  # Minimum document frequency
        )

        # Document vectors and categories
        self.document_vectors = None
        self.document_categories = None
        self.document_clusters = None
        self.initialized = False

        # Enhanced metrics tracking
        self.recommendation_metrics = {
            "total_recommendations": 0,
            "user_interactions": 0,
            "diversity_scores": [],
            "relevance_scores": [],
            "user_satisfaction": defaultdict(list),  # Track by user_id
        }

    async def initialize(self, documents: List[Document]):
        """Initialize the recommendation service with improved document analysis."""
        if self.initialized:
            return

        self.documents = documents

        # Extract document contents and titles for better feature representation
        document_contents = [f"{doc.title} {doc.content}" for doc in documents]

        # Create TF-IDF vectors
        self.document_vectors = self.tfidf_vectorizer.fit_transform(document_contents)

        # Perform clustering to categorize documents
        self.document_clusters = self._cluster_documents()

        # Create document similarity matrix for diversity calculations
        self.document_similarity = squareform(
            pdist(self.document_vectors.toarray(), "cosine")
        )

        # Load user profiles
        await self._load_user_profiles()

        # Load metrics if they exist
        stored_metrics = await load_metrics("recommendation_metrics")
        if stored_metrics:
            self.recommendation_metrics.update(stored_metrics)

        self.initialized = True
        logger.info("Enhanced recommendation service initialized successfully")

    def _cluster_documents(self) -> np.ndarray:
        """Cluster documents to enable more diverse recommendations."""
        # Determine optimal number of clusters (simplified)
        n_clusters = min(10, len(self.documents) // 3 + 1)

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(self.document_vectors)

        logger.info(f"Clustered documents into {n_clusters} categories")
        return clusters

    async def _load_user_profiles(self):
        """Load user profiles from file with better error handling."""
        users_file = os.path.join(settings.DATA_DIR, "users.json")
        if os.path.exists(users_file):
            try:
                with open(users_file, "r") as f:
                    users_data = json.load(f)
                    for user_data in users_data:
                        user_id = user_data.get("user_id")
                        if user_id:
                            self.users[user_id] = UserProfile(**user_data)
                logger.info(f"Loaded {len(self.users)} user profiles")
            except Exception as e:
                logger.error(f"Error loading user profiles: {e}")
                logger.info("Creating new user profiles storage")
                self.users = {}
        else:
            logger.info("No existing user profiles found. Creating new storage.")

    async def _save_user_profiles(self):
        """Save user profiles with enhanced error handling."""
        users_file = os.path.join(settings.DATA_DIR, "users.json")
        os.makedirs(settings.DATA_DIR, exist_ok=True)

        try:
            with open(users_file, "w") as f:
                # Convert datetime objects to strings
                users_data = [user.dict() for user in self.users.values()]
                json.dump(users_data, f, default=str)
            logger.info(f"Saved {len(self.users)} user profiles")
            return True
        except Exception as e:
            logger.error(f"Error saving user profiles: {e}")
            return False

    async def add_chat_to_user_history(
        self, user_id: str, user_message: str, assistant_message: str
    ):
        """Add a chat to history and update user interests."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)

        # Add message to chat history
        self.users[user_id].chat_history.append(
            ChatMessage(
                user_message=user_message,
                assistant_message=assistant_message,
                timestamp=datetime.now(),
            )
        )

        # Extract interests from user message
        await self._update_user_interests(user_id, user_message)

        # Save updated profiles
        await self._save_user_profiles()

    async def _update_user_interests(self, user_id: str, message: str):
        """Extract and update user interests from message content."""
        if not self.initialized:
            return

        # Vectorize user message
        message_vector = self.tfidf_vectorizer.transform([message])

        # Calculate similarity with all documents
        similarities = cosine_similarity(
            message_vector, self.document_vectors
        ).flatten()

        # Find the most relevant topics
        top_indices = np.argsort(similarities)[-5:]  # Top 5 most similar docs

        # Extract most important terms from these documents
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Only consider reasonably similar docs
                doc = self.documents[idx]
                cluster = self.document_clusters[idx]

                # Check if interest already exists
                interest_exists = False
                for interest in self.users[user_id].interests:
                    if interest.document_id == doc.id:
                        # Update existing interest
                        interest.strength += 0.2 * similarities[idx]
                        interest.last_mentioned = datetime.now()
                        interest_exists = True
                        break

                # Add new interest if it doesn't exist
                if not interest_exists:
                    self.users[user_id].interests.append(
                        UserInterest(
                            topic=doc.title,
                            document_id=doc.id,
                            category=str(cluster),
                            strength=similarities[idx],
                            first_mentioned=datetime.now(),
                            last_mentioned=datetime.now(),
                        )
                    )

        # Decay old interests
        for interest in self.users[user_id].interests:
            days_since_mention = (datetime.now() - interest.last_mentioned).days
            if days_since_mention > 0:
                interest.strength *= 0.95**days_since_mention  # Exponential decay

    async def mark_document_as_viewed(self, user_id: str, document_id: str):
        """Mark a document as viewed and update metrics."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)

        if document_id not in self.users[user_id].viewed_documents:
            self.users[user_id].viewed_documents.append(document_id)

            # Update interaction metrics
            self.recommendation_metrics["user_interactions"] += 1

            # Find if this was a recommended document
            for rec in self.users[user_id].recent_recommendations:
                if rec.document_id == document_id:
                    # Record satisfaction based on relevance
                    self.recommendation_metrics["user_satisfaction"][user_id].append(
                        rec.relevance_score
                    )
                    break

            await self._save_user_profiles()

            # Save updated metrics
            await save_metrics("recommendation_metrics", self.recommendation_metrics)

    def _calculate_diversity_score(
        self, recommendations: List[Recommendation]
    ) -> float:
        """Calculate diversity score of recommendations."""
        if len(recommendations) <= 1:
            return 1.0  # Maximum diversity with 0-1 items

        doc_indices = []
        for rec in recommendations:
            for i, doc in enumerate(self.documents):
                if doc.id == rec.document_id:
                    doc_indices.append(i)
                    break

        # Calculate pairwise dissimilarity (1 - similarity)
        diversity_scores = []
        for i in range(len(doc_indices)):
            for j in range(i + 1, len(doc_indices)):
                idx1, idx2 = doc_indices[i], doc_indices[j]
                dissimilarity = self.document_similarity[idx1, idx2]
                diversity_scores.append(dissimilarity)

        return (
            sum(diversity_scores) / len(diversity_scores) if diversity_scores else 1.0
        )

    async def generate_recommendations(
        self, user_id: str, current_query: str
    ) -> List[Recommendation]:
        """Generate personalized recommendations with diversity considerations."""
        if not self.initialized:
            logger.warning(
                "Recommendation service not initialized - returning empty recommendations"
            )
            return []

        # Add debugging to trace the recommendation flow
        logger.info(
            f"Generating recommendations for user {user_id} with query: {current_query}"
        )

        # Ensure user exists
        if user_id not in self.users:
            logger.info(f"Creating new user profile for {user_id}")
            self.users[user_id] = UserProfile(user_id=user_id)

        user_profile = self.users[user_id]

        # Debug check - make sure we have documents to work with
        if not self.documents or len(self.documents) == 0:
            logger.warning("No documents available for recommendations")
            return []

        logger.info(f"Working with {len(self.documents)} documents for recommendations")

        # Check if necessary components are available
        if self.document_vectors is None or self.document_vectors.shape[0] == 0:
            logger.warning(
                "Document vectors not available - cannot generate personalized recommendations"
            )
            # Provide fallback recommendations
            return self._generate_fallback_recommendations(user_id)

        try:
            # Vectorize current query
            query_vector = self.tfidf_vectorizer.transform([current_query])

            # Combine interests and query for personalized recommendations
            interest_score = np.zeros(len(self.documents))

            # Get user interests with decay based on recency
            for interest in user_profile.interests:
                days_since_mention = (datetime.now() - interest.last_mentioned).days
                decay_factor = max(0.1, (0.9**days_since_mention))

                # Find document index
                for i, doc in enumerate(self.documents):
                    if doc.id == interest.document_id:
                        interest_score[i] += interest.strength * decay_factor
                        break

            # Calculate query similarity
            logger.debug("Calculating query similarity")
            query_similarity = cosine_similarity(
                query_vector, self.document_vectors
            ).flatten()

            # Combine scores (weighted)
            combined_scores = (0.7 * query_similarity) + (0.3 * interest_score)

            # Get viewed documents to exclude
            viewed_documents = set(user_profile.viewed_documents)
            logger.debug(f"User has viewed {len(viewed_documents)} documents")

            # Extract skill/technology terms from the query to boost relevant recommendations
            tech_terms = self._extract_tech_terms(current_query)
            logger.debug(f"Extracted tech terms from query: {tech_terms}")

            # Prepare recommendations with diversity and tech term boosting
            document_scores = [(i, score) for i, score in enumerate(combined_scores)]

            # Boost scores for documents containing relevant tech terms
            if tech_terms:
                logger.debug("Boosting scores for relevant tech terms")
                for i, (doc_idx, score) in enumerate(document_scores):
                    doc = self.documents[doc_idx]
                    doc_content = f"{doc.title} {doc.content}".lower()

                    for term in tech_terms:
                        if term.lower() in doc_content:
                            # Boost the score for this document
                            document_scores[i] = (doc_idx, score * 1.5)
                            logger.debug(
                                f"Boosted score for document {doc.title} containing term {term}"
                            )

            # Sort by score
            document_scores.sort(key=lambda x: x[1], reverse=True)

            recommendations = []
            selected_clusters = set()

            # Add debugging
            logger.debug(f"Top 5 document scores: {document_scores[:5]}")

            for doc_idx, similarity in document_scores:
                if len(recommendations) >= settings.MAX_RECOMMENDATIONS:
                    break

                doc = self.documents[doc_idx]

                # Skip if already viewed
                if doc.id in viewed_documents:
                    logger.debug(f"Skipping already viewed document: {doc.title}")
                    continue

                # Get cluster for this document
                doc_cluster = None
                if (
                    hasattr(self, "document_clusters")
                    and self.document_clusters is not None
                ):
                    if len(self.document_clusters) > doc_idx:
                        doc_cluster = self.document_clusters[doc_idx]

                # Promote diversity by limiting docs from same cluster, but only if we have sufficient clusters
                if (
                    doc_cluster is not None
                    and doc_cluster in selected_clusters
                    and len(selected_clusters) < 3
                ):
                    logger.debug(
                        f"Skipping document from already selected cluster: {doc_cluster}"
                    )
                    continue

                if doc_cluster is not None:
                    selected_clusters.add(doc_cluster)

                # Lower the threshold for including recommendations
                if similarity > 0.05:
                    explanation = self._generate_enhanced_explanation(
                        doc, current_query, similarity, user_profile
                    )

                    # Create a dictionary for Streamlit compatibility
                    rec_dict = {
                        "document_id": doc.id,
                        "title": doc.title,
                        "path": doc.path,
                        "explanation": explanation,
                        "relevance_score": float(similarity),
                        "tags": doc.tags if hasattr(doc, "tags") else [],
                    }

                    recommendations.append(rec_dict)
                    logger.debug(
                        f"Added recommendation: {doc.title} with score {similarity:.2f}"
                    )

            # If we still don't have recommendations, add some general ones
            if not recommendations and len(self.documents) > 0:
                logger.info(
                    "No specific recommendations found, adding general recommendations"
                )
                return self._generate_fallback_recommendations(user_id)

            # Update metrics
            self.recommendation_metrics["total_recommendations"] += len(recommendations)

            # Track diversity score
            diversity_score = self._calculate_diversity_score(recommendations)
            self.recommendation_metrics["diversity_scores"].append(diversity_score)

            # Track relevance scores
            for rec in recommendations:
                self.recommendation_metrics["relevance_scores"].append(
                    rec["relevance_score"]
                )

            # Store recommendations with user
            user_profile.recent_recommendations = [
                Recommendation(
                    document_id=rec["document_id"],
                    title=rec["title"],
                    path=rec["path"],
                    explanation=rec["explanation"],
                    relevance_score=rec["relevance_score"],
                    tags=rec.get("tags", []),
                )
                for rec in recommendations
            ]
            await self._save_user_profiles()

            # Save metrics
            await save_metrics("recommendation_metrics", self.recommendation_metrics)

            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            logger.error(traceback.format_exc())
            # Return fallback recommendations on error
            return self._generate_fallback_recommendations(user_id)

    def _generate_fallback_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when personalized ones cannot be created."""
        try:
            fallback_recs = []

            # Fixed: Access viewed_documents directly from UserProfile object
            if user_id in self.users:
                viewed_docs = set(self.users[user_id].viewed_documents)
            else:
                # Create user if doesn't exist
                self.users[user_id] = UserProfile(user_id=user_id)
                viewed_docs = set()

            logger.info(
                f"Generating fallback recommendations for user {user_id} with {len(viewed_docs)} viewed docs"
            )

            # First try to recommend unviewed documents
            count = 0
            for doc in self.documents:
                if doc.id not in viewed_docs and count < 3:
                    fallback_recs.append(
                        {
                            "document_id": doc.id,
                            "title": doc.title,
                            "path": doc.path,
                            "explanation": "Recommended resource about Shakers",
                            "relevance_score": 0.5,
                            "tags": doc.tags if hasattr(doc, "tags") else [],
                        }
                    )
                    count += 1
                    logger.info(f"Added fallback recommendation: {doc.title}")

            # If we couldn't find enough unviewed documents, include some viewed ones
            # with a different explanation
            if len(fallback_recs) < 2 and len(self.documents) > 0:
                logger.info("Not enough unviewed documents, including viewed ones")
                # Sort documents by some criteria (here we just use the first few)
                for doc in self.documents:
                    if count < 3:  # Still limit to 3 total recommendations
                        # Skip if already added
                        if any(rec["document_id"] == doc.id for rec in fallback_recs):
                            continue

                        fallback_recs.append(
                            {
                                "document_id": doc.id,
                                "title": doc.title,
                                "path": doc.path,
                                "explanation": (
                                    "This resource may be worth reviewing again"
                                    if doc.id in viewed_docs
                                    else "Recommended resource about Shakers"
                                ),
                                "relevance_score": 0.4,  # Lower score for viewed documents
                                "tags": doc.tags if hasattr(doc, "tags") else [],
                            }
                        )
                        count += 1
                        logger.info(f"Added supplementary recommendation: {doc.title}")

            logger.info(f"Created {len(fallback_recs)} fallback recommendations")
            return fallback_recs
        except Exception as e:
            logger.error(f"Error creating fallback recommendations: {e}")
            logger.error(traceback.format_exc())
            # Return empty list as a last resort
            return []

    def _extract_tech_terms(self, query: str) -> List[str]:
        """Extract technical terms from a query to enhance skill-based searches."""
        # Common tech skills/frameworks to look for
        tech_terms = [
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

        # Find matching terms in the query
        query_lower = query.lower()
        matching_terms = []

        for term in tech_terms:
            if term in query_lower:
                matching_terms.append(term)

        return matching_terms

    def _generate_enhanced_explanation(
        self,
        document: Document,
        query: str,
        similarity: float,
        user_profile: UserProfile,
    ) -> str:
        """Generate a personalized explanation for why a document is being recommended."""
        # Look for matching interests
        matching_interests = [
            interest
            for interest in user_profile.interests
            if interest.document_id == document.id
            or interest.topic.lower() in document.title.lower()
        ]

        if similarity > 0.8:
            return f"Highly relevant to your current question about {' '.join(query.split()[:3])}..."
        elif matching_interests:
            interest = matching_interests[0]
            time_frame = (
                "recent"
                if (datetime.now() - interest.last_mentioned).days < 3
                else "previous"
            )
            return f"Based on your {time_frame} interest in {interest.topic}"
        elif similarity > 0.6:
            return f"Related to topics you've been exploring about Shakers"
        elif similarity > 0.4:
            return f"This provides helpful context for your question about Shakers"
        else:
            return "Recommended to help you understand Shakers better"

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for recommendation system."""
        metrics = {
            "total_recommendations": self.recommendation_metrics[
                "total_recommendations"
            ],
            "user_interactions": self.recommendation_metrics["user_interactions"],
            "interaction_rate": self.recommendation_metrics["user_interactions"]
            / max(1, self.recommendation_metrics["total_recommendations"]),
            "avg_diversity": sum(self.recommendation_metrics["diversity_scores"])
            / max(1, len(self.recommendation_metrics["diversity_scores"])),
            "avg_relevance": sum(self.recommendation_metrics["relevance_scores"])
            / max(1, len(self.recommendation_metrics["relevance_scores"])),
            "user_count": len(self.users),
        }
        return metrics
