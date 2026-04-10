"""
Configuracion central del sistema.
Carga variables de entorno y define constantes globales.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import pytz


class Settings(BaseSettings):
    # App
    app_name: str = "Sales Agent SaaS"
    app_env: str = "development"
    app_secret_key: str
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Encripcion simetrica (Fernet) para valores sensibles en BD
    # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str

    # Anthropic
    anthropic_api_key: str

    # Voyage AI (embeddings RAG)
    voyage_api_key: str
    ai_model_simple: str = "claude-haiku-4-5"
    ai_model_standard: str = "claude-sonnet-4-6"
    ai_model_complex: str = "claude-opus-4-6"

    # WhatsApp
    whatsapp_webhook_verify_token: str
    whatsapp_app_secret: str

    # Email
    sendgrid_api_key: Optional[str] = None   # Opcional en desarrollo
    email_from: str = "noreply@yoursaas.com"
    email_from_name: str = "Sales Agent"

    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_s3_bucket: Optional[str] = None

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # Limites de costos
    ai_cost_alert_threshold_usd: float = 50.0
    ai_cost_hard_limit_usd: float = 100.0
    whatsapp_daily_message_limit: int = 1000

    # Sentry
    sentry_dsn: Optional[str] = None

    # Configuracion general
    default_timezone: str = "America/Bogota"
    default_language: str = "es"
    business_hours_start: int = 6   # 6:00 AM
    business_hours_end: int = 21    # 9:00 PM

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def tz(self) -> pytz.BaseTzInfo:
        return pytz.timezone(self.default_timezone)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
