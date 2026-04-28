"""
Zonas, rutas y visitas de la fuerza de ventas.

Jerarquía:
  Zone  → agrupa clientes geográficamente
  Route → ejecución periódica sobre una zona (presencial o por el agente IA)
  RouteVisit → cada contacto individual con un cliente dentro de una ruta
"""
from sqlalchemy import (Column, String, ForeignKey, Date, Integer, Text,
                        DateTime, Boolean, Enum as SAEnum, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class RouteType(str, enum.Enum):
    PRESENTIAL = "presential"   # Visita física del vendedor
    AGENT_WA   = "agent_wa"     # Contacto proactivo del agente IA por WhatsApp


class RouteStatus(str, enum.Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"


class VisitType(str, enum.Enum):
    PRESENTIAL = "presential"   # Visita física
    AGENT_WA   = "agent_wa"     # Contacto WA iniciado por el agente


class VisitStatus(str, enum.Enum):
    PENDING          = "pending"           # Por visitar / contactar
    VISITED_SALE     = "visited_sale"      # Contacto con venta
    VISITED_NO_SALE  = "visited_no_sale"   # Contacto sin venta
    NOT_VISITED      = "not_visited"       # No se pudo contactar
    ESCALATED        = "escalated"         # Agente escaló al vendedor presencial


# ── Zone ─────────────────────────────────────────────────────────────────────

class Zone(UUIDMixin, TimestampMixin, Base):
    """
    Agrupación geográfica de clientes.
    Una zona puede tener múltiples rutas activas (distintos días o distintos
    tipos: presencial + agent_wa), lo que permite la alta frecuencia de visita.
    """
    __tablename__ = "zones"

    tenant_id   = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"),
                         nullable=False, index=True)
    name        = Column(String(200), nullable=False)   # "Zona Norte Magangué"
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)

    routes  = relationship("Route",  back_populates="zone",    lazy="select")
    clients = relationship("Client", back_populates="zone",    lazy="select")

    def __repr__(self):
        return f"<Zone {self.name}>"


# ── Route ─────────────────────────────────────────────────────────────────────

class Route(UUIDMixin, TimestampMixin, Base):
    """
    Ruta comercial: define quién visita qué zona, en qué días, con qué
    horario y de qué forma (presencial o agente IA).

    Una zona puede tener N rutas activas simultáneas:
      • Ruta Zona Norte - Lunes       → presential  → Manuel Iglesias
      • Ruta Zona Norte - Miércoles   → agent_wa    → Agente IA
    """
    __tablename__ = "routes"

    tenant_id      = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"),
                            nullable=False, index=True)
    zone_id        = Column(PGUUID(as_uuid=True), ForeignKey("zones.id"),
                            nullable=True, index=True)
    salesperson_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"),
                            nullable=False, index=True)

    name           = Column(String(200), nullable=True)
    route_type     = Column(SAEnum(RouteType, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
                            default=RouteType.PRESENTIAL, nullable=False)

    # Días operativos (ISO: 1=Lun … 6=Sáb) almacenados como JSONB array
    # Ej: [1, 3, 5] → Lun, Mié, Vie
    operating_days = Column(JSONB, nullable=True)
    delivery_days  = Column(JSONB, nullable=True)

    # Horarios variables por día de la semana
    # {"1": {"start":"07:30","end":"16:00","cutoff":"15:30"}, "6": {...}}
    daily_schedule = Column(JSONB, nullable=True)

    status         = Column(SAEnum(RouteStatus, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
                            default=RouteStatus.PENDING, nullable=False)
    is_active      = Column(Boolean, default=True, nullable=False)
    notes          = Column(Text, nullable=True)

    # Métricas acumuladas de la ruta (desnormalizadas para dashboard rápido)
    total_clients       = Column(Integer, default=0)
    visited_count       = Column(Integer, default=0)
    sales_count         = Column(Integer, default=0)
    total_sales_amount  = Column(String(50), default="0")

    zone        = relationship("Zone", back_populates="routes")
    salesperson = relationship("User", back_populates="routes")
    visits      = relationship("RouteVisit", back_populates="route",
                               order_by="RouteVisit.visit_order", lazy="select")

    def __repr__(self):
        return f"<Route {self.name} [{self.route_type}]>"


# ── RouteVisit ────────────────────────────────────────────────────────────────

class RouteVisit(UUIDMixin, TimestampMixin, Base):
    """
    Registro de cada contacto (presencial o WA) con un cliente dentro de una ruta.

    Para rutas agent_wa:
      - pre_visit_notification_sent_at registra cuándo el agente envió el mensaje
      - visited_at registra cuándo el cliente respondió (o cuándo se cerró la ventana)
      - Si el cliente no responde → status=ESCALATED y se notifica al vendedor presencial

    Para rutas presential:
      - El vendedor registra el resultado al final de la visita
    """
    __tablename__ = "route_visits"

    tenant_id  = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"),
                        nullable=False, index=True)
    route_id   = Column(PGUUID(as_uuid=True), ForeignKey("routes.id"),
                        nullable=False, index=True)
    client_id  = Column(PGUUID(as_uuid=True), ForeignKey("clients.id"),
                        nullable=False, index=True)

    visit_order = Column(Integer, nullable=False, default=0)
    visit_type  = Column(SAEnum(VisitType, native_enum=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False,
                         default=VisitType.PRESENTIAL)
    status      = Column(SAEnum(VisitStatus, native_enum=False, values_callable=lambda obj: [e.value for e in obj]), default=VisitStatus.PENDING,
                         nullable=False)

    # Notificación pre-visita / mensaje inicial del agente
    pre_visit_notification_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Momento del contacto efectivo
    visited_at = Column(DateTime(timezone=True), nullable=True)
    notes      = Column(Text, nullable=True)

    # Escalación: cuando el agente no logra respuesta, escala al vendedor humano
    escalated_to_salesperson_id = Column(PGUUID(as_uuid=True),
                                         ForeignKey("users.id"), nullable=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)

    route      = relationship("Route",  back_populates="visits")
    client     = relationship("Client")
    escalated_to = relationship("User",
                                foreign_keys=[escalated_to_salesperson_id])

    def __repr__(self):
        return f"<RouteVisit {self.client_id} [{self.visit_type}] - {self.status}>"
