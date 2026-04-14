"""
Configuración central del backend.
Lee variables desde archivo .env (o variables de entorno del sistema).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- MQTT ---
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "sensors"
    mqtt_client_id: str = "backend_worker_01"

    # --- Base de datos ---
    database_url: str = "sqlite:///./data/workshop.db"

    # --- Modelo ML ---
    model_path: str = "./models/model_rf.pkl"
    scaler_path: str = "./models/scaler.pkl"
    label_encoder_path: str = "./models/label_encoder.pkl"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True

    # --- Ventana de datos (debe coincidir con el firmware) ---
    window_size: int = 50
    sample_rate_hz: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instancia global — importar desde aquí en todos los módulos
settings = Settings()
