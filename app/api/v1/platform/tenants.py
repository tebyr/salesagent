"""
Gestion de tenants desde la plataforma SaaS.
Solo accesible para el admin del tenant especial '__platform__'.
Crear el super-admin con: python scripts/seed_platform.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel, field_validator
from typing import Optional
import uuid
import re

from app.core.database import get_db
from app.core.security import require_platform_admin
from app.core.crypto import encrypt_value
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.order import Order

router = APIRouter(prefix="/tenants", tags=["Platform - Tenants"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TenantCreate(BaseModel):
    name: str
    slug: str
    nit: Optional[str] = None
    plan: str = "starter"
    agent_name: str = "Agente Comercial"
    agent_personality: Optional[str] = None
    primary_color: str = "#2563EB"
    logo_url: Optional[str] = None
    email_footer: Optional[str] = None
    # Config inicial de email gerencial
    management_emails: list[str] = []
    # Config WhatsApp opcional al crear
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_phone_display: Optional[str] = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("El slug solo puede contener letras minúsculas, números, guiones y guiones bajos")
        if v == "__platform__":
            raise ValueError("El slug '__platform__' está reservado para la plataforma")
        return v

    @field_validator("plan")
    @classmethod
    def plan_valid(cls, v: str) -> str:
        allowed = {"starter", "professional", "enterprise"}
        if v not in allowed:
            raise ValueError(f"Plan inválido. Opciones: {allowed}")
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    nit: Optional[str] = None
    plan: Optional[str] = None
    agent_name: Optional[str] = None
    agent_personality: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None
    email_footer: Optional[str] = None
    management_emails: Optional[list[str]] = None
    schedule_config: Optional[dict] = None

    @field_validator("plan")
    @classmethod
    def plan_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"starter", "professional", "enterprise"}:
            raise ValueError("Plan inválido. Opciones: starter, professional, enterprise")
        return v


class WhatsAppReset(BaseModel):
    phone_number_id: str
    business_account_id: str
    access_token: str
    phone_display: str


class TenantKPIs(BaseModel):
    total_users: int
    active_users: int
    total_clients: int
    active_clients: int
    total_products: int
    orders_last_30d: int


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    nit: Optional[str]
    is_active: bool
    plan: str
    agent_name: str
    agent_personality: Optional[str]
    primary_color: str
    logo_url: Optional[str]
    whatsapp_phone_display: Optional[str]
    whatsapp_configured: bool
    schedule_config: dict
    email_config: dict
    created_at: str


class TenantDetailOut(TenantOut):
    kpis: TenantKPIs


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[TenantOut])
async def list_tenants(
    is_active: Optional[bool] = None,
    plan: Optional[str] = None,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los tenants del sistema (excepto __platform__)."""
    filters = [Tenant.slug != "__platform__"]
    if is_active is not None:
        filters.append(Tenant.is_active == is_active)
    if plan:
        filters.append(Tenant.plan == plan)

    result = await db.execute(
        select(Tenant).where(and_(*filters)).order_by(Tenant.name)
    )
    tenants = result.scalars().all()
    return [_tenant_to_out(t) for t in tenants]


