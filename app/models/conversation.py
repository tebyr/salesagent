"""
Estado de conversaciones WhatsApp.
Cada numero de telefono tiene un estado de conversacion activo.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON, Text, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import enum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ConversationRole(str, enum.Enum):
    SALESPERSON = "salesperson"
    CLIENT = "client"
    MANAGER = "manager"


class ConversationState(str, enum.Enum):
    IDLE = "idle"                     # Sin conversacion activa
    GREETING = "greeting"             # Saludo inicial
    SALESPERSON_MENU = "salesperson_menu"       # Menu principal vendedor
    CLIENT_MENU = "client_menu"       # Menu principal cliente
    TAKING_ORDER = "taking_order"     # Tomando pedido (agente con cliente)
    CONFIRMING_ORDER = "confirming_order"  # Confirmando pedido
    AWAITING_RESPONSE = "awaiting_response"  # Esperando respuesta del usuario
    CLOSED = "closed"                 # Conversacion cerrada


class WhatsAppConversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "wa_conversations"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identificacion del participante
    phone_normalized = Column(String(20), nullable=False, index=True)
    role = Column(SAEnum(ConversationRole, native_enum=False), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), nullable=True)    # Si es vendedor o gerente
    client_id = Column(PGUUID(as_uuid=True), nullable=True)  # Si es tendero

    # Estado de la conversacion
    state = Column(SAEnum(ConversationState, native_enum=False), default=ConversationState.IDLE, nullable=False)

    # Contexto (JSON con datos del flujo actual)
    context = Column(JSON, default={})

    # Historial reciente para el agente (ultimos N mensajes)
    recent_messages = Column(JSON, default=[])

    # Timestamps de actividad
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_outbound_at = Column(DateTime(timezone=True), nullable=True)

    # WhatsApp conversation window (24h desde ultimo mensaje del usuario)
    wa_window_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_window_open = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Conversation {self.phone_normalized} ({self.role}) - {self.state}>"


class MessageLog(UUIDMixin, Base):
    """Log de todos los mensajes enviados y recibidos."""
    __tablename__ = "message_logs"

    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("wa_conversations.id"), nullable=True)

    wa_message_id = Column(String(100), nullable=True, index=True)  # ID de Meta
    direction = Column(String(10), nullable=False)  # inbound | outbound
    phone = Column(String(20), nullable=False)
    message_type = Column(String(50), nullable=False)  # text | template | interactive | image
    content = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)  # sent | delivered | read | failed

    # Si fue enviado por el agente o por el scheduler
    triggered_by = Column(String(100), nullable=True)
    ai_model_used  = Column(String(50), nullable=True)
    ai_tokens_used = Column(Integer,    nullable=True)   # total tokens (input+output)
