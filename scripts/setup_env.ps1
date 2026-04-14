# ============================================================
#  setup_env.ps1  —  Crea el entorno virtual e instala paquetes
#
#  Ejecutar UNA SOLA VEZ antes del taller (o después de clonar).
#  Crea un entorno virtual en backend/.venv e instala todo.
#
#  Uso:
#      .\scripts\setup_env.ps1
#      .\scripts\setup_env.ps1 -IncludeML    # también instala dependencias ML
# ============================================================

param(
    [switch]$IncludeML   # instalar también paquetes de entrenamiento
)

$Root       = Split-Path $PSScriptRoot -Parent
$BackendDir = Join-Path $Root "backend"
$VenvDir    = Join-Path $BackendDir ".venv"
$ReqFile    = Join-Path $BackendDir "requirements.txt"
$MlReqFile  = Join-Path $Root "ml\requirements-ml.txt"

Write-Host ""
Write-Host "=== Setup del entorno Python ===" -ForegroundColor Cyan
Write-Host "  Python: $(python --version 2>&1)"
Write-Host ""

# Verificar Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python no encontrado. Instalar desde https://python.org" -ForegroundColor Red
    exit 1
}

$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVer -lt [version]"3.11") {
    Write-Host "[ERROR] Se requiere Python >= 3.11 (actual: $pyVer)" -ForegroundColor Red
    exit 1
}

# Crear entorno virtual si no existe
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creando entorno virtual en backend/.venv ..." -ForegroundColor White
    python -m venv $VenvDir
    Write-Host "  [OK] Entorno creado" -ForegroundColor Green
} else {
    Write-Host "  [OK] Entorno virtual ya existe ($VenvDir)" -ForegroundColor DarkGreen
}

# Activar entorno
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
. $ActivateScript
Write-Host "  [OK] Entorno activado" -ForegroundColor Green

# Actualizar pip
Write-Host ""
Write-Host "Actualizando pip ..."
python -m pip install --upgrade pip --quiet
Write-Host "  [OK] pip actualizado" -ForegroundColor Green

# Instalar dependencias del backend
Write-Host ""
Write-Host "Instalando dependencias del backend (requirements.txt) ..."
pip install -r $ReqFile
Write-Host "  [OK] Backend instalado" -ForegroundColor Green

# Instalar dependencias ML si se solicitó
if ($IncludeML) {
    Write-Host ""
    Write-Host "Instalando dependencias ML (requirements-ml.txt) ..."
    if (Test-Path $MlReqFile) {
        pip install -r $MlReqFile
        Write-Host "  [OK] ML instalado" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] No se encontró: $MlReqFile" -ForegroundColor Yellow
    }
}

# Crear .env si no existe
$EnvFile    = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Host ""
        Write-Host "  [OK] Creado backend/.env desde .env.example" -ForegroundColor Green
        Write-Host "       Editar si necesitas cambiar configuración de red." -ForegroundColor Yellow
    }
}

# Crear directorio de modelos
$ModelsDir = Join-Path $BackendDir "models"
if (-not (Test-Path $ModelsDir)) {
    New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null
    Write-Host "  [OK] Creado backend/models/" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup completado ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor White
Write-Host "  1. Entrenar modelo:    cd ml && python scripts/03_train.py" -ForegroundColor Yellow
Write-Host "  2. Copiar modelos:     .\scripts\copy_models.ps1" -ForegroundColor Yellow
Write-Host "  3. Iniciar broker:     .\scripts\start_broker.ps1      (terminal 1)" -ForegroundColor Yellow
Write-Host "  4. Iniciar backend:    .\scripts\start_backend.ps1     (terminal 2)" -ForegroundColor Yellow
Write-Host "  5. Verificar sistema:  python scripts\check_integration.py" -ForegroundColor Yellow
Write-Host "  6. Simular ESP32:      python scripts\simulate_esp32.py --motion vibracion" -ForegroundColor Yellow
Write-Host ""
