"""
Metas y cuotas de venta por vendedor y periodo.
Schema disenado para ser flexible: metas diarias, semanales y mensuales.
"""
from sqlalchemy import Column, String, ForeignKey, Float, Integer, Date, Boolean, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class GoalPeriodType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class SalesGoal(UUIDMixin, TimestampMixin, Base):
    """
    Meta de ventas por vendedor y periodo.

    Ejemplo de uso:
    - Meta mensual: period_type=monthly, period_start=2024-03-01, period_end=2024-03-31
    - Meta semanal: period_type=weekly, period_start=2024-03-04, period_end=2024-03-10
    """
    __tablename__ = "sales_goals"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    salesperson_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    period_type = Column(SAEnum(GoalPeriodType, native_enum=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)

    # Metas cuantitativas
    target_amount = Column(Float, nullable=True)         # Meta de ventas en COP
    target_visits = Column(Integer, nullable=True)       # Meta de visitas
    target_effective_visits = Column(Integer, nullable=True)  # Visitas con venta
    target_new_clients = Column(Integer, nullable=True)  # Clientes nuevos
    target_active_clients = Column(Integer, nullable=True)  # Clientes activos (que compraron)
    target_catalog_coverage = Column(Float, nullable=True)  # % del catalogo que se debe vender

    # Metas por categoria de producto (JSON: {categoria: monto_cop})
    target_by_category = Column(JSON, default={})

    # Metas de productos especificos (campanas) (JSON: {product_id: cantidad})
    target_campaigns = Column(JSON, default={})

    # Estado
    is_active = Column(Boolean, default=True)

    # Notas del gerente
    notes = Column(String(500), nullable=True)

    salesperson = relationship("User", back_populates="goals")

    def __repr__(self):
        return f"<SalesGoal {self.period_type} {self.period_start} - {self.target_amount}>"


class GoalProgress(UUIDMixin, Base):
    """
    Snapshot diario del avance de cada vendedor vs su meta.
    Calculado y guardado por el scheduler para consulta rapida.
    """
    __tablename__ = "goal_progress"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    goal_id = Column(PGUUID(as_uuid=True), ForeignKey("sales_goals.id"), nullable=False, index=True)
    salesperson_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)

    # Actual acumulado al dia del snapshot
    actual_amount = Column(Float, default=0.0)
    actual_visits = Column(Integer, default=0)
    actual_effective_visits = Column(Integer, default=0)
    actual_active_clients = Column(Integer, default=0)

    # Porcentajes de cumplimiento
    pct_amount = Column(Float, default=0.0)    # % de la meta de monto
    pct_visits = Column(Float, default=0.0)    # % de la meta de visitas

    # Proyeccion al cierre del periodo (tendencia lineal)
    projected_amount = Column(Float, nullable=True)
    projected_pct = Column(Float, nullable=True)

    # Dias transcurridos y restantes en el periodo
    days_elapsed = Column(Integer, default=0)
    days_remaining = Column(Integer, default=0)

    goal = relationship("SalesGoal")
