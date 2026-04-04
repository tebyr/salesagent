"""
Modelos de analytics: afinidad cliente-producto y snapshots de ventas.
Calculados periodicamente por el scheduler.
"""
from sqlalchemy import Column, ForeignKey, Float, Integer, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin


class ClientProductAffinity(UUIDMixin, Base):
    """
    Score de afinidad entre un cliente y un producto.
    Calculado con base en historial de compras, frecuencia y recencia.
    Score de 0 a 1 donde 1 = muy alta probabilidad de compra.
    """
    __tablename__ = "client_product_affinities"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)

    # Score de afinidad (0-1)
    affinity_score = Column(Float, nullable=False, default=0.0)

    # Componentes del score
    purchase_frequency = Column(Float, default=0.0)   # Cuantas veces ha comprado
    recency_score = Column(Float, default=0.0)         # Que tan reciente fue la ultima compra
    amount_score = Column(Float, default=0.0)          # Monto relativo vs promedio

    # Estadisticas
    total_purchases = Column(Integer, default=0)
    last_purchase_date = Column(Date, nullable=True)
    avg_quantity_per_order = Column(Float, nullable=True)

    last_calculated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="affinities")
    product = relationship("Product")


class DailySalesSnapshot(UUIDMixin, Base):
    """
    Snapshot diario de ventas por vendedor.
    Pre-calculado para consultas rapidas en reportes y notificaciones.
    """
    __tablename__ = "daily_sales_snapshots"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    salesperson_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)

    # Ventas del dia
    orders_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    clients_visited = Column(Integer, default=0)
    clients_with_sale = Column(Integer, default=0)
    effectiveness_rate = Column(Float, default=0.0)  # clients_with_sale / clients_visited

    # Acumulado del mes hasta esta fecha
    month_cumulative_amount = Column(Float, default=0.0)
    month_cumulative_orders = Column(Integer, default=0)

    # vs Meta
    daily_goal_amount = Column(Float, nullable=True)
    monthly_goal_amount = Column(Float, nullable=True)
    pct_daily_goal = Column(Float, nullable=True)
    pct_monthly_goal = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
