"""
Fixtures compartidas para toda la suite de tests.

Estrategia:
  - Los tests son unitarios: no requieren PostgreSQL ni Redis en ejecucion.
  - Las variables de entorno requeridas por Settings se inyectan via os.environ
    antes de que el modulo app.core.config sea importado.
  - Los servicios que acceden a BD reciben una sesion AsyncMock inyectada.
  - Los tests de API usan httpx.AsyncClient con ASGITransport (sin servidor real).

Orden de importacion deliberado:
  1. Parchear os.environ ANTES de cualquier import de app.*
  2. Importar app.* solo dentro de fixtures (lazy) o despues del patch
"""
import os
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Variables de entorno minimas para que Settings() no falle ──────────────
# Se aplican ANTES de cualquier import de modulos de la app.
_TEST_ENV = {
    "APP_SECRET_KEY": "test-secret-key-32chars-xxxxxxxxxxx",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    "ENCRYPTION_KEY": "dGVzdC1rZXktMzItY2hhcnMtZm9yLXRlc3Rpbmc=",  # base64 valido
    "ANTHROPIC_API_KEY": "sk-ant-test-000",
    "VOYAGE_API_KEY": "pa-test-000",
    "WHATSAPP_WEBHOOK_VERIFY_TOKEN": "test-verify-token",
    "WHATSAPP_APP_SECRET": "test-app-secret",
    "JWT_SECRET_KEY": "test-jwt-secret-key-32chars-xxxxx",
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "redis://localhost:6379/1",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/2",
}

for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)


# ── IDs fijos reutilizables en toda la suite ───────────────────────────────
TENANT_ID  = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
USER_ID    = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
CLIENT_ID  = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
PRODUCT_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000004")
ZONE_ID    = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


# ── Fabricas de objetos de dominio (sin BD) ────────────────────────────────

@pytest.fixture()
def make_tenant():
    """Retorna una funcion factory para Tenant mock."""
    def _factory(**kwargs):
        from app.models.tenant import Tenant
        defaults = dict(
            id=TENANT_ID,
            name="Distribuciones La Garantia",
            slug="distribuciones-la-garantia",
            agent_name="AgenteGarantia",
            primary_color="#1D4ED8",
            whatsapp_phone_number_id="123456789",
            whatsapp_access_token="gAAAAAB_test_encrypted_token",
            whatsapp_app_secret="test-secret",
            is_active=True,
            schedule_config={"timezone": "America/Bogota"},
            email_config={"management_emails": ["admin@test.co"]},
        )
        defaults.update(kwargs)
        obj = MagicMock(spec=Tenant)
        for k, v in defaults.items():
            setattr(obj, k, v)
        return obj
    return _factory


@pytest.fixture()
def make_user():
    """Retorna una funcion factory para User mock."""
    def _factory(**kwargs):
        from app.models.user import User, UserRole
        defaults = dict(
            id=USER_ID,
            tenant_id=TENANT_ID,
            name="Carlos Mendez",
            phone="+573001111111",
            phone_normalized="573001111111",
            role=UserRole.SALESPERSON,
            is_active=True,
            whatsapp_opt_in=True,
        )
        defaults.update(kwargs)
        obj = MagicMock(spec=User)
        for k, v in defaults.items():
            setattr(obj, k, v)
        return obj
    return _factory


@pytest.fixture()
def make_client():
    """Retorna una funcion factory para Client mock."""
    def _factory(**kwargs):
        from app.models.client import Client
        defaults = dict(
            id=CLIENT_ID,
            tenant_id=TENANT_ID,
            salesperson_id=USER_ID,
            business_name="Tienda El Progreso",
            phone="+573011000101",
            phone_normalized="573011000101",
            is_active=True,
            whatsapp_opt_in=True,
            avg_purchase_frequency_days=14,
            last_purchase_date=date.today(),
            segment="A",
            channel_type="tradicional",
        )
        defaults.update(kwargs)
        obj = MagicMock(spec=Client)
        for k, v in defaults.items():
            setattr(obj, k, v)
        return obj
    return _factory


@pytest.fixture()
def make_product():
    """Retorna una funcion factory para Product mock."""
    def _factory(**kwargs):
        from app.models.product import Product
        defaults = dict(
            id=PRODUCT_ID,
            tenant_id=TENANT_ID,
            sku="GRA-001",
            name="Arroz Diana x 5Kg",
            brand="Diana",
            category="granos",
            subcategory="arroz",
            unit="Bulto",
            unit_content="10 bolsas",
            price=220_000.0,
            price_promo=None,
            is_active=True,
            is_featured=False,
            rotation_flag=None,
            description=None,
            semantic_tags=None,
            embedding=None,
        )
        defaults.update(kwargs)
        obj = MagicMock(spec=Product)
        for k, v in defaults.items():
            setattr(obj, k, v)
        return obj
    return _factory


@pytest.fixture()
def mock_db():
    """
    Sesion de BD simulada (AsyncMock).
    Configura los metodos mas comunes usados en los servicios.
    """
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture()
def async_session_ctx(mock_db):
    """
    Context manager asincrono que simula AsyncSessionLocal().
    Usar con: patch("app.core.database.AsyncSessionLocal", async_session_ctx)
    """
    class _Ctx:
        async def __aenter__(self):
            return mock_db
        async def __aexit__(self, *args):
            pass
    return _Ctx


@pytest.fixture()
def fernet_key() -> str:
    """Llave Fernet valida generada para tests."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()
