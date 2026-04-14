# ============================================================
#  start_backend.ps1  —  Inicia el servidor FastAPI
#
#  Uso:
#      .\scripts\start_backend.ps1
#      .\scripts\start_backend.ps1 -Port 8080 -Reload
#
#  Requiere:
#      - Python 3.11+ con los paquetes de backend/requirements.txt
#      - backend/.env configurado (copiar de backend/.env.example)
#      - Modelos en backend/models/ (usar copy_models.ps1)
# ============================================================

param(
    [string]$Host   = "0.0.0.0",
    [int]   $Port   = 8000,
    [switch]$Reload                  # útil en desarrollo: recarga al editar
)

$Root       = Split-Path $PSScriptRoot -Parent
$BackendDir = Join-Path $Root "backend"
$EnvFile    = Join-Path $BackendDir ".env"
$ModelsDir  = Join-Path $BackendDir "models"

Write-Host ""
Write-Host "=== Iniciando backend FastAPI ===" -ForegroundColor Cyan
Write-Host "  Directorio: $BackendDir"
Write-Host "  URL:        http://$Host`:$Port"
Write-Host ""

# ── Verificaciones previas ───────────────────────────────────────────────────

# .env
if (-not (Test-Path $EnvFile)) {
    Write-Host "[WARN] No existe backend/.env — copiando desde .env.example" -ForegroundColor Yellow
    $example = Join-Path $BackendDir ".env.example"
    if (Test-Path $example) {
        Copy-Item $example $EnvFile
        Write-Host "       Creado backend/.env. Edítalo si necesitas cambiar configuración." -ForegroundColor Yellow
    } else {
        Write-Host "[ERROR] Tampoco existe backend/.env.example" -ForegroundColor Red
        exit 1
    }
}

# Modelos ML
$requiredModels = @("model_rf.pkl", "scaler.pkl", "label_encoder.pkl")
$missingModels  = @()
foreach ($m in $requiredModels) {
    if (-not (Test-Path (Join-Path $ModelsDir $m))) {
        $missingModels += $m
    }
}
if ($missingModels.Count -gt 0) {
    Write-Host "[WARN] Faltan modelos ML:" -ForegroundColor Yellow
    $missingModels | ForEach-Object { Write-Host "         $_" -ForegroundColor Yellow }
    Write-Host "       El backend arrancará pero /predict no funcionará." -ForegroundColor Yellow
    Write-Host "       Para entrenar: .\scripts\copy_models.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# ── Arrancar uvicorn ─────────────────────────────────────────────────────────
Push-Location $BackendDir

Write-Host "  Swagger UI:  http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "  Health:      http://localhost:$Port/health" -ForegroundColor Green
Write-Host ""

if ($Reload) {
    Write-Host "  Modo desarrollo: recarga automática activada" -ForegroundColor DarkYellow
    Write-Host ""
    python -m uvicorn app.main:app --host $Host --port $Port --reload
} else {
    python -m uvicorn app.main:app --host $Host --port $Port
}

Pop-Location
