"""
Agente de Clientes (Tenderos).

Responsabilidades:
- Enviar notificaciones pre-visita con ofertas relevantes
- Sugerir productos basado en historico de compras
- Tomar pedidos directamente si el vendedor no llega/no cierra venta
- Responder consultas de clientes sobre productos y precios
"""
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.models.analytics import ClientProductAffinity
from app.models.product import Product
from app.services.embedding_service import search_products
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
        client_id: UUID = None,
        db: AsyncSession = None,
    ) -> str:
        """
        Genera el mensaje pre-visita para el tendero.
        Se envia antes de que el vendedor llegue para que el cliente
        este informado y expectante.
        Si se reciben client_id y db, enriquece las recomendaciones con RAG.
        """
        # Enriquecer recomendaciones con búsqueda semántica si hay sesión BD
        if client_id and db:
            rag_recs = await self._build_rag_recommendations(
                client_id=client_id,
                tenant_id=self.tenant_id,
                context_hint="productos para reabastecer negocio",
                db=db,
            )
            # RAG tiene prioridad — va primero; se deduplicaa por nombre
            final_recs = rag_recs + [
                r for r in recommendations
                if r.get("name") not in {p["name"] for p in rag_recs}
            ]
        else:
            final_recs = recommendations

        context = f"""
CLIENTE: {client_name}
VENDEDOR: {salesperson_name}
VISITA ESTIMADA: {visit_time_estimate}

PRODUCTOS RECOMENDADOS BASADO EN SUS COMPRAS:
{self._format_client_recommendations(final_recs)}

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
        client_id: UUID = None,
        db: AsyncSession = None,
    ) -> str:
        """
        Genera mensaje de seguimiento cuando el vendedor no logro visitar al cliente.
        El agente intenta cerrar la venta directamente.
        Si se reciben client_id y db, enriquece las recomendaciones con RAG.
        """
        # Enriquecer recomendaciones con búsqueda semántica si hay sesión BD
        if client_id and db:
            rag_recs = await self._build_rag_recommendations(
                client_id=client_id,
                tenant_id=self.tenant_id,
                context_hint="productos que necesita reponer el negocio",
                db=db,
            )
            final_recs = rag_recs + [
                r for r in recommendations
                if r.get("name") not in {p["name"] for p in rag_recs}
            ]
        else:
            final_recs = recommendations

        context = f"""
CLIENTE: {client_name}
DIAS SIN COMPRA: {days_since_last_purchase}
VENDEDOR ASIGNADO: {salesperson_name}

PRODUCTOS RECOMENDADOS:
{self._format_client_recommendations(final_recs)}

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
        client_id: UUID = None,
        db: AsyncSession = None,
    ) -> tuple[str, list]:
        """
        Responde una consulta del tendero.
        Maneja el flujo de toma de pedidos.
        Si se reciben client_id y db, el mensaje del cliente se usa como hint
        semántico para recuperar productos relevantes via RAG.
        Retorna (mensaje_respuesta, acciones_ejecutadas)
        """
        # Enriquecer available_products con RAG usando el mensaje como hint semántico
        if client_id and db:
            rag_products = await self._build_rag_recommendations(
                client_id=client_id,
                tenant_id=self.tenant_id,
                context_hint=message,   # el mensaje del cliente es el mejor hint
                db=db,
                top_k=10,
            )
            # RAG tiene prioridad; deduplicar por nombre
            all_products = rag_products + [
                p for p in context_data.get("available_products", [])
                if p.get("name") not in {r["name"] for r in rag_products}
            ]
            context_data = {**context_data, "available_products": all_products}

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

        # Extraer texto y tool calls desde respuesta LiteLLM (formato OpenAI)
        text_response, tool_calls = self._extract_content_and_tools(response)
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

    # --- RAG ---

    async def _build_rag_recommendations(
        self,
        client_id: UUID,
        tenant_id: UUID,
        context_hint: str,
        db: AsyncSession,
        top_k: int = 8,
    ) -> list[dict]:
        """
        Recupera productos semánticamente relevantes para el cliente combinando:
        1. Sus top 3 categorías por affinity_score acumulado (historial real).
        2. Una búsqueda semántica con search_products filtrada por la top categoría.

        Nota: ClientProductAffinity no tiene total_net_value — se usa la suma
        de affinity_score como proxy de valor histórico por categoría.

        Graceful degradation: cualquier fallo retorna lista vacía para que
        el agente siga funcionando con los recommendations del caller.
        """
        try:
            # 1. Top 3 categorías del cliente por affinity_score acumulado
            cat_result = await db.execute(
                select(
                    Product.category,
                    func.sum(ClientProductAffinity.affinity_score).label("total_score"),
                )
                .join(Product, ClientProductAffinity.product_id == Product.id)
                .where(
                    ClientProductAffinity.client_id == client_id,
                    ClientProductAffinity.tenant_id == tenant_id,
                )
                .group_by(Product.category)
                .order_by(desc("total_score"))
                .limit(3)
            )
            top_categories = [row.category for row in cat_result.all() if row.category]

            # 2. Construir query semántica
            if top_categories:
                semantic_query = (
                    f"{context_hint}. "
                    f"Cliente compra frecuentemente: {', '.join(top_categories)}"
                )
            else:
                semantic_query = context_hint

            # 3. Búsqueda semántica — filtro estructural por top categoría si existe
            products = await search_products(
                query=semantic_query,
                tenant_id=tenant_id,
                top_k=top_k,
                db=db,
                category=top_categories[0] if top_categories else None,
            )

            if not products:
                return []

            # 4. Convertir Product ORM → dict compatible con _format_client_recommendations
            return [
                {
                    "name": p.name,
                    "price": p.price or 0,
                    "sku": p.sku,
                    "promo_text": None,
                }
                for p in products
            ]

        except Exception as exc:
            logger.warning(
                "rag_recommendations_failed",
                client_id=str(client_id),
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            return []

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
