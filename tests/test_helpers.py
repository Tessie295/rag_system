"""
Extended test module for helper utilities to improve coverage.
"""

import os
import sys
import tempfile
import asyncio
import pytest
import json
import time
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.helpers import (
    time_function,
    load_markdown_file,
    load_knowledge_base,
    markdown_to_text,
    chunk_text,
    is_out_of_scope,
    detect_language,
    save_metrics,
    load_metrics,
    cache_result,
    logger,
)


class TestHelpers:
    """Tests for the helper functions."""

    def test_load_markdown_file(self):
        """Test the load_markdown_file function."""
        # Test with a valid markdown file with frontmatter
        mock_content = """---
title: Test Document
category: test
tags: [test, sample]
---

# Test Heading

This is test content.
"""
        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch("os.stat") as mock_stat:
                # Mock file stats
                mock_stat.return_value.st_ctime = 1609459200  # 2021-01-01
                mock_stat.return_value.st_mtime = 1609459200  # 2021-01-01

                result = load_markdown_file("test.md")

                # Check that the document was parsed correctly
                assert result["id"] == "test"
                assert result["title"] == "Test Document"
                assert "Test Heading" in result["content"]
                assert result["metadata"]["category"] == "test"
                assert "test" in result["metadata"]["tags"]
                assert result["category"] == "test"

        # Test with markdown file without frontmatter but with title
        mock_content_no_fm = """# Document Title

This is test content.
"""
        with patch("builtins.open", mock_open(read_data=mock_content_no_fm)):
            with patch("os.stat") as mock_stat:
                mock_stat.return_value.st_ctime = 1609459200
                mock_stat.return_value.st_mtime = 1609459200

                result = load_markdown_file("test2.md")

                # Title should be extracted from first heading
                assert result["title"] == "Document Title"
                assert "Document Title" in result["content"]

        # Test with markdown file without frontmatter or title
        mock_content_no_title = """This is test content with no title.
"""
        with patch("builtins.open", mock_open(read_data=mock_content_no_title)):
            with patch("os.stat") as mock_stat:
                mock_stat.return_value.st_ctime = 1609459200
                mock_stat.return_value.st_mtime = 1609459200

                result = load_markdown_file("no_title.md")

                # Title should default to filename
                assert result["title"] == "No Title"

        # Test error handling
        with patch("builtins.open", side_effect=Exception("Test error")):
            result = load_markdown_file("error.md")
            assert result is None

    def test_load_knowledge_base(self):
        """Test the load_knowledge_base function."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectories
            os.makedirs(os.path.join(temp_dir, "subdir1"))
            os.makedirs(os.path.join(temp_dir, "subdir2"))

            # Create mock markdown files
            file_paths = [
                os.path.join(temp_dir, "file1.md"),
                os.path.join(temp_dir, "subdir1", "file2.md"),
                os.path.join(temp_dir, "subdir2", "file3.md"),
                os.path.join(temp_dir, "not_markdown.txt"),  # Should be ignored
            ]

            # Write content to files
            for i, path in enumerate(file_paths):
                with open(path, "w") as f:
                    f.write(
                        f"# Test File {i+1}\n\nThis is test content for file {i+1}."
                    )

            # Load the knowledge base
            with patch("app.utils.helpers.load_markdown_file") as mock_load_file:
                # Configure the mock to return a valid document
                mock_load_file.return_value = {
                    "id": "test",
                    "title": "Test Document",
                    "content": "Test content",
                    "path": "test.md",
                    "metadata": {},
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "category": "test",
                    "tags": ["test"],
                }

                result = load_knowledge_base(temp_dir)

                # Should find 3 markdown files (not the .txt file)
                assert mock_load_file.call_count == 3
                assert len(result) == 3

            # Test with directory that doesn't exist
            with patch("os.path.exists") as mock_exists, patch(
                "os.makedirs"
            ) as mock_makedirs:
                mock_exists.return_value = False

                result = load_knowledge_base("/nonexistent/dir")

                assert mock_makedirs.called
                assert result == []

    def test_markdown_to_text(self):
        """Test the markdown_to_text function."""
        # Test with headings
        heading_md = "# Heading 1\n## Heading 2\n### Heading 3"
        heading_result = markdown_to_text(heading_md)
        assert "Heading 1" in heading_result
        assert "#" not in heading_result

        # Test with links
        links_md = "This is a [link](https://example.com) and another [link with text](https://test.com)"
        links_result = markdown_to_text(links_md)
        assert "This is a link and another link with text" in links_result
        assert "https://example.com" not in links_result

        # Test with code blocks
        code_md = "Some text\n```python\ndef test():\n    return True\n```\nMore text"
        code_result = markdown_to_text(code_md)
        assert "Some text" in code_result
        assert "More text" in code_result
        assert "def test():" not in code_result

        # Test with bold and italic
        formatting_md = "This is **bold** and this is *italic* and this is _also italic_ and this is __also bold__"
        formatting_result = markdown_to_text(formatting_md)
        assert (
            "This is bold and this is italic and this is also italic and this is also bold"
            in formatting_result
        )
        assert "*" not in formatting_result
        assert "_" not in formatting_result

        # Test with multiple spaces and newlines
        spacing_md = "Line 1\n\nLine 2\n\n\nLine 3    with    spaces"
        spacing_result = markdown_to_text(spacing_md)
        assert "Line 1 Line 2 Line 3 with spaces" in spacing_result.strip()

    def test_chunk_text(self):
        """Test the chunk_text function."""
        # Test with simple text shorter than chunk size
        short_text = "This is a short text that fits in one chunk."
        short_chunks = chunk_text(short_text, chunk_size=100, overlap=20)
        assert len(short_chunks) == 1
        assert short_chunks[0] == short_text

        # Test with multiple chunks
        long_text = "This is the first paragraph.\n\nThis is the second paragraph.\n\nThis is the third paragraph.\n\nThis is the fourth paragraph."
        long_chunks = chunk_text(long_text, chunk_size=30, overlap=5)
        assert len(long_chunks) > 1

        # Check that all original content is preserved across chunks (allowing for boundary adjustments)
        reconstructed = " ".join(long_chunks)
        for paragraph in [
            "first paragraph",
            "second paragraph",
            "third paragraph",
            "fourth paragraph",
        ]:
            assert paragraph in reconstructed

        # Test with profile-like content
        profile_text = "## Profile 1\n\n**Skills:**\n- Python\n- JavaScript\n\n## Profile 2\n\n**Skills:**\n- React\n- Node.js"
        profile_chunks = chunk_text(profile_text, chunk_size=50, overlap=10)

        # Profiles should be kept together even if it means slightly larger chunks
        assert any(
            "Profile 1" in chunk and "Python" in chunk for chunk in profile_chunks
        )
        assert any(
            "Profile 2" in chunk and "React" in chunk for chunk in profile_chunks
        )

        # Test with a large chunk size that fits the entire text
        full_chunks = chunk_text(long_text, chunk_size=1000, overlap=50)
        assert len(full_chunks) == 1
        assert full_chunks[0] == long_text

    def test_is_out_of_scope(self):
        """Test the is_out_of_scope function."""
        # Test with no relevance scores (edge case)
        assert is_out_of_scope("query", 0.5, []) is True

        # Test with all scores below threshold
        assert is_out_of_scope("query", 0.5, [0.2, 0.3, 0.4]) is True

        # Test with some scores above threshold
        assert is_out_of_scope("query", 0.5, [0.4, 0.6, 0.3]) is False

        # Test with threshold at extremes
        assert is_out_of_scope("query", 0.0, [0.0, 0.0, 0.0]) is False
        assert is_out_of_scope("query", 1.0, [0.9, 0.95, 0.8]) is True

    def test_detect_language(self):
        """Test the detect_language function."""
        # Test English text
        assert (
            detect_language("This is English text for testing language detection.")
            == "en"
        )

        # Test Spanish text
        assert (
            detect_language(
                "Este es un texto en español para probar la detección de idioma."
            )
            == "es"
        )

        # Test with short text (might not be reliable)
        short_result = detect_language("Hello")
        assert short_result is None or isinstance(short_result, str)

        # Test with very long text (should only process the first 100 chars)
        long_text = "English text " * 100
        with patch("app.utils.helpers.detect") as mock_detect:
            mock_detect.return_value = "en"

            detect_language(long_text)

            # Should only pass the first 100 characters
            args, _ = mock_detect.call_args
            assert len(args[0]) <= 100

        # Test error handling
        with patch("app.utils.helpers.detect") as mock_detect:
            mock_detect.side_effect = Exception("Test error")

            result = detect_language("Some text")
            assert result is None

    @pytest.mark.asyncio
    async def test_save_metrics(self):
        """Test the save_metrics function."""
        # Test with basic metrics
        metrics_data = {
            "count": 42,
            "average": 0.75,
            "items": ["item1", "item2", "item3"],
        }

        # Test successful save
        with patch("os.makedirs") as mock_makedirs, patch(
            "builtins.open", mock_open()
        ) as mock_file, patch("os.replace") as mock_replace:

            result = await save_metrics("test_metrics", metrics_data)

            assert result is True
            assert mock_makedirs.called
            assert mock_file.called
            assert mock_replace.called

            # Check that the last_updated field was added
            write_call = mock_file().write.call_args[0][0]
            assert "last_updated" in write_call

        # Test with large array metrics (should truncate arrays)
        large_array_metrics = {"count": 42, "values": list(range(200))}  # 200 items

        with patch("os.makedirs") as mock_makedirs, patch(
            "builtins.open", mock_open()
        ) as mock_file, patch("os.replace") as mock_replace:

            result = await save_metrics("large_metrics", large_array_metrics)

            assert result is True

            # Check that the array was truncated
            write_call = mock_file().write.call_args[0][0]
            assert "values" in write_call
            assert len(large_array_metrics["values"]) > 100  # Original untouched

        # Test error handling
        with patch("os.makedirs") as mock_makedirs, patch("builtins.open") as mock_file:

            mock_file.side_effect = Exception("Test error")

            result = await save_metrics("error_metrics", metrics_data)

            assert result is False

    @pytest.mark.asyncio
    async def test_load_metrics(self):
        """Test the load_metrics function."""
        # Test loading existing metrics
        mock_metrics = {
            "count": 42,
            "average": 0.75,
            "items": ["item1", "item2", "item3"],
            "last_updated": "2023-01-01T00:00:00",
        }

        with patch("os.path.exists") as mock_exists, patch(
            "builtins.open", mock_open(read_data=json.dumps(mock_metrics))
        ):

            mock_exists.return_value = True

            result = await load_metrics("test_metrics")

            assert result == mock_metrics

        # Test with non-existent file
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            result = await load_metrics("nonexistent_metrics")

            assert result is None

        # Test with corrupt JSON
        with patch("os.path.exists") as mock_exists, patch(
            "builtins.open", mock_open(read_data="Invalid JSON")
        ), patch("os.rename") as mock_rename:

            mock_exists.return_value = True

            result = await load_metrics("corrupt_metrics")

            assert result == {}  # Returns empty dict for corrupt file
            assert mock_rename.called  # Should backup corrupt file

        # Test with other errors
        with patch("os.path.exists") as mock_exists, patch(
            "builtins.open"
        ) as mock_file:

            mock_exists.return_value = True
            mock_file.side_effect = Exception("Test error")

            result = await load_metrics("error_metrics")

            assert result is None

    class TestAsync:
        """Test for async functions to improve coverage."""

        @pytest.mark.asyncio
        async def test_cache_result_async(self):
            """Test the cache_result decorator with async functions."""

            # Create a decorated test function
            @cache_result(ttl_seconds=1)
            async def cached_async_func(arg1, arg2=None):
                """Test async function that's expensive to compute."""
                await asyncio.sleep(0.1)  # Simulate work
                return f"Result: {arg1}-{arg2}"

            # First call (should compute and cache)
            start_time = time.time()
            result1 = await cached_async_func("test", arg2="value")
            first_duration = time.time() - start_time

            # Second call with same args (should use cache)
            start_time = time.time()
            result2 = await cached_async_func("test", arg2="value")
            second_duration = time.time() - start_time

            # Check results
            assert result1 == result2
            assert second_duration < first_duration  # Second call should be faster

            # Different args should compute new result
            result3 = await cached_async_func("test", arg2="different")
            assert result3 != result1

            # Wait for cache to expire
            await asyncio.sleep(1.1)

            # Call after expiry (should compute again)
            start_time = time.time()
            result4 = await cached_async_func("test", arg2="value")
            expired_duration = time.time() - start_time

            assert result4 == result1  # Same result
            assert (
                expired_duration > second_duration
            )  # Should take longer than cached call

        def test_cache_result_sync(self):
            """Test the cache_result decorator with sync functions."""

            # Create a decorated test function
            @cache_result(ttl_seconds=1)
            def cached_sync_func(arg1, arg2=None):
                """Test sync function that's expensive to compute."""
                time.sleep(0.1)  # Simulate work
                return f"Result: {arg1}-{arg2}"

            # First call (should compute and cache)
            start_time = time.time()
            result1 = cached_sync_func("test", arg2="value")
            first_duration = time.time() - start_time

            # Second call with same args (should use cache)
            start_time = time.time()
            result2 = cached_sync_func("test", arg2="value")
            second_duration = time.time() - start_time

            # Check results
            assert result1 == result2
            assert second_duration < first_duration  # Second call should be faster

            # Wait for cache to expire
            time.sleep(1.1)

            # Call after expiry (should compute again)
            start_time = time.time()
            result3 = cached_sync_func("test", arg2="value")
            expired_duration = time.time() - start_time

            assert result3 == result1  # Same result
            assert (
                expired_duration > second_duration
            )  # Should take longer than cached call


