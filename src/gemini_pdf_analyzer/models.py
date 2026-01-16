"""
Data models for Gemini PDF Analyzer.

Defines dataclasses for PDF documents and analysis results.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PdfDocument:
    """Represents a loaded PDF document with extracted text."""
    
    path: Path
    filename: str
    text: str
    page_count: int = 0
    
    @property
    def text_length(self) -> int:
        """Return the length of extracted text."""
        return len(self.text)


@dataclass  
class PdfAnalysisResult:
    """Result of Gemini analysis for a single PDF document."""
    
    filename: str
    summary: str
    key_entities: str
    action_items: str
    keywords: List[str] = field(default_factory=list)
    raw_response: str = ""
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if analysis was successful."""
        return self.error is None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        return {
            "filename": self.filename,
            "summary": self.summary,
            "key_entities": self.key_entities,
            "action_items": self.action_items,
            "keywords": ", ".join(self.keywords) if self.keywords else "",
            "error": self.error or "",
        }
