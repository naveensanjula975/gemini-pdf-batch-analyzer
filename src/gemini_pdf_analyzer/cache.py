"""
Caching module for Gemini PDF Analyzer.

Provides file-based caching to avoid re-analyzing unchanged PDF files.
"""

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import PdfAnalysisResult, PdfDocument

logger = logging.getLogger(__name__)

CACHE_FILENAME = ".analysis_cache.json"


def _compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of a file for change detection."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _get_cache_path(cache_dir: Path) -> Path:
    """Get the path to the cache file."""
    return cache_dir / CACHE_FILENAME


def load_cache(cache_dir: Path) -> Dict[str, dict]:
    """
    Load the analysis cache from disk.
    
    Args:
        cache_dir: Directory containing the cache file
        
    Returns:
        Dictionary mapping filenames to cached data
    """
    cache_path = _get_cache_path(cache_dir)
    
    if not cache_path.exists():
        logger.debug("No cache file found, starting fresh")
        return {}
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        logger.info(f"Loaded {len(cache)} cached results from {cache_path}")
        return cache
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return {}


def save_cache(cache_dir: Path, cache: Dict[str, dict]) -> None:
    """
    Save the analysis cache to disk.
    
    Args:
        cache_dir: Directory to save the cache file
        cache: Cache dictionary to save
    """
    cache_path = _get_cache_path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(cache)} results to cache")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def get_cached_result(
    cache: Dict[str, dict],
    doc: PdfDocument
) -> Optional[PdfAnalysisResult]:
    """
    Get a cached result if the file hasn't changed.
    
    Args:
        cache: Cache dictionary
        doc: PDF document to check
        
    Returns:
        Cached PdfAnalysisResult if valid, None if not cached or changed
    """
    if doc.filename not in cache:
        return None
    
    cached = cache[doc.filename]
    
    # Verify file hasn't changed by comparing hash
    try:
        current_hash = _compute_file_hash(doc.path)
        if cached.get("file_hash") != current_hash:
            logger.debug(f"Cache miss (file changed): {doc.filename}")
            return None
    except Exception:
        return None
    
    # Reconstruct the result
    try:
        result = PdfAnalysisResult(
            filename=cached["filename"],
            summary=cached["summary"],
            key_entities=cached["key_entities"],
            action_items=cached["action_items"],
            keywords=cached.get("keywords", []),
            raw_response=cached.get("raw_response", ""),
            error=cached.get("error"),
        )
        logger.debug(f"Cache hit: {doc.filename}")
        return result
    except Exception as e:
        logger.debug(f"Failed to restore cached result for {doc.filename}: {e}")
        return None


def cache_result(
    cache: Dict[str, dict],
    doc: PdfDocument,
    result: PdfAnalysisResult
) -> None:
    """
    Add or update a result in the cache.
    
    Args:
        cache: Cache dictionary to update
        doc: PDF document that was analyzed
        result: Analysis result to cache
    """
    try:
        file_hash = _compute_file_hash(doc.path)
        cache[doc.filename] = {
            "filename": result.filename,
            "summary": result.summary,
            "key_entities": result.key_entities,
            "action_items": result.action_items,
            "keywords": result.keywords,
            "raw_response": result.raw_response,
            "error": result.error,
            "file_hash": file_hash,
            "cached_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Failed to cache result for {doc.filename}: {e}")


def clear_cache(cache_dir: Path) -> bool:
    """
    Clear the analysis cache.
    
    Args:
        cache_dir: Directory containing the cache file
        
    Returns:
        True if cache was cleared, False if no cache existed
    """
    cache_path = _get_cache_path(cache_dir)
    
    if cache_path.exists():
        cache_path.unlink()
        logger.info("Cache cleared")
        return True
    return False
