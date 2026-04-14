#!/usr/bin/env python3
"""
Simulador de ESP32 para el taller.

Publica ventanas de datos IMU sintéticos al broker MQTT,
emulando exactamente el payload que envía el firmware real.
Permite probar el backend y el pipeline ML sin hardware físico.

Uso:
    python scripts/simulate_esp32.py                  # modo por defecto
    python scripts/simulate_esp32.py --motion vibracion
    python scripts/simulate_esp32.py --motion libre --rate 2.0 --count 20
    python scripts/simulate_esp32.py --list-motions

Modos disponibles (reproducen perfiles distintos de aceleración x/y/z):
    reposo      Dispositivo quieto en una superficie plana
    vibracion   Vibración de motor/maquinaria (alta frecuencia)
    golpe       Impacto brusco seguido de reposo
    rotacion    Rotación lenta y continua
    libre       Lanzamiento/caída libre
    random      Señal completamente aleatoria (ruido)
"""

import argparse
import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable

# ── Dependencia paho-mqtt ───────────────────────────────────────────────────
try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[ERROR] Falta paho-mqtt. Instalar con:  pip install paho-mqtt")
    raise SystemExit(1)

# ── Constantes ───────────────────────────────────────────────────────────────
WINDOW_SIZE = 50  # muestras por ventana (idéntico al firmware)
SAMPLE_HZ = 100  # frecuencia de muestreo (Hz)
GRAVITY = 9.81  # m/s²

DEFAULT_BROKER = "localhost"
DEFAULT_PORT = 1883
DEFAULT_DEVICE = "esp32s3_001"
DEFAULT_TOPIC = "sensors/{device_id}/raw"


# ── Generadores de señal ─────────────────────────────────────────────────────
def _noise(std: float = 0.02) -> float:
    return random.gauss(0, std)


def gen_reposo() -> tuple[list, list, list]:
    """Acelerómetro en reposo sobre eje Z con ruido mínimo."""
    ax = [_noise(0.015) for _ in range(WINDOW_SIZE)]
    ay = [_noise(0.015) for _ in range(WINDOW_SIZE)]
    az = [GRAVITY + _noise(0.015) for _ in range(WINDOW_SIZE)]
    return ax, ay, az


def gen_vibracion(freq: float = 25.0, amp: float = 0.8) -> tuple[list, list, list]:
    """Vibración sinusoidal de alta frecuencia (motor, maquinaria)."""
    t = [i / SAMPLE_HZ for i in range(WINDOW_SIZE)]
    ax = [amp * math.sin(2 * math.pi * freq * ti) + _noise(0.05) for ti in t]
    ay = [amp * math.cos(2 * math.pi * freq * ti) + _noise(0.05) for ti in t]
    az = [GRAVITY + _noise(0.05) for _ in t]
    return ax, ay, az


def gen_golpe(peak: float = 15.0) -> tuple[list, list, list]:
    """Impacto brusco en muestra 10, resto en reposo."""
    ax, ay, az = gen_reposo()
    ax[10] = peak + _noise(0.5)
    ay[10] = peak / 3 + _noise(0.5)
    az[10] = GRAVITY + peak / 2 + _noise(0.5)
    return ax, ay, az


def gen_rotacion(omega: float = 1.5) -> tuple[list, list, list]:
    """Rotación lenta: componente gravitacional que se proyecta en ejes."""
    t = [i / SAMPLE_HZ for i in range(WINDOW_SIZE)]
    ax = [GRAVITY * math.sin(omega * ti) + _noise(0.03) for ti in t]
    ay = [GRAVITY * math.cos(omega * ti) + _noise(0.03) for ti in t]
    az = [_noise(0.03) for _ in t]
    return ax, ay, az


def gen_libre() -> tuple[list, list, list]:
    """Caída libre: acelerómetro reporta ~0 en todos los ejes."""
    ax = [_noise(0.05) for _ in range(WINDOW_SIZE)]
    ay = [_noise(0.05) for _ in range(WINDOW_SIZE)]
    az = [_noise(0.05) for _ in range(WINDOW_SIZE)]
    return ax, ay, az


def gen_random() -> tuple[list, list, list]:
    """Ruido completamente aleatorio."""
    ax = [random.uniform(-20, 20) for _ in range(WINDOW_SIZE)]
    ay = [random.uniform(-20, 20) for _ in range(WINDOW_SIZE)]
    az = [random.uniform(-5, 25) for _ in range(WINDOW_SIZE)]
    return ax, ay, az


MOTION_GENERATORS: dict[str, Callable] = {
    "reposo": gen_reposo,
    "vibracion": gen_vibracion,
    "golpe": gen_golpe,
    "rotacion": gen_rotacion,
    "libre": gen_libre,
    "random": gen_random,
}


# ── Publicador MQTT ──────────────────────────────────────────────────────────
def _round(values: list, decimals: int = 4) -> list:
    return [round(v, decimals) for v in values]


