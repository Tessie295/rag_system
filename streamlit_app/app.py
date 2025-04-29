import streamlit as st
import requests
import uuid
import time
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import json
import traceback
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any

import logging

# Configure the logger (this is a simple configuration)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
API_URL = "http://localhost:8000/api"
DEFAULT_USER_ID = str(uuid.uuid4())  # Generate unique IDs for new users

# Set page config with improved styling
st.set_page_config(
    page_title="Shakers AI Support System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #1E3A8A;
    }
    .source-card {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .recommendation-card {
        background-color: #EFF6FF;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid #3B82F6;
    }
    .metric-card {
        background-color: #F9FAFB;
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .info-text {
        color: #6B7280;
        font-size: 0.9rem;
    }
    .highlight {
        background-color: #FEFCE8;
        padding: 0.2rem 0.4rem;
        border-radius: 0.25rem;
    }
    /* Chat styling */
    .user-bubble {
        background-color: #E9F2FF;
        padding: 0.75rem 1rem;
        border-radius: 0.75rem 0.75rem 0.75rem 0.25rem;
        margin-bottom: 0.75rem;
    }
    .assistant-bubble {
        background-color: #F3F4F6;
        padding: 0.75rem 1rem;
        border-radius: 0.75rem 0.75rem 0.25rem 0.75rem;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for persistent data
if "user_id" not in st.session_state:
    st.session_state.user_id = DEFAULT_USER_ID
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "response_times" not in st.session_state:
    st.session_state.response_times = []
if "query_count" not in st.session_state:
    st.session_state.query_count = 0
if "evaluation_scores" not in st.session_state:
    st.session_state.evaluation_scores = []
if "last_recommendations" not in st.session_state:
    st.session_state.last_recommendations = []
if "viewed_documents" not in st.session_state:
    st.session_state.viewed_documents = set()

# App header with logo
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://via.placeholder.com/100x100.png?text=Shakers", width=80)
with col2:
    st.markdown("<div class='main-header'>Shakers AI Support System</div>", unsafe_allow_html=True)
    st.markdown("<div class='info-text'>Find answers about the platform and discover the perfect talent for your projects</div>", unsafe_allow_html=True)

# Sidebar for settings and metrics
with st.sidebar:
    st.header("🔧 Settings")
    
    # User settings
    user_col1, user_col2 = st.columns([3, 1])
    with user_col1:
        user_id = st.text_input("User ID", value=st.session_state.user_id)
        st.session_state.user_id = user_id
    with user_col2:
        if st.button("New ID"):
            st.session_state.user_id = str(uuid.uuid4())
            st.rerun()
    
    # Advanced settings in expander
    with st.expander("Advanced Settings"):
        st.checkbox("Enable detailed explanations", value=True, key="detailed_explanations")
        st.checkbox("Show source relevance scores", value=True, key="show_relevance")
        st.select_slider("Max recommendations", options=[1, 2, 3, 4, 5], value=3, key="max_recommendations")
    
    # API health check
    st.header("🔌 API Status")
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=3)
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            # Show status with colored indicator
            status_col1, status_col2 = st.columns([1, 3])
            with status_col1:
                if health_data.get("status") == "ok":
                    st.markdown("🟢")
                else:
                    st.markdown("🟠")
            with status_col2:
                st.markdown("**API Status: Online**" if health_data.get("status") == "ok" else "**API Status: Degraded**")
            
            # Show additional metrics if available
            if "metrics" in health_data:
                metrics = health_data["metrics"]
                
                # Create metric cards in columns
                metric_cols = st.columns(3)
                
                with metric_cols[0]:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    st.metric("Total Queries", metrics.get("total_queries", 0))
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with metric_cols[1]:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    st.metric("Avg Response Time", f"{metrics.get('avg_processing_time', 0):.2f}s")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with metric_cols[2]:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    answer_ratio = metrics.get("answered_ratio", 0) * 100
                    st.metric("Success Rate", f"{answer_ratio:.1f}%")
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error(f"API Status: Error ({health_response.status_code})")
    except Exception as e:
        st.error("API Status: Offline - Check if API server is running")
        st.error(f"Error details: {str(e)}")
    
    # Performance Analytics
    st.header("📊 Analytics")
    
    # Only show analytics if we have data
    if st.session_state.response_times:
        # Response time metrics
        avg_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        
        # Show current session metrics
        st.subheader("Current Session")
        metrics_cols = st.columns(2)
        with metrics_cols[0]:
            st.metric("Queries", st.session_state.query_count)
        with metrics_cols[1]:
            st.metric("Avg Time", f"{avg_time:.2f}s")
        
        # Create response time chart with improved styling
        if len(st.session_state.response_times) > 1:
            times_df = pd.DataFrame({
                "Query": range(1, len(st.session_state.response_times) + 1),
                "Response Time (s)": st.session_state.response_times
            })
            
            fig = px.line(
                times_df, 
                x="Query", 
                y="Response Time (s)",
                markers=True,
                title="Response Time Trend"
            )
            fig.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=30, b=10),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Show answer quality metrics if available
        if st.session_state.evaluation_scores:
            st.subheader("Answer Quality")
            
            eval_df = pd.DataFrame(st.session_state.evaluation_scores)
            
            # Create average scores chart
            avg_scores = {
                "Metric": ["Correctness", "Relevance", "Completeness", "Overall"],
                "Score": [
                    sum(score["correctness_score"] for score in st.session_state.evaluation_scores) / len(st.session_state.evaluation_scores),
                    sum(score["relevance_score"] for score in st.session_state.evaluation_scores) / len(st.session_state.evaluation_scores),
                    sum(score["completeness_score"] for score in st.session_state.evaluation_scores) / len(st.session_state.evaluation_scores),
                    sum(score["overall_score"] for score in st.session_state.evaluation_scores) / len(st.session_state.evaluation_scores)
                ]
            }
            
            avg_df = pd.DataFrame(avg_scores)
            
            fig = px.bar(
                avg_df,
                x="Metric",
                y="Score",
                color="Metric",
                title="Average Quality Scores"
            )
            fig.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=30, b=10),
                showlegend=False,
                yaxis=dict(range=[0, 1])
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Analytics will appear after your first query")

