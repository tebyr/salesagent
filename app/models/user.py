"""
Usuarios del sistema: vendedores, gerentes y admins.
Todos pertenecen a un tenant (empresa distribuidora).
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"              # Admin del SaaS (nosotros)
    MANAGER = "manager"          # Gerente comercial del tenant
    SUPERVISOR = "supervisor"    # Supervisor de zona
    SALESPERSON = "salesperson"  # Vendedor de campo
    AGENT = "agent"              # Vendedor virtual IA — se asigna a rutas agent_wa


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_users_tenant_external_id"),
    )

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Datos personales
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=False)  # Con codigo de pais: +573001234567
    phone_normalized = Column(String(20), nullable=False, index=True)  # Solo digitos

    # Acceso
    role = Column(SAEnum(UserRole, native_enum=False), nullable=False, default=UserRole.SALESPERSON)
    is_active = Column(Boolean, default=True, nullable=False)
    password_hash = Column(String(200), nullable=True)  # Para acceso al panel admin

    # WhatsApp
    whatsapp_opt_in = Column(Boolean, default=False, nullable=False)  # Acepto recibir mensajes

    # Zona/region asignada (para supervisores y gerentes)
    zone = Column(String(100), nullable=True)

    # Integracion ERP
    external_id = Column(String(100), nullable=True, index=True)    # ID en el sistema externo del tenant
    external_source = Column(String(50), nullable=True)              # 'siesa', 'world_office', 'sap', etc.

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    routes = relationship("Route", back_populates="salesperson", lazy="select")
    orders = relationship("Order", back_populates="salesperson", lazy="select")
    goals = relationship("SalesGoal", back_populates="salesperson", lazy="select")

    def __repr__(self):
        return f"<User {self.name} ({self.role}) - {self.phone}>"
