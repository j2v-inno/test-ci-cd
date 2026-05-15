# Stops every container the demo brought up.
$ErrorActionPreference = "SilentlyContinue"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    docker compose -f docker-compose.prod.yml down
    docker compose -f docker-compose.staging.yml down
    docker compose -f docker-compose.dev.yml down
    docker compose -f docker-compose.registry.yml down
    Write-Output "All demo containers stopped."
} finally {
    Pop-Location
}