# Main chat interface in two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.header("💬 Chat with Shakers AI")
    
    # Chat container with improved styling
    chat_container = st.container(height=500)
    
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"<div class='user-bubble'>{message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='assistant-bubble'>{message['content']}</div>", unsafe_allow_html=True)
                
                # Show sources if available
                if "sources" in message and message["sources"]:
                    with st.expander("📄 View Sources"):
                        for source in message["sources"]:
                            relevance = source.get('relevance_score', 0)
                            relevance_text = f" (Relevance: {relevance:.2f})" if st.session_state.show_relevance else ""
                            
                            st.markdown(f"<div class='source-card'>", unsafe_allow_html=True)
                            st.markdown(f"**{source['title']}**{relevance_text}")
                            
                            if "snippet" in source and source["snippet"]:
                                st.markdown(f"<div class='info-text'>{source['snippet']}</div>", unsafe_allow_html=True)
                            
                            # Add a button to mark as viewed explicitly
                            if st.button(f"View Document: {source['title']}", key=f"view_{uuid.uuid4()}_{source['document_id']}_{message['timestamp']}"):
                                if source['document_id'] not in st.session_state.viewed_documents:
                                    # Call API to mark document as viewed
                                    try:
                                        requests.post(
                                            f"{API_URL}/documents/{source['document_id']}/view",
                                            json={"user_id": st.session_state.user_id}
                                        )
                                        st.session_state.viewed_documents.add(source['document_id'])
                                        st.success(f"Marked '{source['title']}' as viewed")
                                    except:
                                        st.error("Could not update view status")
                            
                            st.markdown("</div>", unsafe_allow_html=True)
    
    # User input
    query = st.chat_input("Ask a question about Shakers or finding talent...")

with col2:
    st.header("🔍 Recommended Resources")
    
    # Display recommendations with improved error handling
    recommendation_container = st.container(height=500)
    
    with recommendation_container:
        # Initialize if not present
        if "last_recommendations" not in st.session_state:
            st.session_state.last_recommendations = []
        
        # Add debug information but remove from production
        logger.debug(f"Recommendations in state: {len(st.session_state.last_recommendations)}")
        
        if st.session_state.last_recommendations:
            try:
                for rec in st.session_state.last_recommendations:
                    # Safely access recommendation properties with dict.get() method
                    # This handles both dict-like and object-like access patterns
                    title = rec.get('title', rec['title'] if isinstance(rec, dict) else getattr(rec, 'title', 'Unknown Title'))
                    doc_id = rec.get('document_id', rec['document_id'] if isinstance(rec, dict) else getattr(rec, 'document_id', 'unknown'))
                    explanation = rec.get('explanation', rec['explanation'] if isinstance(rec, dict) else getattr(rec, 'explanation', 'Recommended resource'))
                    
                    # Render recommendation card
                    st.markdown(f"<div class='recommendation-card'>", unsafe_allow_html=True)
                    st.markdown(f"**{title}**")
                    st.markdown(f"<div class='info-text'>{explanation}</div>", unsafe_allow_html=True)
                    
                    # Safely get tags with error handling
                    try:
                        tags = rec.get('tags', rec['tags'] if isinstance(rec, dict) and 'tags' in rec else getattr(rec, 'tags', []))
                        if tags:
                            tags_html = ' '.join([f"<span class='highlight'>{tag}</span>" for tag in tags])
                            st.markdown(f"<div style='margin-top: 0.5rem;'>{tags_html}</div>", unsafe_allow_html=True)
                    except Exception as e:
                        logger.error(f"Error displaying tags: {e}")
                    
                    # Add view button
                    if st.button(f"View Resource", key=f"rec_{doc_id}"):
                        if doc_id not in st.session_state.viewed_documents:
                            try:
                                requests.post(
                                    f"{API_URL}/documents/{doc_id}/view",
                                    json={"user_id": st.session_state.user_id}
                                )
                                st.session_state.viewed_documents.add(doc_id)
                                st.success(f"Marked '{title}' as viewed")
                            except Exception as e:
                                st.error(f"Could not update view status: {str(e)}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error displaying recommendations: {str(e)}")
                logger.error(f"Recommendation display error: {str(e)}")
                logger.error(f"Recommendation data: {st.session_state.last_recommendations}")
        else:
            st.info("Recommendations will appear based on your questions.\nTry asking about specific skills like 'Angular' or 'Python'.")

