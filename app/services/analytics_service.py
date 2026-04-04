"""
Servicio de analytics: calcula KPIs, afinidades y proyecciones.
Centraliza toda la logica de consultas analiticas.
"""
from datetime import date, timedelta
from sqlalchemy import select, func, and_, desc
from app.core.database import AsyncSessionLocal
import structlog

logger = structlog.get_logger()


class AnalyticsService:
    """Calculos de analytics para un tenant especifico."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def get_salesperson_goal_progress(
        self,
        salesperson_id: str,
        date: date = None,
    ) -> dict:
        """
        Calcula el progreso del vendedor vs su meta del mes actual.
        Incluye proyeccion al cierre del periodo.
        """
        from app.models.goal import SalesGoal, GoalPeriodType
        from app.models.order import Order, OrderStatus
        from sqlalchemy.dialects.postgresql import UUID
        import uuid

        today = date or date.today()
        # Encontrar el primer y ultimo dia del mes
        period_start = today.replace(day=1)
        next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = next_month - timedelta(days=1)

        async with AsyncSessionLocal() as db:
            # Meta mensual del vendedor
            goal_result = await db.execute(
                select(SalesGoal).where(
                    and_(
                        SalesGoal.tenant_id == self.tenant_id,
                        SalesGoal.salesperson_id == salesperson_id,
                        SalesGoal.period_type == GoalPeriodType.MONTHLY,
                        SalesGoal.period_start == period_start,
                        SalesGoal.is_active == True,
                    )
                )
            )
            goal = goal_result.scalar_one_or_none()

            # Ventas acumuladas del mes
            sales_result = await db.execute(
                select(func.sum(Order.total_amount)).where(
                    and_(
                        Order.tenant_id == self.tenant_id,
                        Order.salesperson_id == salesperson_id,
                        Order.order_date >= period_start,
                        Order.order_date <= today,
                        Order.status.in_([
                            OrderStatus.CONFIRMED,
                            OrderStatus.DISPATCHED,
                            OrderStatus.DELIVERED,
                        ])
                    )
                )
            )
            actual_amount = sales_result.scalar() or 0.0

        target_amount = goal.target_amount if goal else 0.0
        target_visits = goal.target_visits if goal else 0

        days_elapsed = (today - period_start).days + 1
        days_in_period = (period_end - period_start).days + 1
        days_remaining = (period_end - today).days

        pct_amount = (actual_amount / target_amount * 100) if target_amount > 0 else 0

        # Proyeccion lineal: si sigo a este ritmo, cuanto vendo al final del mes
        daily_rate = actual_amount / days_elapsed if days_elapsed > 0 else 0
        projected_amount = daily_rate * days_in_period
        projected_pct = (projected_amount / target_amount * 100) if target_amount > 0 else 0

        # Cuanto necesito vender por dia para alcanzar la meta
        gap = max(0, target_amount - actual_amount)
        suggested_daily_target = gap / days_remaining if days_remaining > 0 else 0

        return {
            "target_amount": target_amount,
            "actual_amount": actual_amount,
            "pct_amount": pct_amount,
            "target_visits": target_visits,
            "period_start": str(period_start),
            "period_end": str(period_end),
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "projected_amount": projected_amount,
            "projected_pct": projected_pct,
            "gap_amount": gap,
            "suggested_daily_target": suggested_daily_target,
        }

    async def get_route_data_for_briefing(
        self,
        salesperson_id: str,
        route_id: str,
        date: date,
    ) -> dict:
        """Obtiene los datos de la ruta para el briefing matutino."""
        from app.models.route import Route, RouteVisit
        from app.models.client import Client
        from app.models.product import Promotion

        async with AsyncSessionLocal() as db:
            # Clientes en la ruta
            visits_result = await db.execute(
                select(RouteVisit, Client).join(
                    Client, RouteVisit.client_id == Client.id
                ).where(
                    RouteVisit.route_id == route_id
                ).order_by(RouteVisit.visit_order)
            )
            visits_clients = visits_result.all()

            # Promociones activas
            promos_result = await db.execute(
                select(Promotion).where(
                    and_(
                        Promotion.tenant_id == self.tenant_id,
                        Promotion.is_active == True,
                        Promotion.start_date <= date,
                        Promotion.end_date >= date,
                    )
                ).limit(5)
            )
            promotions = promos_result.scalars().all()

        # Identificar clientes prioritarios
        priority_clients = []
        all_clients = []

        for visit, client in visits_clients:
            client_info = {
                "id": str(client.id),
                "name": client.business_name or client.owner_name,
                "avg_ticket": client.avg_ticket_amount or 0,
                "days_since_purchase": (
                    (date - client.last_purchase_date).days
                    if client.last_purchase_date else 999
                ),
                "segment": client.segment or "C",
            }
            all_clients.append(client_info)

            # Es prioritario si: no ha comprado en su frecuencia esperada O es segmento A/B
            if (
                client.is_overdue_for_visit
                or client.segment in ("A", "B")
            ):
                client_info["priority_reason"] = (
                    "Cliente sin compra" if client.is_overdue_for_visit
                    else f"Cliente {client.segment}"
                )
                priority_clients.append(client_info)

        return {
            "date": str(date),
            "route_id": route_id,
            "total_clients": len(all_clients),
            "priority_clients": priority_clients[:5],
            "all_clients": all_clients,
            "active_promotions": [
                {
                    "title": p.title,
                    "description": p.description or "",
                    "end_date": str(p.end_date),
                }
                for p in promotions
            ],
            "alerts": self._generate_route_alerts(all_clients, priority_clients),
        }

    async def get_client_product_recommendations(
        self,
        client_id: str,
        limit: int = 4,
    ) -> list:
        """
        Obtiene recomendaciones de productos para un cliente especifico.
        Basado en: afinidad, historial de compras y promociones activas.
        """
        from app.models.analytics import ClientProductAffinity
        from app.models.product import Product, Promotion
        from datetime import date as date_type

        today = date_type.today()

        async with AsyncSessionLocal() as db:
            # Productos con alta afinidad
            affinity_result = await db.execute(
                select(ClientProductAffinity, Product).join(
                    Product, ClientProductAffinity.product_id == Product.id
                ).where(
                    and_(
                        ClientProductAffinity.tenant_id == self.tenant_id,
                        ClientProductAffinity.client_id == client_id,
                        Product.is_active == True,
                    )
                ).order_by(desc(ClientProductAffinity.affinity_score)).limit(limit * 2)
            )
            affinity_products = affinity_result.all()

        recommendations = []
        for affinity, product in affinity_products[:limit]:
            recommendations.append({
                "product_id": str(product.id),
                "name": product.name,
                "price": product.price,
                "category": product.category,
                "affinity_score": affinity.affinity_score,
                "last_purchase_date": str(affinity.last_purchase_date) if affinity.last_purchase_date else None,
                "promo_text": None,
            })

        return recommendations

    async def get_active_promotions_for_client(
        self,
        client_id: str,
    ) -> list:
        """Obtiene promociones activas relevantes para un cliente."""
        from app.models.product import Promotion
        from app.models.client import Client
        from datetime import date as date_type

        today = date_type.today()

        async with AsyncSessionLocal() as db:
            client_result = await db.execute(
                select(Client).where(Client.id == client_id)
            )
            client = client_result.scalar_one_or_none()
            if not client:
                return []

            promos_result = await db.execute(
                select(Promotion).where(
                    and_(
                        Promotion.tenant_id == self.tenant_id,
                        Promotion.is_active == True,
                        Promotion.start_date <= today,
                        Promotion.end_date >= today,
                    )
                ).order_by(Promotion.end_date).limit(5)
            )
            promotions = promos_result.scalars().all()

        return [
            {
                "id": str(p.id),
                "title": p.title,
                "description": p.description or "",
                "promo_type": p.promo_type,
                "discount_percent": p.discount_percent,
                "end_date": str(p.end_date),
            }
            for p in promotions
        ]

    async def get_top_recommendations_for_route(
        self,
        salesperson_id: str,
        date: date,
        limit: int = 10,
    ) -> list:
        """Recomendaciones cross-cliente para el briefing del vendedor."""
        from app.models.route import Route, RouteVisit
        from app.models.analytics import ClientProductAffinity
        from app.models.client import Client

        async with AsyncSessionLocal() as db:
            # Obtener clientes en la ruta de hoy
            result = await db.execute(
                select(RouteVisit.client_id).join(
                    Route, RouteVisit.route_id == Route.id
                ).where(
                    and_(
                        Route.salesperson_id == salesperson_id,
                        Route.date == date,
                    )
                )
            )
            client_ids = [str(r[0]) for r in result.all()]

        recommendations = []
        for client_id in client_ids[:5]:
            client_recs = await self.get_client_product_recommendations(
                client_id=client_id, limit=2
            )
            # Obtener nombre del cliente
            async with AsyncSessionLocal() as db:
                client_result = await db.execute(
                    select(Client).where(Client.id == client_id)
                )
                client = client_result.scalar_one_or_none()

            if client and client_recs:
                recommendations.append({
                    "client_name": client.business_name or client.owner_name,
                    "product_name": client_recs[0]["name"],
                    "reason": f"Alta afinidad ({client_recs[0]['affinity_score']:.0%})",
                })

        return recommendations[:limit]

    def _generate_route_alerts(self, all_clients: list, priority_clients: list) -> list:
        """Genera alertas relevantes para la ruta del dia."""
        alerts = []
        overdue = [c for c in all_clients if c.get("days_since_purchase", 0) > 30]
        if overdue:
            alerts.append(f"{len(overdue)} clientes sin compra hace mas de 30 dias")
        high_value = [c for c in all_clients if c.get("avg_ticket", 0) > 500000]
        if high_value:
            alerts.append(f"{len(high_value)} clientes de alto valor en la ruta hoy")
        return alerts
