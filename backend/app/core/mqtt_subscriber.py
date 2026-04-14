"""
Suscriptor MQTT — hilo de fondo que escucha mensajes del broker.

Responsabilidades:
  - Conectar al broker Mosquitto
  - Suscribirse a topics del patrón sensors/+/raw
  - Parsear payloads JSON
  - Delegar procesamiento al DataProcessor
  - Manejar reconexión automática
"""

import json
import logging
import time

import paho.mqtt.client as mqtt

from app.config import settings
from app.services.data_processor import DataProcessor

logger = logging.getLogger(__name__)

# Topic pattern: sensors/+/raw
#   + es un wildcard de un nivel (acepta cualquier device_id)
TOPIC_RAW = f"{settings.mqtt_topic_prefix}/+/raw"


class MQTTSubscriber:
    """Suscriptor MQTT que corre en un hilo separado."""

    def __init__(self, ml_service):
        self._client = mqtt.Client(
            client_id=settings.mqtt_client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._processor = DataProcessor(ml_service=ml_service)
        self._connected = False
        self._running = False

        # Credenciales opcionales
        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        # Registrar callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self):
        """Conecta al broker y entra en el loop de red (bloqueante)."""
        self._running = True
        logger.info(
            f"[MQTT] Conectando a {settings.mqtt_broker_host}:"
            f"{settings.mqtt_broker_port}..."
        )

        while self._running:
            try:
                self._client.connect(
                    settings.mqtt_broker_host,
                    settings.mqtt_broker_port,
                    keepalive=60,
                )
                self._client.loop_forever()
            except ConnectionRefusedError:
                logger.warning(
                    "[MQTT] Conexión rechazada. ¿Está Mosquitto corriendo? "
                    "Reintentando en 5s..."
                )
                time.sleep(5)
            except OSError as e:
                logger.warning(f"[MQTT] Error de red: {e}. Reintentando en 5s...")
                time.sleep(5)

    def stop(self):
        """Detiene el loop MQTT de forma limpia."""
        self._running = False
        self._client.disconnect()
        logger.info("[MQTT] Suscriptor detenido")

    # ── Callbacks MQTT ────────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            client.subscribe(TOPIC_RAW, qos=1)
            logger.info(f"[MQTT] Conectado al broker | Suscrito a: {TOPIC_RAW}")
        else:
            logger.error(f"[MQTT] Error de conexión, código: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        if self._running:
            logger.warning(
                f"[MQTT] Desconectado (código {reason_code}). Reconectando..."
            )

    def _on_message(self, client, userdata, msg):
        """
        Callback invocado por cada mensaje recibido.

        Extrae el device_id del topic y delega al DataProcessor.
        Topic formato: sensors/{device_id}/raw
        """
        try:
            # Extraer device_id desde el topic
            parts = msg.topic.split("/")
            if len(parts) < 3:
                logger.warning(f"[MQTT] Topic inesperado: {msg.topic}")
                return

            device_id = parts[1]

            # Parsear JSON
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.debug(f"[MQTT] Mensaje recibido de {device_id}")

            # Procesar de forma asíncrona (en el mismo hilo para simplificar)
            self._processor.process(device_id=device_id, payload=payload)

        except json.JSONDecodeError as e:
            logger.error(f"[MQTT] JSON inválido en {msg.topic}: {e}")
        except Exception as e:
            logger.error(f"[MQTT] Error procesando mensaje: {e}", exc_info=True)
