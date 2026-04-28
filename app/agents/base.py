"""
Clase base para todos los sub-agentes del sistema.

Usa LiteLLM como capa de abstracción sobre los LLMs, lo que permite cambiar
de proveedor (Anthropic → OpenAI → Gemini…) modificando solo el nombre del modelo
en config.py o en la llamada, sin tocar el código de los agentes.

Flujo de cada llamada IA:
  1. _call_ai() → llama a litellm.acompletion()
  2. Calcula cost_usd con tarifa del modelo
  3. Lanza _persist_usage() como background task (no bloquea la respuesta)
  4. _persist_usage() inserta en ai_usage_logs y verifica umbrales mensuales
"""
import asyncio
import json
import uuid as uuid_lib
from datetime import datetime, timezone

import litellm
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# ── Configuración LiteLLM ─────────────────────────────────────────────────────
# Silenciar logs verbosos de LiteLLM en desarrollo
litellm.set_verbose = False

# Tarifas por 1M tokens (USD) — actualizar cuando cambien precios
# Fuentes: anthropic.com/pricing · platform.openai.com/pricing · groq.com/pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-haiku-4-5":              {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":             {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":               {"input": 15.00, "output": 75.00},
    # OpenAI
    "gpt-4o-mini":                   {"input": 0.15,  "output": 0.60},
    "gpt-4o":                        {"input": 2.50,  "output": 10.00},
    "o1-mini":                       {"input": 3.00,  "output": 12.00},
    # Google
    "gemini/gemini-pro":             {"input": 0.50,  "output": 1.50},
    "gemini/gemini-flash":           {"input": 0.075, "output": 0.30},
    # Groq — tier de pago (en fase de pruebas puede estar en free tier sin costo)
    "groq/llama-3.1-8b-instant":     {"input": 0.05,  "output": 0.08},
    "groq/llama-3.1-70b-versatile":  {"input": 0.59,  "output": 0.79},
    "groq/llama3-8b-8192":           {"input": 0.05,  "output": 0.08},
    "groq/llama3-70b-8192":          {"input": 0.59,  "output": 0.79},
    "groq/mixtral-8x7b-32768":       {"input": 0.24,  "output": 0.24},
    "groq/gemma2-9b-it":             {"input": 0.20,  "output": 0.20},
}
# Tarifa por defecto si el modelo no está en la tabla
_DEFAULT_PRICING = {"input": 3.00, "output": 15.00}


# ── Utilidades de provider/costo ─────────────────────────────────────────────

