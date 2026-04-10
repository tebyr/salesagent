"""
CRUD de rutas comerciales en el panel admin.

Una ruta define quien visita que zona, en que dias y con que modalidad
(presencial por vendedor humano o agent_wa por el agente IA).
Una zona puede tener multiples rutas activas simultaneamente.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, field_validator
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.route import Route, Zone, RouteType, RouteStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/rutas", tags=["Admin - Rutas"])

# Dias validos: 1=Lun, 2=Mar, 3=Mie, 4=Jue, 5=Vie, 6=Sab
VALID_DAYS = set(range(1, 7))
VALID_ROLES = {UserRole.SALESPERSON, UserRole.AGENT}


# ── Schemas ───────────────────────────────────────────────────────────────────

class RutaCreate(BaseModel):
    salesperson_id: str
    zone_id: Optional[str] = None
    name: Optional[str] = None
    route_type: str = "presential"
    operating_days: list[int] = []
    delivery_days: Optional[list[int]] = None
    daily_schedule: Optional[dict] = None
    notes: Optional[str] = None

    @field_validator("route_type")
    @classmethod
    def validate_route_type(cls, v: str) -> str:
        valid = {rt.value for rt in RouteType}
        if v not in valid:
            raise ValueError(f"route_type debe ser uno de: {valid}")
        return v

    @field_validator("operating_days")
    @classmethod
    def validate_operating_days(cls, v: list[int]) -> list[int]:
        invalid = [d for d in v if d not in VALID_DAYS]
        if invalid:
            raise ValueError(
                f"operating_days contiene dias invalidos: {invalid}. "
                f"Usar 1=Lun, 2=Mar, 3=Mie, 4=Jue, 5=Vie, 6=Sab"
            )
        return sorted(set(v))

    @field_validator("delivery_days")
    @classmethod
    def validate_delivery_days(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return v
        invalid = [d for d in v if d not in VALID_DAYS]
        if invalid:
            raise ValueError(
                f"delivery_days contiene dias invalidos: {invalid}. "
                f"Usar 1=Lun, 2=Mar, 3=Mie, 4=Jue, 5=Vie, 6=Sab"
            )
        return sorted(set(v))


class RutaUpdate(BaseModel):
    zone_id: Optional[str] = None
    salesperson_id: Optional[str] = None
    name: Optional[str] = None
    route_type: Optional[str] = None
    operating_days: Optional[list[int]] = None
    delivery_days: Optional[list[int]] = None
    daily_schedule: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

    @field_validator("route_type")
    @classmethod
    def validate_route_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = {rt.value for rt in RouteType}
        if v not in valid:
            raise ValueError(f"route_type debe ser uno de: {valid}")
        return v

    @field_validator("operating_days")
    @classmethod
    def validate_operating_days(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return v
        invalid = [d for d in v if d not in VALID_DAYS]
        if invalid:
            raise ValueError(f"operating_days contiene dias invalidos: {invalid}")
        return sorted(set(v))

    @field_validator("delivery_days")
    @classmethod
    def validate_delivery_days(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return v
        invalid = [d for d in v if d not in VALID_DAYS]
        if invalid:
            raise ValueError(f"delivery_days contiene dias invalidos: {invalid}")
        return sorted(set(v))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = {rs.value for rs in RouteStatus}
        if v not in valid:
            raise ValueError(f"status debe ser uno de: {valid}")
        return v


class RutaOut(BaseModel):
    id: str
    name: Optional[str]
    route_type: str
    status: str
    is_active: bool
    zone_id: Optional[str]
    zone_name: Optional[str]
    salesperson_id: str
    salesperson_name: Optional[str]
    operating_days: Optional[list]
    delivery_days: Optional[list]
    daily_schedule: Optional[dict]
    notes: Optional[str]
    # Metricas desnormalizadas
    total_clients: int
    visited_count: int
    sales_count: int
    total_sales_amount: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ruta_to_out(
    r: Route,
    zone_name: Optional[str] = None,
    salesperson_name: Optional[str] = None,
) -> RutaOut:
    return RutaOut(
        id=str(r.id),
        name=r.name,
        route_type=r.route_type.value if hasattr(r.route_type, "value") else r.route_type,
        status=r.status.value if hasattr(r.status, "value") else r.status,
        is_active=r.is_active,
        zone_id=str(r.zone_id) if r.zone_id else None,
        zone_name=zone_name,
        salesperson_id=str(r.salesperson_id),
        salesperson_name=salesperson_name,
        operating_days=r.operating_days,
        delivery_days=r.delivery_days,
        daily_schedule=r.daily_schedule,
        notes=r.notes,
        total_clients=r.total_clients or 0,
        visited_count=r.visited_count or 0,
        sales_count=r.sales_count or 0,
        total_sales_amount=r.total_sales_amount or "0",
    )


async def _get_ruta_or_404(ruta_id: str, tenant_id: str, db: AsyncSession) -> Route:
    result = await db.execute(
        select(Route).where(
            and_(Route.id == ruta_id, Route.tenant_id == tenant_id)
        )
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return route


async def _validate_zone(zone_id: str, tenant_id: str, db: AsyncSession) -> Zone:
    """Verifica que la zona existe y pertenece al tenant."""
    result = await db.execute(
        select(Zone).where(
            and_(Zone.id == zone_id, Zone.tenant_id == tenant_id, Zone.is_active == True)
        )
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(
            status_code=400,
            detail="La zona no existe o no esta activa en este tenant",
        )
    return zone


async def _validate_salesperson(salesperson_id: str, tenant_id: str, db: AsyncSession) -> User:
    """Verifica que el vendedor/agente existe, pertenece al tenant y tiene rol valido."""
    result = await db.execute(
        select(User).where(
            and_(User.id == salesperson_id, User.tenant_id == tenant_id, User.is_active == True)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="El vendedor no existe o no esta activo en este tenant",
        )
    if user.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"El usuario debe tener rol '{UserRole.SALESPERSON.value}' o '{UserRole.AGENT.value}'",
        )
    return user


async def _enrich_route(route: Route, db: AsyncSession) -> tuple[Optional[str], Optional[str]]:
    """Retorna (zone_name, salesperson_name) para una ruta."""
    zone_name = None
    salesperson_name = None

    if route.zone_id:
        z = await db.get(Zone, route.zone_id)
        zone_name = z.name if z else None

    if route.salesperson_id:
        sp = await db.get(User, route.salesperson_id)
        salesperson_name = sp.name if sp else None

    return zone_name, salesperson_name


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[RutaOut])
async def list_rutas(
    zone_id: Optional[str] = None,
    salesperson_id: Optional[str] = None,
    route_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista rutas del tenant con filtros opcionales."""
    tenant_id = current_user["tenant_id"]
    filters = [Route.tenant_id == tenant_id]

    if zone_id:
        filters.append(Route.zone_id == zone_id)
    if salesperson_id:
        filters.append(Route.salesperson_id == salesperson_id)
    if route_type:
        filters.append(Route.route_type == route_type)
    if is_active is not None:
        filters.append(Route.is_active == is_active)

    result = await db.execute(
        select(Route).where(and_(*filters)).order_by(Route.created_at.desc())
    )
    routes = result.scalars().all()

    out = []
    for r in routes:
        zone_name, salesperson_name = await _enrich_route(r, db)
        out.append(_ruta_to_out(r, zone_name, salesperson_name))
    return out


