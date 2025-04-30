"""
Enhanced recommendation service that leverages search and user profiles.
"""
from datetime import datetime, timedelta
import json
import os
import traceback
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import asyncio

from app.config import settings
from app.models.schemas import (
    UserProfile, 
    Query, 
    Document, 
    Recommendation, 
    ChatMessage, 
    UserInterest
)
from app.utils.helpers import logger, save_metrics, load_metrics
from app.utils.search import SearchEngine

class EnhancedRecommendationService:
    """Enhanced service for generating personalized content recommendations."""
    
    def __init__(self):
        """Initialize the recommendation service with improved capabilities."""
        self.users: Dict[str, UserProfile] = {}
        self.documents: List[Document] = []
        self.search_engine = SearchEngine()
        
        # Document vectors and categories
        self.document_categories = {}
        self.initialized = False
        
        # Enhanced metrics tracking
        self.recommendation_metrics = {
            "total_recommendations": 0,
            "user_interactions": 0,
            "diversity_scores": [],
            "relevance_scores": [],
            "user_satisfaction": defaultdict(list)  # This creates an empty list for any new key automatically
        }
    
    async def initialize(self, documents: List[Document]):
        """Initialize the recommendation service with improved document analysis."""
        if self.initialized:
            return
        
        self.documents = documents
        
        # Initialize search engine
        self.search_engine.initialize(documents)
        
        # Categorize documents
        await self._categorize_documents()
        
        # Load user profiles
        await self._load_user_profiles()
        
        # Load metrics if they exist
        stored_metrics = await load_metrics("recommendation_metrics")
        if stored_metrics:
            self.recommendation_metrics.update(stored_metrics)
        
        self.initialized = True
        logger.info("Enhanced recommendation service initialized successfully")
    
    async def _categorize_documents(self):
        """Categorize documents for better recommendations."""
        # Group documents by path pattern
        categories = {
            'general': [],
            'talent': [],
            'payments': [],
            'technical': [],
            'guides': []
        }
        
        for doc in self.documents:
            # Assign category based on path and content
            if 'freelancer-profiles' in doc.path or 'talent' in doc.path:
                categories['talent'].append(doc.id)
                self.document_categories[doc.id] = 'talent'
            elif 'payment' in doc.path:
                categories['payments'].append(doc.id)
                self.document_categories[doc.id] = 'payments'
            elif 'technical' in doc.path or 'shakers-technical-documentation' in doc.path:
                categories['technical'].append(doc.id)
                self.document_categories[doc.id] = 'technical'
            elif 'guide' in doc.path or 'how-to' in doc.path or 'finding_talent' in doc.path:
                categories['guides'].append(doc.id)
                self.document_categories[doc.id] = 'guides'
            else:
                categories['general'].append(doc.id)
                self.document_categories[doc.id] = 'general'
        
        logger.info(f"Categorized {len(self.documents)} documents into {len(categories)} categories")
    
    async def _load_user_profiles(self):
        """Load user profiles from file with better error handling."""
        users_file = os.path.join(settings.DATA_DIR, "users.json")
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                    for user_data in users_data:
                        user_id = user_data.get('user_id')
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
            with open(users_file, 'w') as f:
                # Convert datetime objects to strings
                users_data = [user.dict() for user in self.users.values()]
                json.dump(users_data, f, default=str)
            logger.info(f"Saved {len(self.users)} user profiles")
            return True
        except Exception as e:
            logger.error(f"Error saving user profiles: {e}")
            return False
    
    async def add_chat_to_user_history(self, user_id: str, user_message: str, assistant_message: str, 
                                      sources_used: List[str] = None):
        """Add a chat to history and update user interests with source tracking."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)
        
        # Add message to chat history with sources
        sources_list = sources_used or []
        self.users[user_id].chat_history.append(
            ChatMessage(
                user_message=user_message,
                assistant_message=assistant_message,
                timestamp=datetime.now(),
                sources_used=sources_list
            )
        )
        
        # Extract interests from user message
        await self._update_user_interests(user_id, user_message, sources_list)
        
        # Save updated profiles
        await self._save_user_profiles()
    
    async def _update_user_interests(self, user_id: str, message: str, sources_used: List[str] = None):
        """Extract and update user interests from message content and used sources."""
        if not self.initialized:
            return
        
        # Analyze the message for topics
        topics = self._extract_topics(message)
        
        # Track source interest
        if sources_used:
            for source_id in sources_used:
                # Find the document
                doc = next((doc for doc in self.documents if doc.id == source_id), None)
                if not doc:
                    continue
                
                # Get category
                category = self.document_categories.get(doc.id, 'general')
                
                # Check if interest already exists
                interest_exists = False
                for interest in self.users[user_id].interests:
                    if interest.document_id == doc.id:
                        # Update existing interest
                        interest.strength += 0.3  # Significant boost for source usage
                        interest.last_mentioned = datetime.now()
                        interest_exists = True
                        break
                
                # Add new interest if it doesn't exist
                if not interest_exists:
                    self.users[user_id].interests.append(
                        UserInterest(
                            topic=doc.title,
                            document_id=doc.id,
                            category=category,
                            strength=1.0,  # Start with high strength for viewed sources
                            first_mentioned=datetime.now(),
                            last_mentioned=datetime.now()
                        )
                    )
        
        # Add interests from extracted topics
        for topic, score in topics:
            # Check for existing topic interest
            topic_exists = False
            for interest in self.users[user_id].interests:
                if interest.topic.lower() == topic.lower():
                    interest.strength += 0.2 * score
                    interest.last_mentioned = datetime.now()
                    topic_exists = True
                    break
            
            # Add new topic if it doesn't exist
            if not topic_exists and score > 0.5:  # Only add significant topics
                # Find most relevant document for this topic
                relevant_docs = self.search_engine.search(topic, limit=1)
                if relevant_docs:
                    doc, _ = relevant_docs[0]
                    category = self.document_categories.get(doc.id, 'general')
                    
                    self.users[user_id].interests.append(
                        UserInterest(
                            topic=topic,
                            document_id=doc.id,
                            category=category,
                            strength=score,
                            first_mentioned=datetime.now(),
                            last_mentioned=datetime.now()
                        )
                    )
        
        # Decay old interests
        for interest in self.users[user_id].interests:
            days_since_mention = (datetime.now() - interest.last_mentioned).days
            if days_since_mention > 0:
                interest.strength *= (0.95 ** days_since_mention)  # Exponential decay
    
    def _extract_topics(self, text: str) -> List[Tuple[str, float]]:
        """Extract topics of interest from text with relevance scores."""
        # Define common topics by category
        topics_by_category = {
            "talent": ["freelancer", "developer", "designer", "writer", "marketer", 
                     "consultant", "hiring", "talent", "skills", "expert", "profiles"],
            "payments": ["payment", "fee", "escrow", "milestone", "transaction", "invoice"],
            "technical": ["architecture", "api", "database", "security", "integration", "deployment"],
            "platform": ["account", "profile", "contract", "proposal", "reviews"]
        }
        
        # Flatten topics for checking
        all_topics = []
        for category, topics in topics_by_category.items():
            for topic in topics:
                all_topics.append((topic, category))
        
        # Count topic mentions
        topic_scores = {}
        text_lower = text.lower()
        
        for topic, category in all_topics:
            # Check for exact word match with word boundaries
            count = len(re.findall(r'\b' + re.escape(topic) + r'\b', text_lower))
            if count > 0:
                score = min(1.0, 0.4 + (count * 0.2))  # Score increases with frequency
                topic_scores[topic] = score
        
        # Extract potential technical skills
        tech_skills = self.search_engine.tech_skills
        for skill in tech_skills:
            if skill in text_lower:
                score = 0.7  # Technical skills are highly relevant
                topic_scores[skill] = score
        
        # Return topics sorted by score
        return sorted(
            [(topic, score) for topic, score in topic_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )
    
    async def mark_document_as_viewed(self, user_id: str, document_id: str):
        """Mark a document as viewed and update metrics."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)
        
        if document_id not in self.users[user_id].viewed_documents:
            self.users[user_id].viewed_documents.append(document_id)
            
            # Add as an interest with high strength
            doc = next((doc for doc in self.documents if doc.id == document_id), None)
            if doc:
                category = self.document_categories.get(doc.id, 'general')
                
                # Check if interest already exists
                interest_exists = False
                for interest in self.users[user_id].interests:
                    if interest.document_id == doc.id:
                        # Update existing interest
                        interest.strength += 0.5  # Strong boost for explicit viewing
                        interest.last_mentioned = datetime.now()
                        interest_exists = True
                        break
                
                # Add new interest if it doesn't exist
                if not interest_exists:
                    self.users[user_id].interests.append(
                        UserInterest(
                            topic=doc.title,
                            document_id=doc.id,
                            category=category,
                            strength=1.0,  # High initial strength for viewed docs
                            first_mentioned=datetime.now(),
                            last_mentioned=datetime.now()
                        )
                    )
            
            # Update interaction metrics
            self.recommendation_metrics["user_interactions"] += 1
            
            # Find if this was a recommended document
            for rec in self.users[user_id].recent_recommendations:
                if rec.document_id == document_id:
                    # Record satisfaction based on relevance
                    # Ensure user_id exists in the user_satisfaction dictionary
                    if user_id not in self.recommendation_metrics["user_satisfaction"]:
                        self.recommendation_metrics["user_satisfaction"][user_id] = []
                    self.recommendation_metrics["user_satisfaction"][user_id].append(rec.relevance_score)
                    break
            
            await self._save_user_profiles()
            
            # Save updated metrics
            await save_metrics("recommendation_metrics", self.recommendation_metrics)
    
    def _calculate_diversity_score(self, doc_ids: List[str]) -> float:
        """Calculate diversity score based on document categories."""
        if len(doc_ids) <= 1:
            return 1.0  # Maximum diversity with 0-1 items
        
        # Count categories
        categories = [self.document_categories.get(doc_id, 'general') for doc_id in doc_ids]
        unique_categories = set(categories)
        
        # Diversity increases with unique categories
        category_diversity = len(unique_categories) / len(doc_ids)
        
        return category_diversity
    
    async def generate_recommendations(self, user_id: str, current_query: str) -> List[Dict[str, Any]]:
        """Generate personalized recommendations with diversity considerations."""
        if not self.initialized:
            logger.warning("Recommendation service not initialized - returning empty recommendations")
            return []
        
        # Add debugging to trace the recommendation flow
        logger.info(f"Generating recommendations for user {user_id} with query: {current_query}")
        
        # Ensure user exists
        if user_id not in self.users:
            logger.info(f"Creating new user profile for {user_id}")
            self.users[user_id] = UserProfile(user_id=user_id)
        
        user_profile = self.users[user_id]
        
        try:
            # Analyze query intent
            intent = self.search_engine.analyze_intent(current_query)
            
            # Get viewed documents to exclude
            viewed_documents = set(user_profile.viewed_documents)
            logger.debug(f"User has viewed {len(viewed_documents)} documents")
            
            # Find documents related to the current query
            query_recommendations = await self._get_query_recommendations(
                current_query, viewed_documents, intent, limit=3
            )
            
            # Get recommendations based on user interests
            interest_recommendations = await self._get_interest_recommendations(
                user_id, current_query, viewed_documents, limit=2
            )
            
            # Combine and deduplicate recommendations
            combined_recommendations = query_recommendations.copy()
            
            # Add interest-based recommendations if not already included
            for rec in interest_recommendations:
                if not any(r["document_id"] == rec["document_id"] for r in combined_recommendations):
                    combined_recommendations.append(rec)
            
            # Limit to max recommendations
            recommendations = combined_recommendations[:settings.MAX_RECOMMENDATIONS]
            
            # If we still don't have enough recommendations, add some general ones
            if len(recommendations) < settings.MAX_RECOMMENDATIONS:
                general_recs = await self._generate_fallback_recommendations(
                    user_id, limit=settings.MAX_RECOMMENDATIONS - len(recommendations)
                )
                
                for rec in general_recs:
                    if not any(r["document_id"] == rec["document_id"] for r in recommendations):
                        recommendations.append(rec)
            
            # Calculate diversity score
            doc_ids = [rec["document_id"] for rec in recommendations]
            diversity_score = self._calculate_diversity_score(doc_ids)
            
            # Update metrics
            self.recommendation_metrics["total_recommendations"] += len(recommendations)
            
            # Track diversity score
            diversity_score = self._calculate_diversity_score(doc_ids)
            self.recommendation_metrics["diversity_scores"].append(diversity_score)
            
            # Track relevance scores
            for rec in recommendations:
                self.recommendation_metrics["relevance_scores"].append(rec["relevance_score"])
            
            # Store recommendations with user
            user_profile.recent_recommendations = [
                Recommendation(
                    document_id=rec["document_id"],
                    title=rec["title"],
                    path=rec["path"],
                    explanation=rec["explanation"],
                    relevance_score=rec["relevance_score"],
                    tags=rec.get("tags", [])
                ) for rec in recommendations
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
            return await self._generate_fallback_recommendations(user_id)
    
    async def _get_query_recommendations(self, query: str, viewed_docs: set, 
                                       intent: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """Get recommendations based on the current query."""
        recommendations = []
        
        # Use the search engine to find relevant documents
        if intent["is_talent_search"]:
            # This is a talent search query, prioritize talent profiles
            search_results = self.search_engine.search_talent(query, limit=limit)
        else:
            # Regular query, use enhanced query if available
            enhanced_query = intent.get("enhanced_query", query)
            search_results = self.search_engine.search(enhanced_query, limit=limit + 2)
        
        # Convert search results to recommendations
        for doc, score in search_results:
            # Skip if already viewed
            if doc.id in viewed_docs:
                continue
            
            # Skip if already in recommendations
            if any(r["document_id"] == doc.id for r in recommendations):
                continue
            
            # Generate explanation
            if intent["is_talent_search"]:
                skills = intent.get("skills_mentioned", [])
                if skills:
                    skills_text = ", ".join(skills[:2])
                    explanation = f"Profile with expertise in {skills_text}"
                else:
                    explanation = "Talent profile matching your search criteria"
            else:
                explanation = "Relevant to your current question"
            
            # Add document to recommendations
            recommendations.append({
                "document_id": doc.id,
                "title": doc.title,
                "path": doc.path,
                "explanation": explanation,
                "relevance_score": float(score),
                "tags": doc.tags if hasattr(doc, "tags") and doc.tags else []
            })
            
            # Stop when we have enough
            if len(recommendations) >= limit:
                break
        
        return recommendations
    
    async def _get_interest_recommendations(self, user_id: str, current_query: str, 
                                          viewed_docs: set, limit: int = 2) -> List[Dict[str, Any]]:
        """Get recommendations based on user interests."""
        user_profile = self.users[user_id]
        recommendations = []
        
        # Skip if no interests
        if not user_profile.interests:
            return []
        
        # Sort interests by strength
        sorted_interests = sorted(
            user_profile.interests, 
            key=lambda x: x.strength,
            reverse=True
        )
        
        # Take top interests
        top_interests = sorted_interests[:5]
        
        # Keep track of categories to ensure diversity
        used_categories = set()
        
        for interest in top_interests:
            # Skip if too many from this category already
            category = interest.category
            if category in used_categories and len(used_categories) < 3:
                continue
            
            # Get documents related to this interest
            interest_query = f"{interest.topic}"
            search_results = self.search_engine.search(interest_query, limit=2)
            
            for doc, score in search_results:
                # Skip if already viewed
                if doc.id in viewed_docs:
                    continue
                
                # Skip if already in recommendations
                if any(r["document_id"] == doc.id for r in recommendations):
                    continue
                
                # Generate explanation
                days_since = (datetime.now() - interest.last_mentioned).days
                if days_since < 1:
                    time_frame = "your current interests"
                elif days_since < 7:
                    time_frame = "your recent interests"
                else:
                    time_frame = "topics you've explored before"
                
                explanation = f"Based on {time_frame} in {interest.topic}"
                
                # Add document to recommendations
                recommendations.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "path": doc.path,
                    "explanation": explanation,
                    "relevance_score": float(score) * 0.9,  # Slightly lower than direct matches
                    "tags": doc.tags if hasattr(doc, "tags") and doc.tags else []
                })
                
                # Track category
                used_categories.add(category)
                
                # Stop when we have enough
                if len(recommendations) >= limit:
                    break
            
            # Stop when we have enough
            if len(recommendations) >= limit:
                break
        
        return recommendations
    
    async def _generate_fallback_recommendations(self, user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when personalized ones cannot be created."""
        try:
            fallback_recs = []
            
            # Get viewed docs
            if user_id in self.users:
                viewed_docs = set(self.users[user_id].viewed_documents)
            else:
                # Create user if doesn't exist
                self.users[user_id] = UserProfile(user_id=user_id)
                viewed_docs = set()
            
            # Get documents from different categories
            categories = ['general', 'talent', 'payments', 'technical', 'guides']
            used_categories = set()
            
            # Select one document from each category
            for category in categories:
                if len(fallback_recs) >= limit:
                    break
                
                # Find documents in this category
                category_docs = [doc for doc in self.documents 
                              if self.document_categories.get(doc.id) == category]
                
                # Skip if no documents in this category
                if not category_docs:
                    continue
                
                # First try unviewed documents
                unviewed_docs = [doc for doc in category_docs if doc.id not in viewed_docs]
                
                if unviewed_docs:
                    # Select a random unviewed document
                    doc = np.random.choice(unviewed_docs)
                    
                    fallback_recs.append({
                        "document_id": doc.id,
                        "title": doc.title,
                        "path": doc.path,
                        "explanation": f"Recommended resource about {category.title()}",
                        "relevance_score": 0.5,
                        "tags": doc.tags if hasattr(doc, "tags") and doc.tags else []
                    })
                    
                    used_categories.add(category)
                elif len(viewed_docs) < len(category_docs):
                    # Select a viewed document that hasn't been recommended yet
                    candidates = [doc for doc in category_docs 
                               if not any(rec["document_id"] == doc.id for rec in fallback_recs)]
                    
                    if candidates:
                        doc = np.random.choice(candidates)
                        
                        fallback_recs.append({
                            "document_id": doc.id,
                            "title": doc.title,
                            "path": doc.path,
                            "explanation": "This resource may be worth reviewing again",
                            "relevance_score": 0.4,
                            "tags": doc.tags if hasattr(doc, "tags") and doc.tags else []
                        })
                        
                        used_categories.add(category)
                else:
                    # All documents in this category have been viewed and recommended
                    continue
            
            return fallback_recs
        
        except Exception as e:
            logger.error(f"Error creating fallback recommendations: {e}")
            logger.error(traceback.format_exc())
            
            # Return minimal recommendations as a last resort
            return [{
                "document_id": doc.id,
                "title": doc.title,
                "path": doc.path,
                "explanation": "Recommended resource about Shakers",
                "relevance_score": 0.3,
                "tags": doc.tags if hasattr(doc, "tags") and doc.tags else []
            } for doc in self.documents[:limit] if doc]
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for recommendation system."""
        metrics = {
            "total_recommendations": self.recommendation_metrics["total_recommendations"],
            "user_interactions": self.recommendation_metrics["user_interactions"],
            "interaction_rate": self.recommendation_metrics["user_interactions"] / max(1, self.recommendation_metrics["total_recommendations"]),
            "avg_diversity": sum(self.recommendation_metrics["diversity_scores"]) / max(1, len(self.recommendation_metrics["diversity_scores"])),
            "avg_relevance": sum(self.recommendation_metrics["relevance_scores"]) / max(1, len(self.recommendation_metrics["relevance_scores"])),
            "user_count": len(self.users)
        }
        return metrics