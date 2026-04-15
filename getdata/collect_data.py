#!/usr/bin/env python3
"""
collect_data.py — Recolector de datos MPU6050 para reconocimiento de gestos.

Uso:
    python collect_data.py --port COM3
    python collect_data.py --port COM3 --output-dir ./dataset

Protocolo con el firmware:
    PC  → ESP32 : "START <gesto>\\n"
    ESP → PC    : "READY <gesto>\\n"
    ESP → PC    : 3000 líneas  "ax,ay,az,gx,gy,gz\\n"
    ESP → PC    : "DONE\\n"

Archivos de salida (un CSV por gesto, se va acumulando):
    drinking.csv  /  driving.csv  /  throwing.csv

Columnas: dataset_id, gesture, ax, ay, az, gx, gy, gz
"""

import argparse
import os
import re
import sys
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("ERROR: pyserial no está instalado.")
    print("  Instálalo con:  pip install pyserial")
    sys.exit(1)

# ── Constantes ──────────────────────────────────────────────────
GESTURES = ["drinking", "driving", "throwing"]
SAMPLES_PER_REC = 3000
DATASETS_PER_GESTURE = 100
BAUD_RATE = 115200
READLINE_TIMEOUT = 5  # segundos por línea mientras espera READY
DATA_TIMEOUT = 60  # segundos máximo para recibir todos los datos

# Control de salida verbosa (activado por --verbose)
VERBOSE = False

# ── Strip de códigos ANSI (logs de ESP-IDF llevan colores) ───────
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(s: str) -> str:
    """Elimina secuencias de escape ANSI de los mensajes del firmware."""
    return _ANSI_RE.sub("", s)