@router.post("/", response_model=RutaOut, status_code=status.HTTP_201_CREATED)
async def create_ruta(
    data: RutaCreate,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea una ruta comercial.
    El vendedor asignado debe pertenecer al tenant y tener rol salesperson o agent.
    La zona (si se indica) debe pertenecer al tenant y estar activa.
    """
    tenant_id = current_user["tenant_id"]

    salesperson = await _validate_salesperson(data.salesperson_id, tenant_id, db)

    zone = None
    if data.zone_id:
        zone = await _validate_zone(data.zone_id, tenant_id, db)

    route = Route(
        tenant_id=uuid.UUID(tenant_id),
        salesperson_id=uuid.UUID(data.salesperson_id),
        zone_id=uuid.UUID(data.zone_id) if data.zone_id else None,
        name=data.name,
        route_type=RouteType(data.route_type),
        operating_days=data.operating_days,
        delivery_days=data.delivery_days,
        daily_schedule=data.daily_schedule,
        notes=data.notes,
    )
    db.add(route)
    await db.flush()

    return _ruta_to_out(
        route,
        zone_name=zone.name if zone else None,
        salesperson_name=salesperson.name,
    )


@router.get("/{ruta_id}", response_model=RutaOut)
async def get_ruta(
    ruta_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna el detalle de una ruta con nombre de zona y vendedor."""
    tenant_id = current_user["tenant_id"]
    route = await _get_ruta_or_404(ruta_id, tenant_id, db)
    zone_name, salesperson_name = await _enrich_route(route, db)
    return _ruta_to_out(route, zone_name, salesperson_name)


@router.patch("/{ruta_id}", response_model=RutaOut)
async def update_ruta(
    ruta_id: str,
    data: RutaUpdate,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza cualquier campo editable de la ruta."""
    tenant_id = current_user["tenant_id"]
    route = await _get_ruta_or_404(ruta_id, tenant_id, db)
    update_data = data.model_dump(exclude_none=True)

    if "salesperson_id" in update_data:
        await _validate_salesperson(update_data["salesperson_id"], tenant_id, db)
        route.salesperson_id = uuid.UUID(update_data.pop("salesperson_id"))

    if "zone_id" in update_data:
        await _validate_zone(update_data["zone_id"], tenant_id, db)
        route.zone_id = uuid.UUID(update_data.pop("zone_id"))

    if "route_type" in update_data:
        route.route_type = RouteType(update_data.pop("route_type"))

    if "status" in update_data:
        route.status = RouteStatus(update_data.pop("status"))

    for field, value in update_data.items():
        setattr(route, field, value)

    await db.flush()
    zone_name, salesperson_name = await _enrich_route(route, db)
    return _ruta_to_out(route, zone_name, salesperson_name)


@router.delete("/{ruta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ruta(
    ruta_id: str,
    current_user: dict = Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactiva una ruta (soft delete). No elimina el registro ni sus visitas historicas.
    """
    tenant_id = current_user["tenant_id"]
    route = await _get_ruta_or_404(ruta_id, tenant_id, db)
    route.is_active = False
    await db.flush()
