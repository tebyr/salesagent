"""
Dashboard del panel admin: KPIs en tiempo real del tenant.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast as sa_cast, Date as SADate, text as sa_text
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.route import Route, RouteVisit, VisitStatus
from app.models.goal import SalesGoal, GoalPeriodType
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(prefix="/dashboard", tags=["Admin - Dashboard"])


class DashboardKPIs(BaseModel):
    # Ventas
    sales_today: float
    sales_this_month: float
    sales_last_month: float
    mom_change_pct: float

    # Equipo
    total_salespersons: int
    active_salespersons_today: int
    total_clients: int
    active_clients_this_month: int

    # Visitas
    visits_planned_today: int
    visits_completed_today: int
    effectiveness_today: float

    # Meta
    team_month_goal: float
    team_month_actual: float
    team_month_pct: float

    # Alertas
    salespersons_below_60pct: int
    inactive_clients_30d: int


class SalespersonSummary(BaseModel):
    id: str
    name: str
    phone: str
    sales_today: float
    sales_month: float
    month_goal: float
    month_pct: float
    visits_today: int
    effectiveness_today: float
    status_color: str  # green | yellow | red


@router.get("/kpis", response_model=DashboardKPIs)
async def get_dashboard_kpis(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """KPIs principales del tenant para el dashboard."""
    tenant_id = current_user["tenant_id"]
    today = date.today()
    weekday = today.isoweekday()  # 1=Lun, 6=Sáb
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(days=1)

    confirmed_statuses = [OrderStatus.CONFIRMED, OrderStatus.DISPATCHED, OrderStatus.DELIVERED]

    # Ventas hoy
    r = await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            and_(Order.tenant_id == tenant_id, Order.order_date == today,
                 Order.status.in_(confirmed_statuses))
        )
    )
    sales_today = float(r.scalar())

    # Ventas este mes
    r = await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            and_(Order.tenant_id == tenant_id,
                 Order.order_date >= month_start, Order.order_date <= today,
                 Order.status.in_(confirmed_statuses))
        )
    )
    sales_this_month = float(r.scalar())

    # Ventas mes pasado
    r = await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            and_(Order.tenant_id == tenant_id,
                 Order.order_date >= last_month_start,
                 Order.order_date <= last_month_end,
                 Order.status.in_(confirmed_statuses))
        )
    )
    sales_last_month = float(r.scalar())
    mom_change = ((sales_this_month - sales_last_month) / sales_last_month * 100
                  if sales_last_month > 0 else 0)

    # Vendedores
    r = await db.execute(
        select(func.count()).where(
            and_(User.tenant_id == tenant_id, User.role == UserRole.SALESPERSON,
                 User.is_active == True)
        )
    )
    total_salespersons = r.scalar()

    # Vendedores con ruta hoy (activos) — operating_days @> '[weekday]'
    r = await db.execute(
        select(func.count(func.distinct(Route.salesperson_id))).where(
            and_(Route.tenant_id == tenant_id, Route.is_active == True,
                 sa_text(f"routes.operating_days @> '[{weekday}]'::jsonb"))
        )
    )
    active_salespersons_today = r.scalar()

    # Clientes totales
    r = await db.execute(
        select(func.count()).where(
            and_(Client.tenant_id == tenant_id, Client.is_active == True)
        )
    )
    total_clients = r.scalar()

    # Clientes activos este mes (compraron)
    r = await db.execute(
        select(func.count(func.distinct(Order.client_id))).where(
            and_(Order.tenant_id == tenant_id,
                 Order.order_date >= month_start,
                 Order.status.in_(confirmed_statuses))
        )
    )
    active_clients_month = r.scalar()

    # Visitas hoy — created_at::date == today
    r = await db.execute(
        select(func.count()).select_from(RouteVisit).join(Route, RouteVisit.route_id == Route.id).where(
            and_(RouteVisit.tenant_id == tenant_id,
                 sa_cast(RouteVisit.created_at, SADate) == today)
        )
    )
    visits_planned = r.scalar()

    r = await db.execute(
        select(func.count()).select_from(RouteVisit).join(Route, RouteVisit.route_id == Route.id).where(
            and_(RouteVisit.tenant_id == tenant_id,
                 sa_cast(RouteVisit.created_at, SADate) == today,
                 RouteVisit.status.in_([
                     VisitStatus.VISITED_SALE,
                     VisitStatus.VISITED_NO_SALE,
                 ])
            )
        )
    )
    visits_completed = r.scalar()

    effectiveness = (visits_completed / visits_planned * 100) if visits_planned > 0 else 0

    # Meta del equipo este mes
    r = await db.execute(
        select(func.coalesce(func.sum(SalesGoal.target_amount), 0)).where(
            and_(SalesGoal.tenant_id == tenant_id,
                 SalesGoal.period_type == GoalPeriodType.MONTHLY,
                 SalesGoal.period_start == month_start,
                 SalesGoal.is_active == True)
        )
    )
    team_month_goal = float(r.scalar())
    team_month_pct = (sales_this_month / team_month_goal * 100) if team_month_goal > 0 else 0

    # Alertas: vendedores bajo 60%
    salespersons_below = 0
    if team_month_goal > 0:
        r = await db.execute(
            select(User.id).where(
                and_(User.tenant_id == tenant_id, User.role == UserRole.SALESPERSON,
                     User.is_active == True)
            )
        )
        salesperson_ids = [str(row[0]) for row in r.all()]
        for vid in salesperson_ids:
            r2 = await db.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                    and_(Order.tenant_id == tenant_id, Order.salesperson_id == vid,
                         Order.order_date >= month_start,
                         Order.status.in_(confirmed_statuses))
                )
            )
            v_sales = float(r2.scalar())
            r3 = await db.execute(
                select(SalesGoal.target_amount).where(
                    and_(SalesGoal.tenant_id == tenant_id,
                         SalesGoal.salesperson_id == vid,
                         SalesGoal.period_type == GoalPeriodType.MONTHLY,
                         SalesGoal.period_start == month_start,
                         SalesGoal.is_active == True)
                )
            )
            v_goal = float(r3.scalar() or 0)
            if v_goal > 0 and (v_sales / v_goal * 100) < 60:
                salespersons_below += 1

    # Clientes inactivos 30 dias
    cutoff = today - timedelta(days=30)
    r = await db.execute(
        select(func.count()).where(
            and_(Client.tenant_id == tenant_id,
                 Client.is_active == True,
                 Client.last_purchase_date < cutoff)
        )
    )
    inactive_clients = r.scalar()

    return DashboardKPIs(
        sales_today=sales_today,
        sales_this_month=sales_this_month,
        sales_last_month=sales_last_month,
        mom_change_pct=round(mom_change, 1),
        total_salespersons=total_salespersons,
        active_salespersons_today=active_salespersons_today,
        total_clients=total_clients,
        active_clients_this_month=active_clients_month,
        visits_planned_today=visits_planned,
        visits_completed_today=visits_completed,
        effectiveness_today=round(effectiveness, 1),
        team_month_goal=team_month_goal,
        team_month_actual=sales_this_month,
        team_month_pct=round(team_month_pct, 1),
        salespersons_below_60pct=salespersons_below,
        inactive_clients_30d=inactive_clients,
    )


@router.get("/salespersons-performance", response_model=list[SalespersonSummary])
async def get_salespersons_performance(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rendimiento de todos los vendedores para la tabla del dashboard."""
    tenant_id = current_user["tenant_id"]
    today = date.today()
    month_start = today.replace(day=1)
    confirmed_statuses = [OrderStatus.CONFIRMED, OrderStatus.DISPATCHED, OrderStatus.DELIVERED]
    weekday = today.isoweekday()

    result = await db.execute(
        select(User).where(
            and_(User.tenant_id == tenant_id, User.role == UserRole.SALESPERSON,
                 User.is_active == True)
        ).order_by(User.name)
    )
    salespersons = result.scalars().all()

    summaries = []
    for salesperson in salespersons:
        vid = str(salesperson.id)

        r = await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                and_(Order.tenant_id == tenant_id, Order.salesperson_id == vid,
                     Order.order_date == today, Order.status.in_(confirmed_statuses))
            )
        )
        sales_today = float(r.scalar())

        r = await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                and_(Order.tenant_id == tenant_id, Order.salesperson_id == vid,
                     Order.order_date >= month_start,
                     Order.status.in_(confirmed_statuses))
            )
        )
        sales_month = float(r.scalar())

        r = await db.execute(
            select(SalesGoal.target_amount).where(
                and_(SalesGoal.tenant_id == tenant_id, SalesGoal.salesperson_id == vid,
                     SalesGoal.period_type == GoalPeriodType.MONTHLY,
                     SalesGoal.period_start == month_start,
                     SalesGoal.is_active == True)
            )
        )
        month_goal = float(r.scalar() or 0)
        month_pct = (sales_month / month_goal * 100) if month_goal > 0 else 0

        r = await db.execute(
            select(func.count()).select_from(RouteVisit).join(Route, RouteVisit.route_id == Route.id).where(
                and_(RouteVisit.tenant_id == tenant_id,
                     sa_cast(RouteVisit.created_at, SADate) == today,
                     Route.salesperson_id == vid)
            )
        )
        visits_today = r.scalar()

        r = await db.execute(
            select(func.count()).select_from(RouteVisit).join(Route, RouteVisit.route_id == Route.id).where(
                and_(RouteVisit.tenant_id == tenant_id,
                     sa_cast(RouteVisit.created_at, SADate) == today,
                     RouteVisit.status == VisitStatus.VISITED_SALE,
                     Route.salesperson_id == vid)
            )
        )
        sales_visits = r.scalar()
        effectiveness = (sales_visits / visits_today * 100) if visits_today > 0 else 0

        color = "green" if month_pct >= 80 else ("yellow" if month_pct >= 60 else "red")

        summaries.append(SalespersonSummary(
            id=vid,
            name=salesperson.name,
            phone=salesperson.phone,
            sales_today=sales_today,
            sales_month=sales_month,
            month_goal=month_goal,
            month_pct=round(month_pct, 1),
            visits_today=visits_today,
            effectiveness_today=round(effectiveness, 1),
            status_color=color,
        ))

    return sorted(summaries, key=lambda x: x.month_pct, reverse=True)
