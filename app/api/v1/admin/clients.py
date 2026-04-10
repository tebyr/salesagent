"""
CRUD de clientes (tenderos) en el panel admin.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.client import Client
import uuid

router = APIRouter(prefix="/clients", tags=["Admin - Clientes"])


class ClientCreate(BaseModel):
    business_name: str
    owner_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zone: Optional[str] = None
    neighborhood: Optional[str] = None
    salesperson_id: Optional[str] = None
    segment: Optional[str] = "C"
    channel_type: str = "tradicional"
    whatsapp_opt_in: bool = False
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    business_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    zone: Optional[str] = None
    salesperson_id: Optional[str] = None
    segment: Optional[str] = None
    is_active: Optional[bool] = None
    whatsapp_opt_in: Optional[bool] = None
    notes: Optional[str] = None


class ClientOut(BaseModel):
    id: str
    business_name: str
    owner_name: Optional[str]
    phone: str
    email: Optional[str]
    address: Optional[str]
    zone: Optional[str]
    segment: Optional[str]
    salesperson_id: Optional[str]
    is_active: bool
    whatsapp_opt_in: bool
    last_purchase_date: Optional[date]
    avg_ticket_amount: Optional[float]
    avg_purchase_frequency_days: Optional[int]
    total_purchases_count: int
    days_since_last_purchase: Optional[int]


def _normalize_phone(phone: str) -> str:
    normalized = "".join(filter(str.isdigit, phone))
    if len(normalized) == 10 and normalized.startswith("3"):
        normalized = "57" + normalized
    return normalized


def _client_to_out(c: Client) -> ClientOut:
    days_since = None
    if c.last_purchase_date:
        days_since = (date.today() - c.last_purchase_date).days
    return ClientOut(
        id=str(c.id),
        business_name=c.business_name,
        owner_name=c.owner_name,
        phone=c.phone,
        email=c.email,
        address=c.address,
        zone=c.zone,
        segment=c.segment,
        salesperson_id=str(c.salesperson_id) if c.salesperson_id else None,
        is_active=c.is_active,
        whatsapp_opt_in=c.whatsapp_opt_in,
        last_purchase_date=c.last_purchase_date,
        avg_ticket_amount=c.avg_ticket_amount,
        avg_purchase_frequency_days=c.avg_purchase_frequency_days,
        total_purchases_count=c.total_purchases_count,
        days_since_last_purchase=days_since,
    )


@router.get("/", response_model=list[ClientOut])
async def list_clients(
    salesperson_id: Optional[str] = None,
    zone: Optional[str] = None,
    segment: Optional[str] = None,
    is_active: Optional[bool] = None,
    inactive_days: Optional[int] = Query(None, description="Clientes sin compra en N dias"),
    search: Optional[str] = Query(None, description="Buscar por nombre o telefono"),
    limit: int = Query(100, le=500),
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    filters = [Client.tenant_id == tenant_id]

    if salesperson_id:
        filters.append(Client.salesperson_id == salesperson_id)
    if zone:
        filters.append(Client.zone_name == zone)
    if segment:
        filters.append(Client.segment == segment)
    if is_active is not None:
        filters.append(Client.is_active == is_active)
    if inactive_days:
        cutoff = date.today().replace(day=date.today().day) - __import__('datetime').timedelta(days=inactive_days)
        filters.append(Client.last_purchase_date < cutoff)
    if search:
        filters.append(
            or_(
                Client.business_name.ilike(f"%{search}%"),
                Client.owner_name.ilike(f"%{search}%"),
                Client.phone_normalized.contains(search),
            )
        )

    result = await db.execute(
        select(Client).where(and_(*filters))
        .order_by(Client.business_name)
        .limit(limit).offset(offset)
    )
    clients = result.scalars().all()
    return [_client_to_out(c) for c in clients]


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    phone_norm = _normalize_phone(data.phone)

    existing = await db.execute(
        select(Client).where(
            and_(Client.tenant_id == tenant_id,
                 Client.phone_normalized == phone_norm)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe un cliente con ese telefono")

    client = Client(
        tenant_id=uuid.UUID(tenant_id),
        phone_normalized=phone_norm,
        salesperson_id=uuid.UUID(data.salesperson_id) if data.salesperson_id else None,
        **{k: v for k, v in data.model_dump().items()
           if k not in ("salesperson_id",) and v is not None},
    )
    client.phone_normalized = phone_norm
    db.add(client)
    await db.flush()
    return _client_to_out(client)


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user["tenant_id"], db)
    return _client_to_out(client)


@router.patch("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: str,
    data: ClientUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user["tenant_id"], db)
    update_data = data.model_dump(exclude_none=True)
    if "salesperson_id" in update_data:
        client.salesperson_id = uuid.UUID(update_data.pop("salesperson_id")) if update_data["salesperson_id"] else None
    for field, value in update_data.items():
        setattr(client, field, value)
    if data.phone:
        client.phone_normalized = _normalize_phone(data.phone)
    await db.flush()
    return _client_to_out(client)


async def _get_client_or_404(client_id: str, tenant_id: str, db) -> Client:
    result = await db.execute(
        select(Client).where(and_(Client.id == client_id, Client.tenant_id == tenant_id))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client
