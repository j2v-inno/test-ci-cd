# Stage 8: the local "artifact store" — a Docker registry on localhost:5000.
$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    docker compose -f docker-compose.registry.yml up -d
    Write-Output "Registry running at localhost:5000"
} finally {
    Pop-Location
}
