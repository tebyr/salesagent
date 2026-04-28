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

    # Proveedores IA (todos opcionales — al menos uno requerido en runtime)
    # Cambiar AI_MODEL_* en .env para cambiar de proveedor sin tocar código
    anthropic_api_key: Optional[str] = None   # console.anthropic.com
    openai_api_key:    Optional[str] = None   # platform.openai.com
    groq_api_key:      Optional[str] = None   # console.groq.com — gratuito para pruebas

    # Voyage AI (embeddings RAG — requerido solo si se usa búsqueda semántica)
    voyage_api_key: Optional[str] = None      # dash.voyageai.com

    # Modelos por nivel de complejidad — cambiar aquí para cambiar de proveedor
    # Anthropic:  claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-6
    # Groq (dev): groq/llama-3.1-8b-instant | groq/llama-3.1-70b-versatile
    # OpenAI:     gpt-4o-mini | gpt-4o
    ai_model_simple:   str = "groq/llama-3.1-8b-instant"
    ai_model_standard: str = "groq/llama-3.1-70b-versatile"
    ai_model_complex:  str = "groq/llama-3.1-70b-versatile"

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
