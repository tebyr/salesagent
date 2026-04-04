"""
Agente de Clientes (Tenderos).

Responsabilidades:
- Enviar notificaciones pre-visita con ofertas relevantes
- Sugerir productos basado en historico de compras
- Tomar pedidos directamente si el vendedor no llega/no cierra venta
- Responder consultas de clientes sobre productos y precios
"""
from app.agents.base import BaseAgent
from app.core.config import settings
import structlog
import json

logger = structlog.get_logger()


CLIENT_SYSTEM_PROMPT = """Eres {agent_name}, asesor comercial virtual de {company_name}.

Tu rol es atender a los tenderos y comercios del canal tradicional en Colombia.

PERSONALIDAD:
- Amable, servicial y conocedor del negocio del tendero
- Hablas en espanol colombiano natural y cercano
- Eres proactivo ofreciendo lo que el tendero realmente necesita
- Respetas el tiempo del tendero (mensajes cortos y directos)

CAPACIDADES:
1. Informar sobre ofertas y promociones vigentes
2. Recomendar productos basado en su historial de compras
3. Tomar pedidos y confirmarlos al vendedor asignado
4. Responder preguntas sobre productos, precios y disponibilidad
5. Notificar cuando el vendedor viene en camino

REGLAS CRITICAS:
- NUNCA des informacion de otros clientes
- Siempre confirma los pedidos antes de procesarlos
- Si no tienes la informacion, di que verificas con el equipo
- Los pedidos tomados por ti deben pasar al vendedor asignado
- Usa un tono amigable pero profesional
"""

ORDER_TAKING_TOOLS = [
    {
        "name": "get_product_info",
        "description": "Obtiene informacion de un producto: precio, disponibilidad, descripcion",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_query": {
                    "type": "string",
                    "description": "Nombre o codigo del producto a buscar"
                }
            },
            "required": ["product_query"]
        }
    },
    {
        "name": "add_to_order",
        "description": "Agrega un producto al pedido actual del cliente",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "ID del producto"},
                "product_name": {"type": "string", "description": "Nombre del producto"},
                "quantity": {"type": "number", "description": "Cantidad a pedir"},
                "unit_price": {"type": "number", "description": "Precio unitario en COP"}
            },
            "required": ["product_id", "product_name", "quantity", "unit_price"]
        }
    },
    {
        "name": "confirm_order",
        "description": "Confirma y finaliza el pedido del cliente",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_summary": {
                    "type": "string",
                    "description": "Resumen del pedido para confirmar con el cliente"
                }
            },
            "required": ["order_summary"]
        }
    }
]


class ClientAgent(BaseAgent):

    def get_system_prompt(self) -> str:
        return CLIENT_SYSTEM_PROMPT.format(
            agent_name=self.agent_name,
            company_name=self.tenant_config.get("name", "nuestra empresa"),
        )

    async def generate_pre_visit_notification(
        self,
        client_name: str,
        salesperson_name: str,
        visit_time_estimate: str,
        recommendations: list,
        active_promotions: list,
    ) -> str:
        """
        Genera el mensaje pre-visita para el tendero.
        Se envia antes de que el vendedor llegue para que el cliente
        este informado y expectante.
        """
        context = f"""
CLIENTE: {client_name}
VENDEDOR: {salesperson_name}
VISITA ESTIMADA: {visit_time_estimate}

PRODUCTOS RECOMENDADOS BASADO EN SUS COMPRAS:
{self._format_client_recommendations(recommendations)}

OFERTAS ESPECIALES DE HOY:
{self._format_promotions_for_client(active_promotions)}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Genera un mensaje de WhatsApp para notificar a {client_name}
que su vendedor {salesperson_name} lo visitara hoy.

El mensaje debe:
1. Informar que el vendedor viene hoy ({visit_time_estimate})
2. Mostrar 2-3 productos recomendados especificamente para su negocio
3. Mencionar las mejores ofertas disponibles
4. Invitarlo a preparar su pedido

Tono: amigable y cercano. Maximo 200 palabras.
Usa emojis con moderacion (max 3-4).

{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_simple,
            max_tokens=400,
        )
        return self._extract_text(response)

    async def generate_no_visit_followup(
        self,
        client_name: str,
        salesperson_name: str,
        days_since_last_purchase: int,
        recommendations: list,
        active_promotions: list,
    ) -> str:
        """
        Genera mensaje de seguimiento cuando el vendedor no logro visitar al cliente.
        El agente intenta cerrar la venta directamente.
        """
        context = f"""
CLIENTE: {client_name}
DIAS SIN COMPRA: {days_since_last_purchase}
VENDEDOR ASIGNADO: {salesperson_name}

PRODUCTOS RECOMENDADOS:
{self._format_client_recommendations(recommendations)}

OFERTAS VIGENTES:
{self._format_promotions_for_client(active_promotions)}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Genera un mensaje de WhatsApp para contactar a {client_name}.
Su vendedor no pudo visitarlo hoy. Llevamos {days_since_last_purchase} dias sin pedido.

