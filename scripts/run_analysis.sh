#!/bin/bash
# Gemini PDF Batch Analyzer - Unix Run Script
# Usage: ./scripts/run_analysis.sh [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default values
INPUT_DIR="data/input_pdfs"
OUTPUT_DIR="data/output"
MAX_DOCS=""
VERBOSE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-dir|-i)
            INPUT_DIR="$2"
            shift 2
            ;;
        --output-dir|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --max-docs|-n)
            MAX_DOCS="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check/create virtual environment
if [ ! -f ".venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
else
    source .venv/bin/activate
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Copy .env.example to .env and add your API key."
    echo "  cp .env.example .env"
    exit 1
fi

# Build command
CMD="python -m gemini_pdf_analyzer --input-dir $INPUT_DIR --output-dir $OUTPUT_DIR"

if [ -n "$MAX_DOCS" ]; then
    CMD="$CMD --max-docs $MAX_DOCS"
fi

if [ -n "$VERBOSE" ]; then
    CMD="$CMD $VERBOSE"
fi

# Run
echo ""
echo "========================================"
echo "  Gemini PDF Batch Analyzer"
echo "========================================"
echo ""
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

eval $CMD
