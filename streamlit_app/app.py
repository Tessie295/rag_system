import streamlit as st
import requests
import uuid
import time
import pandas as pd
import altair as alt
from datetime import datetime
import json

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
            st.write(f"You: {message['content']}")
        else:
            st.write(f"AI: {message['content']}")
            
            if "sources" in message:
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.write(f"📄 **{source['title']}** (Relevance: {source['relevance_score']:.2f})")
            
            if "recommendations" in message:
                with st.expander("Recommended for you"):
                    for rec in message["recommendations"]:
                        st.write(f"📚 **{rec['title']}**")
                        st.write(f"_{rec['explanation']}_")

# User input
query = st.text_input("Ask a question about Shakers", key="user_query")

if st.button("Submit") and query:
    # Add user message to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now().isoformat()
    })
    
    # Increment query count
    st.session_state.query_count += 1
    
    # Show spinner during API call
    with st.spinner("Thinking..."):
        try:
            # Send query to API
            start_time = time.time()
            response = requests.post(
                f"{API_URL}/query",
                json={"query": query, "user_id": st.session_state.user_id},
                timeout=30  # Add timeout
            )
            response_time = time.time() - start_time
            
            # Add response time to history
            st.session_state.response_times.append(response_time)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Add AI response to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": data["answer"],
                        "sources": data["sources"],
                        "recommendations": data["recommendations"],
                        "timestamp": datetime.now().isoformat(),
                        "processing_time": data["processing_time"]
                    })
                except json.JSONDecodeError as e:
                    st.error(f"Error parsing response: {e}")
                    st.error(f"Response content: {response.text[:500]}...")
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {str(e)}")
            st.error("Make sure the API server is running at http://localhost:8000")
    
    # Clear the input box and refresh the page to show new messages
    st.rerun()