# ── Utilidades de puerto serie ───────────────────────────────────
def detect_port() -> str:
    """Detecta automáticamente el puerto del ESP32."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        return None
    # Preferir puertos con "USB" o "CP210" o "CH340" en la descripción
    for p in ports:
        desc = (p.description or "").upper()
        if any(k in desc for k in ("USB", "CP21", "CH34", "JTAG", "UART")):
            return p.device
    return ports[0].device


def open_serial(port: str, baud: int) -> serial.Serial:
    ser = serial.Serial(port, baud, timeout=3)
    # El circuito DTR del ESP32-S3 puede resetear el chip al abrir el puerto.
    # Esperamos hasta 8 s a que el firmware envíe "FIRMWARE_OK".
    print("  Esperando firmware...", end="", flush=True)
    deadline = time.time() + 8
    firmware_ok = False
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            break
        line = strip_ansi(raw.decode("ascii", errors="replace")).strip()
        if VERBOSE:
            print(f"\n  [BOOT] {repr(line)}", flush=True)
        if line == "FIRMWARE_OK":
            firmware_ok = True
            break
    if firmware_ok:
        print(" OK")
    else:
        print(" (sin FIRMWARE_OK — el firmware puede estar ya corriendo)")
    ser.timeout = READLINE_TIMEOUT
    ser.reset_input_buffer()
    return ser


# ── Dataset helpers ──────────────────────────────────────────────
def count_datasets(filepath: str) -> int:
    """Cuenta cuántos datasets completos hay en el CSV."""
    if not os.path.exists(filepath):
        return 0
    total_data_lines = 0
    with open(filepath, "r") as f:
        for line in f:
            # Saltar encabezado
            if line.startswith("dataset_id"):
                continue
            if line.strip():
                total_data_lines += 1
    return total_data_lines // SAMPLES_PER_REC


def save_dataset(filepath: str, gesture: str, dataset_id: int, samples: list):
    """Agrega un dataset al CSV del gesto correspondiente."""
    write_header = not os.path.exists(filepath)
    with open(filepath, "a", newline="") as f:
        if write_header:
            f.write("dataset_id,gesture,ax,ay,az,gx,gy,gz\n")
        for line in samples:
            f.write(f"{dataset_id},{gesture},{line}\n")


# ── Comunicación con el firmware ─────────────────────────────────
def collect_one(ser: serial.Serial, gesture: str) -> list | None:
    """
    Envía START, espera READY y recibe las muestras.
    Devuelve lista de líneas CSV o None si hay error.
    """
    # Limpiar buffer antes de enviar
    ser.reset_input_buffer()

    # Enviar comando
    cmd = f"START {gesture}\n"
    ser.write(cmd.encode("ascii"))
    ser.flush()

    # Esperar READY (timeout = READLINE_TIMEOUT segundos)
    print(f"  Enviando comando... ", end="", flush=True)
    deadline = time.time() + 10
    ready_received = False
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = strip_ansi(raw.decode("ascii", errors="replace")).strip()
        if VERBOSE:
            print(f"\n  [RX] {repr(line)}", flush=True)
        if line == f"READY {gesture}":
            ready_received = True
            if not VERBOSE:
                print("READY ✓")
            else:
                print(f"  READY ✓ — grabando...")
            break
        if line.startswith("ERROR"):
            print(f"\n  Firmware error: {line}")
            return None

    if not ready_received:
        print("\n  Timeout esperando READY del firmware.")
        print("  DIAGNÓSTICO: usa --verbose para ver qué recibe el script.")
        print("  Posibles causas:")
        print("    1. Firmware no flasheado o crasheando (MPU6050 desconectado?)")
        print("    2. Puerto incorrecto — verifica que COM7 sea el puerto de datos")
        print("    3. Firmware compilado con console en USB-JTAG pero COM7 es UART0")
        return None

    # Recibir muestras
    samples = []
    ser.timeout = 2  # Timeout por línea durante recepción de datos
    print(
        f"  Grabando 3 s y recibiendo {SAMPLES_PER_REC} muestras...", end="", flush=True
    )

    deadline = time.time() + DATA_TIMEOUT
    done_received = False

    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = strip_ansi(raw.decode("ascii", errors="replace")).strip()
        if line == "DONE":
            done_received = True
            break
        if line:
            samples.append(line)

    ser.timeout = READLINE_TIMEOUT  # Restaurar timeout original

    if not done_received:
        print(f"\n  Timeout esperando DONE (recibidas {len(samples)} muestras).")
        return None

    if len(samples) != SAMPLES_PER_REC:
        print(
            f"\n  ADVERTENCIA: esperadas {SAMPLES_PER_REC}, recibidas {len(samples)}."
        )
        return None

    print(f" {len(samples)} OK")
    return samples


# ── Interfaz de usuario ──────────────────────────────────────────
def show_progress(output_dir: str):
    print("\n  Progreso actual:")
    for g in GESTURES:
        filepath = os.path.join(output_dir, f"{g}.csv")
        count = count_datasets(filepath)
        bar_len = 20
        filled = int(bar_len * count / DATASETS_PER_GESTURE)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"    {g:<10} [{bar}] {count:3d}/{DATASETS_PER_GESTURE}")


def record_gesture(ser: serial.Serial, gesture: str, output_dir: str):
    """Bucle interactivo para grabar un gesto hasta completar 100 datasets."""
    filepath = os.path.join(output_dir, f"{gesture}.csv")
    dataset_id = count_datasets(filepath) + 1

    if dataset_id > DATASETS_PER_GESTURE:
        print(
            f"  '{gesture}' ya está completo ({DATASETS_PER_GESTURE}/{DATASETS_PER_GESTURE})."
        )
        return

    while dataset_id <= DATASETS_PER_GESTURE:
        print(f"\n  Gesto: {gesture}  |  Dataset {dataset_id}/{DATASETS_PER_GESTURE}")
        print(
            "  Prepara el gesto y presiona ENTER para iniciar la grabación (o 'q' para volver)..."
        )
        ans = input("  > ").strip().lower()
        if ans == "q":
            break

        samples = collect_one(ser, gesture)

        if samples is None:
            print("  Error en la recolección. Intentalo de nuevo.")
            continue

        save_dataset(filepath, gesture, dataset_id, samples)
        print(f"  Guardado en: {filepath}  (dataset #{dataset_id})")
        dataset_id += 1

        if dataset_id > DATASETS_PER_GESTURE:
            print(
                f"\n  ¡Gesto '{gesture}' completado! ({DATASETS_PER_GESTURE} datasets)"
            )
            break

        ans2 = (
            input("  ¿Continuar grabando este gesto? (ENTER = sí, 'q' = volver): ")
            .strip()
            .lower()
        )
        if ans2 == "q":
            break


# ── Main ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Recolector de datos MPU6050 (ESP32-S3)"
    )
    parser.add_argument("--port", help="Puerto serial (ej: COM3, /dev/ttyUSB0)")
    parser.add_argument(
        "--baud", type=int, default=BAUD_RATE, help=f"Baud rate (default: {BAUD_RATE})"
    )
    parser.add_argument(
        "--output-dir",
        default="dataset",
        help="Directorio de salida (default: ./dataset)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Mostrar todas las líneas recibidas del firmware (diagnóstico)",
    )
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    # ── Detectar puerto ──
    if not args.port:
        args.port = detect_port()
        if not args.port:
            # Listar puertos disponibles para que el usuario elija
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                print("No se encontraron puertos seriales.")
                print("Conecta el ESP32 y vuelve a intentarlo.")
                sys.exit(1)
            print("Puertos disponibles:")
            for i, p in enumerate(ports):
                print(f"  {i + 1}. {p.device}  —  {p.description}")
            try:
                idx = int(input("Selecciona número de puerto: ")) - 1
                args.port = ports[idx].device
            except (ValueError, IndexError):
                print("Selección inválida.")
                sys.exit(1)
        else:
            print(f"Puerto detectado automáticamente: {args.port}")

    # ── Conectar ──
    try:
        print(f"Conectando a {args.port} @ {args.baud} baud...")
        ser = open_serial(args.port, args.baud)
        print("Conexión establecida.\n")
    except serial.SerialException as e:
        print(f"Error al abrir puerto {args.port}: {e}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # ── Menú principal ──
    print("=" * 50)
    print("  GetData — Captura de gestos MPU6050")
    print("=" * 50)
    print(f"  Muestras por dataset : {SAMPLES_PER_REC} @ 1 KHz (3 s)")
    print(f"  Datasets por gesto   : {DATASETS_PER_GESTURE}")
    print(f"  Directorio de salida : {os.path.abspath(args.output_dir)}")
    show_progress(args.output_dir)

    while True:
        print("\n" + "-" * 40)
        print("  MENÚ PRINCIPAL")
        print("-" * 40)
        for i, g in enumerate(GESTURES):
            filepath = os.path.join(args.output_dir, f"{g}.csv")
            count = count_datasets(filepath)
            status = (
                "✓ COMPLETO"
                if count >= DATASETS_PER_GESTURE
                else f"{count}/{DATASETS_PER_GESTURE}"
            )
            print(f"  {i + 1}. Grabar '{g}'  [{status}]")
        print(f"  {len(GESTURES) + 1}. Ver progreso")
        print(f"  {len(GESTURES) + 2}. Salir")

        choice = input("\n  Opción: ").strip()

        try:
            idx = int(choice) - 1
        except ValueError:
            print("  Opción inválida.")
            continue

        if idx < len(GESTURES):
            record_gesture(ser, GESTURES[idx], args.output_dir)
        elif idx == len(GESTURES):
            show_progress(args.output_dir)
        elif idx == len(GESTURES) + 1:
            break
        else:
            print("  Opción inválida.")

    ser.close()
    print("\nDesconectado. ¡Hasta luego!")


if __name__ == "__main__":
    main()
