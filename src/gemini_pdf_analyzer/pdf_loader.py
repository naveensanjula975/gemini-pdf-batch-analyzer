"""
PDF loader module for Gemini PDF Analyzer.

Handles scanning directories for PDFs and extracting text using pypdf.
"""

import fnmatch
import logging
from pathlib import Path
from typing import List, Optional

from pypdf import PdfReader
from tqdm import tqdm

from .models import PdfDocument

logger = logging.getLogger(__name__)


def list_pdf_files(
    input_dir: Path,
    filter_pattern: Optional[str] = None
) -> List[Path]:
    """
    Scan a directory for PDF files.
    
    Args:
        input_dir: Directory to scan for PDFs
        filter_pattern: Optional glob/fnmatch pattern to filter filenames
        
    Returns:
        List of paths to PDF files
        
    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")
    
    pdf_files = list(input_dir.glob("*.pdf"))
    pdf_files.extend(input_dir.glob("*.PDF"))
    
    # Remove duplicates (case-insensitive systems might have both)
    unique_files = list(set(pdf_files))
    
    # Apply filter pattern if provided
    if filter_pattern:
        filtered = [
            f for f in unique_files 
            if fnmatch.fnmatch(f.name.lower(), filter_pattern.lower())
        ]
        logger.info(f"Filter '{filter_pattern}' matched {len(filtered)} of {len(unique_files)} files")
        unique_files = filtered
    
    unique_files.sort(key=lambda p: p.name.lower())
    
    logger.info(f"Found {len(unique_files)} PDF files in {input_dir}")
    return unique_files


def extract_text(path: Path) -> tuple[str, int]:
    """
    Extract text content from a PDF file.
    
    Args:
        path: Path to the PDF file
        
    Returns:
        Tuple of (extracted text, page count)
        
    Raises:
        Exception: If PDF cannot be read or parsed
    """
    logger.debug(f"Extracting text from: {path.name}")
    
    reader = PdfReader(path)
    page_count = len(reader.pages)
    
    text_parts = []
    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
        except Exception as e:
            logger.warning(f"Failed to extract text from page {i+1} of {path.name}: {e}")
            text_parts.append("")
    
    full_text = "\n\n".join(text_parts)
    logger.debug(f"Extracted {len(full_text)} characters from {page_count} pages")
    
    return full_text, page_count


def load_pdfs(
    input_dir: Path,
    max_docs: Optional[int] = None,
    filter_pattern: Optional[str] = None,
    show_progress: bool = True
) -> List[PdfDocument]:
    """
    Load all PDF files from a directory.
    
    Args:
        input_dir: Directory containing PDF files
        max_docs: Maximum number of documents to load (None for all)
        filter_pattern: Optional glob/fnmatch pattern to filter filenames
        show_progress: Whether to show a progress bar
        
    Returns:
        List of PdfDocument objects with extracted text
    """
    pdf_files = list_pdf_files(input_dir, filter_pattern)
    
    if max_docs is not None:
        pdf_files = pdf_files[:max_docs]
        logger.info(f"Limited to {max_docs} documents")
    
    documents = []
    
    # Create progress bar iterator
    iterator = tqdm(
        pdf_files,
        desc="Loading PDFs",
        unit="file",
        disable=not show_progress
    )
    
    for pdf_path in iterator:
        iterator.set_postfix_str(pdf_path.name[:30])
        try:
            text, page_count = extract_text(pdf_path)
            doc = PdfDocument(
                path=pdf_path,
                filename=pdf_path.name,
                text=text,
                page_count=page_count,
            )
            documents.append(doc)
            logger.debug(f"Loaded: {pdf_path.name} ({page_count} pages, {len(text)} chars)")
        except Exception as e:
            logger.error(f"Failed to load {pdf_path.name}: {e}")
            # Create a document entry with error info
            doc = PdfDocument(
                path=pdf_path,
                filename=pdf_path.name,
                text="",
                page_count=0,
            )
            documents.append(doc)
    
    logger.info(f"Successfully loaded {len(documents)} documents")
    return documents
