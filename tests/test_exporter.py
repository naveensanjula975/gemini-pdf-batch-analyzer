"""Tests for the exporter module."""

import csv
import json
from pathlib import Path

import pytest

from gemini_pdf_analyzer.exporter import (
    export_to_csv,
    export_to_json,
    export_results,
)
from gemini_pdf_analyzer.models import PdfAnalysisResult


@pytest.fixture
def sample_results() -> list[PdfAnalysisResult]:
    """Create sample analysis results for testing."""
    return [
        PdfAnalysisResult(
            filename="doc1.pdf",
            summary="Summary of document 1",
            key_entities="Entity A, Entity B",
            action_items="Action 1, Action 2",
            keywords=["keyword1", "keyword2"],
        ),
        PdfAnalysisResult(
            filename="doc2.pdf",
            summary="Summary of document 2",
            key_entities="Entity C",
            action_items="None",
            keywords=["keyword3"],
        ),
        PdfAnalysisResult(
            filename="failed.pdf",
            summary="",
            key_entities="",
            action_items="",
            keywords=[],
            error="Failed to process",
        ),
    ]


class TestExportToCsv:
    """Tests for export_to_csv function."""
    
    def test_export_creates_file(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test that CSV file is created."""
        output_path = export_to_csv(
            sample_results,
            tmp_path,
            filename="test_output.csv",
        )
        
        assert output_path.exists()
        assert output_path.suffix == ".csv"
    
    def test_export_csv_content(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test CSV file contains expected data."""
        output_path = export_to_csv(
            sample_results,
            tmp_path,
            filename="test_output.csv",
        )
        
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0]["filename"] == "doc1.pdf"
        assert rows[0]["summary"] == "Summary of document 1"
        assert "keyword1" in rows[0]["keywords"]
        assert rows[2]["error"] == "Failed to process"
    
    def test_export_csv_auto_filename(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test auto-generated filename."""
        output_path = export_to_csv(sample_results, tmp_path)
        
        assert output_path.exists()
        assert "analysis_results" in output_path.name
        assert output_path.suffix == ".csv"
    
    def test_export_creates_directory(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test that output directory is created if it doesn't exist."""
        nested_dir = tmp_path / "nested" / "output"
        
        output_path = export_to_csv(
            sample_results,
            nested_dir,
            filename="test.csv",
        )
        
        assert nested_dir.exists()
        assert output_path.exists()


class TestExportToJson:
    """Tests for export_to_json function."""
    
    def test_export_jsonl_format(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test JSONL export format."""
        output_path = export_to_json(
            sample_results,
            tmp_path,
            filename="test.jsonl",
            jsonl=True,
        )
        
        assert output_path.exists()
        
        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "filename" in data
            assert "summary" in data
    
    def test_export_json_array_format(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test JSON array export format."""
        output_path = export_to_json(
            sample_results,
            tmp_path,
            filename="test.json",
            jsonl=False,
        )
        
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["filename"] == "doc1.pdf"


class TestExportResults:
    """Tests for export_results multi-format function."""
    
    def test_export_multiple_formats(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test exporting to multiple formats at once."""
        output_files = export_results(
            sample_results,
            tmp_path,
            formats=["csv", "jsonl"],
        )
        
        assert "csv" in output_files
        assert "jsonl" in output_files
        assert output_files["csv"].exists()
        assert output_files["jsonl"].exists()
    
    def test_export_default_formats(
        self,
        sample_results: list[PdfAnalysisResult],
        tmp_path: Path,
    ) -> None:
        """Test default format selection."""
        output_files = export_results(sample_results, tmp_path)
        
        # Default should include csv and jsonl
        assert "csv" in output_files
        assert "jsonl" in output_files
    
    def test_export_empty_results(self, tmp_path: Path) -> None:
        """Test exporting empty results list."""
        output_files = export_results([], tmp_path, formats=["csv"])
        
        assert output_files["csv"].exists()
        
        with open(output_files["csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 0