El mensaje debe:
1. Saludar y mencionar que su vendedor quiso visitarlos hoy
2. Ofrecer tomar el pedido directamente por WhatsApp
3. Mostrar 2-3 productos atractivos con sus ofertas
4. Indicar que es facil: solo responde con lo que necesitas

Tono: amigable y sin presion. Maximo 180 palabras.

{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_simple,
            max_tokens=350,
        )
        return self._extract_text(response)

    async def respond_to_client(
        self,
        client_name: str,
        message: str,
        conversation_history: list,
        context_data: dict,
        current_order: dict = None,
    ) -> tuple[str, list]:
        """
        Responde una consulta del tendero.
        Maneja el flujo de toma de pedidos.
        Retorna (mensaje_respuesta, acciones_ejecutadas)
        """
        system_with_context = self.get_system_prompt() + f"""

CONTEXTO DEL CLIENTE {client_name}:
- Ticket promedio: {self._format_cop(context_data.get('avg_ticket', 0))}
- Productos frecuentes: {', '.join(context_data.get('frequent_products', [])[:5])}
- Pedido actual en progreso: {json.dumps(current_order) if current_order else 'Ninguno'}

PRODUCTOS DISPONIBLES PARA RECOMENDAR:
{self._format_available_products(context_data.get('available_products', []))}

OFERTAS ACTIVAS:
{self._format_promotions_for_client(context_data.get('active_promotions', []))}
"""
        messages = conversation_history + [
            {"role": "user", "content": message}
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_standard,
            max_tokens=500,
            tools=ORDER_TAKING_TOOLS,
            system=system_with_context,
        )

        # Procesar tool calls si las hay
        tool_calls = []
        text_response = ""

        for block in response.content:
            if block.type == "text":
                text_response += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "tool": block.name,
                    "input": block.input,
                    "id": block.id,
                })

        return text_response, tool_calls

    async def generate_order_confirmation(
        self,
        client_name: str,
        order_items: list,
        total_amount: float,
        salesperson_name: str,
    ) -> str:
        """Genera el mensaje de confirmacion del pedido."""
        items_text = "\n".join([
            f"- {item.get('name')} x{item.get('quantity')} = {self._format_cop(item.get('total', 0))}"
            for item in order_items
        ])

        messages = [
            {
                "role": "user",
                "content": f"""Genera un mensaje de confirmacion de pedido para {client_name}.

PEDIDO:
{items_text}
TOTAL: {self._format_cop(total_amount)}

El mensaje debe:
1. Confirmar el pedido con el resumen
2. Indicar que {salesperson_name} coordinara la entrega
3. Dar las gracias

Conciso y amigable. Maximo 100 palabras."""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_simple,
            max_tokens=200,
        )
        return self._extract_text(response)

    async def generate_promotion_broadcast(
        self,
        client_name: str,
        client_segment: str,
        promotions: list,
        personalized_recommendations: list,
    ) -> str:
        """Genera mensaje de difusion de oferta/promocion personalizado para el cliente."""
        context = f"""
CLIENTE: {client_name}
SEGMENTO: {client_segment}

PROMOCIONES RELEVANTES PARA ESTE CLIENTE:
{self._format_promotions_for_client(promotions)}

PRODUCTOS QUE LE INTERESARIAN BASADO EN SU HISTORIAL:
{self._format_client_recommendations(personalized_recommendations)}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Genera un mensaje de WhatsApp con las mejores ofertas para {client_name}.

El mensaje debe sentirse PERSONALIZADO (no generico).
Muestra 2-3 ofertas mas relevantes para ESTE cliente especifico.
Incluye un llamado a la accion claro.
Maximo 150 palabras.

{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_simple,
            max_tokens=300,
        )
        return self._extract_text(response)

    # --- Helpers ---

    def _format_client_recommendations(self, recs: list) -> str:
        if not recs:
            return "- Sin recomendaciones disponibles"
        lines = []
        for r in recs[:4]:
            price = self._format_cop(r.get('price', 0))
            promo = f" 🔥 {r.get('promo_text', '')}" if r.get('promo_text') else ""
            lines.append(f"- {r.get('name')} - {price}{promo}")
        return "\n".join(lines)

    def _format_promotions_for_client(self, promos: list) -> str:
        if not promos:
            return "- Sin ofertas especiales hoy"
        lines = []
        for p in promos[:3]:
            lines.append(f"- {p.get('title')}: {p.get('description', '')} (hasta {p.get('end_date', '')})")
        return "\n".join(lines)

    def _format_available_products(self, products: list) -> str:
        if not products:
            return "- Sin productos disponibles"
        lines = []
        for p in products[:10]:
            lines.append(f"- {p.get('name')} ({p.get('sku', '')}) - {self._format_cop(p.get('price', 0))}")
        return "\n".join(lines)