def publish_window(
    client: mqtt.Client,
    device_id: str,
    motion: str,
    window_num: int,
) -> None:
    """Construye y publica una ventana de datos."""
    gen = MOTION_GENERATORS[motion]
    ax, ay, az = gen()

    payload = {
        "device_id": device_id,
        "timestamp": int(time.time()),
        "window_num": window_num,
        "motion_type": motion,  # campo extra para debugging (backend lo ignora)
        "ax": _round(ax),
        "ay": _round(ay),
        "az": _round(az),
        "temperature": round(25.0 + random.uniform(-1.5, 1.5), 2),
        "battery": 100,
    }

    topic = DEFAULT_TOPIC.format(device_id=device_id)
    result = client.publish(topic, json.dumps(payload), qos=1)
    result.wait_for_publish(timeout=5.0)

    print(
        f"  [{window_num:04d}] motion={motion:<10s} "
        f"ax_mean={sum(ax)/len(ax):+.3f}  "
        f"topic={topic}"
    )


def run_simulator(
    broker: str,
    port: int,
    device_id: str,
    motion: str,
    rate: float,
    count: int | None,
) -> None:
    # ── Configurar cliente MQTT ──────────────────────────────────────────────
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"simulator_{device_id}",
    )

    connected = False

    def on_connect(c, userdata, flags, rc, props):
        nonlocal connected
        if rc == 0:
            connected = True
            print(f"[MQTT] Conectado al broker {broker}:{port}")
        else:
            print(f"[MQTT] Error de conexión: código {rc}")

    def on_disconnect(c, userdata, flags, rc, props):
        nonlocal connected
        connected = False
        print(f"[MQTT] Desconectado (rc={rc})")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # ── Publicar mensaje LWT ─────────────────────────────────────────────────
    status_topic = f"sensors/{device_id}/status"
    client.will_set(
        status_topic,
        json.dumps({"status": "offline", "source": "simulator"}),
        qos=1,
        retain=True,
    )

    try:
        client.connect(broker, port, keepalive=60)
    except ConnectionRefusedError:
        print(f"[ERROR] No se pudo conectar a {broker}:{port}")
        print(f"        ¿Está corriendo Mosquitto? Ejecuta:")
        print(f"        mosquitto -c config/mosquitto.conf")
        raise SystemExit(1)

    client.loop_start()

    # Esperar conexión
    deadline = time.time() + 5
    while not connected and time.time() < deadline:
        time.sleep(0.1)

    if not connected:
        print("[ERROR] Timeout esperando conexión MQTT")
        client.loop_stop()
        raise SystemExit(1)

    # ── Publicar estado online ───────────────────────────────────────────────
    client.publish(
        status_topic,
        json.dumps({"status": "online", "source": "simulator", "motion": motion}),
        qos=1,
        retain=True,
    )

    interval = 1.0 / rate
    print(f"\n[SIM] device_id={device_id}  motion={motion}  rate={rate:.1f} win/s")
    print(f"[SIM] Publicando en 'sensors/{device_id}/raw'  (Ctrl+C para detener)\n")

    window_num = 0
    try:
        while True:
            t0 = time.monotonic()
            current_motion = (
                motion if motion != "auto" else random.choice(list(MOTION_GENERATORS))
            )
            publish_window(client, device_id, current_motion, window_num)
            window_num += 1

            if count is not None and window_num >= count:
                print(f"\n[SIM] Enviadas {count} ventanas. Fin.")
                break

            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n[SIM] Interrumpido. Ventanas enviadas: {window_num}")

    finally:
        client.publish(
            status_topic,
            json.dumps({"status": "offline", "source": "simulator"}),
            qos=1,
            retain=True,
        )
        time.sleep(0.3)
        client.loop_stop()
        client.disconnect()


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Simulador de ESP32 para el taller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--broker", default=DEFAULT_BROKER, help="Host broker MQTT")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Puerto MQTT")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="device_id a usar")
    parser.add_argument(
        "--motion",
        default="reposo",
        choices=list(MOTION_GENERATORS) + ["auto"],
        help="Perfil de movimiento ('auto' alterna aleatoriamente)",
    )
    parser.add_argument(
        "--rate", default=1.0, type=float, help="Ventanas por segundo (default: 1.0)"
    )
    parser.add_argument(
        "--count",
        default=None,
        type=int,
        help="Número de ventanas a enviar (default: infinito)",
    )
    parser.add_argument(
        "--list-motions",
        action="store_true",
        help="Listar perfiles de movimiento disponibles y salir",
    )

    args = parser.parse_args()

    if args.list_motions:
        descriptions = {
            "reposo": "Dispositivo quieto, ruido mínimo",
            "vibracion": "Vibración sinusoidal alta frecuencia (motor)",
            "golpe": "Impacto brusco único en la muestra 10",
            "rotacion": "Rotación lenta continua",
            "libre": "Caída libre — acelerómetro ~0 en todos los ejes",
            "random": "Señal completamente aleatoria",
            "auto": "Alterna aleatoriamente entre todos los perfiles",
        }
        print("\nPerfiles de movimiento disponibles:\n")
        for name, desc in descriptions.items():
            print(f"  {name:<12s}  {desc}")
        print()
        return

    run_simulator(
        broker=args.broker,
        port=args.port,
        device_id=args.device,
        motion=args.motion,
        rate=args.rate,
        count=args.count,
    )


if __name__ == "__main__":
    main()
