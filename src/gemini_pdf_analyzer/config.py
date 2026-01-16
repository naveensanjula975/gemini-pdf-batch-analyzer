"""
Configuration module for Gemini PDF Analyzer.

Handles loading configuration from environment variables and provides defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class AppConfig:
    """Application configuration settings."""
    
    gemini_api_key: str
    input_dir: Path
    output_dir: Path
    model_name: str = "gemini-2.0-flash"
    max_chars_per_doc: int = 15000
    max_docs: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Ensure paths are Path objects."""
        if isinstance(self.input_dir, str):
            self.input_dir = Path(self.input_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)


def load_config(
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    model_name: Optional[str] = None,
    max_docs: Optional[int] = None,
) -> AppConfig:
    """
    Load configuration from environment variables and CLI overrides.
    
    CLI arguments take precedence over environment variables.
    
    Args:
        input_dir: Override for input directory path
        output_dir: Override for output directory path
        model_name: Override for Gemini model name
        max_docs: Maximum number of documents to process
        
    Returns:
        AppConfig instance with all settings
        
    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    # Load .env file if present
    load_dotenv()
    
    # Get API key (required)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required. "
            "Set it in .env file or export it in your shell."
        )
    
    # Get paths with defaults
    default_input = os.getenv("INPUT_DIR", "data/input_pdfs")
    default_output = os.getenv("OUTPUT_DIR", "data/output")
    default_model = os.getenv("MODEL_NAME", "gemini-2.0-flash")
    default_max_chars = int(os.getenv("MAX_CHARS_PER_DOC", "15000"))
    
    return AppConfig(
        gemini_api_key=api_key,
        input_dir=Path(input_dir) if input_dir else Path(default_input),
        output_dir=Path(output_dir) if output_dir else Path(default_output),
        model_name=model_name or default_model,
        max_chars_per_doc=default_max_chars,
        max_docs=max_docs,
    )