@router.post("/", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo tenant en la plataforma."""
    # Verificar slug único
    existing = await db.execute(select(Tenant).where(Tenant.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un tenant con el slug '{data.slug}'",
        )

    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        nit=data.nit,
        plan=data.plan,
        agent_name=data.agent_name,
        agent_personality=data.agent_personality,
        primary_color=data.primary_color,
        logo_url=data.logo_url,
        email_footer=data.email_footer,
        email_config={"management_emails": data.management_emails, "from_name": None},
        is_active=True,
    )

    # Configurar WhatsApp si se proveen credenciales al crear
    if data.whatsapp_access_token and data.whatsapp_phone_number_id:
        tenant.whatsapp_phone_number_id = data.whatsapp_phone_number_id
        tenant.whatsapp_business_account_id = data.whatsapp_business_account_id
        tenant.whatsapp_access_token = encrypt_value(data.whatsapp_access_token)
        tenant.whatsapp_phone_display = data.whatsapp_phone_display

    db.add(tenant)
    await db.flush()
    return _tenant_to_out(tenant)


@router.get("/{tenant_id}", response_model=TenantDetailOut)
async def get_tenant(
    tenant_id: str,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """Detalle de un tenant con KPIs básicos."""
    tenant = await _get_tenant_or_404(tenant_id, db)
    kpis = await _calculate_kpis(tenant.id, db)
    out = _tenant_to_out(tenant)
    return TenantDetailOut(**out.model_dump(), kpis=kpis)


@router.patch("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza datos del tenant: plan, nombre, personalidad del agente, etc."""
    tenant = await _get_tenant_or_404(tenant_id, db)

    update_data = data.model_dump(exclude_none=True)

    # management_emails va dentro de email_config, no como campo directo
    if "management_emails" in update_data:
        current_email_config = tenant.email_config or {}
        current_email_config["management_emails"] = update_data.pop("management_emails")
        tenant.email_config = current_email_config

    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.flush()
    return _tenant_to_out(tenant)


@router.post("/{tenant_id}/suspend", response_model=TenantOut)
async def suspend_tenant(
    tenant_id: str,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspende un tenant: desactiva el tenant y todos sus usuarios.
    El scheduler ignorará tenants con is_active=False.
    """
    tenant = await _get_tenant_or_404(tenant_id, db)

    if not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tenant ya está suspendido")

    tenant.is_active = False

    # Desactivar todos los usuarios del tenant
    users_result = await db.execute(
        select(User).where(and_(User.tenant_id == tenant.id, User.is_active == True))
    )
    for user in users_result.scalars().all():
        user.is_active = False

    await db.flush()
    return _tenant_to_out(tenant)


@router.post("/{tenant_id}/activate", response_model=TenantOut)
async def activate_tenant(
    tenant_id: str,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Reactiva un tenant suspendido.
    Los usuarios se reactivan solo si tenían is_active=True antes de la suspensión.
    Nota: por simplicidad reactiva el admin del tenant para que pueda gestionar sus propios usuarios.
    """
    tenant = await _get_tenant_or_404(tenant_id, db)

    if tenant.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tenant ya está activo")

    tenant.is_active = True

    # Reactivar solo el usuario ADMIN del tenant para que pueda gestionar el resto
    admin_result = await db.execute(
        select(User).where(
            and_(
                User.tenant_id == tenant.id,
                User.role == UserRole.ADMIN,
            )
        )
    )
    admin = admin_result.scalar_one_or_none()
    if admin:
        admin.is_active = True

    await db.flush()
    return _tenant_to_out(tenant)


@router.post("/{tenant_id}/reset-token", response_model=TenantOut)
async def reset_whatsapp_token(
    tenant_id: str,
    data: WhatsAppReset,
    _: dict = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Rota las credenciales de WhatsApp de un tenant.
    El nuevo token se encripta con Fernet antes de guardarse.
    """
    tenant = await _get_tenant_or_404(tenant_id, db)

    tenant.whatsapp_phone_number_id = data.phone_number_id
    tenant.whatsapp_business_account_id = data.business_account_id
    tenant.whatsapp_access_token = encrypt_value(data.access_token)
    tenant.whatsapp_phone_display = data.phone_display

    await db.flush()
    return _tenant_to_out(tenant)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_tenant_or_404(tenant_id: str, db: AsyncSession) -> Tenant:
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ID inválido")

    result = await db.execute(
        select(Tenant).where(and_(Tenant.id == tid, Tenant.slug != "__platform__"))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")
    return tenant


async def _calculate_kpis(tenant_id, db: AsyncSession) -> TenantKPIs:
    from app.models.client import Client
    from app.models.product import Product
    from datetime import datetime, timedelta, timezone

    # Usuarios
    users_q = await db.execute(
        select(
            func.count(User.id).label("total"),
            func.count(User.id).filter(User.is_active == True).label("active"),
        ).where(User.tenant_id == tenant_id)
    )
    users_row = users_q.one()

    # Clientes
    clients_q = await db.execute(
        select(
            func.count(Client.id).label("total"),
            func.count(Client.id).filter(Client.is_active == True).label("active"),
        ).where(Client.tenant_id == tenant_id)
    )
    clients_row = clients_q.one()

    # Productos activos
    products_q = await db.execute(
        select(func.count(Product.id)).where(
            and_(Product.tenant_id == tenant_id, Product.is_active == True)
        )
    )
    total_products = products_q.scalar() or 0

    # Órdenes últimos 30 días
    since = datetime.now(timezone.utc) - timedelta(days=30)
    orders_q = await db.execute(
        select(func.count(Order.id)).where(
            and_(Order.tenant_id == tenant_id, Order.created_at >= since)
        )
    )
    orders_30d = orders_q.scalar() or 0

    return TenantKPIs(
        total_users=users_row.total,
        active_users=users_row.active,
        total_clients=clients_row.total,
        active_clients=clients_row.active,
        total_products=total_products,
        orders_last_30d=orders_30d,
    )


def _tenant_to_out(t: Tenant) -> TenantOut:
    return TenantOut(
        id=str(t.id),
        name=t.name,
        slug=t.slug,
        nit=t.nit,
        is_active=t.is_active,
        plan=t.plan,
        agent_name=t.agent_name,
        agent_personality=t.agent_personality,
        primary_color=t.primary_color,
        logo_url=t.logo_url,
        whatsapp_phone_display=t.whatsapp_phone_display,
        whatsapp_configured=bool(t.whatsapp_phone_number_id and t.whatsapp_access_token),
        schedule_config=t.schedule_config or {},
        email_config=t.email_config or {},
        created_at=t.created_at.isoformat() if t.created_at else "",
    )
