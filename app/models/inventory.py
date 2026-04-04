"""
Inventario disponible en bodega por producto y tenant.
"""
from sqlalchemy import Column, ForeignKey, Float, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Inventory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True, unique=True)

    quantity_available = Column(Float, default=0.0, nullable=False)
    quantity_reserved = Column(Float, default=0.0, nullable=False)  # Pedidos pendientes
    quantity_minimum = Column(Float, default=0.0)   # Stock minimo de alerta

    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory")

    @property
    def quantity_real_available(self) -> float:
        return max(0.0, self.quantity_available - self.quantity_reserved)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_real_available <= self.quantity_minimum
