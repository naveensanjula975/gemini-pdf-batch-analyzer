"""Tests for the analyzer module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gemini_pdf_analyzer.analyzer import (
    _parse_response,
    analyze_document,
    create_client,
)
from gemini_pdf_analyzer.config import AppConfig
from gemini_pdf_analyzer.models import PdfDocument


class TestParseResponse:
    """Tests for _parse_response helper function."""
    
    def test_parse_complete_response(self) -> None:
        """Test parsing a well-formed response."""
        response = """SUMMARY:
This is a test document about Python programming.

KEY ENTITIES:
Python, Programming, Testing, pytest

ACTION ITEMS:
Review the code, Write more tests

KEYWORDS:
python, testing, code, development, software"""
        
        result = _parse_response(response, "test.pdf")
        
        assert result.filename == "test.pdf"
        assert "test document" in result.summary.lower() or "python" in result.summary.lower()
        assert len(result.keywords) > 0
    
    def test_parse_partial_response(self) -> None:
        """Test parsing a response with missing sections."""
        response = """SUMMARY:
Just a summary, nothing else."""
        
        result = _parse_response(response, "partial.pdf")
        
        assert result.filename == "partial.pdf"
        assert "summary" in result.summary.lower() or "Just" in result.summary
    
    def test_parse_empty_response(self) -> None:
        """Test parsing an empty response."""
        result = _parse_response("", "empty.pdf")
        
        assert result.filename == "empty.pdf"
        # Should have some default handling


class TestCreateClient:
    """Tests for create_client function."""
    
    @patch("gemini_pdf_analyzer.analyzer.genai.Client")
    def test_create_client_success(self, mock_client_class: MagicMock) -> None:
        """Test successful client creation."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        result = create_client("test-api-key")
        
        mock_client_class.assert_called_once_with(api_key="test-api-key")
        assert result == mock_client


class TestAnalyzeDocument:
    """Tests for analyze_document function."""
    
    @pytest.fixture
    def sample_config(self) -> AppConfig:
        """Create a sample config for testing."""
        return AppConfig(
            gemini_api_key="test-key",
            input_dir=Path("input"),
            output_dir=Path("output"),
            model_name="gemini-2.0-flash",
            max_chars_per_doc=1000,
        )
    
    @pytest.fixture
    def sample_document(self) -> PdfDocument:
        """Create a sample document for testing."""
        return PdfDocument(
            path=Path("test.pdf"),
            filename="test.pdf",
            text="This is sample document text for testing purposes.",
            page_count=1,
        )
    
    def test_analyze_empty_document(self, sample_config: AppConfig) -> None:
        """Test handling of empty document."""
        empty_doc = PdfDocument(
            path=Path("empty.pdf"),
            filename="empty.pdf",
            text="",
            page_count=0,
        )
        
        mock_client = MagicMock()
        result = analyze_document(mock_client, empty_doc, sample_config)
        
        assert result.filename == "empty.pdf"
        assert result.error is not None or "no extractable text" in result.summary.lower()
        # Should not call the API for empty documents
        mock_client.models.generate_content.assert_not_called()
    
    @patch("gemini_pdf_analyzer.analyzer.time.sleep")  # Speed up tests
    def test_analyze_document_success(
        self,
        mock_sleep: MagicMock,
        sample_document: PdfDocument,
        sample_config: AppConfig,
    ) -> None:
        """Test successful document analysis."""
        mock_response = MagicMock()
        mock_response.text = """SUMMARY:
Test document summary.

KEY ENTITIES:
Test Entity

ACTION ITEMS:
Test action

KEYWORDS:
test, document"""
        
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        result = analyze_document(mock_client, sample_document, sample_config)
        
        assert result.filename == "test.pdf"
        assert result.is_successful
        assert "summary" in result.summary.lower() or "Test" in result.summary
    
    @patch("gemini_pdf_analyzer.analyzer.time.sleep")
    def test_analyze_document_api_error_retries(
        self,
        mock_sleep: MagicMock,
        sample_document: PdfDocument,
        sample_config: AppConfig,
    ) -> None:
        """Test retry behavior on API errors."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        
        result = analyze_document(mock_client, sample_document, sample_config)
        
        # Should have retried 3 times
        assert mock_client.models.generate_content.call_count == 3
        assert result.error is not None
        assert "API Error" in result.error
    
    def test_analyze_document_truncates_long_text(
        self,
        sample_config: AppConfig,
    ) -> None:
        """Test that long documents are truncated."""
        long_doc = PdfDocument(
            path=Path("long.pdf"),
            filename="long.pdf",
            text="A" * 5000,  # Much longer than max_chars_per_doc
            page_count=10,
        )
        sample_config.max_chars_per_doc = 1000
        
        mock_response = MagicMock()
        mock_response.text = "SUMMARY:\nTest"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        analyze_document(mock_client, long_doc, sample_config)
        
        # Check that the prompt was called with truncated text
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents") or call_args.args[0]
        # The prompt should not contain all 5000 'A's
        assert len(prompt) < 5000
