"""
Fixtures compartidas para tests de integración.

Estrategia:
  - Se conectan a PostgreSQL real (contenedor Docker de test).
  - Cada test corre dentro de una transacción que se revierte al final
    → aislamiento sin truncar tablas manualmente.
  - Las dependencias externas (Claude API, WhatsApp, Voyage AI, SendGrid)
    se mockean en cada módulo de test.

Variables de entorno requeridas (o se usan los defaults de test):
  TEST_DATABASE_URL  → postgresql+asyncpg://postgres:postgres@localhost:5433/salesagent_test
                       (puerto 5433 para no colisionar con la BD de dev en 5432)

Levantar la BD de test:
  docker-compose up -d postgres   # usa el mismo contenedor si el puerto es el mismo
  # o bien un contenedor dedicado:
  # docker run -d --name pg_test -e POSTGRES_PASSWORD=postgres -p 5433:5432 pgvector/pgvector:pg16
"""
import os
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ── Inyectar variables de entorno ANTES de importar la app ─────────────────
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/salesagent_test",
)

_TEST_ENV = {
    "APP_SECRET_KEY": "test-secret-key-32chars-xxxxxxxxxxx",
    "DATABASE_URL": TEST_DATABASE_URL,
    "ENCRYPTION_KEY": "dGVzdC1rZXktMzItY2hhcnMtZm9yLXRlc3Rpbmc=",
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

# ── Imports de la app (después del patch de env) ────────────────────────────
from app.core.database import Base  # noqa: E402
from app.models import (  # noqa: E402  — importar todos para que Base.metadata los conozca
    tenant, user, client, product, route, order, goal, analytics, conversation, notification
)
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.goal import SalesGoal, GoalPeriodType  # noqa: E402
from app.models.order import Order, OrderStatus, OrderSource  # noqa: E402
from app.models.analytics import ClientProductAffinity  # noqa: E402


# ── Motor de BD de test (scope=session → se crea una vez) ───────────────────

@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    return engine


@pytest_asyncio.fixture(scope="session")
async def setup_database(test_engine):
    """Crea todas las tablas al inicio de la sesión de tests y las elimina al final."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session(test_engine, setup_database) -> AsyncSession:
    """
    Sesión con transacción anidada (SAVEPOINT).
    Cada test recibe su propia sesión limpia; al terminar se hace rollback
    sin afectar otros tests ni la BD.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        async with session_factory() as session:
            await session.begin_nested()   # SAVEPOINT
            yield session
            await session.rollback()       # rollback al SAVEPOINT → test aislado
        await conn.rollback()              # rollback de la transacción externa


# ── Fabricas de registros reales en BD ─────────────────────────────────────

@pytest_asyncio.fixture()
async def tenant_db(db_session) -> Tenant:
    """Inserta un Tenant real en la BD de test."""
    t = Tenant(
        id=uuid.uuid4(),
        name="Distribuciones La Garantía",
        slug=f"garantia-{uuid.uuid4().hex[:8]}",
        agent_name="AgenteTest",
        primary_color="#1D4ED8",
        whatsapp_phone_number_id="123456789",
        whatsapp_access_token="token-plain-test",
        is_active=True,
        schedule_config={"timezone": "America/Bogota"},
        email_config={"management_emails": ["gerente@test.co"]},
        plan="starter",
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture()
async def salesperson_db(db_session, tenant_db) -> User:
    """Inserta un vendedor real ligado al tenant."""
    from app.core.security import hash_password
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        name="Carlos Mendez",
        email=f"carlos_{uuid.uuid4().hex[:6]}@test.co",
        phone="+573001111111",
        phone_normalized="573001111111",
        role=UserRole.SALESPERSON,
        password_hash=hash_password("test1234"),
        is_active=True,
        whatsapp_opt_in=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture()
async def manager_db(db_session, tenant_db) -> User:
    """Inserta un gerente real ligado al tenant."""
    from app.core.security import hash_password
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        name="Ana Gerente",
        email=f"ana_{uuid.uuid4().hex[:6]}@test.co",
        phone="+573009999999",
        phone_normalized="573009999999",
        role=UserRole.MANAGER,
        password_hash=hash_password("test1234"),
        is_active=True,
        whatsapp_opt_in=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture()
async def client_db(db_session, tenant_db, salesperson_db) -> Client:
    """Inserta un cliente (tendero) real ligado al tenant y al vendedor."""
    c = Client(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        salesperson_id=salesperson_db.id,
        business_name="Tienda El Progreso",
        owner_name="Pedro Gómez",
        phone="+573011000101",
        phone_normalized="573011000101",
        is_active=True,
        whatsapp_opt_in=True,
        segment="A",
        channel_type="tradicional",
        avg_purchase_frequency_days=14,
        last_purchase_date=date.today() - timedelta(days=10),
    )
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture()
async def product_db(db_session, tenant_db) -> Product:
    """Inserta un producto real ligado al tenant."""
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        sku=f"GRA-{uuid.uuid4().hex[:6]}",
        name="Arroz Diana x 5Kg",
        brand="Diana",
        category="granos",
        subcategory="arroz",
        unit="Bulto",
        price=220_000.0,
        is_active=True,
        is_featured=False,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture()
async def goal_db(db_session, tenant_db, salesperson_db) -> SalesGoal:
    """Inserta una meta mensual real para el vendedor."""
    today = date.today()
    period_start = today.replace(day=1)
    next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    period_end = next_month - timedelta(days=1)

    g = SalesGoal(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        salesperson_id=salesperson_db.id,
        period_type=GoalPeriodType.MONTHLY,
        period_start=period_start,
        period_end=period_end,
        target_amount=10_000_000.0,
        target_visits=80,
        is_active=True,
    )
    db_session.add(g)
    await db_session.flush()
    return g


@pytest_asyncio.fixture()
async def order_db(db_session, tenant_db, client_db, salesperson_db, product_db) -> Order:
    """Inserta una orden confirmada real para usar en cálculos de analytics."""
    from app.models.order import OrderItem
    o = Order(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        client_id=client_db.id,
        salesperson_id=salesperson_db.id,
        order_date=date.today(),
        status=OrderStatus.CONFIRMED,
        source=OrderSource.SALESPERSON,
        subtotal=440_000.0,
        total_amount=440_000.0,
    )
    db_session.add(o)
    await db_session.flush()

    item = OrderItem(
        id=uuid.uuid4(),
        order_id=o.id,
        product_id=product_db.id,
        quantity=2,
        unit_price=220_000.0,
        subtotal=440_000.0,
    )
    db_session.add(item)
    await db_session.flush()
    return o


@pytest_asyncio.fixture()
async def affinity_db(db_session, tenant_db, client_db, product_db) -> ClientProductAffinity:
    """Inserta una afinidad cliente-producto real."""
    a = ClientProductAffinity(
        id=uuid.uuid4(),
        tenant_id=tenant_db.id,
        client_id=client_db.id,
        product_id=product_db.id,
        affinity_score=0.85,
        purchase_frequency=0.7,
        recency_score=0.9,
        amount_score=0.8,
        total_purchases=5,
        last_purchase_date=date.today() - timedelta(days=10),
    )
    db_session.add(a)
    await db_session.flush()
    return a


# ── Helper: parchear AsyncSessionLocal para que use la sesión de test ───────

@pytest.fixture()
def patch_db(db_session, monkeypatch):
    """
    Reemplaza AsyncSessionLocal en todos los servicios/agentes con un
    context manager que devuelve la sesión de test (ya dentro de SAVEPOINT).
    Úsalo como fixture en tests que llaman servicios que abren su propia sesión.
    """
    class _FakeCtx:
        async def __aenter__(self_inner):
            return db_session
        async def __aexit__(self_inner, *args):
            pass  # NO cerrar ni hacer commit: el test controla la transacción

    def _fake_session_local():
        return _FakeCtx()

    monkeypatch.setattr("app.core.database.AsyncSessionLocal", _fake_session_local)
    monkeypatch.setattr("app.services.conversation_service.AsyncSessionLocal", _fake_session_local)
    monkeypatch.setattr("app.services.analytics_service.AsyncSessionLocal", _fake_session_local)
    monkeypatch.setattr("app.services.order_service.AsyncSessionLocal", _fake_session_local)
    return db_session


# ── Config de tenant para instanciar agentes ────────────────────────────────

@pytest.fixture()
def tenant_config(tenant_db) -> dict:
    return {
        "name": tenant_db.name,
        "agent_name": tenant_db.agent_name,
        "primary_color": tenant_db.primary_color,
        "management_emails": ["gerente@test.co"],
    }
