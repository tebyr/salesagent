"""
TenantService — lookup y operaciones sobre tenants.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
import structlog

logger = structlog.get_logger()


class TenantService:
    """
    Servicio stateless: crea su propia sesion de DB por operacion.
    Se instancia una vez por mensaje del webhook.
    """

    async def get_tenant_by_phone_number_id(self, phone_number_id: str) -> Tenant | None:
        """
        Busca el tenant que tiene configurado ese phone_number_id de WhatsApp.
        Es el punto de entrada del webhook para identificar a quien va dirigido el mensaje.
        """
        if not phone_number_id:
            return None

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(
                    Tenant.whatsapp_phone_number_id == phone_number_id,
                    Tenant.is_active == True,
                )
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            logger.warning(
                "tenant_not_found",
                phone_number_id=phone_number_id,
            )
        return tenant

    async def get_tenant_by_id(self, tenant_id: str) -> Tenant | None:
        """Obtiene un tenant por su UUID."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True,
                )
            )
            return result.scalar_one_or_none()

    async def get_all_active_tenants(self) -> list[Tenant]:
        """Retorna todos los tenants activos. Usado por el scheduler."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.is_active == True)
            )
            return list(result.scalars().all())

    async def get_management_emails(self, tenant_id: str) -> list[str]:
        """Retorna los emails de gerencia configurados para un tenant."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return []
        email_config = tenant.email_config or {}
        return email_config.get("management_emails", [])
