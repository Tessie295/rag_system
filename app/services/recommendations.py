from datetime import datetime
import json
import os
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from app.models.schemas import UserProfile, Query, Document, Recommendation
from app.models.schemas import ChatMessage
from app.utils.helpers import logger

class RecommendationService:
    """Service for generating personalized content recommendations."""
    
    def __init__(self):
        """Initialize the recommendation service."""
        self.users: Dict[str, UserProfile] = {}
        self.documents: List[Document] = []
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english'
        )
        self.document_vectors = None
        self.initialized = False
    
    async def initialize(self, documents: List[Document]):
        """Initialize the recommendation service with documents."""
        if self.initialized:
            return
        
        self.documents = documents
        document_contents = [doc.content for doc in documents]
        self.document_vectors = self.tfidf_vectorizer.fit_transform(document_contents)
        await self._load_user_profiles()
        self.initialized = True
        logger.info("Recommendation service initialized successfully")
    
    async def _load_user_profiles(self):
        """Load user profiles from file if it exists."""
        users_file = os.path.join("app/data", "users_app.json")
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
    
    async def _save_user_profiles(self):
        """Save user profiles to file."""
        users_file = os.path.join("app/data", "users_app.json")
        try:
            with open(users_file, 'w') as f:
                users_data = [user.dict() for user in self.users.values()]
                json.dump(users_data, f, default=str)
            logger.info(f"Saved {len(self.users)} user profiles")
        except Exception as e:
            logger.error(f"Error saving user profiles: {e}")
    
    # async def add_query_to_user_history(self, user_id: str, query: str):
    #     """Add a query to the user's history."""
    #     if user_id not in self.users:
    #         self.users[user_id] = UserProfile(user_id=user_id)
        
    #     self.users[user_id].queries.append(Query(text=query, user_id=user_id))
    #     await self._save_user_profiles()
    
    async def add_chat_to_user_history(self, user_id: str, user_message: str, assistant_message: str):
        """Add a chat (user and assistant message) to the user's history."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)
        
        self.users[user_id].chat_history.append(
            ChatMessage(
                user_message=user_message,
                assistant_message=assistant_message,
                timestamp=datetime.now()
            )
        )
        
        # Save updated user profiles
        await self._save_user_profiles()
    
    async def mark_document_as_viewed(self, user_id: str, document_id: str):
        """Mark a document as viewed by the user."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)
        
        if document_id not in self.users[user_id].viewed_documents:
            self.users[user_id].viewed_documents.append(document_id)
            await self._save_user_profiles()
    
    async def generate_recommendations(self, user_id: str, current_query: str) -> List[Recommendation]:
        """Generate personalized recommendations based on user history and current query."""
        if not self.initialized:
            logger.error("Recommendation service not initialized")
            return []
        
        user_profile = self.users.get(user_id, UserProfile(user_id=user_id))
        
        # Extract user queries from chat history instead of using the queries array
        query_history = [chat.user_message for chat in user_profile.chat_history]
        all_queries = query_history + [current_query]
        
        if not query_history:
            query_text = current_query
        else:
            query_text = " ".join(all_queries[-3:] * 2 + all_queries)
        
        # Rest of the method remains the same
        query_vector = self.tfidf_vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vector, self.document_vectors).flatten()
        viewed_documents = set(user_profile.viewed_documents)
        
        document_similarities = [(i, sim) for i, sim in enumerate(similarities)]
        document_similarities.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for doc_idx, similarity in document_similarities:
            if len(recommendations) >= settings.MAX_RECOMMENDATIONS:
                break
                
            doc = self.documents[doc_idx]
            if doc.id not in viewed_documents:
                explanation = self._generate_explanation(doc, current_query, similarity)
                recommendations.append(
                    Recommendation(
                        document_id=doc.id,
                        title=doc.title,
                        path=doc.path,
                        explanation=explanation,
                        relevance_score=float(similarity)
                    )
                )
        
        return recommendations
    
    def _generate_explanation(self, document: Document, query: str, similarity: float) -> str:
        """Generate an explanation for why a document is being recommended."""
        if similarity > 0.8:
            return f"Highly relevant to your current question about {' '.join(query.split()[:3])}..."
        elif similarity > 0.6:
            return f"Related to topics you've been exploring in Shakers"
        else:
            return "You might find this useful to understand Shakers better"