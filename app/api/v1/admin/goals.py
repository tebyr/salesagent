"""
Gestion de metas y cuotas de venta por vendedor.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.goal import SalesGoal, GoalPeriodType
import uuid

router = APIRouter(prefix="/goals", tags=["Admin - Metas"])


class GoalCreate(BaseModel):
    salesperson_id: str
    period_type: str = "monthly"
    period_start: date
    period_end: date
    target_amount: Optional[float] = None
    target_visits: Optional[int] = None
    target_effective_visits: Optional[int] = None
    target_new_clients: Optional[int] = None
    target_active_clients: Optional[int] = None
    target_catalog_coverage: Optional[float] = None
    target_by_category: Optional[dict] = None
    notes: Optional[str] = None


class GoalBulkCreate(BaseModel):
    """Crear la misma meta para multiples vendedores a la vez."""
    salesperson_ids: list[str]
    period_type: str = "monthly"
    period_start: date
    period_end: date
    target_amount: Optional[float] = None
    target_visits: Optional[int] = None
    target_effective_visits: Optional[int] = None


class GoalOut(BaseModel):
    id: str
    salesperson_id: str
    period_type: str
    period_start: date
    period_end: date
    target_amount: Optional[float]
    target_visits: Optional[int]
    target_effective_visits: Optional[int]
    target_new_clients: Optional[int]
    target_active_clients: Optional[int]
    is_active: bool
    notes: Optional[str]
    # Progress (calculado)
    actual_amount: Optional[float] = None
    pct_amount: Optional[float] = None


@router.get("/", response_model=list[GoalOut])
async def list_goals(
    salesperson_id: Optional[str] = None,
    period_type: Optional[str] = None,
    period_start: Optional[date] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.order import Order, OrderStatus
    from sqlalchemy import func

    tenant_id = current_user["tenant_id"]
    filters = [SalesGoal.tenant_id == tenant_id, SalesGoal.is_active == True]

    if salesperson_id:
        filters.append(SalesGoal.salesperson_id == salesperson_id)
    if period_type:
        filters.append(SalesGoal.period_type == GoalPeriodType(period_type))
    if period_start:
        filters.append(SalesGoal.period_start == period_start)

    result = await db.execute(
        select(SalesGoal).where(and_(*filters)).order_by(SalesGoal.period_start.desc())
    )
    goals = result.scalars().all()

    today = date.today()
    confirmed = [OrderStatus.CONFIRMED, OrderStatus.DISPATCHED, OrderStatus.DELIVERED]

    out = []
    for g in goals:
        # Calcular progreso actual
        r = await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                and_(Order.tenant_id == tenant_id,
                     Order.salesperson_id == str(g.salesperson_id),
                     Order.order_date >= g.period_start,
                     Order.order_date <= min(g.period_end, today),
                     Order.status.in_(confirmed))
            )
        )
        actual = float(r.scalar())
        pct = (actual / g.target_amount * 100) if g.target_amount and g.target_amount > 0 else None

        out.append(GoalOut(
            id=str(g.id),
            salesperson_id=str(g.salesperson_id),
            period_type=g.period_type.value,
            period_start=g.period_start,
            period_end=g.period_end,
            target_amount=g.target_amount,
            target_visits=g.target_visits,
            target_effective_visits=g.target_effective_visits,
            target_new_clients=g.target_new_clients,
            target_active_clients=g.target_active_clients,
            is_active=g.is_active,
            notes=g.notes,
            actual_amount=actual,
            pct_amount=round(pct, 1) if pct is not None else None,
        ))
    return out


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]

    # Desactivar meta anterior del mismo periodo si existe
    existing = await db.execute(
        select(SalesGoal).where(
            and_(SalesGoal.tenant_id == tenant_id,
                 SalesGoal.salesperson_id == data.salesperson_id,
                 SalesGoal.period_type == GoalPeriodType(data.period_type),
                 SalesGoal.period_start == data.period_start,
                 SalesGoal.is_active == True)
        )
    )
    for old_goal in existing.scalars().all():
        old_goal.is_active = False

    goal = SalesGoal(
        tenant_id=uuid.UUID(tenant_id),
        salesperson_id=uuid.UUID(data.salesperson_id),
        period_type=GoalPeriodType(data.period_type),
        period_start=data.period_start,
        period_end=data.period_end,
        target_amount=data.target_amount,
        target_visits=data.target_visits,
        target_effective_visits=data.target_effective_visits,
        target_new_clients=data.target_new_clients,
        target_active_clients=data.target_active_clients,
        target_by_category=data.target_by_category or {},
        notes=data.notes,
    )
    db.add(goal)
    await db.flush()

    return GoalOut(
        id=str(goal.id), salesperson_id=str(goal.salesperson_id),
        period_type=goal.period_type.value, period_start=goal.period_start,
        period_end=goal.period_end, target_amount=goal.target_amount,
        target_visits=goal.target_visits, target_effective_visits=goal.target_effective_visits,
        target_new_clients=goal.target_new_clients, target_active_clients=goal.target_active_clients,
        is_active=goal.is_active, notes=goal.notes,
    )


@router.post("/bulk", response_model=list[GoalOut], status_code=status.HTTP_201_CREATED)
async def create_goals_bulk(
    data: GoalBulkCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea la misma meta para multiples vendedores de una vez."""
    tenant_id = current_user["tenant_id"]
    results = []

    for salesperson_id in data.salesperson_ids:
        existing = await db.execute(
            select(SalesGoal).where(
                and_(SalesGoal.tenant_id == tenant_id,
                     SalesGoal.salesperson_id == salesperson_id,
                     SalesGoal.period_type == GoalPeriodType(data.period_type),
                     SalesGoal.period_start == data.period_start,
                     SalesGoal.is_active == True)
            )
        )
        for old in existing.scalars().all():
            old.is_active = False

        goal = SalesGoal(
            tenant_id=uuid.UUID(tenant_id),
            salesperson_id=uuid.UUID(salesperson_id),
            period_type=GoalPeriodType(data.period_type),
            period_start=data.period_start,
            period_end=data.period_end,
            target_amount=data.target_amount,
            target_visits=data.target_visits,
            target_effective_visits=data.target_effective_visits,
        )
        db.add(goal)
        await db.flush()
        results.append(GoalOut(
            id=str(goal.id), salesperson_id=str(goal.salesperson_id),
            period_type=goal.period_type.value, period_start=goal.period_start,
            period_end=goal.period_end, target_amount=goal.target_amount,
            target_visits=goal.target_visits, target_effective_visits=goal.target_effective_visits,
            target_new_clients=None, target_active_clients=None,
            is_active=True, notes=None,
        ))
    return results


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SalesGoal).where(
            and_(SalesGoal.id == goal_id, SalesGoal.tenant_id == current_user["tenant_id"])
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    goal.is_active = False
