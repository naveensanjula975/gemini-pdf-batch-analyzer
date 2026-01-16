"""
Export module for Gemini PDF Analyzer.

Handles exporting analysis results to CSV, JSON, and Excel formats.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from .models import PdfAnalysisResult

logger = logging.getLogger(__name__)


def _ensure_output_dir(output_dir: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_dir.mkdir(parents=True, exist_ok=True)


def _generate_filename(prefix: str, extension: str) -> str:
    """Generate a timestamped filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def _results_to_dataframe(results: List[PdfAnalysisResult]) -> pd.DataFrame:
    """Convert results to a pandas DataFrame with proper column ordering."""
    data = [result.to_dict() for result in results]
    df = pd.DataFrame(data)
    
    # Reorder columns for readability
    column_order = ["filename", "summary", "key_entities", "action_items", "keywords", "error"]
    columns = [col for col in column_order if col in df.columns]
    return df[columns]


def export_to_csv(
    results: List[PdfAnalysisResult],
    output_dir: Path,
    filename: str | None = None
) -> Path:
    """
    Export analysis results to a CSV file.
    
    Args:
        results: List of analysis results to export
        output_dir: Directory to save the CSV file
        filename: Optional custom filename (auto-generated if not provided)
        
    Returns:
        Path to the created CSV file
    """
    _ensure_output_dir(output_dir)
    
    if not filename:
        filename = _generate_filename("analysis_results", "csv")
    
    output_path = output_dir / filename
    df = _results_to_dataframe(results)
    
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Exported {len(results)} results to CSV: {output_path}")
    
    return output_path


def export_to_excel(
    results: List[PdfAnalysisResult],
    output_dir: Path,
    filename: str | None = None
) -> Path:
    """
    Export analysis results to an Excel file (.xlsx).
    
    Args:
        results: List of analysis results to export
        output_dir: Directory to save the Excel file
        filename: Optional custom filename (auto-generated if not provided)
        
    Returns:
        Path to the created Excel file
    """
    _ensure_output_dir(output_dir)
    
    if not filename:
        filename = _generate_filename("analysis_results", "xlsx")
    
    output_path = output_dir / filename
    df = _results_to_dataframe(results)
    
    # Write to Excel with formatting
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Analysis Results")
        
        # Auto-adjust column widths
        worksheet = writer.sheets["Analysis Results"]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            )
            # Cap at 50 chars for readability
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width
    
    logger.info(f"Exported {len(results)} results to Excel: {output_path}")
    
    return output_path


def export_to_json(
    results: List[PdfAnalysisResult],
    output_dir: Path,
    filename: str | None = None,
    jsonl: bool = True
) -> Path:
    """
    Export analysis results to JSON format.
    
    Args:
        results: List of analysis results to export
        output_dir: Directory to save the JSON file
        filename: Optional custom filename (auto-generated if not provided)
        jsonl: If True, export as JSON Lines (one JSON object per line)
        
    Returns:
        Path to the created JSON file
    """
    _ensure_output_dir(output_dir)
    
    extension = "jsonl" if jsonl else "json"
    if not filename:
        filename = _generate_filename("analysis_results", extension)
    
    output_path = output_dir / filename
    
    # Convert to dictionaries
    data = [result.to_dict() for result in results]
    
    with open(output_path, "w", encoding="utf-8") as f:
        if jsonl:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Exported {len(results)} results to JSON: {output_path}")
    
    return output_path


def export_results(
    results: List[PdfAnalysisResult],
    output_dir: Path,
    formats: List[str] | None = None
) -> dict[str, Path]:
    """
    Export results to multiple formats.
    
    Args:
        results: List of analysis results to export
        output_dir: Directory to save output files
        formats: List of formats to export ("csv", "json", "jsonl", "excel")
                 Defaults to ["csv", "jsonl"]
                 
    Returns:
        Dictionary mapping format names to output file paths
    """
    if formats is None:
        formats = ["csv", "jsonl"]
    
    output_files = {}
    
    for fmt in formats:
        if fmt == "csv":
            output_files["csv"] = export_to_csv(results, output_dir)
        elif fmt == "json":
            output_files["json"] = export_to_json(results, output_dir, jsonl=False)
        elif fmt == "jsonl":
            output_files["jsonl"] = export_to_json(results, output_dir, jsonl=True)
        elif fmt == "excel":
            output_files["excel"] = export_to_excel(results, output_dir)
        else:
            logger.warning(f"Unknown export format: {fmt}")
    
    return output_files