def _detect_provider(model: str) -> str:
    """Detecta el proveedor a partir del nombre del modelo."""
    m = model.lower()
    if "claude" in m:
        return "anthropic"
    if "gpt" in m or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if "gemini" in m:
        return "google"
    if m.startswith("groq/"):
        return "groq"
    if "mistral" in m or "mixtral" in m:
        return "mistral"
    if "llama" in m:
        return "meta"
    return "unknown"


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calcula costo en USD usando la tabla de tarifas local."""
    pricing = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    return (
        (input_tokens  / 1_000_000) * pricing["input"] +
        (output_tokens / 1_000_000) * pricing["output"]
    )


def _convert_tools_to_litellm(tools: list) -> list:
    """
    Convierte tools de formato Anthropic a formato OpenAI/LiteLLM.

    Anthropic usa:  {"name": ..., "description": ..., "input_schema": {...}}
    LiteLLM usa:    {"type": "function", "function": {"name": ..., "parameters": {...}}}
    """
    converted = []
    for tool in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", tool.get("parameters", {})),
            },
        })
    return converted


# ── Clase base ────────────────────────────────────────────────────────────────

class BaseAgent:
    """
    Agente base con LiteLLM como proveedor de IA y registro automático de costos.

    Todos los sub-agentes heredan de esta clase y solo necesitan implementar
    get_system_prompt(). El resto del ciclo de vida (llamada, parseo, costos)
    está centralizado aquí.
    """

    def __init__(self, tenant_id: str, tenant_config: dict):
        self.tenant_id    = tenant_id
        self.tenant_config = tenant_config
        self.agent_name   = tenant_config.get("agent_name", "Agente Comercial")

        # Configurar API keys en LiteLLM según los proveedores disponibles
        if settings.anthropic_api_key:
            litellm.anthropic_key = settings.anthropic_api_key
        if settings.openai_api_key:
            litellm.openai_key = settings.openai_api_key
        if settings.groq_api_key:
            # LiteLLM lee GROQ_API_KEY del entorno; asignarlo explícitamente por consistencia
            import os
            os.environ["GROQ_API_KEY"] = settings.groq_api_key

    def get_system_prompt(self) -> str:
        raise NotImplementedError

    async def _call_ai(
        self,
        messages: list,
        model: str = None,
        max_tokens: int = 1024,
        tools: list = None,
        system: str = None,
        triggered_by: str = "unknown",
        conversation_id: str = None,
    ):
        """
        Llama al LLM via LiteLLM con registro automático de costos.

        Args:
            messages:        Historial de mensajes [{"role": ..., "content": ...}]
            model:           Nombre del modelo (ej. "claude-sonnet-4-6", "gpt-4o")
            max_tokens:      Límite de tokens en la respuesta
            tools:           Herramientas en formato Anthropic (se convierten internamente)
            system:          System prompt (si None, usa get_system_prompt())
            triggered_by:    Origen de la llamada para trazabilidad
            conversation_id: ID de la conversación WhatsApp (nullable)

        Returns:
            Objeto de respuesta LiteLLM (formato OpenAI)
        """
        model         = model or settings.ai_model_standard
        system_prompt = system or self.get_system_prompt()

        # System prompt como primer mensaje (compatible con todos los proveedores)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        kwargs: dict = {
            "model":      model,
            "max_tokens": max_tokens,
            "messages":   full_messages,
        }

        if tools:
            kwargs["tools"] = _convert_tools_to_litellm(tools)

        try:
            response = await litellm.acompletion(**kwargs)

            input_tokens  = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost_usd      = _calculate_cost(model, input_tokens, output_tokens)
            provider      = _detect_provider(model)

            logger.info(
                "ai_call_completed",
                tenant_id=self.tenant_id,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost_usd, 6),
                agent=self.__class__.__name__,
                triggered_by=triggered_by,
            )

            # Persistir en BD sin bloquear la respuesta al usuario
            asyncio.create_task(self._persist_usage(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                triggered_by=triggered_by,
                conversation_id=conversation_id,
            ))

            return response

        except Exception as e:
            logger.error(
                "ai_call_failed",
                tenant_id=self.tenant_id,
                model=model,
                error=str(e),
                agent=self.__class__.__name__,
            )
            raise

    async def _persist_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        triggered_by: str,
        conversation_id: str = None,
    ) -> None:
        """
        Persiste el registro de uso en ai_usage_logs y verifica umbrales de costo.

        Se ejecuta como background task — los errores aquí no afectan la respuesta
        al usuario pero se registran en structlog/Sentry.

        Umbrales configurables en .env:
          AI_COST_ALERT_THRESHOLD_USD (default: $50)  → warning en logs
          AI_COST_HARD_LIMIT_USD      (default: $100) → error en logs (no bloquea aún)
        """
        from app.core.database import AsyncSessionLocal
        from app.models.ai_usage import AIUsageLog
        from sqlalchemy import select, func

        try:
            async with AsyncSessionLocal() as db:
                # Insertar el registro de uso
                log = AIUsageLog(
                    tenant_id=uuid_lib.UUID(self.tenant_id),
                    provider=provider,
                    model=model,
                    agent_class=self.__class__.__name__,
                    triggered_by=triggered_by,
                    conversation_id=(
                        uuid_lib.UUID(conversation_id) if conversation_id else None
                    ),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost_usd=cost_usd,
                )
                db.add(log)
                await db.flush()

                # Verificar costo acumulado del mes para este tenant
                now         = datetime.now(timezone.utc)
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                result = await db.execute(
                    select(func.sum(AIUsageLog.cost_usd)).where(
                        AIUsageLog.tenant_id == uuid_lib.UUID(self.tenant_id),
                        AIUsageLog.created_at >= month_start,
                    )
                )
                monthly_cost = float(result.scalar() or 0)

                if monthly_cost >= settings.ai_cost_hard_limit_usd:
                    logger.error(
                        "ai_cost_hard_limit_reached",
                        tenant_id=self.tenant_id,
                        monthly_cost_usd=round(monthly_cost, 4),
                        hard_limit_usd=settings.ai_cost_hard_limit_usd,
                        action="revisar_tenant_y_considerar_suspension",
                    )
                elif monthly_cost >= settings.ai_cost_alert_threshold_usd:
                    logger.warning(
                        "ai_cost_alert",
                        tenant_id=self.tenant_id,
                        monthly_cost_usd=round(monthly_cost, 4),
                        alert_threshold_usd=settings.ai_cost_alert_threshold_usd,
                    )

                await db.commit()

        except Exception as e:
            logger.error(
                "ai_usage_persist_failed",
                error=str(e),
                tenant_id=self.tenant_id,
                model=model,
            )

    # ── Helpers de parseo de respuesta ───────────────────────────────────────

    def _extract_text(self, response) -> str:
        """Extrae el texto de la respuesta LiteLLM (formato OpenAI)."""
        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError):
            return ""

    def _extract_content_and_tools(self, response) -> tuple[str, list]:
        """
        Extrae texto y tool calls de una respuesta LiteLLM.

        Normaliza el formato OpenAI a la estructura interna del sistema:
          tool_calls: [{"tool": str, "input": dict, "id": str}]

        Usado por ClientAgent para procesar toma de pedidos.
        """
        try:
            message    = response.choices[0].message
            text       = message.content or ""
            tool_calls = []

            if message.tool_calls:
                for tc in message.tool_calls:
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, AttributeError):
                        arguments = {}
                    tool_calls.append({
                        "tool":  tc.function.name,
                        "input": arguments,
                        "id":    tc.id,
                    })

            return text, tool_calls

        except (AttributeError, IndexError):
            return "", []

    # ── Formateo de valores ───────────────────────────────────────────────────

    def _format_cop(self, amount: float) -> str:
        """Formatea un monto en pesos colombianos."""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}K"
        return f"${amount:.0f}"

    def _format_pct(self, value: float) -> str:
        """Formatea un porcentaje."""
        return f"{value:.1f}%"
