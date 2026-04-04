"""
Pedidos y sus items. Fuente principal del historial de ventas.
"""
from sqlalchemy import Column, String, ForeignKey, Float, Integer, Date, DateTime, Text, Enum as SAEnum, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"           # Borrador (tomado por agente)
    PENDING = "pending"       # Pendiente confirmacion
    CONFIRMED = "confirmed"   # Confirmado
    DISPATCHED = "dispatched" # Despachado
    DELIVERED = "delivered"   # Entregado
    CANCELLED = "cancelled"   # Cancelado


class OrderSource(str, enum.Enum):
    SALESPERSON = "salesperson"         # Tomado por vendedor en campo
    AGENT_WA = "agent_wa"     # Tomado por el agente via WhatsApp
    ADMIN = "admin"           # Ingresado manualmente en panel


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_orders_tenant_external_id"),
    )

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    salesperson_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    order_number = Column(String(50), nullable=True, index=True)  # Numero en ERP externo
    order_date = Column(Date, nullable=False, index=True)
    delivery_date = Column(Date, nullable=True)

    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    source = Column(SAEnum(OrderSource), default=OrderSource.SALESPERSON, nullable=False)

    # Montos en COP
    subtotal = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0, nullable=False)

    notes = Column(Text, nullable=True)

    # Integracion ERP — bidireccional: nace NULL, el ERP devuelve su referencia al confirmar
    external_id = Column(String(100), nullable=True, index=True)    # ID/numero en el ERP del tenant
    external_source = Column(String(50), nullable=True)              # 'siesa', 'world_office', 'sap', etc.

    client = relationship("Client", back_populates="orders")
    salesperson = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", lazy="select", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_number or self.id} - {self.total_amount}>"


class OrderItem(UUIDMixin, Base):
    __tablename__ = "order_items"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    order_id = Column(PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)

    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
