# Shakers AI Support System API Documentation

This document provides a comprehensive guide to the Shakers AI Support System API, following the OpenAPI/Swagger specification.

## Base URL

All API endpoints are accessible at: `http://localhost:8000/api`

## Authentication

Currently, the API does not require authentication. However, each request should include a unique user ID to personalize the experience and track user history.

## Endpoints

### Query Processing

#### `POST /query`

Process a user query to get an answer with relevant sources and recommendations.

**Request:**
```json
{
  "query": "string",
  "user_id": "string",
  "context": {}
}
```

**Response:**
```json
{
  "answer": "string",
  "sources": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "relevance_score": 0.0,
      "snippet": "string"
    }
  ],
  "recommendations": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "explanation": "string",
      "relevance_score": 0.0,
      "tags": ["string"]
    }
  ],
  "processing_time": 0.0,
  "evaluation": {
    "correctness_score": 0.0,
    "relevance_score": 0.0,
    "completeness_score": 0.0,
    "overall_score": 0.0,
    "feedback": "string"
  }
}
```

**Description:**
- `query`: The user's question about Shakers
- `user_id`: Unique identifier for the user
- `context`: Optional additional context for the query

**Response Fields:**
- `answer`: The generated response to the user's query
- `sources`: References to documents used to generate the answer
- `recommendations`: Personalized document recommendations
- `processing_time`: Time taken to process the query in seconds
- `evaluation`: Quality evaluation of the response (if enabled)

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `500`: Server error
- `503`: Service initializing

### Health Check

#### `GET /health`

