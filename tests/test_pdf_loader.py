"""Tests for the PDF loader module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gemini_pdf_analyzer.models import PdfDocument
from gemini_pdf_analyzer.pdf_loader import (
    extract_text,
    list_pdf_files,
    load_pdfs,
)


class TestListPdfFiles:
    """Tests for list_pdf_files function."""
    
    def test_list_pdf_files_empty_directory(self, tmp_path: Path) -> None:
        """Test listing PDFs in an empty directory."""
        result = list_pdf_files(tmp_path)
        assert result == []
    
    def test_list_pdf_files_with_pdfs(self, tmp_path: Path) -> None:
        """Test listing PDFs when files exist."""
        (tmp_path / "doc1.pdf").touch()
        (tmp_path / "doc2.pdf").touch()
        (tmp_path / "other.txt").touch()
        
        result = list_pdf_files(tmp_path)
        
        assert len(result) == 2
        names = [p.name for p in result]
        assert "doc1.pdf" in names
        assert "doc2.pdf" in names
        assert "other.txt" not in names
    
    def test_list_pdf_files_with_filter(self, tmp_path: Path) -> None:
        """Test filtering PDFs by filename pattern."""
        (tmp_path / "report_2024.pdf").touch()
        (tmp_path / "report_2025.pdf").touch()
        (tmp_path / "invoice_001.pdf").touch()
        
        result = list_pdf_files(tmp_path, filter_pattern="report*.pdf")
        
        assert len(result) == 2
        names = [p.name for p in result]
        assert "report_2024.pdf" in names
        assert "report_2025.pdf" in names
        assert "invoice_001.pdf" not in names
    
    def test_list_pdf_files_nonexistent_directory(self) -> None:
        """Test error when directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            list_pdf_files(Path("/nonexistent/directory"))
    
    def test_list_pdf_files_not_a_directory(self, tmp_path: Path) -> None:
        """Test error when path is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.touch()
        
        with pytest.raises(ValueError):
            list_pdf_files(file_path)


class TestExtractText:
    """Tests for extract_text function."""
    
    @patch("gemini_pdf_analyzer.pdf_loader.PdfReader")
    def test_extract_text_success(self, mock_reader_class: MagicMock) -> None:
        """Test successful text extraction from PDF."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader_class.return_value = mock_reader
        
        text, page_count = extract_text(Path("test.pdf"))
        
        assert "Page 1 content" in text
        assert "Page 2 content" in text
        assert page_count == 2
    
    @patch("gemini_pdf_analyzer.pdf_loader.PdfReader")
    def test_extract_text_empty_page(self, mock_reader_class: MagicMock) -> None:
        """Test handling of page with no extractable text."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader
        
        text, page_count = extract_text(Path("test.pdf"))
        
        assert text == ""
        assert page_count == 1


class TestLoadPdfs:
    """Tests for load_pdfs function."""
    
    @patch("gemini_pdf_analyzer.pdf_loader.extract_text")
    @patch("gemini_pdf_analyzer.pdf_loader.list_pdf_files")
    def test_load_pdfs_success(
        self,
        mock_list: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path
    ) -> None:
        """Test successful loading of multiple PDFs."""
        mock_list.return_value = [
            tmp_path / "doc1.pdf",
            tmp_path / "doc2.pdf",
        ]
        mock_extract.return_value = ("Sample text content", 5)
        
        result = load_pdfs(tmp_path, show_progress=False)
        
        assert len(result) == 2
        assert all(isinstance(doc, PdfDocument) for doc in result)
        assert result[0].filename == "doc1.pdf"
        assert result[0].text == "Sample text content"
        assert result[0].page_count == 5
    
    @patch("gemini_pdf_analyzer.pdf_loader.extract_text")
    @patch("gemini_pdf_analyzer.pdf_loader.list_pdf_files")
    def test_load_pdfs_with_max_docs(
        self,
        mock_list: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path
    ) -> None:
        """Test max_docs limit is respected."""
        mock_list.return_value = [
            tmp_path / f"doc{i}.pdf" for i in range(10)
        ]
        mock_extract.return_value = ("Text", 1)
        
        result = load_pdfs(tmp_path, max_docs=3, show_progress=False)
        
        assert len(result) == 3
    
    @patch("gemini_pdf_analyzer.pdf_loader.extract_text")
    @patch("gemini_pdf_analyzer.pdf_loader.list_pdf_files")
    def test_load_pdfs_with_filter(
        self,
        mock_list: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path
    ) -> None:
        """Test filter pattern is passed to list_pdf_files."""
        mock_list.return_value = [tmp_path / "report.pdf"]
        mock_extract.return_value = ("Text", 1)
        
        load_pdfs(tmp_path, filter_pattern="report*.pdf", show_progress=False)
        
        mock_list.assert_called_once_with(tmp_path, "report*.pdf")
    
    @patch("gemini_pdf_analyzer.pdf_loader.extract_text")
    @patch("gemini_pdf_analyzer.pdf_loader.list_pdf_files")
    def test_load_pdfs_handles_extraction_error(
        self,
        mock_list: MagicMock,
        mock_extract: MagicMock,
        tmp_path: Path
    ) -> None:
        """Test handling of PDF extraction errors."""
        mock_list.return_value = [tmp_path / "bad.pdf"]
        mock_extract.side_effect = Exception("Cannot read PDF")
        
        result = load_pdfs(tmp_path, show_progress=False)
        
        assert len(result) == 1
        assert result[0].text == ""
