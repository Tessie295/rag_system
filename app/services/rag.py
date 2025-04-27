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

from app.config import settings
from app.models.schemas import Document, Source, RAGResponse
from app.utils.helpers import (
    load_knowledge_base,
    chunk_text,
    is_out_of_scope,
    time_function,
    logger
)

class RAGService:
    """Retrieval-Augmented Generation service for answering queries."""
    
    def __init__(self):
        """Initialize the RAG service."""
        self.llm = ChatOpenAI(
            model_name=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.2
        )
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.vector_store = None
        self.documents = []
        self.initialized = False
        
        # Define the RAG prompt template
        self.rag_template = ChatPromptTemplate.from_template(
            """You are an AI assistant for Shakers, a platform that connects clients with freelance talent.
            Answer the following question based ONLY on the provided context. If the question cannot be answered 
            based on the context, respond with "I don't have enough information to answer this question."
            
            Context:
            {context}
            
            Question: {query}
            
            Your answer should be clear, concise, and directly address the question. Include references to the 
            relevant documents where appropriate."""
        )
        self.rag_chain = LLMChain(llm=self.llm, prompt=self.rag_template)
    
    async def initialize(self):
        """Initialize the RAG service by loading documents and creating the vector store."""
        if self.initialized:
            return
        
        # Load documents from the knowledge base
        logger.info("Loading knowledge base documents...")
        raw_documents = load_knowledge_base(settings.KNOWLEDGE_BASE_DIR)
        self.documents = [Document(**doc) for doc in raw_documents]
        
        # Process documents for the vector store
        logger.info("Creating vector store...")
        langchain_docs = []
        for doc in self.documents:
            chunks = chunk_text(doc.content)
            for i, chunk in enumerate(chunks):
                langchain_docs.append(
                    LangchainDocument(
                        page_content=chunk,
                        metadata={
                            "document_id": doc.id,
                            "title": doc.title,
                            "path": doc.path,
                            "chunk_id": i
                        }
                    )
                )
        
        # Create vector store
        self.vector_store = FAISS.from_documents(langchain_docs, self.embeddings)
        
        # Save vector store for later reuse
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        self.vector_store.save_local(settings.VECTOR_DB_PATH)
        
        self.initialized = True
        logger.info("RAG service initialized successfully")
    
    @time_function
    async def process_query(self, query: str) -> RAGResponse:
        """Process a user query and generate a response with sources."""
        if not self.initialized:
            await self.initialize()
        
        # Retrieve relevant documents
        retrieval_results = self.vector_store.similarity_search_with_score(
            query, k=settings.MAX_SOURCES
        )
        
        # Prepare context and sources
        context = ""
        sources = []
        relevance_scores = []
        
        for doc, score in retrieval_results:
            context += f"\n\n--- Document: {doc.metadata['title']} ---\n{doc.page_content}"
            relevance_score = float(1.0 - score)  # Convert distance to similarity score
            relevance_scores.append(relevance_score)
            
            sources.append(Source(
                document_id=doc.metadata["document_id"],
                title=doc.metadata["title"],
                path=doc.metadata["path"],
                relevance_score=relevance_score
            ))
        
        logger.debug(f"Query: {query}, Relevance scores: {relevance_scores}, Threshold: {settings.SIMILARITY_THRESHOLD}")
        logger.debug(f"Out of scope result: {is_out_of_scope(query, settings.SIMILARITY_THRESHOLD, relevance_scores)}")
        
        # Check if query is out of scope
        if is_out_of_scope(query, settings.SIMILARITY_THRESHOLD, relevance_scores):
            answer = "I'm sorry, I don't have enough information to answer this question. This topic may be outside the scope of my knowledge about Shakers."
        else:
            # Generate answer using the RAG chain
            result = await self.rag_chain.arun(context=context, query=query)
            answer = result.strip()
        
        response = RAGResponse(
            query=query,
            answer=answer,
            sources=sources,
            processing_time=0.0  # Will be updated by the time_function decorator
        )
        
        return response
    


    