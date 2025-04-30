import os
import sys
import tempfile
import pytest
from unittest.mock import patch, mock_open

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.helpers import (
    time_function,
    load_markdown_file,
    load_knowledge_base,
    markdown_to_text,
    chunk_text,
    is_out_of_scope,
)

# ---------- Tests for time_function ----------

def test_time_function_sync():
    @time_function
    def add(x, y):
        return x + y

    result, duration = add(3, 4)
    assert result == 7
    assert duration >= 0


@pytest.mark.asyncio
async def test_time_function_async():
    @time_function
    async def async_add(x, y):
        return x + y

    result, duration = await async_add(5, 6)
    assert result == 11
    assert duration >= 0

# ---------- Tests for is_out_of_scope ----------

def test_is_out_of_scope_empty_scores():
    assert is_out_of_scope("query", 0.5, []) is True

def test_is_out_of_scope_all_below_threshold():
    assert is_out_of_scope("query", 0.8, [0.3, 0.5]) is True

def test_is_out_of_scope_some_above_threshold():
    assert is_out_of_scope("query", 0.5, [0.6, 0.7]) is False
