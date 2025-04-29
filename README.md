# Shakers AI Support System (Fictional)

An intelligent technical support system with personalized recommendation capabilities for the Shakers platform.

## Features

- **RAG Query Service**: Answer technical user questions based on the provided knowledge base
- **Personalized Recommendation Service**: Proactively recommend relevant resources based on user query history
- **Metrics Dashboard**: Track system performance through a Streamlit dashboard

## Project Structure

```
shakers-ai-support/
│
├── app/
│   ├── main.py                # FastAPI entry point
│   ├── api/                   # Routes and controllers
│   │   └── endpoints.py
│   ├── services/              # System logic (RAG, recommendations)
│   │   ├── rag.py
│   │   └── recommendations.py
│   ├── data/                  # Simulations: docs, users, history
│   │   ├── knowledge_base/    # Markdown files
│   │   ├── users.json
│   │   └── queries.json
│   ├── models/                # Data models (Pydantic)
│   │   └── schemas.py
│   ├── utils/                 # Utilities (vectorization, logs, etc.)
│   │   └── helpers.py
│   └── config.py              # Configuration (.env reading)
│
├── tests/
│   ├── test_rag.py
│   ├── test_recommendations.py
│   └── test_api.py
│
├── streamlit_app/
│   └── app.py                 # Streamlit dashboard
│
├── .env.example               # Environment variables template
├── requirements.txt           # Dependencies
└── run.sh                     # Run script
```

## Getting Started

### Prerequisites

- Python 3.12
- OpenAI API key for language model access

### Installation

1. Clone this repository:
   ```
   git clone git@github.com:Tessie295/rag_system.git
   cd rag_system
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env file with your OpenAI API key and other settings
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

## Testing

To Do

## Adding to the Knowledge Base

Add new markdown files to the `app/data/knowledge_base/` directory. The system will automatically index these files for RAG queries.


## License

This project is licensed under the MIT License - see the LICENSE file for details.
