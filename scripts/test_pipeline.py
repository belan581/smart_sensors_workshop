#!/usr/bin/env python3
"""
Script de prueba end-to-end del pipeline: Backend → MQTT → ML → API.

Lee los endpoints del backend y verifica que respondan correctamente.
Puede ejecutarse con o sin el simulador activo.

Uso:
    python scripts/test_pipeline.py               # solo prueba de API
    python scripts/test_pipeline.py --send-mqtt   # también publica 3 ventanas y verifica

Requiere:
    - Backend corriendo en localhost:8000
    - Mosquitto corriendo en localhost:1883 (si se usa --send-mqtt)
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Añadir scripts al path para reusar el simulador
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

BASE_URL = "http://localhost:8000"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def get(path: str, timeout: float = 5.0):
    """Realiza GET y devuelve (status_code, dict|None)."""
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, str(e)


def post(path: str, body: dict, timeout: float = 10.0):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, None
    except Exception as e:
        return 0, str(e)


def ok(label, condition, detail=""):
    icon = f"{GREEN}✓{RESET}" if condition else f"{RED}✗{RESET}"
    print(f"  {icon}  {label}")
    if not condition and detail:
        print(f"     {YELLOW}→ {detail}{RESET}")
    return condition


def section(title):
    print(f"\n{BOLD}── {title} {'─' * (45 - len(title))}{RESET}")


passed = 0
failed = 0


def test(label, condition, detail=""):
    global passed, failed
    result = ok(label, condition, detail)
    if result:
        passed += 1
    else:
        failed += 1
    return result


# ────────────────────────────────────────────────────────────────────────────
def run_tests(send_mqtt: bool):
    global passed, failed

    # ── Health ───────────────────────────────────────────────────────────────
    section("GET /health")
    code, data = get("/health")
    test("Código HTTP 200", code == 200, f"código={code}")
    if data and isinstance(data, dict):
        test("database_ok = true", data.get("database_ok"), "BD no inicializada")
        test(
            "model_loaded = true", data.get("model_loaded"), "Modelo .pkl no encontrado"
        )
        if not data.get("mqtt_connected"):
            print(
                f"  {YELLOW}!  mqtt_connected = false — ¿Está Mosquitto corriendo?{RESET}"
            )

    # ── Sensores ─────────────────────────────────────────────────────────────
    section("GET /sensors")
    code, data = get("/sensors")
    test("Código HTTP 200", code == 200, f"código={code}")
    test("Responde lista", isinstance(data, list), "Se esperaba una lista JSON")

    # ── POST /predict (HTTP directo — sin MQTT) ──────────────────────────────
    section("POST /predict (inferencia directa sin MQTT)")

    import math, random

    t = [i / 100 for i in range(50)]
    fake_window = {
        "device_id": "test_pipeline",
        "ax": [
            0.8 * math.sin(2 * math.pi * 25 * ti) + random.gauss(0, 0.02) for ti in t
        ],
        "ay": [
            0.8 * math.cos(2 * math.pi * 25 * ti) + random.gauss(0, 0.02) for ti in t
        ],
        "az": [9.81 + random.gauss(0, 0.02) for _ in t],
    }

    code, data = post("/predict", fake_window)
    test("Código HTTP 200", code == 200, f"código={code}  resp={data}")
    if data and isinstance(data, dict):
        test("Campo 'label'", "label" in data)
        test("Campo 'confidence'", "confidence" in data)
        test(
            "Campo 'probabilities'",
            "probabilities" in data or "all_probabilities" in data,
        )
        if "label" in data:
            print(
                f"     {YELLOW}→ Predicción: {data['label']}  "
                f"(confianza: {data.get('confidence', '?'):.2%}){RESET}"
            )

    # ── Predicciones históricas ──────────────────────────────────────────────
    section("GET /predictions/latest")
    code, data = get("/predictions/latest")
    test("Código HTTP 200", code == 200, f"código={code}")

    # ── Estadísticas ────────────────────────────────────────────────────────
    section("GET /stats")
    code, data = get("/stats")
    test("Código HTTP 200", code == 200, f"código={code}")
    if data and isinstance(data, dict):
        test("Campo 'total_measurements'", "total_measurements" in data)

    # ── Cola MQTT + verificación asíncrona ───────────────────────────────────
    if send_mqtt:
        section("Flujo MQTT completo (simulate → broker → backend → DB)")
        try:
            from simulate_esp32 import run_simulator
        except ImportError:
            test(
                "Import simulate_esp32",
                False,
                "Asegúrate de ejecutar desde la raíz del proyecto",
            )
            return

        import threading

        thread = threading.Thread(
            target=run_simulator,
            kwargs=dict(
                broker="localhost",
                port=1883,
                device_id="test_mqtt_flow",
                motion="vibracion",
                rate=2.0,
                count=3,
            ),
            daemon=True,
        )
        print("  Publicando 3 ventanas vía MQTT...")
        thread.start()
        thread.join(timeout=10)

        # Esperar un momento para que el backend procese
        time.sleep(1.5)

        code, data = get("/sensors")
        found = any(s.get("device_id") == "test_mqtt_flow" for s in (data or []))
        test(
            "Sensor 'test_mqtt_flow' registrado en BD",
            found,
            "El backend puede no haber recibido el mensaje MQTT",
        )

        code, data = get("/predictions/latest")
        has_pred = data and len(data) > 0
        test(
            "Predicciones generadas vía MQTT",
            bool(has_pred),
            "Verifica que el modelo esté cargado y el backend suscrito al topic",
        )

    # ── Resumen ───────────────────────────────────────────────────────────────
    total = passed + failed
    section(f"RESUMEN  ─  {passed}/{total} pruebas pasadas")
    if failed == 0:
        print(f"\n  {GREEN}{BOLD}✓ Pipeline verificado correctamente{RESET}\n")
    else:
        print(f"\n  {RED}{BOLD}✗ {failed} prueba(s) fallaron{RESET}\n")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Prueba end-to-end del pipeline")
    parser.add_argument(
        "--send-mqtt",
        action="store_true",
        help="Publica 3 ventanas reales vía MQTT y verifica",
    )
    parser.add_argument(
        "--base-url", default=BASE_URL, help=f"URL del backend (default: {BASE_URL})"
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url.rstrip("/")

    print(f"\n{BOLD}Taller IoT — Test de pipeline{RESET}")
    print(f"Backend: {BASE_URL}")

    ok_all = run_tests(send_mqtt=args.send_mqtt)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
