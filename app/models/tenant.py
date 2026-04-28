"""
Tenant = Empresa distribuidora cliente del SaaS.
Cada tenant tiene su propio numero de WhatsApp, branding y configuracion.
"""
from sqlalchemy import Column, String, Boolean, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    # Identificacion
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)  # identificador URL-friendly
    nit = Column(String(20), nullable=True)  # NIT empresa
    is_active = Column(Boolean, default=True, nullable=False)

    # WhatsApp Business (cada tenant tiene su numero propio)
    whatsapp_phone_number_id = Column(String(50), nullable=True)   # ID del numero en Meta
    whatsapp_business_account_id = Column(String(50), nullable=True)
    whatsapp_access_token = Column(Text, nullable=True)  # Token de acceso encriptado
    whatsapp_phone_display = Column(String(20), nullable=True)  # Numero a mostrar

    # Nombre del agente (personalizable por tenant)
    agent_name = Column(String(100), default="Agente Comercial", nullable=False)
    agent_personality = Column(Text, nullable=True)  # Instrucciones de personalidad

    # Branding para emails
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#2563EB", nullable=False)  # hex color
    email_footer = Column(Text, nullable=True)

    # Configuracion de horarios (parametrizable)
    schedule_config = Column(JSON, default={
        "morning_briefing": "06:30",      # Hora briefing matutino vendedores
        "pre_visit_start": "08:00",       # Inicio notificaciones pre-visita clientes
        "pre_visit_end": "17:00",         # Fin notificaciones pre-visita
        "daily_summary": "18:30",         # Resumen diario vendedores
        "performance_report": "20:00",    # Reporte rendimiento + proyeccion
        "management_report_day": "monday", # Dia reporte gerencial
        "management_report_time": "07:00", # Hora reporte gerencial
        "timezone": "America/Bogota",
        "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
    })

    # Configuracion de email para gerencia
    email_config = Column(JSON, default={
        "management_emails": [],  # Lista de emails gerenciales
        "from_name": None,        # Si None, usa agent_name
    })

    # Plan SaaS
    plan = Column(String(50), default="starter", nullable=False)  # starter | professional | enterprise
    max_salespersons = Column(Integer, default=50)

    # Relationships
    users = relationship("User", back_populates="tenant", lazy="select")
    clients = relationship("Client", back_populates="tenant", lazy="select")
    products = relationship("Product", back_populates="tenant", lazy="select")

    def __repr__(self):
        return f"<Tenant {self.name} ({self.slug})>"
