# ============================================================
#  copy_models.ps1
#  Copia los artefactos ML desde ml/outputs/ → backend/models/
#
#  Uso:
#      .\scripts\copy_models.ps1
#      .\scripts\copy_models.ps1 -MlOutputs "ml\outputs" -BackendModels "backend\models"
# ============================================================

param(
    [string]$MlOutputs     = "ml\outputs",
    [string]$BackendModels = "backend\models"
)

$Root = Split-Path $PSScriptRoot -Parent

$SrcDir = Join-Path $Root $MlOutputs
$DstDir = Join-Path $Root $BackendModels

Write-Host ""
Write-Host "=== Copiar modelos ML al backend ===" -ForegroundColor Cyan
Write-Host "  Origen:  $SrcDir"
Write-Host "  Destino: $DstDir"
Write-Host ""

# Verificar que el directorio de origen existe
if (-not (Test-Path $SrcDir)) {
    Write-Host "[ERROR] No existe el directorio: $SrcDir" -ForegroundColor Red
    Write-Host "        Ejecuta primero el entrenamiento:" -ForegroundColor Yellow
    Write-Host "          cd ml" -ForegroundColor Yellow
    Write-Host "          python scripts/03_train.py" -ForegroundColor Yellow
    exit 1
}

# Verificar qué archivos existen en el origen
$required = @("model_rf.pkl", "scaler.pkl", "label_encoder.pkl")
$optional = @("model_mlp.pkl", "training_report.json")

$missing = @()
foreach ($f in $required) {
    if (-not (Test-Path (Join-Path $SrcDir $f))) {
        $missing += $f
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[ERROR] Faltan archivos requeridos en $SrcDir :" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "          - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "        Ejecuta el entrenamiento:" -ForegroundColor Yellow
    Write-Host "          cd ml && python scripts/03_train.py" -ForegroundColor Yellow
    exit 1
}

# Crear directorio de destino si no existe
if (-not (Test-Path $DstDir)) {
    New-Item -ItemType Directory -Path $DstDir -Force | Out-Null
    Write-Host "[INFO] Directorio creado: $DstDir" -ForegroundColor Green
}

# Copiar archivos requeridos
$copied = 0
foreach ($f in $required) {
    $src = Join-Path $SrcDir $f
    $dst = Join-Path $DstDir $f
    Copy-Item -Path $src -Destination $dst -Force
    $size = (Get-Item $src).Length
    Write-Host "  [OK] $f  ($([Math]::Round($size/1KB, 1)) KB)" -ForegroundColor Green
    $copied++
}

# Copiar archivos opcionales si existen
foreach ($f in $optional) {
    $src = Join-Path $SrcDir $f
    if (Test-Path $src) {
        $dst = Join-Path $DstDir $f
        Copy-Item -Path $src -Destination $dst -Force
        Write-Host "  [OK] $f  (opcional)" -ForegroundColor DarkGreen
        $copied++
    }
}

Write-Host ""
Write-Host "  $copied archivo(s) copiados correctamente." -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximo paso:" -ForegroundColor White
Write-Host "  .\scripts\start_backend.ps1" -ForegroundColor Yellow
Write-Host ""
