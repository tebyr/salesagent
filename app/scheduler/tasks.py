"""
Tareas programadas con Celery.
Estas son las tareas proactivas del agente: briefings, reportes, etc.
"""
import asyncio
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
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
                access_token=tenant.whatsapp_access_token,
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
                access_token=tenant.whatsapp_access_token,
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
    """Placeholder - implementacion similar a morning briefings."""
    logger.info("sending_salesperson_daily_summaries")


async def _send_salesperson_performance_reports():
    """Placeholder - implementacion similar a morning briefings."""
    logger.info("sending_salesperson_performance_reports")


async def _send_no_visit_followups():
    """Placeholder - agente contacta clientes no visitados."""
    logger.info("sending_no_visit_followups")


async def _send_management_daily_reports():
    """Placeholder - reporte diario a gerencia por email."""
    logger.info("sending_management_daily_reports")


async def _send_management_weekly_reports():
    """Placeholder - reporte semanal a gerencia por email."""
    logger.info("sending_management_weekly_reports")


async def _check_and_send_performance_alerts():
    """Placeholder - alertas de bajo rendimiento."""
    logger.info("checking_performance_alerts")


async def _calculate_product_affinities():
    """Placeholder - calculo de afinidades."""
    logger.info("calculating_product_affinities")


async def _generate_daily_sales_snapshots():
    """Placeholder - snapshots diarios."""
    logger.info("generating_daily_snapshots")


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
