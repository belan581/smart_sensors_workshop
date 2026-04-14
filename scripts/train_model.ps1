# ============================================================
#  train_model.ps1  —  Entrena el modelo ML completo
#
#  Opcionalmente genera dataset sintético si no hay datos reales.
#
#  Uso:
#      .\scripts\train_model.ps1
#      .\scripts\train_model.ps1 -Synthetic         # genera datos y entrena
#      .\scripts\train_model.ps1 -Synthetic -Copy   # entrena y copia al backend
# ============================================================

param(
    [switch]$Synthetic,      # usar dataset sintético en lugar de real
    [switch]$Copy,           # copiar modelos al backend después de entrenar
    [int]   $SamplesPerClass = 200
)

$Root  = Split-Path $PSScriptRoot -Parent
$MlDir = Join-Path $Root "ml"

Write-Host ""
Write-Host "=== Entrenamiento del modelo ML ===" -ForegroundColor Cyan
Write-Host ""

Push-Location $Root

# ── Generar dataset sintético si se solicitó ────────────────────────────────
if ($Synthetic) {
    Write-Host "Generando dataset sintético ($SamplesPerClass muestras/clase) ..."
    python scripts\generate_fake_dataset.py --samples-per-class $SamplesPerClass
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Falló la generación del dataset" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host ""
}

# ── Verificar que hay dataset ────────────────────────────────────────────────
$dataDir = Join-Path $MlDir "data\raw"
$csvFiles = Get-ChildItem -Path $dataDir -Filter "*.csv" -ErrorAction SilentlyContinue

if ($csvFiles.Count -eq 0) {
    Write-Host "[ERROR] No hay datos CSV en ml/data/raw/" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Opciones:" -ForegroundColor Yellow
    Write-Host "  1. Generar datos sintéticos: .\scripts\train_model.ps1 -Synthetic" -ForegroundColor Yellow
    Write-Host "  2. Colocar tu CSV en:        ml\data\raw\dataset.csv" -ForegroundColor Yellow
    Pop-Location
    exit 1
}

# ── Ejecutar pipeline ML ─────────────────────────────────────────────────────
$mlScripts = @(
    @{ Script = "ml\scripts\01_prepare_data.py";  Name = "1/3 Preparar datos"     },
    @{ Script = "ml\scripts\02_extract_features.py"; Name = "2/3 Extraer features" },
    @{ Script = "ml\scripts\03_train.py";          Name = "3/3 Entrenar modelo"   },
)

foreach ($step in $mlScripts) {
    Write-Host "[$($step.Name)] ..." -ForegroundColor White
    python $step.Script
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Falló: $($step.Script)" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "  [OK]" -ForegroundColor Green
    Write-Host ""
}

# ── Copiar al backend si se solicitó ─────────────────────────────────────────
if ($Copy) {
    Write-Host "Copiando modelos al backend ..."
    & ".\scripts\copy_models.ps1"
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        exit 1
    }
}

Pop-Location

Write-Host "=== Entrenamiento completado ===" -ForegroundColor Cyan
Write-Host ""
if (-not $Copy) {
    Write-Host "Para copiar al backend:" -ForegroundColor Yellow
    Write-Host "  .\scripts\copy_models.ps1" -ForegroundColor Yellow
    Write-Host ""
}