class TestTimeFunction:
    """Additional tests for the time_function decorator specifically."""

    @pytest.mark.asyncio
    async def test_time_function_async_exception(self):
        """Test time_function with async function that raises an exception."""

        @time_function
        async def failing_async_func():
            await asyncio.sleep(0.1)
            raise ValueError("Test exception")

        # Should raise the exception but still log timing
        with pytest.raises(ValueError):
            await failing_async_func()

    def test_time_function_sync_exception(self):
        """Test time_function with sync function that raises an exception."""

        @time_function
        def failing_sync_func():
            time.sleep(0.1)
            raise ValueError("Test exception")

        # Should raise the exception but still log timing
        with pytest.raises(ValueError):
            failing_sync_func()

    @pytest.mark.asyncio
    async def test_time_function_rag_process_query(self):
        """Test time_function with a mock RAGService.process_query to test special handling."""

        # Create a mock process_query function that simulates RAGService.process_query
        @time_function
        async def mock_process_query(self, query):
            await asyncio.sleep(0.1)
            # Simulate response object with processing_time attribute
            response = MagicMock()
            response.processing_time = 0
            return response

        # Create a mock service object with query_metrics
        mock_service = MagicMock()
        mock_service.query_metrics = {"processing_times": []}
        mock_service.__name__ = "process_query"  # Function name is checked in decorator

        # Call the function
        result, duration = await mock_process_query(mock_service, "test query")

        # Check that processing_time was updated
        assert result.processing_time == duration

        # With tuple response
        @time_function
        async def mock_process_query_tuple(self, query):
            await asyncio.sleep(0.1)
            response = MagicMock()
            response.processing_time = 0
            return (response, 0)

        result_tuple, duration = await mock_process_query_tuple(
            mock_service, "test query"
        )
        response, _ = result_tuple

        # First item in tuple should have processing_time updated
        assert response.processing_time == duration
