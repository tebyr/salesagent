"""
Configuracion de notificaciones programadas por tenant.
Permite parametrizar cuando y como se envian los mensajes automaticos.
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, JSON, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import enum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class NotificationEventType(str, enum.Enum):
    # Vendedor
    SALESPERSON_MORNING_BRIEFING = "salesperson_morning_briefing"      # Briefing matutino
    SALESPERSON_DAILY_SUMMARY = "salesperson_daily_summary"            # Resumen del dia
    SALESPERSON_PERFORMANCE_REPORT = "salesperson_performance_report"  # Rendimiento vs meta
    SALESPERSON_ROUTE_REMINDER = "salesperson_route_reminder"          # Recordatorio de visita pendiente

    # Cliente (tendero)
    CLIENT_PRE_VISIT = "client_pre_visit"          # Notificacion pre-visita del vendedor
    CLIENT_PROMOTION = "client_promotion"          # Oferta/promocion activa
    CLIENT_REORDER_REMINDER = "client_reorder_reminder"  # Recordatorio de recompra
    CLIENT_NO_VISIT_FOLLOWUP = "client_no_visit_followup"  # Seguimiento si no hubo visita

    # Gerencia
    MANAGEMENT_DAILY_REPORT = "management_daily_report"
    MANAGEMENT_WEEKLY_REPORT = "management_weekly_report"
    MANAGEMENT_ALERT_LOW_PERFORMANCE = "management_alert_low_performance"
    MANAGEMENT_ALERT_INACTIVE_CLIENT = "management_alert_inactive_client"


class NotificationSchedule(UUIDMixin, TimestampMixin, Base):
    """Configuracion de cuando enviar cada tipo de notificacion."""
    __tablename__ = "notification_schedules"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    event_type = Column(SAEnum(NotificationEventType), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Horario (cron expression o hora simple)
    schedule_time = Column(String(50), nullable=True)  # HH:MM
    schedule_days = Column(JSON, default=[])  # ["monday","tuesday",...] o [] para todos los dias laborales

    # Configuracion especifica del evento (JSON)
    config = Column(JSON, default={})
    # Ejemplos:
    # salesperson_morning_briefing: {"days_before_visit": 0}
    # client_pre_visit: {"hours_before": 2}
    # management_alert_low_performance: {"threshold_pct": 60}

    def __repr__(self):
        return f"<NotificationSchedule {self.event_type} - {self.schedule_time}>"


class NotificationLog(UUIDMixin, Base):
    """Log de notificaciones enviadas para evitar duplicados y para auditoria."""
    __tablename__ = "notification_logs"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    schedule_id = Column(PGUUID(as_uuid=True), ForeignKey("notification_schedules.id"), nullable=True)

    event_type = Column(SAEnum(NotificationEventType), nullable=False, index=True)
    recipient_phone = Column(String(20), nullable=False)
    recipient_type = Column(String(20), nullable=False)  # salesperson | client | manager
    recipient_id = Column(PGUUID(as_uuid=True), nullable=True)

    sent_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False)  # sent | failed | skipped
    error_message = Column(Text, nullable=True)

    # Referencia al dia/periodo de la notificacion
    reference_date = Column(String(10), nullable=True)  # YYYY-MM-DD
