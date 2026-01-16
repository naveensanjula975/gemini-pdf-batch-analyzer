# Gemini PDF Batch Analyzer - Windows Run Script
# Usage: .\scripts\run_analysis.ps1 [options]

param(
    [string]$InputDir = "data/input_pdfs",
    [string]$OutputDir = "data/output",
    [int]$MaxDocs = 0,
    [switch]$Verbose
)

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Change to project root
Push-Location $ProjectRoot

try {
    # Check if virtual environment exists
    $VenvPath = Join-Path $ProjectRoot ".venv"
    $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    
    if (-not (Test-Path $ActivateScript)) {
        Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
        python -m venv .venv
        
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        & $ActivateScript
        pip install -e ".[dev]"
    } else {
        # Activate virtual environment
        & $ActivateScript
    }
    
    # Check for .env file
    $EnvFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $EnvFile)) {
        Write-Host "WARNING: .env file not found. Copy .env.example to .env and add your API key." -ForegroundColor Red
        Write-Host "  cp .env.example .env" -ForegroundColor Yellow
        exit 1
    }
    
    # Build command arguments
    $Args = @(
        "-m", "gemini_pdf_analyzer",
        "--input-dir", $InputDir,
        "--output-dir", $OutputDir
    )
    
    if ($MaxDocs -gt 0) {
        $Args += "--max-docs"
        $Args += $MaxDocs
    }
    
    if ($Verbose) {
        $Args += "--verbose"
    }
    
    # Run the analyzer
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  Gemini PDF Batch Analyzer" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    Write-Host "Input:  $InputDir" -ForegroundColor White
    Write-Host "Output: $OutputDir" -ForegroundColor White
    Write-Host ""
    
    python @Args
    
} finally {
    Pop-Location
}
