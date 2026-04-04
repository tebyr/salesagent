"""
CRUD de vendedores en el panel admin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.user import User, UserRole
import uuid

router = APIRouter(prefix="/salespersons", tags=["Admin - Vendedores"])


class SalespersonCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    role: str = "salesperson"
    zone: Optional[str] = None
    password: Optional[str] = None
    whatsapp_opt_in: bool = True


class SalespersonUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None
    whatsapp_opt_in: Optional[bool] = None


class SalespersonOut(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str]
    role: str
    zone: Optional[str]
    is_active: bool
    whatsapp_opt_in: bool

    class Config:
        from_attributes = True


def _normalize_phone(phone: str) -> str:
    normalized = "".join(filter(str.isdigit, phone))
    if len(normalized) == 10 and normalized.startswith("3"):
        normalized = "57" + normalized
    return normalized


@router.get("/", response_model=list[SalespersonOut])
async def list_salespersons(
    is_active: Optional[bool] = None,
    zone: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    filters = [
        User.tenant_id == tenant_id,
        User.role.in_([UserRole.SALESPERSON, UserRole.SUPERVISOR]),
    ]
    if is_active is not None:
        filters.append(User.is_active == is_active)
    if zone:
        filters.append(User.zone == zone)

    result = await db.execute(
        select(User).where(and_(*filters)).order_by(User.name)
    )
    salespersons = result.scalars().all()
    return [SalespersonOut(id=str(v.id), name=v.name, phone=v.phone,
                      email=v.email, role=v.role.value, zone=v.zone,
                      is_active=v.is_active, whatsapp_opt_in=v.whatsapp_opt_in)
            for v in salespersons]


@router.post("/", response_model=SalespersonOut, status_code=status.HTTP_201_CREATED)
async def create_salesperson(
    data: SalespersonCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    phone_norm = _normalize_phone(data.phone)

    # Verificar que no exista el telefono en este tenant
    existing = await db.execute(
        select(User).where(
            and_(User.tenant_id == tenant_id,
                 User.phone_normalized == phone_norm)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese telefono")

    role = UserRole(data.role) if data.role in [r.value for r in UserRole] else UserRole.SALESPERSON
    user = User(
        tenant_id=uuid.UUID(tenant_id),
        name=data.name,
        phone=data.phone,
        phone_normalized=phone_norm,
        email=data.email,
        role=role,
        zone=data.zone,
        whatsapp_opt_in=data.whatsapp_opt_in,
        password_hash=hash_password(data.password) if data.password else None,
    )
    db.add(user)
    await db.flush()
    return SalespersonOut(id=str(user.id), name=user.name, phone=user.phone,
                     email=user.email, role=user.role.value, zone=user.zone,
                     is_active=user.is_active, whatsapp_opt_in=user.whatsapp_opt_in)


@router.get("/{salesperson_id}", response_model=SalespersonOut)
async def get_salesperson(
    salesperson_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    salesperson = await _get_salesperson_or_404(salesperson_id, current_user["tenant_id"], db)
    return SalespersonOut(id=str(salesperson.id), name=salesperson.name, phone=salesperson.phone,
                     email=salesperson.email, role=salesperson.role.value, zone=salesperson.zone,
                     is_active=salesperson.is_active, whatsapp_opt_in=salesperson.whatsapp_opt_in)


@router.patch("/{salesperson_id}", response_model=SalespersonOut)
async def update_salesperson(
    salesperson_id: str,
    data: SalespersonUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    salesperson = await _get_salesperson_or_404(salesperson_id, current_user["tenant_id"], db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(salesperson, field, value)
    if data.phone:
        salesperson.phone_normalized = _normalize_phone(data.phone)
    await db.flush()
    return SalespersonOut(id=str(salesperson.id), name=salesperson.name, phone=salesperson.phone,
                     email=salesperson.email, role=salesperson.role.value, zone=salesperson.zone,
                     is_active=salesperson.is_active, whatsapp_opt_in=salesperson.whatsapp_opt_in)


@router.delete("/{salesperson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_salesperson(
    salesperson_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    salesperson = await _get_salesperson_or_404(salesperson_id, current_user["tenant_id"], db)
    salesperson.is_active = False
    await db.flush()


async def _get_salesperson_or_404(salesperson_id: str, tenant_id: str, db) -> User:
    result = await db.execute(
        select(User).where(
            and_(User.id == salesperson_id, User.tenant_id == tenant_id)
        )
    )
    salesperson = result.scalar_one_or_none()
    if not salesperson:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    return salesperson
