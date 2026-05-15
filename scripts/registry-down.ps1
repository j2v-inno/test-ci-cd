$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    docker compose -f docker-compose.registry.yml down
} finally {
    Pop-Location
}
