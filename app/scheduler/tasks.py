"""
Tareas programadas con Celery.
Estas son las tareas proactivas del agente: briefings, reportes, etc.
"""
import asyncio
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.core.crypto import decrypt_value
import structlog
import sentry_sdk

logger = structlog.get_logger()

celery_app = Celery(
    "salesagent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    timezone="America/Bogota",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Programacion periodica
    beat_schedule={
        # ===== VENDEDORES =====
        # 6:30 AM - Briefing matutino (lunes a sabado)
        "salesperson-morning-briefing": {
            "task": "app.scheduler.tasks.send_salesperson_morning_briefings",
            "schedule": crontab(hour=6, minute=30, day_of_week="1-6"),
        },
        # 6:00 - 17:00 - Notificaciones pre-visita a clientes (cada 30 min, se filtra por ruta)
        "client-pre-visit-notifications": {
            "task": "app.scheduler.tasks.send_pre_visit_notifications",
            "schedule": crontab(hour="8-17", minute=0),
        },
        # 18:30 - Resumen del dia para vendedores
        "salesperson-daily-summary": {
            "task": "app.scheduler.tasks.send_salesperson_daily_summaries",
            "schedule": crontab(hour=18, minute=30, day_of_week="1-6"),
        },
        # 20:00 - Reporte de rendimiento + proyeccion
        "salesperson-performance-report": {
            "task": "app.scheduler.tasks.send_salesperson_performance_reports",
            "schedule": crontab(hour=20, minute=0, day_of_week="1-6"),
        },
        # Seguimiento clientes no visitados (19:00)
        "client-no-visit-followup": {
            "task": "app.scheduler.tasks.send_no_visit_followups",
            "schedule": crontab(hour=19, minute=0, day_of_week="1-6"),
        },

        # ===== GERENCIA =====
        # Reporte diario gerencia (7:00 AM lunes a sabado)
        "management-daily-report": {
            "task": "app.scheduler.tasks.send_management_daily_reports",
            "schedule": crontab(hour=7, minute=0, day_of_week="1-6"),
        },
        # Reporte semanal (lunes 7:30 AM)
        "management-weekly-report": {
            "task": "app.scheduler.tasks.send_management_weekly_reports",
            "schedule": crontab(hour=7, minute=30, day_of_week="1"),
        },
        # Alertas de bajo rendimiento (11:00 AM y 4:00 PM)
        "management-performance-alerts": {
            "task": "app.scheduler.tasks.check_and_send_performance_alerts",
            "schedule": crontab(hour="11,16", minute=0, day_of_week="1-6"),
        },

        # ===== ANALYTICS =====
        # Calcular afinidades cliente-producto (cada noche a las 2 AM)
        "calculate-product-affinities": {
            "task": "app.scheduler.tasks.calculate_product_affinities",
            "schedule": crontab(hour=2, minute=0),
        },
        # Generar snapshots diarios de ventas (11:55 PM)
        "generate-daily-snapshots": {
            "task": "app.scheduler.tasks.generate_daily_sales_snapshots",
            "schedule": crontab(hour=23, minute=55),
        },
    }
)


@celery_app.task(bind=True, name="app.scheduler.tasks.send_salesperson_morning_briefings")
def send_salesperson_morning_briefings(self):
    """
    6:30 AM - Envia el briefing matutino a todos los vendedores activos de todos los tenants.
    Incluye: ruta del dia, clientes prioritarios, metas, tips del dia.
    """
    import asyncio
    asyncio.run(_send_salesperson_morning_briefings())


@celery_app.task(bind=True, name="app.scheduler.tasks.send_pre_visit_notifications")
def send_pre_visit_notifications(self):
    """
    8:00 AM - 5:00 PM - Envia notificaciones a clientes antes de la visita del vendedor.
    Se ejecuta cada hora y filtra los clientes cuya visita es proxima.
    """
    import asyncio
    asyncio.run(_send_pre_visit_notifications())


@celery_app.task(bind=True, name="app.scheduler.tasks.send_salesperson_daily_summaries")
def send_salesperson_daily_summaries(self):
    """6:30 PM - Envia el resumen del dia a cada vendedor."""
    import asyncio
    asyncio.run(_send_salesperson_daily_summaries())


@celery_app.task(bind=True, name="app.scheduler.tasks.send_salesperson_performance_reports")
def send_salesperson_performance_reports(self):
    """8:00 PM - Envia reporte de rendimiento vs meta + proyeccion a cada vendedor."""
    import asyncio
    asyncio.run(_send_salesperson_performance_reports())


@celery_app.task(bind=True, name="app.scheduler.tasks.send_no_visit_followups")
def send_no_visit_followups(self):
    """7:00 PM - Agente contacta directamente a clientes que no fueron visitados hoy."""
    import asyncio
    asyncio.run(_send_no_visit_followups())


@celery_app.task(bind=True, name="app.scheduler.tasks.send_management_daily_reports")
def send_management_daily_reports(self):
    """7:00 AM - Envia reporte diario por email a gerencia."""
    import asyncio
    asyncio.run(_send_management_daily_reports())


@celery_app.task(bind=True, name="app.scheduler.tasks.send_management_weekly_reports")
def send_management_weekly_reports(self):
    """Lunes 7:30 AM - Envia reporte semanal por email a gerencia."""
    import asyncio
    asyncio.run(_send_management_weekly_reports())


