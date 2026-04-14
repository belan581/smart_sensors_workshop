# ============================================================
#  start_broker.ps1  —  Inicia el broker Mosquitto
#
#  Uso:
#      .\scripts\start_broker.ps1
#
#  Requisito: mosquitto.exe en el PATH
#    Descarga: https://mosquitto.org/download/
#    Instalación típica: C:\Program Files\mosquitto\
# ============================================================

param(
    [string]$ConfigFile = "config\mosquitto.conf"
)

$Root   = Split-Path $PSScriptRoot -Parent
$Config = Join-Path $Root $ConfigFile

Write-Host ""
Write-Host "=== Iniciando broker Mosquitto ===" -ForegroundColor Cyan
Write-Host "  Config: $Config"
Write-Host ""

# Verificar que mosquitto está disponible; si no, intentar con la ruta por defecto
$MosquittoExe = "mosquitto"
if (-not (Get-Command mosquitto -ErrorAction SilentlyContinue)) {
    $DefaultPath = "C:\Program Files\mosquitto\mosquitto.exe"
    if (Test-Path $DefaultPath) {
        $MosquittoExe = $DefaultPath
        Write-Host "  (mosquitto no está en el PATH, usando $DefaultPath)" -ForegroundColor Yellow
    } else {
        Write-Host "[ERROR] 'mosquitto' no está en el PATH." -ForegroundColor Red
        Write-Host ""
        Write-Host "  Opciones:" -ForegroundColor Yellow
        Write-Host "  1. Descargar desde: https://mosquitto.org/download/" -ForegroundColor Yellow
        Write-Host "  2. Agregar al PATH: C:\Program Files\mosquitto\" -ForegroundColor Yellow
        Write-Host "     (Panel de control → Sistema → Variables de entorno)" -ForegroundColor Yellow
        exit 1
    }
}

# Verificar que el archivo de config existe
if (-not (Test-Path $Config)) {
    Write-Host "[ERROR] No se encontró: $Config" -ForegroundColor Red
    exit 1
}

Write-Host "Mosquitto versión: $(& $MosquittoExe -h 2>&1 | Select-String 'version' | Select-Object -First 1)"
Write-Host ""
Write-Host "  Puerto: 1883 (MQTT)"
Write-Host "  Acceso anónimo: habilitado (para el taller)"
Write-Host "  Log: consola"
Write-Host ""
Write-Host "  Presiona Ctrl+C para detener el broker."
Write-Host ""

# Iniciar mosquitto en primer plano (para ver logs en la terminal)
& $MosquittoExe -c $Config -v
