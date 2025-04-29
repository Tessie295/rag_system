import os
import time
import json
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from langchain.chains.question_answering import load_qa_chain
from langchain.chains import RetrievalQA
from sklearn.metrics.pairwise import cosine_similarity
import concurrent.futures
import asyncio
import functools
import threading
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.models.schemas import Document, Source, RAGResponse, QueryEvaluation
from app.utils.helpers import (
    load_knowledge_base,
    chunk_text,
    is_out_of_scope,
    time_function,
    logger,
    save_metrics
)
from app.utils.evaluation import evaluate_answer

class RAGService:
    """Enhanced Retrieval-Augmented Generation service with optimized performance."""
    
    def __init__(self):
        """Initialize the RAG service with improved components."""
        self.llm = ChatOpenAI(
            model_name=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            request_timeout=settings.LLM_TIMEOUT  # Add timeout to prevent hanging
        )
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            request_timeout=settings.EMBEDDINGS_TIMEOUT  # Add timeout
        )
        
        # Optimize text splitter for faster processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self.vector_store = None
        self.documents = []
        self.initialized = False
        self.last_update_timestamp = None
        
        # Response cache for frequently asked questions
        self.response_cache = {}
        
        # Add a ThreadPoolExecutor for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Enhanced RAG prompt template 
        self.rag_template = ChatPromptTemplate.from_template(
            """You are an AI assistant for Shakers, a platform that connects clients with freelance talent.
            Answer the following question based ONLY on the provided context. 
            
            Context:
            {context}
            
            Question: {query}
            
            Important instructions for skill-based queries:
            - If the question asks about people with specific skills (like Python, Angular, React, etc.), identify ALL profiles that mention those skills.
            - A person is considered to have expertise in a technology if it's listed in their skills section, EVEN IF their job title doesn't explicitly mention it.
            - For example, a "Full-Stack Developer" with "Angular" in their skills list should be considered an Angular developer.
            - If you find ANY matches in the context that have the requested skill, include them in your answer.
            - If you don't find a PERFECT match, but find someone with related skills, include them rather than saying you don't have information.
            
            Your answer should be clear, concise, and directly address the question. When using information from the context, cite the specific document like this: [Document: Title]. Be thorough - if the information exists in the context, make sure to provide it.
            """
        )
        
        # Alternative template for ambiguous queries 
        self.ambiguous_template = ChatPromptTemplate.from_template(
            """You are an AI assistant for Shakers. The user asked an ambiguous question.
            Based on the provided context, provide the most helpful response possible.
            
            Context:
            {context}
            
            Question: {query}
            
            Acknowledge the ambiguity briefly, then provide helpful information from the sources.
            Keep your response under 150 words for faster delivery.
            """
        )
        
        self.rag_chain = LLMChain(llm=self.llm, prompt=self.rag_template)
        self.ambiguous_chain = LLMChain(llm=self.llm, prompt=self.ambiguous_template)
        
        # Add evaluation metrics tracking
        self.query_metrics = {
            "total_queries": 0,
            "answered_queries": 0,
            "out_of_scope_queries": 0,
            "processing_times": [],
            "relevance_scores": []
        }
    
    async def initialize(self, force_refresh=False):
        """Initialize the RAG service with optimized loading."""
        if self.initialized and not force_refresh:
            return
        
        # Check if vector store exists and is recent enough
        vector_store_exists = os.path.exists(settings.VECTOR_DB_PATH)
        
        if vector_store_exists and not force_refresh:
            try:
                # Load existing vector store with allow_dangerous_deserialization=True
                logger.info("Loading existing vector store...")
                start_time = time.time()
                self.vector_store = FAISS.load_local(
                    settings.VECTOR_DB_PATH, 
                    self.embeddings,
                    allow_dangerous_deserialization=True  
                )
                logger.info(f"Vector store loaded in {time.time() - start_time:.2f} seconds")
                
                # Load documents from the knowledge base
                logger.info("Loading knowledge base documents...")
                start_time = time.time()
                
                # Use the executor for parallel loading
                def load_docs():
                    return load_knowledge_base(settings.KNOWLEDGE_BASE_DIR)
                
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                raw_documents = await loop.run_in_executor(self.executor, load_docs)
                
                self.documents = [Document(**doc) for doc in raw_documents]
                logger.info(f"Documents loaded in {time.time() - start_time:.2f} seconds")
                
                self.initialized = True
                self.last_update_timestamp = time.time()
                logger.info("RAG service initialized from existing vector store")
                return
            except Exception as e:
                logger.error(f"Error loading existing vector store: {e}")
                logger.info("Will create a new vector store instead")
            
        # Create new vector store with optimized processing
        logger.info("Creating new vector store...")
        start_time = time.time()
        
        # Load documents in a background thread
        loop = asyncio.get_event_loop()
        raw_documents = await loop.run_in_executor(
            self.executor, 
            lambda: load_knowledge_base(settings.KNOWLEDGE_BASE_DIR)
        )
        
        self.documents = [Document(**doc) for doc in raw_documents]
        
        # Process documents for the vector store with optimized chunking
        async def process_document(doc):
            chunks = self.text_splitter.split_text(doc.content)
            
            result = []
            for i, chunk in enumerate(chunks):
                result.append(
                    LangchainDocument(
                        page_content=chunk,
                        metadata={
                            "document_id": doc.id,
                            "title": doc.title,
                            "path": doc.path,
                            "chunk_id": i,
                            "doc_source": "knowledge_base"
                        }
                    )
                )
            return result
        
        # Process documents in parallel for faster initialization
        tasks = [process_document(doc) for doc in self.documents]
        results = await asyncio.gather(*tasks)
        
        # Flatten the results
        langchain_docs = []
        for doc_chunks in results:
            langchain_docs.extend(doc_chunks)
        
        # Create vector store with optimized parameters
        self.vector_store = FAISS.from_documents(
            langchain_docs, 
            self.embeddings,
            normalize_L2=True  # Normalize vectors for better similarity search
        )

        # Save vector store for later reuse
        os.makedirs(os.path.dirname(settings.VECTOR_DB_PATH), exist_ok=True)
        try:
            logger.info(f"Saving vector store to {settings.VECTOR_DB_PATH}")
            self.vector_store.save_local(settings.VECTOR_DB_PATH)
            logger.info("Vector store saved successfully")
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            # Continue even if save fails - the in-memory store is still usable

        self.initialized = True
        self.last_update_timestamp = time.time()
        logger.info(f"RAG service initialized in {time.time() - start_time:.2f} seconds")
    
    async def update_knowledge_base(self):
        """Update the knowledge base with new documents."""
        logger.info("Updating knowledge base...")
        
        # Load the latest documents in background thread
        loop = asyncio.get_event_loop()
        raw_documents = await loop.run_in_executor(
            self.executor,
            lambda: load_knowledge_base(settings.KNOWLEDGE_BASE_DIR)
        )
        
        new_documents = [Document(**doc) for doc in raw_documents]
        
        # Compare with existing documents to find new ones
        existing_ids = {doc.id for doc in self.documents}
        docs_to_add = [doc for doc in new_documents if doc.id not in existing_ids]
        
        if not docs_to_add:
            logger.info("No new documents found")
            return False
        
        logger.info(f"Found {len(docs_to_add)} new documents to add")
        
        # Process new documents in parallel
        async def process_document(doc):
            chunks = self.text_splitter.split_text(doc.content)
            result = []
            for i, chunk in enumerate(chunks):
                result.append(
                    LangchainDocument(
                        page_content=chunk,
                        metadata={
                            "document_id": doc.id,
                            "title": doc.title,
                            "path": doc.path,
                            "chunk_id": i,
                            "doc_source": "knowledge_base",
                            "added_date": time.time()
                        }
                    )
                )
            return result
            
        tasks = [process_document(doc) for doc in docs_to_add]
        results = await asyncio.gather(*tasks)
        
        # Flatten the results
        langchain_docs = []
        for doc_chunks in results:
            langchain_docs.extend(doc_chunks)
        
        # Add to vector store
        self.vector_store.add_documents(langchain_docs)
        
        # Save updated vector store
        self.vector_store.save_local(settings.VECTOR_DB_PATH)
        
        # Update document list
        self.documents = new_documents
        self.last_update_timestamp = time.time()
        
        # Clear the cache when knowledge base is updated
        self.response_cache = {}
        
        logger.info(f"Knowledge base updated with {len(docs_to_add)} new documents")
        return True
    
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the query with improved detection for skill and profile searches."""
        # Check cache for frequent queries to avoid redundant processing
        cache_key = f"analysis_{query}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]
        
        # Enhanced preprocessing for skill and profile queries
        query_lower = query.lower()
        is_skill_query = any(term in query_lower for term in [
            "skill", "expertise", "proficiency", "knowledge", "angular", "react", 
            "python", "java", "developer", "engineer", "programmer"
        ])
        is_profile_query = any(term in query_lower for term in [
            "profile", "freelancer", "consultant", "expert", "professional", 
            "talent", "who knows", "who has experience", "find me"
        ])
        
        # Adjust query for better retrieval if it's about skills or profiles
        search_query = query
        if is_skill_query or is_profile_query:
            # Expand search terms to improve recall for these query types
            tech_terms = self._extract_tech_terms(query)
            if tech_terms:
                expanded_terms = []
                for term in tech_terms:
                    expanded_terms.append(term)
                    # For development skills, also search for related job titles
                    if term in ["angular", "react", "vue", "javascript", "python", "java"]:
                        expanded_terms.extend(["developer", "engineer", "programmer", "coder"])
                    # For design skills, also search for related job titles
                    elif term in ["ui", "ux", "design", "figma"]:
                        expanded_terms.extend(["designer", "creative", "artist"])
                        
                search_query = f"{query} {' '.join(expanded_terms)}"
                logger.debug(f"Expanded query: {search_query}")
        
        # Get initial retrieval results with the enhanced query
        start_time = time.time()
        retrieval_results = self.vector_store.similarity_search_with_score(
            search_query, k=min(settings.MAX_SOURCES * 2, 8)  
        )
        retrieval_time = time.time() - start_time
        logger.debug(f"Retrieval completed in {retrieval_time:.4f}s")
        
        # Extract relevance scores
        relevance_scores = [float(1.0 - score) for _, score in retrieval_results]
        
        # Determine query type
        query_analysis = {
            "type": "normal",
            "is_ambiguous": False,
            "is_out_of_scope": False,
            "max_relevance": max(relevance_scores) if relevance_scores else 0,
            "avg_relevance": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
            "relevance_variance": np.var(relevance_scores) if len(relevance_scores) > 1 else 0,
            "retrieval_time": retrieval_time,
            "is_skill_query": is_skill_query,
            "is_profile_query": is_profile_query
        }
        
        # Adjust out-of-scope detection for skill/profile queries
        if is_skill_query or is_profile_query:
            # Be more lenient with the threshold for these query types
            adjusted_threshold = settings.SIMILARITY_THRESHOLD * 0.8
            query_analysis["is_out_of_scope"] = max(relevance_scores) < adjusted_threshold if relevance_scores else True
        else:
            query_analysis["is_out_of_scope"] = max(relevance_scores) < settings.SIMILARITY_THRESHOLD if relevance_scores else True
        
        if query_analysis["is_out_of_scope"]:
            query_analysis["type"] = "out_of_scope"
        elif query_analysis["relevance_variance"] > settings.AMBIGUITY_THRESHOLD:
            query_analysis["is_ambiguous"] = True
            query_analysis["type"] = "ambiguous"
        
        # Cache the analysis for future use
        self.response_cache[cache_key] = query_analysis
        
        return query_analysis

    def _extract_tech_terms(self, query: str) -> List[str]:
        """Extract technical terms from a query to enhance skill-based searches."""
        # Common tech skills/frameworks to look for
        tech_terms = [
            "python", "javascript", "typescript", "java", "c#", "c++", "go", "golang", "rust",
            "react", "angular", "vue", "node", "express", "django", "flask", "spring",
            "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "devops",
            "machine learning", "ai", "data science", "nlp", "computer vision",
            "android", "ios", "mobile", "web", "frontend", "backend", "fullstack",
            "ui", "ux", "design", "figma", "sketch", "adobe", 
            "sql", "nosql", "postgresql", "mysql", "mongodb", "database",
            "terraform", "ansible", "jenkins", "cicd", "security"
        ]
        
        # Find matching terms in the query
        query_lower = query.lower()
        matching_terms = []
        
        for term in tech_terms:
            if term in query_lower:
                matching_terms.append(term)
        
        return matching_terms
    
    def _run_llm_chain(self, chain, context, query):
        """Synchronous wrapper to run LLM chain with timeout protection."""
        try:
            result = chain.run(context=context, query=query)
            return result
        except Exception as e:
            logger.error(f"Error running LLM chain: {e}")
            return "I apologize, but I'm having trouble processing your request. Please try a more specific question about Shakers."
    
    @time_function
    async def process_query(self, query: str, user_id: str = None) -> RAGResponse:
        """Process a user query with optimized retrieval and processing for speed."""
        start_time = time.time()
        
        if not self.initialized:
            await self.initialize()
        
        # Update metrics
        self.query_metrics["total_queries"] += 1
        
        # Check cache for exact query matches
        cache_key = f"response_{query}"
        if cache_key in self.response_cache and settings.ENABLE_CACHING:
            cached_response = self.response_cache[cache_key]
            logger.info(f"Retrieved response from cache for query: {query}")
            # Still record the processing time for metrics
            processing_time = time.time() - start_time
            self.query_metrics["processing_times"].append(processing_time)
            return cached_response
        
        # Analyze the query - optimized version
        query_analysis = await self.analyze_query(query)
        logger.debug(f"Query analysis completed in {time.time() - start_time:.4f}s")
        
        # If out of scope, return quickly without additional processing
        if query_analysis["is_out_of_scope"]:
            logger.info(f"Query identified as out of scope: {query}")
            self.query_metrics["out_of_scope_queries"] += 1
            
            # Create a quick response without further processing
            answer = "I'm sorry, I don't have enough information to answer this question about Shakers. This topic appears to be outside the scope of my knowledge about the platform."
            
            # Record the processing time for metrics
            processing_time = time.time() - start_time
            self.query_metrics["processing_times"].append(processing_time)
            
            response = RAGResponse(
                query=query,
                answer=answer,
                sources=[],
                processing_time=processing_time,
                query_type="out_of_scope",
                evaluation=None
            )
            
            # Don't cache out-of-scope responses
            return response
        
        # Retrieve relevant documents - reuse results from query analysis if possible
        retrieval_start = time.time()
        retrieval_results = self.vector_store.similarity_search_with_score(
            query, k=settings.MAX_SOURCES
        )
        logger.debug(f"Document retrieval completed in {time.time() - retrieval_start:.4f}s")
        
        # Prepare context and sources - optimized for speed
        context_parts = []
        sources = []
        relevance_scores = []
        
        # Add document content to context with minimal formatting for speed
        for doc, score in retrieval_results:
            context_parts.append(f"--- Document: {doc.metadata['title']} ---\n{doc.page_content}")
            relevance_score = float(1.0 - score)
            relevance_scores.append(relevance_score)
            
            # Create source with minimal information for speed
            sources.append(Source(
                document_id=doc.metadata["document_id"],
                title=doc.metadata["title"],
                path=doc.metadata["path"],
                relevance_score=relevance_score
            ))
        
        # Join context parts for faster processing
        context = "\n\n".join(context_parts)
        
        # Store the relevance scores for metrics
        if relevance_scores:
            self.query_metrics["relevance_scores"].append(max(relevance_scores))
        
        # Choose the right chain based on query type
        llm_start = time.time()
        if query_analysis["is_ambiguous"]:
            logger.info(f"Processing ambiguous query: {query}")
            # Run LLM in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._run_llm_chain(self.ambiguous_chain, context, query)
            )
        else:
            logger.info(f"Processing standard query: {query}")
            # Run LLM in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._run_llm_chain(self.rag_chain, context, query)
            )
        
        answer = result.strip()
        self.query_metrics["answered_queries"] += 1
        logger.debug(f"LLM processing completed in {time.time() - llm_start:.4f}s")
        
        # Skip evaluation for faster responses
        evaluation = None
        if settings.ENABLE_EVALUATION and time.time() - start_time < 3.0:
            # Only evaluate if we have time within the performance budget
            try:
                evaluation_start = time.time()
                evaluation = await evaluate_answer(query, answer, [doc.page_content for doc, _ in retrieval_results])
                logger.debug(f"Evaluation completed in {time.time() - evaluation_start:.4f}s")
            except Exception as e:
                logger.error(f"Error during evaluation: {e}")
        
        # Record the total processing time
        processing_time = time.time() - start_time
        self.query_metrics["processing_times"].append(processing_time)
        
        # Create response
        response = RAGResponse(
            query=query,
            answer=answer,
            sources=sources,
            processing_time=processing_time,
            query_type="ambiguous" if query_analysis["is_ambiguous"] else "normal",
            evaluation=evaluation
        )
        
        # Cache the response for future identical queries
        if settings.ENABLE_CACHING and processing_time < 3.0: 
            self.response_cache[cache_key] = response
        
        # Log performance metrics
        logger.info(f"Query processed in {processing_time:.4f}s")
        
        # Save metrics in background to avoid blocking
        asyncio.create_task(save_metrics("rag_metrics", self.query_metrics))
        
        return response
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the RAG system."""
        metrics = {
            "total_queries": self.query_metrics["total_queries"],
            "answered_ratio": self.query_metrics["answered_queries"] / max(1, self.query_metrics["total_queries"]),
            "out_of_scope_ratio": self.query_metrics["out_of_scope_queries"] / max(1, self.query_metrics["total_queries"]),
            "avg_processing_time": sum(self.query_metrics["processing_times"]) / max(1, len(self.query_metrics["processing_times"])),
            "avg_relevance_score": sum(self.query_metrics["relevance_scores"]) / max(1, len(self.query_metrics["relevance_scores"])),
            "document_count": len(self.documents),
            "last_update": self.last_update_timestamp,
            "processing_times": self.query_metrics["processing_times"][-10:] if self.query_metrics["processing_times"] else []
        }
        return metrics