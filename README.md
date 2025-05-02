# Shakers AI Support System (Fictional)

> An intelligent query system that provides answers to technical questions and recommends relevant resources based on user's interests.

## 📋 Overview

The Shakers AI Support System is a comprehensive platform designed to help clients find information about the Shakers freelancing platform and discover suitable talent for their projects. The system leverages natural language processing, retrieval-augmented generation (RAG), and recommendation algorithms to provide accurate answers and personalized suggestions.

![Shakers AI Support System](app/data/logo/shakersworks_logo.jpeg)


## ✨ Features

### Core Functionality
- **RAG Query Service**: Answers technical questions based on the Shakers knowledge base
- **Personalized Recommendations**: Suggests relevant resources based on user interaction history
- **Talent Matching**: Helps clients find freelancers with specific skills and experience

### Technical Capabilities
- Fast response times (under 5 seconds, almost)
- Source attribution for all answers
- Out-of-scope query detection
- Personalized and diverse recommendations
- Performance metrics and monitoring

## 📁 Project Structure

```
app/
├── api/
│   └── endpoints.py      # API route definitions
├── docs/                 # API docs
├── config.py             # Configuration settings
├── data/                 # Knowledge base and cached data
├── models/               # Data models
│   └── schemas.py        # Pydantic schemas
├── services/             # Core services
│   ├── rag.py            # RAG query service
│   └── enhanced_recommendations.py  # Recommendation service
├── utils/                # Utility functions
│   ├── evaluation.py     # Response evaluation
│   ├── helpers.py        # Helper functions
│   └── search.py         # Search functionality
├── main.py               # FastAPI application entry point
└── streamlit_app/
│   └── app.py                 # Streamlit frontend
tests/
├── data/                 # Test data
└── test_*.py             # Test modules
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- FastAPI
- Streamlit (for the frontend)
- Other dependencies listed in `requirements.txt`

### Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:Tessie295/rag_system.git
   cd rag_system
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (API keys, etc.)
   ```


### Running the Application

1. Start the FastAPI backend:
   ```
   uvicorn app.main:app --reload
   ```

2. In a separate terminal, start the Streamlit dashboard:
   ```
   streamlit run streamlit_app/app.py
   ```

3. Access the API at http://localhost:8000 and the dashboard at http://localhost:8501

## 🔍 Usage

### Web Interface

The Streamlit web interface provides:
- A chat interface for asking questions
- Display of relevant source documents
- Personalized recommendations
- Performance metrics and analytics

### API Endpoints

The system exposes several API endpoints:

- `POST /api/query`: Process a user query
- `GET /api/health`: Check system health
- `GET /api/metrics`: Get detailed performance metrics
- `POST /api/knowledge-base/update`: Update the knowledge base
- `GET /api/documents`: Retrieve available documents
- `POST /api/documents/{document_id}/view`: Mark a document as viewed
- `GET /api/user/{user_id}`: Get a user's profile
- `POST /api/evaluate/recommendations`: Evaluate recommendation quality
- `POST /api/reset`: Reset all stored data

Detailed API documentation is available at http://localhost:8000/docs when the server is running.

## 📚 System Architecture

The system is built with the following components:

### Backend (FastAPI)

- **RAG Service**: Processes queries using retrieval-augmented generation
- **Recommendation Service**: Provides personalized document recommendations
- **Search Engine**: Facilitates efficient document retrieval
- **Evaluation Module**: Assesses response quality and relevance

### Frontend (Streamlit)

- **Chat Interface**: Allows users to ask questions and view responses
- **Recommendation Display**: Shows personalized resource suggestions
- **Analytics Dashboard**: Presents system performance metrics

### Data Flow

1. User submits a query through the chat interface
2. The query is processed by the RAG service
3. Relevant documents are retrieved from the knowledge base
4. A response is generated based on the retrieved documents
5. User interests are updated based on the query and viewed documents
6. Personalized recommendations are generated
7. The response and recommendations are displayed to the user

## 🔧 Configuration

The system can be configured through environment variables or the `.env` file:

- `OPENAI_API_KEY`: OpenAI API key for LLM access
- `LLM_MODEL`: The language model to use (default: "gpt-3.5-turbo")
- `MAX_SOURCES`: Maximum number of sources to include in responses
- `ENABLE_EVALUATION`: Whether to evaluate response quality
- `ENABLE_CACHING`: Whether to cache responses for similar queries

Additional settings can be found in `app/config.py`.

## 🔒 Security

The current implementation is designed for development and testing. For production deployment, consider:

- Adding authentication and authorization
- Securing API endpoints
- Implementing rate limiting
- Configuring HTTPS


## 🧪 Testing - 

Run the test suite with:

```bash
Make coverage
```
or

```bash
pytest 
```

Key test modules include:
- `test_rag.py`: Tests for the RAG query system
- `test_recommendations.py`: Tests for the recommendation system
- `test_main.py`: API endpoint tests
- `test_helpers.py`: Utility function tests
- and more...

You can see the results of code coverage on htmlcov/index.html

TODO: more tests and supervise non-passed tests.

## Adding to the Knowledge Base

Add new markdown files to the `app/data/knowledge_base/` directory. The system will automatically index these files for RAG queries.


## License

This project is licensed under the MIT License - see the LICENSE file for details.
