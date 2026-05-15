# End-to-end local CI/CD demo driver.
# Runs each GitHub Actions workflow via `act`, in the order the diagram shows.
#
# Prereqs:
#   - Docker Desktop running
#   - `act` installed (https://github.com/nektos/act)
#   - Local registry up:  .\scripts\registry-up.ps1
#
# Usage:
#   .\scripts\run-pipeline.ps1                 # full pipeline up to QA gate
#   .\scripts\run-pipeline.ps1 -Stage pr       # just PR validation
#   .\scripts\run-pipeline.ps1 -Stage staging  # promote to staging
#   .\scripts\run-pipeline.ps1 -Stage prod     # release to prod
[CmdletBinding()]
param(
    [ValidateSet("all", "pr", "build", "dev", "qa", "staging", "prod")]
    [string]$Stage = "all",
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Act {
    param([string]$Event, [string]$WorkflowFile, [string[]]$ExtraArgs = @())
    Write-Host ""
    Write-Host "===== act $Event ($WorkflowFile) =====" -ForegroundColor Cyan
    & act $Event -W $WorkflowFile @ExtraArgs
    if ($LASTEXITCODE -ne 0) { throw "act failed for $WorkflowFile" }
}

try {
    if ($Stage -in @("all", "pr")) {
        Invoke-Act -Event "pull_request" -WorkflowFile ".github/workflows/pr-validation.yml"
    }

    if ($Stage -in @("all", "build")) {
        Invoke-Act -Event "push" -WorkflowFile ".github/workflows/main-build.yml"
    }

    if ($Stage -in @("all", "dev")) {
        Invoke-Act -Event "workflow_dispatch" -WorkflowFile ".github/workflows/deploy-dev.yml" `
            -ExtraArgs @("--input", "image_tag=$ImageTag")
    }

    if ($Stage -in @("all", "qa")) {
        Invoke-Act -Event "workflow_dispatch" -WorkflowFile ".github/workflows/qa-tests.yml"
    }

    if ($Stage -eq "staging") {
        Invoke-Act -Event "workflow_dispatch" -WorkflowFile ".github/workflows/deploy-staging.yml" `
            -ExtraArgs @("--input", "image_tag=$ImageTag")
    }

    if ($Stage -eq "prod") {
        Invoke-Act -Event "workflow_dispatch" -WorkflowFile ".github/workflows/deploy-prod.yml" `
            -ExtraArgs @("--input", "image_tag=$ImageTag", "--input", "release_notes=local demo")
    }

    Write-Host ""
    Write-Host "Pipeline stage '$Stage' completed successfully." -ForegroundColor Green
} finally {
    Pop-Location
}
