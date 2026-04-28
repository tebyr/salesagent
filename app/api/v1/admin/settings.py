"""
Configuracion del tenant: WhatsApp, branding, horarios, emails gerenciales.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.tenant import Tenant
import uuid

router = APIRouter(prefix="/settings", tags=["Admin - Configuracion"])


class SecurityConfig(BaseModel):
    session_timeout_minutes: int = 30
    session_warning_minutes: int = 2


class TenantSettingsOut(BaseModel):
    id: str
    name: str
    slug: str
    agent_name: str
    agent_personality: Optional[str]
    primary_color: str
    logo_url: Optional[str]
    whatsapp_phone_display: Optional[str]
    whatsapp_configured: bool
    whatsapp_config: dict          # campos no sensibles: phone_number_id, business_account_id, phone_display
    schedule_config: dict
    email_config: dict
    security_config: dict
    plan: str


class TenantSettingsUpdate(BaseModel):
    agent_name: Optional[str] = None
    agent_personality: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None
    email_footer: Optional[str] = None
    schedule_config: Optional[dict] = None
    email_config: Optional[dict] = None


class WhatsAppConfig(BaseModel):
    phone_number_id: str
    business_account_id: str
    access_token: Optional[str] = None   # si viene vacío, se conserva el token existente
    phone_display: str


class ScheduleConfig(BaseModel):
    morning_briefing: str = "06:30"
    pre_visit_start: str = "08:00"
    pre_visit_end: str = "17:00"
    daily_summary: str = "18:30"
    performance_report: str = "20:00"
    management_report_day: str = "monday"
    management_report_time: str = "07:00"
    timezone: str = "America/Bogota"
    working_days: list[str] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


@router.get("/", response_model=TenantSettingsOut)
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(current_user["tenant_id"], db)
    return _tenant_to_out(tenant)


@router.patch("/", response_model=TenantSettingsOut)
async def update_settings(
    data: TenantSettingsUpdate,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(current_user["tenant_id"], db)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)
    await db.flush()
    return _tenant_to_out(tenant)


@router.put("/whatsapp", response_model=TenantSettingsOut)
async def configure_whatsapp(
    data: WhatsAppConfig,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Configura las credenciales de WhatsApp Business para el tenant."""
    tenant = await _get_tenant(current_user["tenant_id"], db)
    tenant.whatsapp_phone_number_id = data.phone_number_id
    tenant.whatsapp_business_account_id = data.business_account_id
    tenant.whatsapp_phone_display = data.phone_display
    # Solo actualizar el token si se envió uno nuevo (no vacío)
    if data.access_token and data.access_token.strip():
        from app.core.crypto import encrypt_value
        tenant.whatsapp_access_token = encrypt_value(data.access_token.strip())
    await db.flush()
    return _tenant_to_out(tenant)


@router.put("/schedule", response_model=TenantSettingsOut)
async def update_schedule(
    data: ScheduleConfig,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza los horarios de las notificaciones automaticas."""
    tenant = await _get_tenant(current_user["tenant_id"], db)
    tenant.schedule_config = data.model_dump()
    await db.flush()
    return _tenant_to_out(tenant)


@router.put("/security", response_model=TenantSettingsOut)
async def update_security_config(
    data: SecurityConfig,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza la configuracion de seguridad del panel. Solo administradores y managers."""
    if data.session_warning_minutes >= data.session_timeout_minutes:
        raise HTTPException(
            status_code=400,
            detail="El tiempo de aviso debe ser menor que el tiempo de cierre de sesion",
        )
    if data.session_timeout_minutes < 5:
        raise HTTPException(status_code=400, detail="El tiempo minimo de inactividad es 5 minutos")
    if data.session_warning_minutes < 1:
        raise HTTPException(status_code=400, detail="El tiempo minimo de aviso es 1 minuto")

    tenant = await _get_tenant(current_user["tenant_id"], db)
    tenant.security_config = data.model_dump()
    await db.flush()
    return _tenant_to_out(tenant)


@router.post("/test-whatsapp")
async def test_whatsapp_connection(
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Verifica que las credenciales de WhatsApp esten correctas."""
    from app.services.whatsapp_service import WhatsAppService
    import httpx

    tenant = await _get_tenant(current_user["tenant_id"], db)
    if not tenant.whatsapp_phone_number_id or not tenant.whatsapp_access_token:
        raise HTTPException(status_code=400, detail="WhatsApp no esta configurado")

    try:
        from app.core.crypto import decrypt_value
        token = decrypt_value(tenant.whatsapp_access_token)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://graph.facebook.com/v20.0/{tenant.whatsapp_phone_number_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return {"status": "ok", "phone_info": r.json()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error de conexion: {str(e)}")


async def _get_tenant(tenant_id: str, db) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


def _tenant_to_out(t: Tenant) -> TenantSettingsOut:
    return TenantSettingsOut(
        id=str(t.id),
        name=t.name,
        slug=t.slug,
        agent_name=t.agent_name,
        agent_personality=t.agent_personality,
        primary_color=t.primary_color,
        logo_url=t.logo_url,
        whatsapp_phone_display=t.whatsapp_phone_display,
        whatsapp_configured=bool(t.whatsapp_phone_number_id and t.whatsapp_access_token),
        # Campos no sensibles de WhatsApp para pre-poblar el formulario. El access_token NO se devuelve.
        whatsapp_config={
            "phone_number_id": t.whatsapp_phone_number_id or "",
            "business_account_id": t.whatsapp_business_account_id or "",
            "phone_display": t.whatsapp_phone_display or "",
        },
        schedule_config=t.schedule_config or {},
        email_config=t.email_config or {},
        security_config=t.security_config or {"session_timeout_minutes": 30, "session_warning_minutes": 2},
        plan=t.plan,
    )
