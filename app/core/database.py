"""
Configuracion de base de datos con SQLAlchemy async.
Soporte multi-tenant via tenant_id en todas las tablas.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.core.config import settings
import structlog

logger = structlog.get_logger()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.app_debug,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


def get_sync_session_for_task():
    """
    Context manager de sesion async para uso fuera del ciclo de FastAPI.
    Usado exclusivamente por tareas Celery que llaman codigo async via asyncio.run().

    Uso:
        async with get_sync_session_for_task() as db:
            await some_service(db)
    """
    return AsyncSessionLocal()
