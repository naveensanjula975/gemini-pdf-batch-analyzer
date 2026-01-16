"""Tests for the caching module."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from gemini_pdf_analyzer.cache import (
    load_cache,
    save_cache,
    get_cached_result,
    cache_result,
    clear_cache,
    _compute_file_hash,
)
from gemini_pdf_analyzer.models import PdfDocument, PdfAnalysisResult


class TestComputeFileHash:
    """Tests for file hash computation."""
    
    def test_compute_hash_same_content(self, tmp_path: Path) -> None:
        """Files with same content should have same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("hello world")
        file2.write_text("hello world")
        
        assert _compute_file_hash(file1) == _compute_file_hash(file2)
    
    def test_compute_hash_different_content(self, tmp_path: Path) -> None:
        """Files with different content should have different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("hello")
        file2.write_text("world")
        
        assert _compute_file_hash(file1) != _compute_file_hash(file2)


class TestLoadSaveCache:
    """Tests for cache loading and saving."""
    
    def test_load_cache_empty(self, tmp_path: Path) -> None:
        """Test loading cache when no cache file exists."""
        result = load_cache(tmp_path)
        assert result == {}
    
    def test_save_and_load_cache(self, tmp_path: Path) -> None:
        """Test saving and loading cache."""
        cache = {
            "test.pdf": {
                "filename": "test.pdf",
                "summary": "Test summary",
                "file_hash": "abc123"
            }
        }
        
        save_cache(tmp_path, cache)
        loaded = load_cache(tmp_path)
        
        assert loaded == cache
    
    def test_clear_cache(self, tmp_path: Path) -> None:
        """Test clearing the cache."""
        cache = {"test.pdf": {"summary": "test"}}
        save_cache(tmp_path, cache)
        
        result = clear_cache(tmp_path)
        
        assert result is True
        assert load_cache(tmp_path) == {}
    
    def test_clear_cache_nonexistent(self, tmp_path: Path) -> None:
        """Test clearing non-existent cache returns False."""
        result = clear_cache(tmp_path)
        assert result is False


class TestCacheResult:
    """Tests for caching and retrieving results."""
    
    @pytest.fixture
    def sample_doc(self, tmp_path: Path) -> PdfDocument:
        """Create a sample document with an actual file."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")
        return PdfDocument(
            path=pdf_path,
            filename="test.pdf",
            text="Sample text",
            page_count=1,
        )
    
    @pytest.fixture
    def sample_result(self) -> PdfAnalysisResult:
        """Create a sample analysis result."""
        return PdfAnalysisResult(
            filename="test.pdf",
            summary="Test summary",
            key_entities="Entity A",
            action_items="Action 1",
            keywords=["test", "sample"],
        )
    
    def test_cache_and_retrieve_result(
        self,
        sample_doc: PdfDocument,
        sample_result: PdfAnalysisResult
    ) -> None:
        """Test caching and retrieving a result."""
        cache = {}
        
        cache_result(cache, sample_doc, sample_result)
        retrieved = get_cached_result(cache, sample_doc)
        
        assert retrieved is not None
        assert retrieved.filename == sample_result.filename
        assert retrieved.summary == sample_result.summary
        assert retrieved.keywords == sample_result.keywords
    
    def test_cache_miss_file_changed(
        self,
        sample_doc: PdfDocument,
        sample_result: PdfAnalysisResult
    ) -> None:
        """Test cache miss when file has changed."""
        cache = {}
        
        cache_result(cache, sample_doc, sample_result)
        
        # Modify the file
        sample_doc.path.write_bytes(b"modified content")
        
        retrieved = get_cached_result(cache, sample_doc)
        assert retrieved is None
    
    def test_cache_miss_not_cached(self, sample_doc: PdfDocument) -> None:
        """Test cache miss when file not in cache."""
        cache = {}
        
        result = get_cached_result(cache, sample_doc)
        assert result is None
