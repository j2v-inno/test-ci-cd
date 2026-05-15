# Fast local feedback loop — skip CI, just run tests against the live virtualenv.
# Mirrors Stage 2 ("Local Development") in the diagram.
$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path .venv)) {
        python -m venv .venv
    }
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\pip.exe install -r requirements-dev.txt
    & .\.venv\Scripts\python.exe -m ruff check .
    & .\.venv\Scripts\python.exe -m pytest tests/unit -v
} finally {
    Pop-Location
}
