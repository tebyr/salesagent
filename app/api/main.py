"""
Aplicacion FastAPI principal.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.webhooks.whatsapp import router as whatsapp_router
from app.api.v1.admin import router as admin_router
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

logger = structlog.get_logger()


def _init_sentry() -> None:
    """
    Inicializa Sentry si SENTRY_DSN esta configurado.
    Se llama a nivel de modulo para que el middleware de Sentry
    quede registrado antes de que FastAPI procese cualquier request.
    En desarrollo/staging, traces_sample_rate=1.0 para ver todo.
    En produccion, se reduce a 0.1 para controlar volumen y costos.
    send_default_pii=False: nunca enviar datos personales (nombres, telefonos) a Sentry.
    """
    if not settings.sentry_dsn:
        return

    traces_sample_rate = 0.1 if settings.is_production else 1.0

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
    )
    logger.info(
        "sentry_initialized",
        env=settings.app_env,
        traces_sample_rate=traces_sample_rate,
    )


_init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializacion y cierre de la aplicacion."""
    logger.info("starting_application", env=settings.app_env)
    await init_db()
    yield
    logger.info("shutting_down_application")


app = FastAPI(
    title="Sales Agent SaaS",
    description="Agente supervisor de equipos comerciales para distribuidoras en Colombia",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(
    whatsapp_router,
    prefix="/api/v1",
    tags=["WhatsApp Webhook"],
)
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}
