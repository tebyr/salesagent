"""
Clase base para todos los sub-agentes del sistema.
Define la interfaz comun y utilitarios compartidos.
"""
from anthropic import AsyncAnthropic
from app.core.config import settings
import structlog

logger = structlog.get_logger()

client = AsyncAnthropic(api_key=settings.anthropic_api_key)


class BaseAgent:
    """Agente base con acceso al cliente de Anthropic y logica comun."""

    def __init__(self, tenant_id: str, tenant_config: dict):
        self.tenant_id = tenant_id
        self.tenant_config = tenant_config
        self.agent_name = tenant_config.get("agent_name", "Agente Comercial")
        self.client = client

    def get_system_prompt(self) -> str:
        raise NotImplementedError

    async def _call_ai(
        self,
        messages: list,
        model: str = None,
        max_tokens: int = 1024,
        tools: list = None,
        system: str = None,
    ) -> dict:
        """Llama a la API de Claude con manejo de errores y logging de costos."""
        model = model or settings.ai_model_standard
        system_prompt = system or self.get_system_prompt()

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        try:
            response = await self.client.messages.create(**kwargs)

            # Log de uso de tokens para control de costos
            logger.info(
                "ai_call_completed",
                tenant_id=self.tenant_id,
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                agent=self.__class__.__name__,
            )

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

    def _extract_text(self, response) -> str:
        """Extrae el texto de la respuesta del modelo."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""

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
