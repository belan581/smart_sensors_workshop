# ============================================================
#  broker.ps1  —  Inicia o detiene el broker Mosquitto TinyML
#
#  Uso:
#      .\scripts\broker.ps1          # iniciar (por defecto)
#      .\scripts\broker.ps1 -Start   # iniciar
#      .\scripts\broker.ps1 -Stop    # detener
#
#  Config utilizada: config\mosquitto_tinyml.conf
#
#  El broker recibe mensajes del ESP32-S3:
#      Topic entrada : sensors/esp32s3_001/drinking
#      Topic reenviado: inference/sensors/esp32s3_001/drinking
#
#  Requisito: mosquitto.exe en el PATH
#    Descarga: https://mosquitto.org/download/
# ============================================================

param(
    [switch]$Start,
    [switch]$Stop,
    [string]$ConfigFile = "config\mosquitto_tinyml.conf"
)

# Por defecto, arrancar si no se pasa ningún flag
if (-not $Start -and -not $Stop) { $Start = $true }

$Root       = Split-Path $PSScriptRoot -Parent
$Config     = Join-Path $Root $ConfigFile
$PidFile    = Join-Path $Root "config\mosquitto_tinyml.pid"

# ── Localizar mosquitto.exe ──────────────────────────────────
function Find-Mosquitto {
    if (Get-Command mosquitto -ErrorAction SilentlyContinue) {
        return "mosquitto"
    }
    $DefaultPath = "C:\Program Files\mosquitto\mosquitto.exe"
    if (Test-Path $DefaultPath) {
        Write-Host "  (mosquitto no está en PATH, usando $DefaultPath)" -ForegroundColor Yellow
        return $DefaultPath
    }
    Write-Host "[ERROR] 'mosquitto' no encontrado." -ForegroundColor Red
    Write-Host "  Descarga: https://mosquitto.org/download/" -ForegroundColor Yellow
    exit 1
}

# ── STOP ─────────────────────────────────────────────────────
if ($Stop) {
    Write-Host ""
    Write-Host "=== Deteniendo broker Mosquitto TinyML ===" -ForegroundColor Cyan

    if (Test-Path $PidFile) {
        $Pid = Get-Content $PidFile -Raw
        try {
            Stop-Process -Id $Pid -Force -ErrorAction Stop
            Remove-Item $PidFile -Force
            Write-Host "  Broker detenido (PID $Pid)." -ForegroundColor Green
        } catch {
            Write-Host "  No se pudo detener PID $Pid (ya terminó?)." -ForegroundColor Yellow
            Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        }
    } else {
        # Fallback: matar todos los procesos mosquitto
        $Procs = Get-Process -Name mosquitto -ErrorAction SilentlyContinue
        if ($Procs) {
            $Procs | Stop-Process -Force
            Write-Host "  $($Procs.Count) proceso(s) mosquitto detenido(s)." -ForegroundColor Green
        } else {
            Write-Host "  No se encontró el broker en ejecución." -ForegroundColor Yellow
        }
    }
    Write-Host ""
    exit 0
}

# ── START ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Broker Mosquitto TinyML ===" -ForegroundColor Cyan
Write-Host "  Config  : $Config"
Write-Host "  Topics  :"
Write-Host "    Entrada  → sensors/esp32s3_001/drinking"
Write-Host "    Reenviado→ inference/sensors/esp32s3_001/drinking"
Write-Host ""

# Verificar config
if (-not (Test-Path $Config)) {
    Write-Host "[ERROR] No se encontró: $Config" -ForegroundColor Red
    exit 1
}

$MosquittoExe = Find-Mosquitto

Write-Host "Mosquitto: $($( & $MosquittoExe --help 2>&1 | Select-String 'mosquitto version' | Select-Object -First 1 ).Line)"
Write-Host ""
Write-Host "  Puerto 1883 abierto. Esperando mensajes del ESP32-S3..."
Write-Host "  Presiona Ctrl+C para detener el broker."
Write-Host ""

# Iniciar en primer plano para ver logs
& $MosquittoExe -c $Config -v
