"""
CRUD de zonas geograficas en el panel admin.

Una zona agrupa clientes geograficamente y puede tener multiples rutas
activas (presencial + agente IA), lo que permite alta frecuencia de visita.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel, field_validator
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.route import Zone, Route
from app.models.client import Client

router = APIRouter(prefix="/zonas", tags=["Admin - Zonas"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ZonaCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre de la zona no puede estar vacio")
        return v.strip()


class ZonaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre de la zona no puede estar vacio")
        return v.strip() if v else v


class ZonaOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    routes_count: int
    clients_count: int


class ZonaDetail(ZonaOut):
    """Detalle de zona con conteos de rutas y clientes."""
    pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _zona_to_out(z: Zone, routes_count: int = 0, clients_count: int = 0) -> ZonaOut:
    return ZonaOut(
        id=str(z.id),
        name=z.name,
        description=z.description,
        is_active=z.is_active,
        routes_count=routes_count,
        clients_count=clients_count,
    )


async def _get_zona_or_404(zona_id: str, tenant_id: str, db: AsyncSession) -> Zone:
    result = await db.execute(
        select(Zone).where(
            and_(Zone.id == zona_id, Zone.tenant_id == tenant_id)
        )
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    return zone


async def _get_counts(zona_id: uuid.UUID, tenant_id: str, db: AsyncSession) -> tuple[int, int]:
    """Retorna (routes_count, clients_count) para una zona."""
    routes_result = await db.execute(
        select(func.count()).where(
            and_(Route.zone_id == zona_id, Route.tenant_id == tenant_id)
        )
    )
    clients_result = await db.execute(
        select(func.count()).where(
            and_(Client.zone_id == zona_id, Client.tenant_id == tenant_id)
        )
    )
    return (
        routes_result.scalar() or 0,
        clients_result.scalar() or 0,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ZonaOut])
async def list_zonas(
    is_active: Optional[bool] = None,
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas las zonas del tenant con sus conteos de rutas y clientes."""
    tenant_id = current_user["tenant_id"]
    filters = [Zone.tenant_id == tenant_id]

    if is_active is not None:
        filters.append(Zone.is_active == is_active)
    if search:
        filters.append(Zone.name.ilike(f"%{search}%"))

    result = await db.execute(
        select(Zone).where(and_(*filters)).order_by(Zone.name)
    )
    zones = result.scalars().all()

    out = []
    for z in zones:
        routes_count, clients_count = await _get_counts(z.id, tenant_id, db)
        out.append(_zona_to_out(z, routes_count, clients_count))
    return out


@router.post("/", response_model=ZonaOut, status_code=status.HTTP_201_CREATED)
async def create_zona(
    data: ZonaCreate,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva zona. El nombre debe ser unico dentro del tenant."""
    tenant_id = current_user["tenant_id"]

    existing = await db.execute(
        select(Zone).where(
            and_(
                Zone.tenant_id == tenant_id,
                Zone.name.ilike(data.name),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una zona con el nombre '{data.name}' en este tenant",
        )

    zone = Zone(
        tenant_id=uuid.UUID(tenant_id),
        name=data.name,
        description=data.description,
    )
    db.add(zone)
    await db.flush()
    return _zona_to_out(zone)


@router.get("/{zona_id}", response_model=ZonaDetail)
async def get_zona(
    zona_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna el detalle de una zona con conteo de rutas y clientes asignados."""
    tenant_id = current_user["tenant_id"]
    zone = await _get_zona_or_404(zona_id, tenant_id, db)
    routes_count, clients_count = await _get_counts(zone.id, tenant_id, db)
    return _zona_to_out(zone, routes_count, clients_count)


@router.patch("/{zona_id}", response_model=ZonaOut)
async def update_zona(
    zona_id: str,
    data: ZonaUpdate,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza nombre, descripcion o estado activo de una zona."""
    tenant_id = current_user["tenant_id"]
    zone = await _get_zona_or_404(zona_id, tenant_id, db)

    if data.name and data.name.strip().lower() != zone.name.lower():
        duplicate = await db.execute(
            select(Zone).where(
                and_(
                    Zone.tenant_id == tenant_id,
                    Zone.name.ilike(data.name),
                    Zone.id != zone.id,
                )
            )
        )
        if duplicate.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe otra zona con el nombre '{data.name}'",
            )

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(zone, field, value)
    await db.flush()

    routes_count, clients_count = await _get_counts(zone.id, tenant_id, db)
    return _zona_to_out(zone, routes_count, clients_count)


@router.delete("/{zona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zona(
    zona_id: str,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactiva una zona (soft delete). No elimina el registro ni sus rutas.
    Las rutas activas de esta zona siguen funcionando hasta que se desactiven
    individualmente.
    """
    tenant_id = current_user["tenant_id"]
    zone = await _get_zona_or_404(zona_id, tenant_id, db)
    zone.is_active = False
    await db.flush()