def make_api_request(query_text: str) -> Dict[str, Any]:
    """Make an API request with enhanced error handling and retry logic."""
    max_retries = 2
    retry_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_URL}/query",
                json={
                    "query": query_text, 
                    "user_id": st.session_state.user_id,
                    "context": {}  # Additional context could be added here
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
            # Handle different error codes
            if response.status_code == 429:  # Rate limit
                st.warning("The API is currently busy. Waiting to retry...")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
                
            if response.status_code >= 500:  # Server error
                st.error(f"Server error (HTTP {response.status_code}). Retrying...")
                time.sleep(retry_delay)
                continue
                
            # Other client errors
            try:
                error_data = response.json()
                error_message = error_data.get('detail', f"HTTP Error: {response.status_code}")
            except:
                error_message = f"HTTP Error: {response.status_code}"
            
            st.error(error_message)
            return None
            
        except requests.exceptions.Timeout:
            st.warning("Request timed out. Retrying...")
            time.sleep(retry_delay)
            continue
            
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            st.error(f"Connection error: {str(e)}")
            st.info("Make sure the API server is running at http://localhost:8000")
            return None
            
        except json.JSONDecodeError:
            st.error("Could not parse the API response as JSON")
            st.code(response.text[:300] + "...")
            return None
            
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            st.error(traceback.format_exc())
            return None
    
    # If we've exhausted retries
    st.error("Maximum retry attempts reached. Please try again later.")
    return None

# Process user query
if query:
    # Add user message to chat history
    message_timestamp = datetime.now().isoformat()
    st.session_state.chat_history.append({
        "role": "user",
        "content": query,
        "timestamp": message_timestamp
    })
    
    # Display the user message immediately for better UX
    st.markdown(f"<div class='user-bubble'>{query}</div>", unsafe_allow_html=True)
    
    # Increment query count
    st.session_state.query_count += 1
    
    # Show spinner during API call
    with st.spinner("Thinking..."):
        start_time = time.time()
        result = make_api_request(query)
        response_time = time.time() - start_time
        
        # Add response time to history
        st.session_state.response_times.append(response_time)
        
        if result:
            # Add AI response to chat history
            assistant_message = {
                "role": "assistant",
                "content": result["answer"],
                "timestamp": datetime.now().isoformat(),
                "processing_time": result.get("processing_time", response_time)
            }
            
            # Add sources if available
            if "sources" in result and result["sources"]:
                assistant_message["sources"] = result["sources"]
            
            # Add recommendations if available - improved logging and debugging
            if "recommendations" in result and result["recommendations"]:
                st.session_state.last_recommendations = result["recommendations"]
                # Print debug info
                logger.info(f"Found {len(result['recommendations'])} recommendations")
            else:
                logger.info("No recommendations in result")
                # Don't clear recommendations if none are available
                # This is the key fix - don't set to empty list which causes loss of previous recommendations
            
            # Add to chat history
            st.session_state.chat_history.append(assistant_message)
            
            # Display the assistant message
            assistant_response = st.chat_message("assistant")
            assistant_response.write(result["answer"])
            
            # Show sources if available
            if "sources" in result and result["sources"]:
                with assistant_response.expander("📄 View Sources"):
                    for source in result["sources"]:
                        relevance = source.get('relevance_score', 0)
                        relevance_text = f" (Relevance: {relevance:.2f})" if st.session_state.show_relevance else ""
                        
                        st.markdown(f"<div class='source-card'>", unsafe_allow_html=True)
                        st.markdown(f"**{source['title']}**{relevance_text}")
                        
                        if "snippet" in source and source["snippet"]:
                            st.markdown(f"<div class='info-text'>{source['snippet']}</div>", unsafe_allow_html=True)
                        
                        # Add a button to mark as viewed explicitly
                        if st.button(f"View Document: {source['title']}", key=f"view_{source['document_id']}_{message_timestamp}_{uuid.uuid4()}"):
                            if source['document_id'] not in st.session_state.viewed_documents:
                                # Call API to mark document as viewed
                                try:
                                    requests.post(
                                        f"{API_URL}/documents/{source['document_id']}/view",
                                        json={"user_id": st.session_state.user_id}
                                    )
                                    st.session_state.viewed_documents.add(source['document_id'])
                                    st.success(f"Marked '{source['title']}' as viewed")
                                except:
                                    st.error("Could not update view status")
                        
                        st.markdown("</div>", unsafe_allow_html=True)
            
            # Force a rerun to refresh recommendations
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div class='info-text'>© 2023 Shakers, Inc. All rights reserved.</div>
        <div>
            <a href='#' target='_blank'>Terms</a> • 
            <a href='#' target='_blank'>Privacy</a> • 
            <a href='#' target='_blank'>Support</a>
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)