Check the status and health of the API.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "string",
  "response_time_target": "string",
  "rag_status": "online",
  "recommendation_status": "online",
  "search_status": "online",
  "metrics": {
    "total_queries": 0,
    "answered_ratio": 0.0,
    "avg_processing_time": 0.0,
    "recent_processing_times": [0.0]
  }
}
```

**Description:**
Provides real-time information about the API's health and performance metrics.

**Status Codes:**
- `200`: Success

### Performance Metrics

#### `GET /metrics`

Get detailed performance metrics for monitoring.

**Response:**
```json
{
  "rag_metrics": {
    "total_queries": 0,
    "answered_ratio": 0.0,
    "out_of_scope_ratio": 0.0,
    "avg_processing_time": 0.0,
    "avg_relevance_score": 0.0,
    "document_count": 0,
    "last_update": "string",
    "processing_times": [0.0]
  },
  "recommendation_metrics": {
    "total_recommendations": 0,
    "user_interactions": 0,
    "interaction_rate": 0.0,
    "avg_diversity": 0.0,
    "avg_relevance": 0.0,
    "user_count": 0
  },
  "user_metrics": {
    "total_users": 0,
    "active_users_24h": 0,
    "avg_queries_per_user": 0.0,
    "user_satisfaction": {}
  },
  "system_health": {
    "uptime": "string",
    "memory_usage": "string",
    "documents_loaded": 0,
    "last_knowledge_base_update": "string",
    "api_status": "string"
  }
}
```

**Description:**
Provides comprehensive metrics about the system's performance and usage.

**Status Codes:**
- `200`: Success
- `503`: Services initializing

### Knowledge Base Management

#### `POST /knowledge-base/update`

Update the knowledge base with new documents.

**Response:**
```json
{
  "status": "success",
  "message": "Knowledge base updated successfully"
}
```

**Description:**
Triggers the system to scan for new documents and update the knowledge base.

**Status Codes:**
- `200`: Success
- `202`: Update in progress
- `500`: Update failed

### Document Management

#### `GET /documents`

Retrieve available documents with optional filtering.

**Parameters:**
- `category` (query, optional): Filter by document category
- `tag` (query, optional): Filter by document tag

**Response:**
```json
[
  {
    "id": "string",
    "title": "string",
    "path": "string",
    "category": "string",
    "tags": ["string"],
    "created_at": "string",
    "updated_at": "string",
    "metadata": {}
  }
]
```

**Description:**
Returns a list of available documents in the knowledge base.

**Status Codes:**
- `200`: Success
- `503`: Service initializing

#### `POST /documents/{document_id}/view`

Mark a document as viewed by a user.

**Path Parameters:**
- `document_id`: ID of the document being viewed

**Request:**
```json
{
  "user_id": "string"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Document marked as viewed by user"
}
```

**Description:**
Records that a specific user has viewed a document for recommendation purposes.

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `404`: Document not found
- `503`: Service initializing

### User Management

#### `GET /user/{user_id}`

Get a user's profile and recommendation history.

**Path Parameters:**
- `user_id`: ID of the user to retrieve

**Response:**
```json
{
  "user_id": "string",
  "viewed_documents": ["string"],
  "chat_history": [
    {
      "user_message": "string",
      "assistant_message": "string",
      "timestamp": "string",
      "feedback": "string",
      "sources_used": ["string"]
    }
  ],
  "interests": [
    {
      "topic": "string",
      "document_id": "string",
      "category": "string",
      "strength": 0.0,
      "first_mentioned": "string",
      "last_mentioned": "string"
    }
  ],
  "last_active": "string",
  "preferences": {},
  "recent_recommendations": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "explanation": "string",
      "relevance_score": 0.0,
      "tags": ["string"]
    }
  ]
}
```

**Description:**
Retrieves a user's profile including viewed documents, chat history, and interests.

**Status Codes:**
- `200`: Success
- `404`: User not found
- `503`: Service initializing

### Recommendation Evaluation

#### `POST /evaluate/recommendations`

Evaluate the quality of recommendations.

**Request:**
```json
{
  "query": "string",
  "recommendations": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "explanation": "string",
      "relevance_score": 0.0,
      "tags": ["string"]
    }
  ],
  "user_history": ["string"]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Recommendations evaluated successfully",
  "metrics": {
    "relevance_score": 0.0,
    "diversity_score": 0.0,
    "overall_score": 0.0,
    "individual_relevance": [0.0]
  }
}
```

**Description:**
Evaluates the quality and relevance of recommendations for a given query.

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `500`: Evaluation failed

### System Maintenance

#### `POST /reset`

Reset all stored data in the application.

**Response:**
```json
{
  "status": "success",
  "message": "All data reset successfully. Services are reinitializing."
}
```

**Description:**
Resets all stored data including user profiles, vector database, and metrics.

**Status Codes:**
- `200`: Success
- `500`: Reset failed

## Data Models

### QueryRequest
```json
{
  "query": "string",
  "user_id": "string",
  "context": {}
}
```

### QueryResponse
```json
{
  "answer": "string",
  "sources": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "relevance_score": 0.0,
      "snippet": "string"
    }
  ],
  "recommendations": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "explanation": "string",
      "relevance_score": 0.0,
      "tags": ["string"]
    }
  ],
  "processing_time": 0.0,
  "evaluation": {
    "correctness_score": 0.0,
    "relevance_score": 0.0,
    "completeness_score": 0.0,
    "overall_score": 0.0,
    "feedback": "string"
  }
}
```

### Source
```json
{
  "document_id": "string",
  "title": "string",
  "path": "string",
  "relevance_score": 0.0,
  "snippet": "string"
}
```

### Recommendation
```json
{
  "document_id": "string",
  "title": "string",
  "path": "string",
  "explanation": "string",
  "relevance_score": 0.0,
  "tags": ["string"]
}
```

### UserProfile
```json
{
  "user_id": "string",
  "viewed_documents": ["string"],
  "chat_history": [
    {
      "user_message": "string",
      "assistant_message": "string",
      "timestamp": "string",
      "feedback": "string",
      "sources_used": ["string"]
    }
  ],
  "interests": [
    {
      "topic": "string",
      "document_id": "string",
      "category": "string",
      "strength": 0.0,
      "first_mentioned": "string",
      "last_mentioned": "string"
    }
  ],
  "last_active": "string",
  "preferences": {},
  "recent_recommendations": [
    {
      "document_id": "string",
      "title": "string",
      "path": "string",
      "explanation": "string",
      "relevance_score": 0.0,
      "tags": ["string"]
    }
  ]
}
```

### PerformanceMetrics
```json
{
  "rag_metrics": {
    "total_queries": 0,
    "answered_ratio": 0.0,
    "out_of_scope_ratio": 0.0,
    "avg_processing_time": 0.0,
    "avg_relevance_score": 0.0,
    "document_count": 0,
    "last_update": "string",
    "processing_times": [0.0]
  },
  "recommendation_metrics": {
    "total_recommendations": 0,
    "user_interactions": 0,
    "interaction_rate": 0.0,
    "avg_diversity": 0.0,
    "avg_relevance": 0.0,
    "user_count": 0
  },
  "user_metrics": {
    "total_users": 0,
    "active_users_24h": 0,
    "avg_queries_per_user": 0.0,
    "user_satisfaction": {}
  },
  "system_health": {
    "uptime": "string",
    "memory_usage": "string",
    "documents_loaded": 0,
    "last_knowledge_base_update": "string",
    "api_status": "string"
  }
}
```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests:

- `200 OK`: The request succeeded
- `202 Accepted`: The request has been accepted for processing
- `400 Bad Request`: The request was invalid
- `404 Not Found`: The requested resource could not be found
- `500 Internal Server Error`: An error occurred on the server
- `503 Service Unavailable`: The service is temporarily unavailable (e.g., during initialization)

Error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Request Rate Limiting

The API does not currently implement rate limiting, but clients should follow best practices and avoid sending excessive requests in a short period.

## API Versioning

The current API version is accessible at `/api`. Future versions will use path versioning (e.g., `/api/v2`).
