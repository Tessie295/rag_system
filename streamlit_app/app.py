import streamlit as st
import requests
import uuid
import time
import pandas as pd
import altair as alt
from datetime import datetime
import json
import traceback

# Constants
API_URL = "http://localhost:8000/api"
DEFAULT_USER_ID = "test_user"

# Set page config
st.set_page_config(
    page_title="Shakers AI Support System",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = DEFAULT_USER_ID
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "response_times" not in st.session_state:
    st.session_state.response_times = []
if "query_count" not in st.session_state:
    st.session_state.query_count = 0

# App title
st.title("Shakers AI Support System")

# Sidebar
with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value=st.session_state.user_id)
    st.session_state.user_id = user_id
    
    # Add a health check indicator
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=2)
        if health_response.status_code == 200:
            st.success("API Status: Online")
        else:
            st.error(f"API Status: Error ({health_response.status_code})")
    except:
        st.error("API Status: Offline - Check if API server is running")
    
    st.header("Metrics")
    
    # Response time metrics
    if st.session_state.response_times:
        avg_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        st.metric("Average Response Time", f"{avg_time:.2f}s")
        
        # Create response time chart
        if len(st.session_state.response_times) > 1:
            times_df = pd.DataFrame({
                "Query": range(1, len(st.session_state.response_times) + 1),
                "Response Time (s)": st.session_state.response_times
            })
            
            chart = alt.Chart(times_df).mark_line().encode(
                x='Query',
                y='Response Time (s)'
            ).properties(height=200)
            
            st.altair_chart(chart, use_container_width=True)
    
    st.metric("Total Queries", st.session_state.query_count)

# Main chat interface
st.header("Chat with Shakers AI")

# Chat container
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(f"{message['content']}")
        else:
            st.chat_message("assistant").write(f"{message['content']}")
            
            if "sources" in message and message["sources"]:
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.write(f"📄 **{source['title']}** (Relevance: {source['relevance_score']:.2f})")
            
            if "recommendations" in message and message["recommendations"]:
                with st.expander("Recommended for you"):
                    for rec in message["recommendations"]:
                        st.write(f"📚 **{rec['title']}**")
                        st.write(f"_{rec['explanation']}_")

# User input
query = st.chat_input("Ask a question about Shakers")

def make_api_request(query_text):
    """Make an API request with error handling"""
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"query": query_text, "user_id": st.session_state.user_id},
            timeout=30
        )
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP Error: {e}")
        try:
            error_data = response.json()
            st.error(f"API Error: {error_data.get('detail', 'Unknown error')}")
        except:
            st.error(f"API Response: {response.text[:300]}...")
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to the API server")
        st.info("Make sure the API server is running at http://localhost:8000")
    except requests.exceptions.Timeout:
        st.error("Timeout Error: The API request timed out")
    except requests.exceptions.RequestException as e:
        st.error(f"Request Error: {e}")
    except json.JSONDecodeError:
        st.error("Error parsing API response as JSON")
        st.code(response.text[:300] + "...")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.error(traceback.format_exc())
    return None

if query:
    # Add user message to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now().isoformat()
    })
    
    # Display the user message immediately
    st.chat_message("user").write(query)
    
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
            
            # Add recommendations if available
            if "recommendations" in result and result["recommendations"]:
                assistant_message["recommendations"] = result["recommendations"]
                
            st.session_state.chat_history.append(assistant_message)
            
            # Display the assistant message
            assistant_response = st.chat_message("assistant")
            assistant_response.write(result["answer"])
            
            # Show sources if available
            if "sources" in result and result["sources"]:
                with assistant_response.expander("Sources"):
                    for source in result["sources"]:
                        st.write(f"📄 **{source['title']}** (Relevance: {source['relevance_score']:.2f})")
            
            # Show recommendations if available
            if "recommendations" in result and result["recommendations"]:
                with assistant_response.expander("Recommended for you"):
                    for rec in result["recommendations"]:
                        st.write(f"📚 **{rec['title']}**")
                        st.write(f"_{rec['explanation']}_")