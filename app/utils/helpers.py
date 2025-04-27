import os
import time
import logging
import re
import markdown
import functools
import asyncio
from typing import List, Dict, Any, Callable, Awaitable, TypeVar, Union, Tuple
import frontmatter
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

T = TypeVar('T')

def time_function(func: Callable) -> Callable:
    """Decorator to measure the execution time of a function.
    Works with both synchronous and asynchronous functions."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Tuple[T, float]:
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        return result, execution_time

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Tuple[T, float]:
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        return result, execution_time

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

def load_markdown_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a markdown file with frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            post = frontmatter.load(file)
            content = post.content
            metadata = post.metadata
            
            # Extract title from the first heading if not in metadata
            if 'title' not in metadata:
                title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                if title_match:
                    metadata['title'] = title_match.group(1)
                else:
                    metadata['title'] = os.path.basename(file_path)
            
            return {
                'id': os.path.basename(file_path).replace('.md', ''),
                'title': metadata.get('title', os.path.basename(file_path)),
                'content': content,
                'path': file_path,
                'metadata': metadata
            }
    except Exception as e:
        logger.error(f"Error loading markdown file {file_path}: {e}")
        return None

def load_knowledge_base(directory_path: str) -> List[Dict[str, Any]]:
    """Load all markdown files from a directory."""
    documents = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                doc = load_markdown_file(file_path)
                if doc:
                    documents.append(doc)
    return documents

def markdown_to_text(markdown_string: str) -> str:
    """Convert markdown to plain text."""
    # Convert markdown to HTML
    html = markdown.markdown(markdown_string)
    # Extract text from HTML
    soup = BeautifulSoup(html, features="html.parser")
    return soup.get_text()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length and end - start == chunk_size:
            # Find the last period or newline to avoid cutting mid-sentence
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            breakpoint = max(last_period, last_newline)
            if breakpoint > start:
                end = breakpoint + 1
        
        chunks.append(text[start:end])
        start = end - overlap if end < text_length else text_length
        
    return chunks

def is_out_of_scope(query: str, threshold: float, relevance_scores: List[float]) -> bool:
    """Determine if a query is out of scope based on the relevance scores."""
    if not relevance_scores:
        return True
    return max(relevance_scores) < threshold