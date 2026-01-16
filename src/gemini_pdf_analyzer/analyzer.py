"""
Gemini analyzer module for PDF analysis.

Handles interaction with Google Gemini API for document analysis.
"""

import logging
import time
from typing import Callable, Dict, List, Optional

from google import genai
from google.genai import types
from tqdm import tqdm

from .config import AppConfig
from .models import PdfDocument, PdfAnalysisResult

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# Analysis prompt template
ANALYSIS_PROMPT = """Analyze the following document and provide a structured analysis.

DOCUMENT TEXT:
{document_text}

Please provide your analysis in the following format:

SUMMARY:
[A concise 2-3 sentence summary of the document's main content and purpose]

KEY ENTITIES:
[List the key people, organizations, dates, and important terms mentioned]

ACTION ITEMS:
[List any action items, tasks, or recommendations found in the document. Write "None identified" if there are no action items]

KEYWORDS:
[Comma-separated list of 5-10 relevant keywords that describe this document]

Respond only with the analysis in the exact format above."""


def create_client(api_key: str) -> genai.Client:
    """
    Initialize the Gemini API client.
    
    Args:
        api_key: Google Gemini API key
        
    Returns:
        Configured Gemini client
    """
    client = genai.Client(api_key=api_key)
    logger.info("Gemini client initialized")
    return client


def _parse_response(response_text: str, filename: str) -> PdfAnalysisResult:
    """
    Parse the structured response from Gemini into a PdfAnalysisResult.
    
    Args:
        response_text: Raw response text from Gemini
        filename: Name of the analyzed file
        
    Returns:
        Parsed PdfAnalysisResult
    """
    # Initialize with defaults
    summary = ""
    key_entities = ""
    action_items = ""
    keywords: List[str] = []
    
    # Parse sections from response
    current_section = None
    current_content: List[str] = []
    
    for line in response_text.split("\n"):
        line_stripped = line.strip()
        line_upper = line_stripped.upper()
        
        if line_upper.startswith("SUMMARY:"):
            if current_section:
                _save_section(current_section, current_content, locals())
            current_section = "summary"
            current_content = [line_stripped[8:].strip()]
        elif line_upper.startswith("KEY ENTITIES:"):
            if current_section:
                _save_section(current_section, current_content, locals())
            current_section = "key_entities"
            current_content = [line_stripped[13:].strip()]
        elif line_upper.startswith("ACTION ITEMS:"):
            if current_section:
                _save_section(current_section, current_content, locals())
            current_section = "action_items"
            current_content = [line_stripped[13:].strip()]
        elif line_upper.startswith("KEYWORDS:"):
            if current_section:
                _save_section(current_section, current_content, locals())
            current_section = "keywords"
            current_content = [line_stripped[9:].strip()]
        elif current_section:
            current_content.append(line_stripped)
    
    # Process final section
    if current_section and current_content:
        content_text = " ".join(c for c in current_content if c)
        if current_section == "summary":
            summary = content_text
        elif current_section == "key_entities":
            key_entities = content_text
        elif current_section == "action_items":
            action_items = content_text
        elif current_section == "keywords":
            keywords = [k.strip() for k in content_text.split(",") if k.strip()]
    
    # Fallback: if no sections parsed, use raw response
    if not any([summary, key_entities, action_items]):
        summary = response_text[:500] if len(response_text) > 500 else response_text
    
    return PdfAnalysisResult(
        filename=filename,
        summary=summary,
        key_entities=key_entities,
        action_items=action_items,
        keywords=keywords,
        raw_response=response_text,
    )


def _save_section(section: str, content: List[str], local_vars: dict) -> None:
    """Helper to save accumulated section content."""
    content_text = " ".join(c for c in content if c)
    if section == "summary":
        local_vars["summary"] = content_text
    elif section == "key_entities":
        local_vars["key_entities"] = content_text
    elif section == "action_items":
        local_vars["action_items"] = content_text


def analyze_document(
    client: genai.Client,
    doc: PdfDocument,
    config: AppConfig
) -> PdfAnalysisResult:
    """
    Analyze a single document using Gemini.
    
    Args:
        client: Initialized Gemini client
        doc: PDF document to analyze
        config: Application configuration
        
    Returns:
        Analysis result for the document
    """
    logger.debug(f"Analyzing: {doc.filename}")
    
    # Handle empty documents
    if not doc.text.strip():
        logger.warning(f"Empty document: {doc.filename}")
        return PdfAnalysisResult(
            filename=doc.filename,
            summary="Document contains no extractable text",
            key_entities="",
            action_items="",
            keywords=[],
            error="Empty document",
        )
    
    # Truncate text if needed
    text = doc.text
    if len(text) > config.max_chars_per_doc:
        text = text[:config.max_chars_per_doc]
        logger.debug(f"Truncated {doc.filename} to {config.max_chars_per_doc} characters")
    
    # Build prompt
    prompt = ANALYSIS_PROMPT.format(document_text=text)
    
    # Call Gemini with retries
    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=config.model_name,
                contents=prompt,
            )
            
            if response.text:
                result = _parse_response(response.text, doc.filename)
                logger.debug(f"Successfully analyzed: {doc.filename}")
                return result
            else:
                raise ValueError("Empty response from Gemini")
                
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {doc.filename}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
    
    # All retries failed
    logger.error(f"Failed to analyze {doc.filename} after {MAX_RETRIES} attempts")
    return PdfAnalysisResult(
        filename=doc.filename,
        summary="",
        key_entities="",
        action_items="",
        keywords=[],
        error=str(last_error) if last_error else "Unknown error",
    )


def analyze_documents(
    client: genai.Client,
    documents: List[PdfDocument],
    config: AppConfig,
    cache: Optional[Dict[str, dict]] = None,
    cache_callback: Optional[Callable[[PdfDocument, PdfAnalysisResult], None]] = None,
    show_progress: bool = True
) -> List[PdfAnalysisResult]:
    """
    Analyze multiple documents with optional caching.
    
    Args:
        client: Initialized Gemini client  
        documents: List of PDF documents to analyze
        config: Application configuration
        cache: Optional cache dictionary for skipping unchanged files
        cache_callback: Optional callback to update cache after each analysis
        show_progress: Whether to show a progress bar
        
    Returns:
        List of analysis results
    """
    from .cache import get_cached_result, cache_result
    
    results = []
    total = len(documents)
    cached_count = 0
    
    # Create progress bar
    iterator = tqdm(
        documents,
        desc="Analyzing PDFs",
        unit="doc",
        disable=not show_progress
    )
    
    for doc in iterator:
        iterator.set_postfix_str(doc.filename[:25])
        
        # Check cache first
        cached_result = None
        if cache is not None:
            cached_result = get_cached_result(cache, doc)
        
        if cached_result is not None:
            results.append(cached_result)
            cached_count += 1
            logger.debug(f"Using cached result for: {doc.filename}")
        else:
            result = analyze_document(client, doc, config)
            results.append(result)
            
            # Update cache
            if cache is not None:
                cache_result(cache, doc, result)
            if cache_callback:
                cache_callback(doc, result)
            
            # Small delay between API calls to avoid rate limiting
            time.sleep(0.5)
    
    successful = sum(1 for r in results if r.is_successful)
    logger.info(f"Completed: {successful}/{total} successful, {cached_count} from cache")
    
    return results