@celery_app.task(bind=True, name="app.scheduler.tasks.check_and_send_performance_alerts")
def check_and_send_performance_alerts(self):
    """11 AM y 4 PM - Verifica y envia alertas de bajo rendimiento a gerencia."""
    import asyncio
    asyncio.run(_check_and_send_performance_alerts())


@celery_app.task(bind=True, name="app.scheduler.tasks.calculate_product_affinities")
def calculate_product_affinities(self):
    """2 AM - Recalcula scores de afinidad cliente-producto."""
    import asyncio
    asyncio.run(_calculate_product_affinities())


@celery_app.task(bind=True, name="app.scheduler.tasks.generate_daily_sales_snapshots")
def generate_daily_sales_snapshots(self):
    """11:55 PM - Genera snapshots diarios de ventas para reportes rapidos."""
    import asyncio
    asyncio.run(_generate_daily_sales_snapshots())


# ============================================================
# IMPLEMENTACIONES ASYNC
# ============================================================

async def _get_active_tenants() -> list:
    """Obtiene todos los tenants activos."""
    from app.core.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.is_active == True)
        )
        return result.scalars().all()


async def _send_salesperson_morning_briefings():
    """Implementacion asincrona del briefing matutino."""
    from datetime import date
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.route import Route, RouteStatus
    from app.services.analytics_service import AnalyticsService
    from app.services.whatsapp_service import WhatsAppService
    from app.agents.sales_agent import SalesAgent
    from sqlalchemy import select, and_
    import uuid

    tenants = await _get_active_tenants()
    today = date.today()

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }
            agent = SalesAgent(str(tenant.id), tenant_config)
            wa_service = WhatsAppService(
                phone_number_id=tenant.whatsapp_phone_number_id,
                access_token=decrypt_value(tenant.whatsapp_access_token),
                tenant_id=str(tenant.id),
            )
            analytics = AnalyticsService(str(tenant.id))

            async with AsyncSessionLocal() as db:
                # Obtener vendedores activos con ruta hoy
                result = await db.execute(
                    select(User, Route).join(
                        Route,
                        and_(
                            Route.salesperson_id == User.id,
                            Route.date == today,
                            Route.status == RouteStatus.PENDING,
                        )
                    ).where(
                        and_(
                            User.tenant_id == tenant.id,
                            User.role == UserRole.VENDOR,
                            User.is_active == True,
                            User.whatsapp_opt_in == True,
                        )
                    )
                )
                salesperson_routes = result.all()

            for salesperson, route in salesperson_routes:
                try:
                    route_data = await analytics.get_route_data_for_briefing(
                        salesperson_id=str(salesperson.id),
                        route_id=str(route.id),
                        date=today,
                    )
                    goal_progress = await analytics.get_salesperson_goal_progress(
                        salesperson_id=str(salesperson.id),
                        date=today,
                    )
                    recommendations = await analytics.get_top_recommendations_for_route(
                        salesperson_id=str(salesperson.id),
                        date=today,
                    )

                    message = await agent.generate_morning_briefing(
                        salesperson_name=salesperson.name,
                        route_data=route_data,
                        goal_progress=goal_progress,
                        top_recommendations=recommendations,
                    )

                    await wa_service.send_text_message(
                        to=salesperson.phone_normalized,
                        text=message,
                    )

                    logger.info(
                        "morning_briefing_sent",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(salesperson.id),
                        salesperson_name=salesperson.name,
                    )

                except Exception as e:
                    logger.error(
                        "morning_briefing_failed",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(salesperson.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error(
                "tenant_morning_briefing_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _send_pre_visit_notifications():
    """Envia notificaciones pre-visita a clientes cuyo vendedor viene en las proximas 2 horas."""
    from datetime import date, datetime, timedelta
    from app.core.database import AsyncSessionLocal
    from app.models.route import Route, RouteVisit, VisitStatus
    from app.models.client import Client
    from app.services.analytics_service import AnalyticsService
    from app.services.whatsapp_service import WhatsAppService
    from app.agents.client_agent import ClientAgent
    from sqlalchemy import select, and_

    tenants = await _get_active_tenants()
    today = date.today()
    now = datetime.now()

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
            }
            agent = ClientAgent(str(tenant.id), tenant_config)
            wa_service = WhatsAppService(
                phone_number_id=tenant.whatsapp_phone_number_id,
                access_token=decrypt_value(tenant.whatsapp_access_token),
                tenant_id=str(tenant.id),
            )
            analytics = AnalyticsService(str(tenant.id))

            async with AsyncSessionLocal() as db:
                # Obtener visitas pendientes de hoy que no han recibido notificacion
                result = await db.execute(
                    select(RouteVisit, Client).join(
                        Client, RouteVisit.client_id == Client.id
                    ).join(
                        Route, RouteVisit.route_id == Route.id
                    ).where(
                        and_(
                            Route.tenant_id == tenant.id,
                            Route.date == today,
                            RouteVisit.status == VisitStatus.PENDING,
                            RouteVisit.pre_visit_notification_sent_at == None,
                            Client.whatsapp_opt_in == True,
                        )
                    ).limit(100)
                )
                visits_clients = result.all()

            for visit, client in visits_clients:
                try:
                    recommendations = await analytics.get_client_product_recommendations(
                        client_id=str(client.id),
                        limit=4,
                    )
                    promotions = await analytics.get_active_promotions_for_client(
                        client_id=str(client.id),
                    )

                    message = await agent.generate_pre_visit_notification(
                        client_name=client.business_name or client.owner_name,
                        salesperson_name="su asesor comercial",
                        visit_time_estimate="hoy",
                        recommendations=recommendations,
                        active_promotions=promotions,
                    )

                    await wa_service.send_text_message(
                        to=client.phone_normalized,
                        text=message,
                    )

                    # Marcar notificacion como enviada
                    async with AsyncSessionLocal() as db:
                        visit_db = await db.get(RouteVisit, visit.id)
                        if visit_db:
                            visit_db.pre_visit_notification_sent_at = now
                            await db.commit()

                except Exception as e:
                    logger.error(
                        "pre_visit_notification_failed",
                        tenant_id=str(tenant.id),
                        client_id=str(client.id),
                        error=str(e),
                    )

        except Exception as e:
            logger.error(
                "tenant_pre_visit_notifications_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _send_salesperson_daily_summaries():
    """
    18:30 — Envia el resumen del dia a cada vendedor con ruta activa hoy.
    Usa los contadores desnormalizados de Route para evitar N+1 queries.
    """
    from datetime import date
    from sqlalchemy import select, and_, text as sa_text
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.route import Route
    from app.services.analytics_service import AnalyticsService
    from app.services.whatsapp_service import WhatsAppService
    from app.agents.sales_agent import SalesAgent

    tenants = await _get_active_tenants()
    today = date.today()
    today_weekday = today.isoweekday()  # 1=Lun … 6=Sab

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }
            agent = SalesAgent(str(tenant.id), tenant_config)
            wa_service = WhatsAppService(
                phone_number_id=tenant.whatsapp_phone_number_id,
                access_token=decrypt_value(tenant.whatsapp_access_token),
                tenant_id=str(tenant.id),
            )
            analytics = AnalyticsService(str(tenant.id))

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User, Route)
                    .join(Route, Route.salesperson_id == User.id)
                    .where(
                        and_(
                            User.tenant_id == tenant.id,
                            User.role == UserRole.SALESPERSON,
                            User.is_active == True,
                            User.whatsapp_opt_in == True,
                            Route.tenant_id == tenant.id,
                            Route.is_active == True,
                            sa_text(f"routes.operating_days @> '[{today_weekday}]'::jsonb"),
                        )
                    )
                )
                salesperson_routes = result.all()

            for salesperson, route in salesperson_routes:
                try:
                    visited = route.visited_count or 0
                    sales_count = route.sales_count or 0
                    total_planned = route.total_clients or 0
                    total_amount = float(route.total_sales_amount or 0)
                    effectiveness = (sales_count / visited) if visited > 0 else 0.0

                    day_results = {
                        "visited": visited,
                        "total_planned": total_planned,
                        "sales_count": sales_count,
                        "total_amount": total_amount,
                        "effectiveness_rate": effectiveness,
                        "not_visited": max(total_planned - visited, 0),
                    }
                    goal_progress = await analytics.get_salesperson_goal_progress(
                        salesperson_id=str(salesperson.id),
                        date=today,
                    )

                    message = await agent.generate_daily_summary(
                        salesperson_name=salesperson.name,
                        day_results=day_results,
                        goal_progress=goal_progress,
                    )
                    await wa_service.send_text_message(
                        to=salesperson.phone_normalized,
                        text=message,
                    )
                    logger.info(
                        "daily_summary_sent",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(salesperson.id),
                    )
                except Exception as e:
                    logger.error(
                        "daily_summary_failed",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(salesperson.id),
                        error=str(e),
                    )
        except Exception as e:
            logger.error(
                "tenant_daily_summary_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _send_salesperson_performance_reports():
    """
    20:00 — Reporte nocturno de rendimiento vs meta + proyeccion para cada vendedor activo.
    """
    from datetime import date
    from sqlalchemy import select, and_, func
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.order import Order, OrderItem, OrderStatus
    from app.models.route import Route, RouteVisit, VisitStatus
    from app.models.goal import SalesGoal
    from app.models.client import Client
    from app.services.analytics_service import AnalyticsService
    from app.services.whatsapp_service import WhatsAppService
    from app.agents.sales_agent import SalesAgent

    tenants = await _get_active_tenants()
    today = date.today()

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }
            agent = SalesAgent(str(tenant.id), tenant_config)
            wa_service = WhatsAppService(
                phone_number_id=tenant.whatsapp_phone_number_id,
                access_token=decrypt_value(tenant.whatsapp_access_token),
                tenant_id=str(tenant.id),
            )
            analytics = AnalyticsService(str(tenant.id))

            async with AsyncSessionLocal() as db:
                # Vendedores activos con WA opt-in
                users_result = await db.execute(
                    select(User).where(
                        and_(
                            User.tenant_id == tenant.id,
                            User.role == UserRole.SALESPERSON,
                            User.is_active == True,
                            User.whatsapp_opt_in == True,
                        )
                    )
                )
                salespersons = users_result.scalars().all()

                # Meta activa del periodo actual
                goals_result = await db.execute(
                    select(SalesGoal).where(
                        and_(
                            SalesGoal.tenant_id == tenant.id,
                            SalesGoal.period_start <= today,
                            SalesGoal.period_end >= today,
                            SalesGoal.is_active == True,
                        )
                    )
                )
                active_goals = {g.salesperson_id: g for g in goals_result.scalars().all()}

            for salesperson in salespersons:
                try:
                    goal = active_goals.get(salesperson.id)
                    period_start = goal.period_start if goal else today.replace(day=1)
                    period_end = goal.period_end if goal else today

                    async with AsyncSessionLocal() as db:
                        # Pedidos confirmados en el periodo
                        orders_result = await db.execute(
                            select(Order).where(
                                and_(
                                    Order.tenant_id == tenant.id,
                                    Order.salesperson_id == salesperson.id,
                                    Order.status == OrderStatus.CONFIRMED,
                                    Order.order_date >= period_start,
                                    Order.order_date <= today,
                                )
                            )
                        )
                        orders = orders_result.scalars().all()

                        # Visitas del periodo
                        visits_result = await db.execute(
                            select(RouteVisit)
                            .join(Route, RouteVisit.route_id == Route.id)
                            .where(
                                and_(
                                    Route.tenant_id == tenant.id,
                                    Route.salesperson_id == salesperson.id,
                                    RouteVisit.visited_at >= period_start,
                                    RouteVisit.visited_at <= today,
                                )
                            )
                        )
                        visits = visits_result.scalars().all()

                    order_amounts = {o.client_id: o.total_amount for o in orders}
                    client_ids_with_orders = list(order_amounts.keys())
                    active_clients = len(set(client_ids_with_orders))
                    total_visits = len(visits)
                    effective_visits = sum(
                        1 for v in visits if v.status == VisitStatus.VISITED_SALE
                    )
                    effectiveness = (effective_visits / total_visits) if total_visits > 0 else 0.0

                    top_clients = sorted(
                        [{"client_id": str(cid), "amount": amt}
                         for cid, amt in order_amounts.items()],
                        key=lambda x: x["amount"], reverse=True
                    )[:3]

                    detailed_metrics = {
                        "active_clients": active_clients,
                        "inactive_clients": 0,
                        "new_clients": 0,
                        "effectiveness_rate": effectiveness,
                        "top_clients": top_clients,
                        "category_performance": {},
                    }

                    goal_progress = await analytics.get_salesperson_goal_progress(
                        salesperson_id=str(salesperson.id),
                        date=today,
                    )

                    message = await agent.generate_performance_report(
                        salesperson_name=salesperson.name,
                        goal_progress=goal_progress,
                        detailed_metrics=detailed_metrics,
                    )
                    await wa_service.send_text_message(
                        to=salesperson.phone_normalized,
                        text=message,
                    )
                    logger.info(
                        "performance_report_sent",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(salesperson.id),
                    )
                except Exception as e:
                    logger.error(
                        "performance_report_failed",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(salesperson.id),
                        error=str(e),
                    )
        except Exception as e:
            logger.error(
                "tenant_performance_reports_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _send_no_visit_followups():
    """
    19:00 — El agente contacta directamente a clientes con visita pendiente o no realizada hoy.
    Solo aplica a clientes con whatsapp_opt_in=True.
    """
    from datetime import date
    from sqlalchemy import select, and_
    from app.core.database import AsyncSessionLocal
    from app.models.route import Route, RouteVisit, VisitStatus
    from app.models.client import Client
    from app.models.user import User
    from app.services.analytics_service import AnalyticsService
    from app.services.whatsapp_service import WhatsAppService
    from app.agents.client_agent import ClientAgent

    tenants = await _get_active_tenants()
    today = date.today()

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
            }
            agent = ClientAgent(str(tenant.id), tenant_config)
            wa_service = WhatsAppService(
                phone_number_id=tenant.whatsapp_phone_number_id,
                access_token=decrypt_value(tenant.whatsapp_access_token),
                tenant_id=str(tenant.id),
            )
            analytics = AnalyticsService(str(tenant.id))

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(RouteVisit, Client, User)
                    .join(Client, RouteVisit.client_id == Client.id)
                    .join(Route, RouteVisit.route_id == Route.id)
                    .join(User, Route.salesperson_id == User.id)
                    .where(
                        and_(
                            Route.tenant_id == tenant.id,
                            RouteVisit.status.in_([
                                VisitStatus.PENDING,
                                VisitStatus.NOT_VISITED,
                            ]),
                            Client.whatsapp_opt_in == True,
                        )
                    )
                    .limit(200)
                )
                rows = result.all()

            for visit, client, salesperson in rows:
                try:
                    days_since = 0
                    if client.last_purchase_date:
                        days_since = (today - client.last_purchase_date).days

                    recommendations = await analytics.get_client_product_recommendations(
                        client_id=str(client.id),
                        limit=3,
                    )
                    promotions = await analytics.get_active_promotions_for_client(
                        client_id=str(client.id),
                    )

                    message = await agent.generate_no_visit_followup(
                        client_name=client.business_name or client.owner_name,
                        salesperson_name=salesperson.name,
                        days_since_last_purchase=days_since,
                        recommendations=recommendations,
                        active_promotions=promotions,
                    )
                    await wa_service.send_text_message(
                        to=client.phone_normalized,
                        text=message,
                    )
                    logger.info(
                        "no_visit_followup_sent",
                        tenant_id=str(tenant.id),
                        client_id=str(client.id),
                    )
                except Exception as e:
                    logger.error(
                        "no_visit_followup_failed",
                        tenant_id=str(tenant.id),
                        client_id=str(client.id),
                        error=str(e),
                    )
        except Exception as e:
            logger.error(
                "tenant_no_visit_followups_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _send_management_daily_reports():
    """
    07:00 — Reporte diario de KPIs a gerencia por email.
    Reporta sobre el dia anterior.
    """
    from datetime import date, timedelta
    from sqlalchemy import select, and_, func
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.order import Order, OrderStatus
    from app.models.route import Route, RouteVisit, VisitStatus
    from app.models.goal import SalesGoal
    from app.services.email_service import EmailService
    from app.services.analytics_service import AnalyticsService
    from app.agents.management_agent import ManagementAgent

    tenants = await _get_active_tenants()
    today = date.today()
    yesterday = today - timedelta(days=1)

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }
            agent = ManagementAgent(str(tenant.id), tenant_config)
            email_service = EmailService(tenant_config)
            analytics = AnalyticsService(str(tenant.id))

            async with AsyncSessionLocal() as db:
                # Vendedores activos
                users_result = await db.execute(
                    select(User).where(
                        and_(
                            User.tenant_id == tenant.id,
                            User.role == UserRole.SALESPERSON,
                            User.is_active == True,
                        )
                    )
                )
                salespersons = users_result.scalars().all()

                # Pedidos confirmados ayer
                orders_result = await db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date == yesterday,
                        )
                    )
                )
                orders_yesterday = orders_result.scalars().all()

                # Meta activa del periodo
                month_start = today.replace(day=1)
                goals_result = await db.execute(
                    select(SalesGoal).where(
                        and_(
                            SalesGoal.tenant_id == tenant.id,
                            SalesGoal.period_start <= today,
                            SalesGoal.period_end >= today,
                            SalesGoal.is_active == True,
                        )
                    )
                )
                goals_map = {g.salesperson_id: g for g in goals_result.scalars().all()}

                # Pedidos del mes para acumulado
                month_orders_result = await db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date >= month_start,
                            Order.order_date <= today,
                        )
                    )
                )
                month_orders = month_orders_result.scalars().all()

            total_sales_yesterday = sum(o.total_amount for o in orders_yesterday)
            total_sales_month = sum(o.total_amount for o in month_orders)
            total_target = sum(
                g.target_amount for g in goals_map.values() if g.target_amount
            )
            month_pct = (total_sales_month / total_target * 100) if total_target > 0 else 0.0

            salesperson_details = []
            alerts = []
            for sp in salespersons:
                sp_orders_yesterday = [o for o in orders_yesterday if o.salesperson_id == sp.id]
                sp_sales_yesterday = sum(o.total_amount for o in sp_orders_yesterday)
                sp_month_orders = [o for o in month_orders if o.salesperson_id == sp.id]
                sp_month_total = sum(o.total_amount for o in sp_month_orders)
                goal = goals_map.get(sp.id)
                sp_target = goal.target_amount if goal else 0
                sp_pct = (sp_month_total / sp_target * 100) if sp_target > 0 else 0.0

                color = "green" if sp_pct >= 80 else ("yellow" if sp_pct >= 50 else "red")
                salesperson_details.append({
                    "name": sp.name,
                    "sales_today": sp_sales_yesterday,
                    "month_total": sp_month_total,
                    "month_target": sp_target,
                    "month_pct": sp_pct,
                    "status_color": color,
                })
                if sp_pct < 50 and sp_target > 0:
                    alerts.append(f"{sp.name}: {sp_pct:.0f}% de meta mensual")

            team_summary = {
                "active_salespersons": len(salespersons),
                "total_salespersons": len(salespersons),
                "total_sales": total_sales_yesterday,
                "total_visits": len(orders_yesterday),
                "avg_effectiveness": 0.0,
                "team_month_pct": month_pct,
                "team_projected_pct": month_pct,
                "company_name": tenant.name,
            }

            report = await agent.generate_daily_report(
                report_date=yesterday.strftime("%d/%m/%Y"),
                team_summary=team_summary,
                salesperson_details=salesperson_details,
                top_alerts=alerts,
            )

            management_emails = await analytics.get_tenant_management_emails(
                tenant_id=str(tenant.id)
            ) if hasattr(analytics, "get_tenant_management_emails") else (
                tenant.email_config or {}
            ).get("management_emails", [])

            await email_service.send_management_report(
                to_emails=management_emails,
                subject=report["subject"],
                html_body=report["html_body"],
                text_summary=report["text_summary"],
            )
            logger.info("management_daily_report_sent", tenant_id=str(tenant.id))
        except Exception as e:
            logger.error(
                "management_daily_report_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _send_management_weekly_reports():
    """
    Lunes 07:30 — Reporte semanal de KPIs a gerencia por email.
    Reporta sobre la semana anterior (Lun-Dom).
    """
    from datetime import date, timedelta
    from sqlalchemy import select, and_
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.order import Order, OrderStatus
    from app.models.goal import SalesGoal
    from app.services.email_service import EmailService
    from app.agents.management_agent import ManagementAgent

    tenants = await _get_active_tenants()
    today = date.today()
    # Semana anterior: lunes a domingo
    week_end = today - timedelta(days=1)            # domingo anterior
    week_start = week_end - timedelta(days=6)       # lunes anterior
    prev_week_end = week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)

    week_label = f"{week_start.strftime('%d/%m')} al {week_end.strftime('%d/%m/%Y')}"

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }
            agent = ManagementAgent(str(tenant.id), tenant_config)
            email_service = EmailService(tenant_config)

            async with AsyncSessionLocal() as db:
                users_result = await db.execute(
                    select(User).where(
                        and_(
                            User.tenant_id == tenant.id,
                            User.role == UserRole.SALESPERSON,
                            User.is_active == True,
                        )
                    )
                )
                salespersons = users_result.scalars().all()

                week_orders_result = await db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date >= week_start,
                            Order.order_date <= week_end,
                        )
                    )
                )
                week_orders = week_orders_result.scalars().all()

                prev_week_orders_result = await db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date >= prev_week_start,
                            Order.order_date <= prev_week_end,
                        )
                    )
                )
                prev_week_orders = prev_week_orders_result.scalars().all()

                goals_result = await db.execute(
                    select(SalesGoal).where(
                        and_(
                            SalesGoal.tenant_id == tenant.id,
                            SalesGoal.period_start <= today,
                            SalesGoal.period_end >= today,
                            SalesGoal.is_active == True,
                        )
                    )
                )
                goals_map = {g.salesperson_id: g for g in goals_result.scalars().all()}

            week_total = sum(o.total_amount for o in week_orders)
            prev_week_total = sum(o.total_amount for o in prev_week_orders)
            wow_change = (
                ((week_total - prev_week_total) / prev_week_total * 100)
                if prev_week_total > 0 else 0.0
            )
            total_target = sum(g.target_amount for g in goals_map.values() if g.target_amount)

            # Acumulado del mes hasta hoy
            month_start = today.replace(day=1)
            month_orders = [o for o in week_orders if o.order_date >= month_start]
            month_total = sum(o.total_amount for o in month_orders)
            month_pct = (month_total / total_target * 100) if total_target > 0 else 0.0

            salesperson_details = []
            for sp in salespersons:
                sp_week = sum(o.total_amount for o in week_orders if o.salesperson_id == sp.id)
                sp_prev = sum(o.total_amount for o in prev_week_orders if o.salesperson_id == sp.id)
                goal = goals_map.get(sp.id)
                sp_target = goal.target_amount if goal else 0
                sp_pct = (month_total / sp_target * 100) if sp_target > 0 else 0.0
                salesperson_details.append({
                    "name": sp.name,
                    "week_total": sp_week,
                    "prev_week_total": sp_prev,
                    "month_pct": sp_pct,
                    "status_color": "green" if sp_pct >= 80 else ("yellow" if sp_pct >= 50 else "red"),
                })

            team_summary = {
                "total_sales": week_total,
                "wow_change": wow_change,
                "month_pct": month_pct,
                "projected_pct": month_pct,
                "company_name": tenant.name,
            }
            kpi_trends = {
                "effectiveness_trend": 0.0,
                "avg_ticket": (week_total / len(week_orders)) if week_orders else 0.0,
                "active_clients": len(set(o.client_id for o in week_orders)),
                "active_clients_pct": 0.0,
                "at_risk_clients": 0,
            }

            report = await agent.generate_weekly_report(
                week_label=week_label,
                team_summary=team_summary,
                salesperson_details=salesperson_details,
                kpi_trends=kpi_trends,
                recommendations=[],
            )

            management_emails = (tenant.email_config or {}).get("management_emails", [])
            await email_service.send_management_report(
                to_emails=management_emails,
                subject=report["subject"],
                html_body=report["html_body"],
                text_summary=report["text_summary"],
            )
            logger.info("management_weekly_report_sent", tenant_id=str(tenant.id))
        except Exception as e:
            logger.error(
                "management_weekly_report_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _check_and_send_performance_alerts():
    """
    11:00 y 16:00 — Detecta vendedores con cumplimiento < 60% de meta mensual
    y envia alerta por email a gerencia.
    """
    from datetime import date
    from sqlalchemy import select, and_
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.goal import SalesGoal
    from app.models.order import Order, OrderStatus
    from app.models.route import Route, RouteVisit, VisitStatus
    from app.services.email_service import EmailService
    from app.agents.management_agent import ManagementAgent

    ALERT_THRESHOLD_PCT = 60.0
    MIN_DAYS_REMAINING = 5

    tenants = await _get_active_tenants()
    today = date.today()

    for tenant in tenants:
        try:
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }
            agent = ManagementAgent(str(tenant.id), tenant_config)
            email_service = EmailService(tenant_config)

            async with AsyncSessionLocal() as db:
                goals_result = await db.execute(
                    select(SalesGoal).where(
                        and_(
                            SalesGoal.tenant_id == tenant.id,
                            SalesGoal.period_start <= today,
                            SalesGoal.period_end >= today,
                            SalesGoal.is_active == True,
                        )
                    )
                )
                active_goals = goals_result.scalars().all()

            alerts_sent = 0
            for goal in active_goals:
                days_remaining = (goal.period_end - today).days
                if days_remaining < MIN_DAYS_REMAINING:
                    continue  # Periodo casi terminado, no enviar alerta

                try:
                    async with AsyncSessionLocal() as db:
                        orders_result = await db.execute(
                            select(Order).where(
                                and_(
                                    Order.tenant_id == tenant.id,
                                    Order.salesperson_id == goal.salesperson_id,
                                    Order.status == OrderStatus.CONFIRMED,
                                    Order.order_date >= goal.period_start,
                                    Order.order_date <= today,
                                )
                            )
                        )
                        orders = orders_result.scalars().all()
                        sp_result = await db.get(User, goal.salesperson_id)

                    if not sp_result:
                        continue

                    actual_amount = sum(o.total_amount for o in orders)
                    target = goal.target_amount or 0
                    pct = (actual_amount / target * 100) if target > 0 else 0.0

                    if pct >= ALERT_THRESHOLD_PCT:
                        continue  # Vendedor en rango aceptable

                    days_elapsed = (today - goal.period_start).days + 1
                    expected_pct = (days_elapsed / (days_elapsed + days_remaining)) * 100
                    required_daily = (
                        (target - actual_amount) / days_remaining
                    ) if days_remaining > 0 else 0

                    root_cause_hints = []
                    if pct < expected_pct * 0.7:
                        root_cause_hints.append("Ritmo de ventas muy por debajo del esperado para esta fecha")
                    if len(orders) < 5:
                        root_cause_hints.append("Bajo numero de pedidos en el periodo")
                    if not root_cause_hints:
                        root_cause_hints.append("Cumplimiento por debajo del umbral critico del 60%")

                    performance_data = {
                        "pct_amount": pct,
                        "target_amount": target,
                        "actual_amount": actual_amount,
                        "days_remaining": days_remaining,
                        "projected_pct": (actual_amount / target * 100 * (days_elapsed + days_remaining) / days_elapsed) if days_elapsed > 0 and target > 0 else 0,
                        "required_daily": required_daily,
                    }

                    alert_text = await agent.generate_low_performance_alert(
                        salesperson_name=sp_result.name,
                        performance_data=performance_data,
                        root_cause_hints=root_cause_hints,
                    )

                    management_emails = (tenant.email_config or {}).get("management_emails", [])
                    await email_service.send_alert(
                        to_emails=management_emails,
                        alert_title=f"Bajo rendimiento: {sp_result.name} ({pct:.0f}% de meta)",
                        alert_body=alert_text,
                        severity="critical" if pct < 40 else "warning",
                    )
                    alerts_sent += 1
                    logger.info(
                        "performance_alert_sent",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(goal.salesperson_id),
                        pct=pct,
                    )
                except Exception as e:
                    logger.error(
                        "performance_alert_failed",
                        tenant_id=str(tenant.id),
                        salesperson_id=str(goal.salesperson_id),
                        error=str(e),
                    )

            logger.info(
                "performance_alerts_completed",
                tenant_id=str(tenant.id),
                alerts_sent=alerts_sent,
            )
        except Exception as e:
            logger.error(
                "tenant_performance_alerts_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _calculate_product_affinities():
    """
    02:00 — Recalcula scores de afinidad cliente-producto a partir de los
    ultimos 90 dias de pedidos confirmados. Borra y re-inserta por tenant.
    """
    from datetime import date, timedelta
    from collections import defaultdict
    from sqlalchemy import select, and_, delete
    from app.core.database import AsyncSessionLocal
    from app.models.order import Order, OrderItem, OrderStatus
    from app.models.analytics import ClientProductAffinity

    tenants = await _get_active_tenants()
    today = date.today()
    cutoff = today - timedelta(days=90)

    for tenant in tenants:
        try:
            async with AsyncSessionLocal() as db:
                # Obtener items de pedidos confirmados ultimos 90 dias
                result = await db.execute(
                    select(OrderItem, Order)
                    .join(Order, OrderItem.order_id == Order.id)
                    .where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date >= cutoff,
                        )
                    )
                )
                rows = result.all()

            # Agrupar por (client_id, product_id)
            stats: dict = defaultdict(lambda: {
                "count": 0,
                "total_qty": 0.0,
                "total_amount": 0.0,
                "last_date": None,
            })
            for item, order in rows:
                key = (order.client_id, item.product_id)
                s = stats[key]
                s["count"] += 1
                s["total_qty"] += item.quantity
                s["total_amount"] += item.total_price
                if s["last_date"] is None or order.order_date > s["last_date"]:
                    s["last_date"] = order.order_date

            if not stats:
                continue

            max_count = max(s["count"] for s in stats.values())
            max_amount = max(s["total_amount"] for s in stats.values()) or 1.0

            affinities = []
            for (client_id, product_id), s in stats.items():
                freq_score = s["count"] / max_count
                days_ago = (today - s["last_date"]).days if s["last_date"] else 90
                recency_score = max(0.0, 1.0 - days_ago / 90)
                amount_score = s["total_amount"] / max_amount
                affinity = round((freq_score * 0.5 + recency_score * 0.3 + amount_score * 0.2), 4)
                avg_qty = round(s["total_qty"] / s["count"], 2) if s["count"] > 0 else 0

                affinities.append(ClientProductAffinity(
                    tenant_id=tenant.id,
                    client_id=client_id,
                    product_id=product_id,
                    affinity_score=affinity,
                    purchase_frequency=freq_score,
                    recency_score=recency_score,
                    amount_score=amount_score,
                    total_purchases=s["count"],
                    last_purchase_date=s["last_date"],
                    avg_quantity_per_order=avg_qty,
                ))

            async with AsyncSessionLocal() as db:
                # Borrar affinities anteriores del tenant y re-insertar
                await db.execute(
                    delete(ClientProductAffinity).where(
                        ClientProductAffinity.tenant_id == tenant.id
                    )
                )
                db.add_all(affinities)
                await db.commit()

            logger.info(
                "product_affinities_calculated",
                tenant_id=str(tenant.id),
                records=len(affinities),
            )
        except Exception as e:
            logger.error(
                "product_affinities_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


async def _generate_daily_sales_snapshots():
    """
    23:55 — Genera el snapshot diario de ventas por vendedor.
    Upsert: si ya existe el registro (salesperson, fecha) lo actualiza.
    """
    from datetime import date
    from sqlalchemy import select, and_, delete
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.order import Order, OrderStatus
    from app.models.route import Route, RouteVisit, VisitStatus
    from app.models.goal import SalesGoal
    from app.models.analytics import DailySalesSnapshot

    tenants = await _get_active_tenants()
    today = date.today()
    month_start = today.replace(day=1)

    for tenant in tenants:
        try:
            async with AsyncSessionLocal() as db:
                users_result = await db.execute(
                    select(User).where(
                        and_(
                            User.tenant_id == tenant.id,
                            User.role == UserRole.SALESPERSON,
                            User.is_active == True,
                        )
                    )
                )
                salespersons = users_result.scalars().all()

                today_orders_result = await db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date == today,
                        )
                    )
                )
                today_orders = today_orders_result.scalars().all()

                month_orders_result = await db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant.id,
                            Order.status == OrderStatus.CONFIRMED,
                            Order.order_date >= month_start,
                            Order.order_date <= today,
                        )
                    )
                )
                month_orders = month_orders_result.scalars().all()

                visits_result = await db.execute(
                    select(RouteVisit)
                    .join(Route, RouteVisit.route_id == Route.id)
                    .where(
                        and_(
                            Route.tenant_id == tenant.id,
                            RouteVisit.visited_at >= today,
                        )
                    )
                )
                today_visits = visits_result.scalars().all()

                goals_result = await db.execute(
                    select(SalesGoal).where(
                        and_(
                            SalesGoal.tenant_id == tenant.id,
                            SalesGoal.period_start <= today,
                            SalesGoal.period_end >= today,
                            SalesGoal.is_active == True,
                        )
                    )
                )
                goals_map = {g.salesperson_id: g for g in goals_result.scalars().all()}

                # Eliminar snapshots del dia para re-calcular frescos
                await db.execute(
                    delete(DailySalesSnapshot).where(
                        and_(
                            DailySalesSnapshot.tenant_id == tenant.id,
                            DailySalesSnapshot.snapshot_date == today,
                        )
                    )
                )

                snapshots = []
                for sp in salespersons:
                    sp_orders_today = [o for o in today_orders if o.salesperson_id == sp.id]
                    sp_orders_month = [o for o in month_orders if o.salesperson_id == sp.id]
                    sp_visits = [v for v in today_visits]

                    total_amount = sum(o.total_amount for o in sp_orders_today)
                    month_cumulative = sum(o.total_amount for o in sp_orders_month)
                    clients_visited = len(set(v.client_id for v in sp_visits))
                    clients_with_sale = len(set(o.client_id for o in sp_orders_today))
                    effectiveness = (clients_with_sale / clients_visited) if clients_visited > 0 else 0.0

                    goal = goals_map.get(sp.id)
                    monthly_goal = goal.target_amount if goal else None
                    days_in_period = (
                        (goal.period_end - goal.period_start).days + 1
                    ) if goal else 30
                    daily_goal = (monthly_goal / days_in_period) if monthly_goal else None
                    pct_daily = (total_amount / daily_goal * 100) if daily_goal else None
                    pct_monthly = (month_cumulative / monthly_goal * 100) if monthly_goal else None

                    snapshots.append(DailySalesSnapshot(
                        tenant_id=tenant.id,
                        salesperson_id=sp.id,
                        snapshot_date=today,
                        orders_count=len(sp_orders_today),
                        total_amount=total_amount,
                        clients_visited=clients_visited,
                        clients_with_sale=clients_with_sale,
                        effectiveness_rate=effectiveness,
                        month_cumulative_amount=month_cumulative,
                        month_cumulative_orders=len(sp_orders_month),
                        daily_goal_amount=daily_goal,
                        monthly_goal_amount=monthly_goal,
                        pct_daily_goal=pct_daily,
                        pct_monthly_goal=pct_monthly,
                    ))

                db.add_all(snapshots)
                await db.commit()

            logger.info(
                "daily_snapshots_generated",
                tenant_id=str(tenant.id),
                records=len(snapshots),
            )
        except Exception as e:
            logger.error(
                "daily_snapshots_failed",
                tenant_id=str(tenant.id),
                error=str(e),
            )


# ── Indexacion semantica de productos (RAG) ───────────────────────────────────

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.scheduler.tasks.index_product_task",
)
def index_product_task(self, product_id: str) -> None:
    """
    Indexa semanticamente un producto generando su embedding via Voyage AI
    y persistiendo el vector en la columna products.embedding.

    Se dispara automaticamente desde los endpoints POST/PATCH de productos.
    Tambien puede invocarse manualmente para re-indexar un producto especifico.

    Args:
        product_id: UUID del producto como string (JSON-serializable para Celery).

    Comportamiento ante errores:
        - Reintenta hasta 3 veces con delay de 60s entre intentos.
        - Si agota los reintentos, captura la excepcion en Sentry y la re-lanza.
    """
    from uuid import UUID
    from app.core.database import get_sync_session_for_task
    from app.services.embedding_service import index_product

    log = logger.bind(product_id=product_id)
    log.info("index_product_task_started")

    try:
        async def _run():
            async with get_sync_session_for_task() as db:
                await index_product(UUID(product_id), db)

        asyncio.run(_run())
        log.info("index_product_task_completed")

    except Exception as exc:
        log.error("index_product_task_failed", error=str(exc))
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc)
