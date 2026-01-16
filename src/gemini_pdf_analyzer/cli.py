"""
CLI entrypoint for Gemini PDF Analyzer.

Provides command-line interface for batch PDF analysis.
"""

import argparse
import logging
import sys
from pathlib import Path

from .analyzer import analyze_documents, create_client
from .cache import load_cache, save_cache, clear_cache
from .config import load_config
from .exporter import export_results
from .pdf_loader import load_pdfs


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging for the application."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="gemini-pdf-analyzer",
        description="Batch analysis of PDF documents using Google Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input-dir data/input_pdfs --output-dir data/output
  %(prog)s --max-docs 10 --verbose
  %(prog)s --filter "report*.pdf" --format csv excel
  %(prog)s --no-cache  # Skip caching, re-analyze all files
  %(prog)s --clear-cache  # Clear cached results
        """,
    )
    
    parser.add_argument(
        "--input-dir", "-i",
        type=str,
        help="Directory containing PDF files to analyze (default: from .env or data/input_pdfs)",
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        help="Directory for output files (default: from .env or data/output)",
    )
    
    parser.add_argument(
        "--model-name", "-m",
        type=str,
        help="Gemini model to use (default: gemini-2.0-flash)",
    )
    
    parser.add_argument(
        "--max-docs", "-n",
        type=int,
        help="Maximum number of PDFs to process (default: all)",
    )
    
    parser.add_argument(
        "--filter", "-F",
        type=str,
        dest="filter_pattern",
        help="Filter pattern for PDF filenames (glob/fnmatch syntax, e.g. 'report*.pdf')",
    )
    
    parser.add_argument(
        "--format", "-f",
        nargs="+",
        choices=["csv", "json", "jsonl", "excel"],
        default=["csv", "jsonl"],
        help="Output formats (default: csv jsonl)",
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching, re-analyze all files",
    )
    
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached results and exit",
    )
    
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars",
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress most output (only show warnings/errors)",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.2.0",
    )
    
    return parser


def main() -> int:
    """
    Main CLI entrypoint.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose, args.quiet)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model_name=args.model_name,
            max_docs=args.max_docs,
        )
        
        # Handle clear-cache command
        if args.clear_cache:
            if clear_cache(config.input_dir):
                logger.info("Cache cleared successfully")
            else:
                logger.info("No cache to clear")
            return 0
        
        logger.info(f"Input directory: {config.input_dir}")
        logger.info(f"Output directory: {config.output_dir}")
        logger.info(f"Model: {config.model_name}")
        if args.filter_pattern:
            logger.info(f"Filter pattern: {args.filter_pattern}")
        
        # Load PDFs
        logger.info("Loading PDF documents...")
        show_progress = not args.no_progress and not args.quiet
        documents = load_pdfs(
            config.input_dir,
            config.max_docs,
            filter_pattern=args.filter_pattern,
            show_progress=show_progress
        )
        
        if not documents:
            logger.warning("No PDF documents found in input directory")
            return 0
        
        logger.info(f"Loaded {len(documents)} document(s)")
        
        # Load cache (unless disabled)
        cache = None
        if not args.no_cache:
            cache = load_cache(config.input_dir)
        
        # Create Gemini client
        logger.info("Initializing Gemini client...")
        client = create_client(config.gemini_api_key)
        
        # Analyze documents
        logger.info("Starting analysis...")
        results = analyze_documents(
            client,
            documents,
            config,
            cache=cache,
            show_progress=show_progress
        )
        
        # Save cache
        if cache is not None:
            save_cache(config.input_dir, cache)
        
        # Export results
        logger.info("Exporting results...")
        output_files = export_results(results, config.output_dir, args.format)
        
        # Summary
        successful = sum(1 for r in results if r.is_successful)
        logger.info("=" * 50)
        logger.info("ANALYSIS COMPLETE")
        logger.info(f"  Documents processed: {len(results)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {len(results) - successful}")
        logger.info("Output files:")
        for fmt, path in output_files.items():
            logger.info(f"  {fmt}: {path}")
        logger.info("=" * 50)
        
        return 0
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
