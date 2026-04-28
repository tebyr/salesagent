"""
Registro de uso de modelos de IA y costos asociados.

Cada llamada a un LLM genera un registro en esta tabla para:
  - Control de costos por tenant (alertas y hard limits)
  - Facturación basada en consumo (SaaS)
  - Análisis de eficiencia por agente y modelo
  - Auditoría de interacciones IA

El modelo es provider-agnostic: funciona con Anthropic, OpenAI, Google o cualquier
proveedor soportado por LiteLLM.
"""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class AIUsageLog(UUIDMixin, TimestampMixin, Base):
    """
    Registro inmutable de cada llamada a un modelo de IA.

    Campos de costo:
      - input_tokens / output_tokens: tokens consumidos
      - total_tokens: suma de ambos (desnormalizado para queries rápidas)
      - cost_usd: costo calculado al momento de la llamada según tarifa del modelo

    Indexado por (tenant_id, created_at) para consultas de costo mensual eficientes.
    """
    __tablename__ = "ai_usage_logs"

    # Tenant dueño de la llamada
    tenant_id       = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"),
                             nullable=False, index=True)

    # Proveedor y modelo
    # provider: anthropic | openai | google | mistral | unknown
    provider        = Column(String(20),  nullable=False)
    # model: claude-sonnet-4-6 | gpt-4o | gemini/gemini-pro | ...
    model           = Column(String(100), nullable=False)

    # Quién generó la llamada
    # agent_class: SalesAgent | ClientAgent | ManagementAgent
    agent_class     = Column(String(50),  nullable=False)
    # triggered_by: inbound_message | scheduler_briefing | scheduler_summary |
    #               scheduler_report | scheduler_followup | scheduler_alert | unknown
    triggered_by    = Column(String(100), nullable=True)

    # Conversación de origen (cuando aplica — llamadas del scheduler son nullable)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("wa_conversations.id"),
                             nullable=True, index=True)

    # Tokens y costo
    input_tokens    = Column(Integer,        nullable=False, default=0)
    output_tokens   = Column(Integer,        nullable=False, default=0)
    total_tokens    = Column(Integer,        nullable=False, default=0)
    # Precision 10,6 soporta hasta $9,999.999999 por llamada
    cost_usd        = Column(Numeric(10, 6), nullable=False, default=0)

    def __repr__(self):
        return (
            f"<AIUsageLog {self.provider}/{self.model} "
            f"tokens={self.total_tokens} cost=${self.cost_usd}>"
        )
