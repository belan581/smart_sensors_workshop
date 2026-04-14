#!/usr/bin/env python3
"""
Script de verificación de integración paso a paso.

Verifica que todos los componentes del sistema estén disponibles
antes de arrancar el taller. Ejecutar desde la raíz del proyecto:

    python scripts/check_integration.py

Salida: estado de cada componente con instrucciones de corrección.
"""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

# ── Colores para terminal ────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

OK = f"{GREEN}[OK]{RESET}"
FAIL = f"{RED}[FAIL]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"


def check(label: str, result: bool, hint: str = "") -> bool:
    status = OK if result else FAIL
    print(f"  {status}  {label}")
    if not result and hint:
        print(f"        {YELLOW}→ {hint}{RESET}")
    return result


def section(title: str):
    print(f"\n{BOLD}{'─' * 50}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")


# ── Raíces del proyecto ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
ML = ROOT / "ml"
FIRMWARE = ROOT / "firmware"
CONFIG = ROOT / "config"

all_ok = True


# ────────────────────────────────────────────────────────────────────────────
# 1. ESTRUCTURA DE ARCHIVOS
# ────────────────────────────────────────────────────────────────────────────
section("1. Estructura de archivos")

critical_files = [
    (BACKEND / "app" / "main.py", "Backend: app/main.py"),
    (BACKEND / "app" / "config.py", "Backend: app/config.py"),
    (BACKEND / "requirements.txt", "Backend: requirements.txt"),
    (BACKEND / ".env.example", "Backend: .env.example"),
    (ML / "scripts" / "03_train.py", "ML: scripts/03_train.py"),
    (ML / "scripts" / "feature_extractor.py", "ML: feature_extractor.py"),
    (CONFIG / "mosquitto.conf", "Config: mosquitto.conf"),
    (FIRMWARE / "main" / "app_main.c", "Firmware: app_main.c"),
]

for path, label in critical_files:
    ok = check(label, path.exists(), f"Archivo no encontrado: {path}")
    all_ok = all_ok and ok


# ────────────────────────────────────────────────────────────────────────────
# 2. ENTORNO PYTHON
# ────────────────────────────────────────────────────────────────────────────
section("2. Entorno Python")

# Python version
python_ok = sys.version_info >= (3, 11)
check(
    f"Python >= 3.11 (actual: {sys.version.split()[0]})",
    python_ok,
    "Instalar Python 3.11+ desde https://python.org",
)
all_ok = all_ok and python_ok

# Paquetes del backend
packages = {
    "fastapi": "pip install fastapi",
    "uvicorn": "pip install uvicorn[standard]",
    "sqlalchemy": "pip install sqlalchemy",
    "paho.mqtt.client": "pip install paho-mqtt",
    "pydantic_settings": "pip install pydantic-settings",
    "joblib": "pip install joblib",
    "numpy": "pip install numpy",
}

for pkg, install_cmd in packages.items():
    try:
        __import__(pkg.split(".")[0])
        check(f"Paquete: {pkg}", True)
    except ImportError:
        check(f"Paquete: {pkg}", False, install_cmd)
        all_ok = False

# Paquetes ML (opcionales para el backend, requeridos para entrenar)
ml_packages = {"pandas": True, "sklearn": True, "matplotlib": True}
print(f"\n  {YELLOW}Paquetes ML (solo necesarios para entrenar):{RESET}")
for pkg, _ in ml_packages.items():
    try:
        __import__(pkg)
        check(f"  ML: {pkg}", True)
    except ImportError:
        print(
            f"  {WARN}  ML: {pkg} — instalar con: pip install scikit-learn pandas matplotlib"
        )


# ────────────────────────────────────────────────────────────────────────────
# 3. MODELO ML
# ────────────────────────────────────────────────────────────────────────────
section("3. Modelo ML")

model_files = [
    (BACKEND / "models" / "model_rf.pkl", "model_rf.pkl"),
    (BACKEND / "models" / "scaler.pkl", "scaler.pkl"),
    (BACKEND / "models" / "label_encoder.pkl", "label_encoder.pkl"),
]

models_ok = True
for path, label in model_files:
    ok = check(
        label,
        path.exists(),
        "Entrenar y copiar: cd ml && python scripts/03_train.py\n"
        "        luego: copy ml\\outputs\\*.pkl backend\\models\\",
    )
    models_ok = models_ok and ok

if not models_ok:
    print(
        f"\n  {YELLOW}Para entrenar el modelo sin dataset real, usa el simulador:{RESET}"
    )
    print(f"  {YELLOW}  python scripts/simulate/generate_fake_dataset.py{RESET}")

all_ok = all_ok and models_ok


# ────────────────────────────────────────────────────────────────────────────
# 4. BROKER MQTT (Mosquitto)
# ────────────────────────────────────────────────────────────────────────────
section("4. Broker MQTT (Mosquitto)")


# Verificar si el puerto 1883 está escuchando
def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


mqtt_up = port_open("localhost", 1883)
check(
    "Puerto 1883 escuchando (Mosquitto)",
    mqtt_up,
    "Iniciar Mosquitto: mosquitto -c config/mosquitto.conf",
)
all_ok = all_ok and mqtt_up


# ────────────────────────────────────────────────────────────────────────────
# 5. BACKEND FASTAPI
# ────────────────────────────────────────────────────────────────────────────
section("5. Backend FastAPI")

backend_up = port_open("localhost", 8000)
check(
    "Puerto 8000 escuchando (FastAPI)",
    backend_up,
    "Iniciar backend: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000",
)

if backend_up:
    # Verificar endpoint /health
    try:
        import urllib.request

        with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as r:
            data = json.loads(r.read())
            check("GET /health → responde", True)
            check(
                "  mqtt_connected",
                data.get("mqtt_connected", False),
                "Verificar que Mosquitto esté corriendo",
            )
            check(
                "  model_loaded",
                data.get("model_loaded", False),
                "Verificar que los .pkl existan en backend/models/",
            )
            check("  database_ok", data.get("database_ok", False))
    except Exception as e:
        check("GET /health → responde", False, str(e))


# ────────────────────────────────────────────────────────────────────────────
# 6. CONFIGURACIÓN
# ────────────────────────────────────────────────────────────────────────────
section("6. Configuración")

env_file = BACKEND / ".env"
check(
    ".env existe en backend/",
    env_file.exists(),
    "Copiar: copy backend\\.env.example backend\\.env",
)

if env_file.exists():
    content = env_file.read_text()
    check(".env tiene MQTT_BROKER_HOST", "MQTT_BROKER_HOST" in content)
    check(".env tiene DATABASE_URL", "DATABASE_URL" in content)
    check(".env tiene MODEL_PATH", "MODEL_PATH" in content)


# ────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ────────────────────────────────────────────────────────────────────────────
section("RESUMEN")

if all_ok:
    print(f"\n  {GREEN}{BOLD}✓ Sistema listo para el taller{RESET}")
    print(f"  Documentación Swagger: http://localhost:8000/docs\n")
else:
    print(f"\n  {RED}{BOLD}✗ Hay componentes que requieren atención{RESET}")
    print(f"  Revisa los mensajes [FAIL] arriba y sigue las instrucciones.\n")

sys.exit(0 if all_ok else 1)
