import os
import time
import logging
import re
import json
import markdown
import functools
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Callable, Awaitable, TypeVar, Union, Tuple, Optional
import frontmatter
from bs4 import BeautifulSoup
import numpy as np
from langdetect import detect, LangDetectException

# Set up enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

T = TypeVar('T')

def time_function(func: Callable) -> Callable:
    """Decorator to measure the execution time of a function.
    Works with both synchronous and asynchronous functions and properly records timing."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            # Run the original function
            result = await func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log the execution time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
            
            # For RAGService.process_query, update processing_time in response and metrics
            if func.__name__ == 'process_query' and args and hasattr(args[0], 'query_metrics'):
                service = args[0]
                
                # Update the metrics
                service.query_metrics["processing_times"].append(execution_time)
                
                # Update the response object with the timing
                if isinstance(result, tuple) and len(result) > 0:
                    response = result[0]
                    if hasattr(response, 'processing_time'):
                        response.processing_time = execution_time
                elif hasattr(result, 'processing_time'):
                    result.processing_time = execution_time
            
            # Return the result and the execution time
            return result, execution_time
            
        except Exception as e:
            # Log exceptions but still track execution time
            execution_time = time.time() - start_time
            logger.error(f"Exception in {func.__name__}: {e} (took {execution_time:.4f} seconds)")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            # Run the original function
            result = func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log the execution time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
            
            # Return the result and the execution time
            return result, execution_time
            
        except Exception as e:
            # Log exceptions but still track execution time
            execution_time = time.time() - start_time
            logger.error(f"Exception in {func.__name__}: {e} (took {execution_time:.4f} seconds)")
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

def load_markdown_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a markdown file with optimized processing for speed."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Parse frontmatter more efficiently
            post = frontmatter.load(file)
            content = post.content
            metadata = post.metadata
            
            # Extract title from the first heading if not in metadata
            if 'title' not in metadata:
                title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                if title_match:
                    metadata['title'] = title_match.group(1)
                else:
                    metadata['title'] = os.path.basename(file_path).replace('.md', '').replace('_', ' ').title()
            
            # Basic file stats - avoid complex processing for speed
            file_stat = os.stat(file_path)
            
            # Only include essential metadata for performance
            return {
                'id': os.path.basename(file_path).replace('.md', ''),
                'title': metadata.get('title', os.path.basename(file_path)),
                'content': content,
                'path': file_path,
                'metadata': metadata,
                'created_at': datetime.fromtimestamp(file_stat.st_ctime),
                'updated_at': datetime.fromtimestamp(file_stat.st_mtime),
                'category': metadata.get('category', os.path.basename(os.path.dirname(file_path))),
                'tags': metadata.get('tags', [])
            }
    except Exception as e:
        logger.error(f"Error loading markdown file {file_path}: {e}")
        return None

def load_knowledge_base(directory_path: str) -> List[Dict[str, Any]]:
    """Load all markdown files from a directory with optimized processing."""
    documents = []
    
    # Make sure directory exists
    if not os.path.exists(directory_path):
        logger.error(f"Knowledge base directory not found: {directory_path}")
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"Created empty knowledge base directory: {directory_path}")
        return documents
    
    # Walk through the directory tree to find all markdown files
    start_time = time.time()
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                doc = load_markdown_file(file_path)
                if doc:
                    documents.append(doc)
    
    logger.info(f"Loaded {len(documents)} documents in {time.time() - start_time:.4f}s")
    return documents

def markdown_to_text(markdown_string: str) -> str:
    """Convert markdown to plain text with optimized processing."""
    # Use a simplified approach for speed
    text = markdown_string
    
    # Remove markdown headings
    text = re.sub(r'#+\s+(.*)', r'\1', text)
    
    # Remove markdown links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```[^`]*```', ' ', text)
    
    # Remove bold/italic markers
    text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 300) -> List[str]:
    """Split text into overlapping chunks with improved profile-aware boundaries."""
    chunks = []
    start = 0
    text_length = len(text)
    
    # Define potential section separators in priority order
    separators = ["\n## ", "\n### ", "\n\n", "\n", ". ", "! ", "? ", ";", ":", " - ", ", ", " "]
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        if end < text_length and end - start == chunk_size:
            # First try to find profile or section boundaries for better chunking
            profile_separator_found = False
            
            # Look for the last occurrence of a profile separator within the chunk
            for separator in separators[:2]:  # Just check the profile separators first (## and ###)
                last_separator = text.rfind(separator, start, end)
                
                if last_separator > start:
                    # Found a profile separator - back up to before it to keep profiles intact
                    end = last_separator
                    profile_separator_found = True
                    break
            
            # If no profile separator found, try other natural breakpoints
            if not profile_separator_found:
                for separator in separators[2:]:  # Check other separators
                    last_separator = text.rfind(separator, start, end)
                    
                    if last_separator > start + chunk_size/2:  # Only use if reasonably far into chunk
                        end = last_separator + len(separator)
                        break
        
        # Add the chunk
        chunk = text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            # Ensure the chunk has enough context by checking for partial profiles
            if chunk.count('###') == 0 and '**Skills:**' in chunk:
                # This chunk has skills but no profile header - try to expand backward
                prev_start = max(0, start - 200)  # Look back a bit more
                expanded_chunk = text[prev_start:end].strip()
                chunks.append(expanded_chunk)
            else:
                chunks.append(chunk)
        
        # Move start position, considering overlap
        start = end - overlap if end < text_length else text_length
    
    return chunks

def is_out_of_scope(query: str, threshold: float, relevance_scores: List[float]) -> bool:
    """Determine if a query is out of scope - simplified for speed."""
    if not relevance_scores:
        return True
    
    # Simple approach: just check max relevance against threshold
    return max(relevance_scores) < threshold

def detect_language(text: str) -> Optional[str]:
    """Detect the language of input text with optimized processing."""
    # Only process the first 100 characters for speed
    sample = text[:100] if len(text) > 100 else text
    try:
        return detect(sample)
    except LangDetectException:
        return None

async def save_metrics(metric_name: str, metrics_data: Dict[str, Any]) -> bool:
    """Save metrics to a JSON file with optimized processing."""
    # Don't block for metrics saving
    metrics_dir = os.path.join("app/data", "metrics")
    os.makedirs(metrics_dir, exist_ok=True)
    
    file_path = os.path.join(metrics_dir, f"{metric_name}.json")
    
    try:
        # Create a copy to avoid modifying the original
        metrics_copy = metrics_data.copy()
        metrics_copy["last_updated"] = datetime.now().isoformat()
        
        # Limit array sizes to prevent excessive file growth
        for key, value in metrics_copy.items():
            if isinstance(value, list) and len(value) > 100:
                # Keep only the most recent 100 items for arrays
                metrics_copy[key] = value[-100:]
        
        # Write to temporary file first for atomicity
        temp_path = file_path + ".tmp"
        with open(temp_path, 'w') as f:
            json.dump(metrics_copy, f, default=str)
        
        # Rename to final path (atomic operation on most filesystems)
        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")
        return False

async def load_metrics(metric_name: str) -> Optional[Dict[str, Any]]:
    """Load metrics from a JSON file with optimized error handling."""
    file_path = os.path.join("app/data", "metrics", f"{metric_name}.json")
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Corrupt metrics file: {file_path}")
        # Backup the corrupt file and return empty metrics
        backup_path = file_path + f".corrupt.{int(time.time())}"
        try:
            os.rename(file_path, backup_path)
            logger.info(f"Backed up corrupt file to {backup_path}")
        except:
            pass
        return {}
    except Exception as e:
        logger.error(f"Error loading metrics: {e}")
        return None

# Cache for expensive operations
_operation_cache = {}

def cache_result(ttl_seconds: int = 3600):
    """Decorator to cache function results for improved performance."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            now = time.time()
            
            # Check if result is in cache and not expired
            if key in _operation_cache:
                result, timestamp = _operation_cache[key]
                if now - timestamp < ttl_seconds:
                    return result
            
            # Execute the function and cache the result
            result = await func(*args, **kwargs)
            _operation_cache[key] = (result, now)
            
            # Clean cache periodically
            if len(_operation_cache) > 100:  # Arbitrary limit
                _clean_cache(now, ttl_seconds)
            
            return result
            
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            now = time.time()
            
            # Check if result is in cache and not expired
            if key in _operation_cache:
                result, timestamp = _operation_cache[key]
                if now - timestamp < ttl_seconds:
                    return result
            
            # Execute the function and cache the result
            result = func(*args, **kwargs)
            _operation_cache[key] = (result, now)
            
            # Clean cache periodically
            if len(_operation_cache) > 100:  # Arbitrary limit
                _clean_cache(now, ttl_seconds)
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def _clean_cache(now: float, ttl_seconds: int):
    """Remove expired items from the operation cache."""
    expired_keys = [
        k for k, (_, t) in _operation_cache.items() 
        if now - t > ttl_seconds
    ]
    for k in expired_keys:
        del _operation_cache[k]