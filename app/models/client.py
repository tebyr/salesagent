"""
Cliente = Tendero / comercio del canal tradicional.
Cada cliente pertenece a un vendedor y tiene historial de compras.
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Float, Integer, Date, JSON, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Client(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_clients_tenant_external_id"),
    )

    tenant_id      = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"),
                           nullable=False, index=True)
    salesperson_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"),
                           nullable=True, index=True)
    zone_id        = Column(PGUUID(as_uuid=True), ForeignKey("zones.id"),
                           nullable=True, index=True)  # Zona geográfica formal

    # Identificacion del negocio
    business_name = Column(String(200), nullable=False)  # Nombre del negocio
    owner_name = Column(String(200), nullable=True)       # Nombre del tendero/propietario
    nit_cc = Column(String(20), nullable=True)            # NIT o cedula

    # Contacto
    phone = Column(String(20), nullable=False)
    phone_normalized = Column(String(20), nullable=False, index=True)
    email = Column(String(200), nullable=True)

    # Ubicacion
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    zone = Column(String(100), nullable=True)    # Zona de ruta
    neighborhood = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Estado
    is_active = Column(Boolean, default=True, nullable=False)
    whatsapp_opt_in = Column(Boolean, default=False, nullable=False)

    # Patron de compras (para recomendaciones)
    avg_purchase_frequency_days = Column(Integer, nullable=True)  # Compra cada N dias
    last_purchase_date = Column(Date, nullable=True)
    avg_ticket_amount = Column(Float, nullable=True)     # Ticket promedio en COP
    total_purchases_count = Column(Integer, default=0)
    total_purchases_amount = Column(Float, default=0.0)

    # Segmentacion
    segment = Column(String(50), nullable=True)  # A, B, C segun volumen
    channel_type = Column(String(50), default="tradicional")  # tradicional | minimercado | supermercado

    # Integracion ERP
    external_id = Column(String(100), nullable=True, index=True)    # ID en el sistema externo del tenant
    external_source = Column(String(50), nullable=True)              # 'siesa', 'world_office', 'sap', etc.

    # Notas y contexto para el agente
    notes = Column(Text, nullable=True)
    preferred_categories = Column(JSON, default=[])   # Categorias preferidas
    tags = Column(JSON, default=[])

    # Relationships
    tenant = relationship("Tenant", back_populates="clients")
    zone   = relationship("Zone",   back_populates="clients")
    orders = relationship("Order", back_populates="client", lazy="select")
    affinities = relationship("ClientProductAffinity", back_populates="client", lazy="select")

    def __repr__(self):
        return f"<Client {self.business_name} - {self.phone}>"

    @property
    def is_overdue_for_visit(self) -> bool:
        if not self.last_purchase_date or not self.avg_purchase_frequency_days:
            return False
        from datetime import date
        days_since = (date.today() - self.last_purchase_date).days
        return days_since > (self.avg_purchase_frequency_days * 1.2)  # 20% de tolerancia
