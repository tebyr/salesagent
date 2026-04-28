"""
Orquestador: recibe mensajes de WhatsApp y los dirige al sub-agente correcto.
Identifica al remitente (vendedor, tendero, gerente) y mantiene el contexto.
"""
from app.agents.sales_agent import SalesAgent
from app.agents.client_agent import ClientAgent
from app.agents.management_agent import ManagementAgent
from app.models.conversation import ConversationRole, ConversationState
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class AgentOrchestrator:
    """
    Punto de entrada unico para todos los mensajes entrantes de WhatsApp.

    Flujo:
    1. Recibe mensaje + numero de telefono
    2. Identifica el tenant (por numero de WhatsApp destino)
    3. Identifica el rol del remitente (vendedor/cliente/gerente)
    4. Delega al sub-agente correspondiente
    5. Retorna la respuesta
    """

    def __init__(self, tenant_id: str, tenant_config: dict):
        self.tenant_id = tenant_id
        self.tenant_config = tenant_config
        self.sales_agent = SalesAgent(tenant_id, tenant_config)
        self.client_agent = ClientAgent(tenant_id, tenant_config)
        self.management_agent = ManagementAgent(tenant_id, tenant_config)

    async def process_inbound_message(
        self,
        phone: str,
        message_text: str,
        conversation_state: dict,
        user_info: dict,
    ) -> dict:
        """
        Procesa un mensaje entrante y retorna la respuesta.

        Args:
            phone: Numero del remitente normalizado
            message_text: Texto del mensaje
            conversation_state: Estado actual de la conversacion (de Redis/DB)
            user_info: Informacion del usuario (rol, nombre, etc.)

        Returns:
            {
                "response_text": str,        # Mensaje a enviar de vuelta
                "new_state": str,            # Nuevo estado de la conversacion
                "actions": list,             # Acciones a ejecutar (ej: crear pedido)
                "context_update": dict,      # Actualizacion del contexto
            }
        """
        role = user_info.get("role")
        name = user_info.get("name", "Usuario")
        current_state = conversation_state.get("state", ConversationState.IDLE)

        logger.info(
            "processing_inbound_message",
            tenant_id=self.tenant_id,
            phone=phone,
            role=role,
            state=current_state,
            message_preview=message_text[:50],
        )

        try:
            if role in (ConversationRole.SALESPERSON, "salesperson", "supervisor", "admin"):
                return await self._handle_salesperson_message(
                    name, message_text, conversation_state, user_info
                )
            elif role in (ConversationRole.CLIENT, "client"):
                return await self._handle_client_message(
                    name, message_text, conversation_state, user_info
                )
            elif role in (ConversationRole.MANAGER, "manager"):
                return await self._handle_manager_message(
                    name, message_text, conversation_state, user_info
                )
            else:
                return await self._handle_unknown_user(phone, message_text)

        except Exception as e:
            logger.error(
                "orchestrator_error",
                tenant_id=self.tenant_id,
                phone=phone,
                error=str(e),
            )
            return {
                "response_text": (
                    "Lo siento, tuve un problema procesando tu mensaje. "
                    "Por favor intenta de nuevo en un momento. 🙏"
                ),
                "new_state": current_state,
                "actions": [],
                "context_update": {},
            }

    async def _handle_salesperson_message(
        self, name: str, message: str, conversation_state: dict, user_info: dict
    ) -> dict:
        """Maneja mensajes de vendedores."""
        context_data = {
            "Meta mensual": user_info.get("month_goal_pct", "N/A"),
            "Ventas hoy": user_info.get("today_sales", "N/A"),
            "Clientes en ruta hoy": user_info.get("clients_today", "N/A"),
            "Clientes visitados": user_info.get("visited_today", "N/A"),
        }

        history = conversation_state.get("recent_messages", [])

        response_text = await self.sales_agent.respond_to_query(
            salesperson_name=name,
            query=message,
            conversation_history=history,
            context_data=context_data,
        )

        # Actualizar historial
        updated_history = (history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response_text},
        ])[-20:]  # Mantener solo los ultimos 20 mensajes

        return {
            "response_text": response_text,
            "new_state": ConversationState.SALESPERSON_MENU,
            "actions": [],
            "context_update": {"recent_messages": updated_history},
        }

    async def _handle_client_message(
        self, name: str, message: str, conversation_state: dict, user_info: dict
    ) -> dict:
        """Maneja mensajes de tenderos."""
        current_state = conversation_state.get("state", ConversationState.IDLE)
        current_order = conversation_state.get("context", {}).get("current_order")

        context_data = {
            "avg_ticket": user_info.get("avg_ticket", 0),
            "frequent_products": user_info.get("frequent_products", []),
            "available_products": user_info.get("available_products", []),
            "active_promotions": user_info.get("active_promotions", []),
        }

        history = conversation_state.get("recent_messages", [])

        response_text, tool_calls = await self.client_agent.respond_to_client(
            client_name=name,
            message=message,
            conversation_history=history,
            context_data=context_data,
            current_order=current_order,
        )

        # Procesar acciones del agente
        actions = []
        context_update = {}
        new_state = current_state

        for tool_call in tool_calls:
            if tool_call["tool"] == "add_to_order":
                # Agregar item al pedido en progreso
                order = current_order or {"items": [], "total": 0}
                order["items"].append(tool_call["input"])
                order["total"] = sum(
                    i.get("unit_price", 0) * i.get("quantity", 1)
                    for i in order["items"]
                )
                context_update["current_order"] = order
                new_state = ConversationState.TAKING_ORDER

            elif tool_call["tool"] == "confirm_order":
                # Procesar el pedido
                actions.append({
                    "type": "create_order",
                    "client_id": user_info.get("client_id"),
                    "salesperson_id": user_info.get("salesperson_id"),
                    "order_data": current_order,
                })
                context_update["current_order"] = None
                new_state = ConversationState.IDLE

        # Actualizar historial
        updated_history = (history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response_text},
        ])[-20:]
        context_update["recent_messages"] = updated_history

        return {
            "response_text": response_text,
            "new_state": new_state,
            "actions": actions,
            "context_update": context_update,
        }

    async def _handle_manager_message(
        self, name: str, message: str, conversation_state: dict, user_info: dict
    ) -> dict:
        """Maneja mensajes de gerentes."""
        context_data = {
            "Ventas hoy equipo": user_info.get("team_sales_today", "N/A"),
            "% meta mes": user_info.get("team_month_pct", "N/A"),
            "Vendedores activos": user_info.get("active_salespersons", "N/A"),
            "Alertas pendientes": user_info.get("active_alerts_count", 0),
        }

        history = conversation_state.get("recent_messages", [])

        response_text = await self.management_agent.respond_to_query(
            manager_name=name,
            query=message,
            conversation_history=history,
            context_data=context_data,
        )

        updated_history = (history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response_text},
        ])[-20:]

        return {
            "response_text": response_text,
            "new_state": ConversationState.SALESPERSON_MENU,
            "actions": [],
            "context_update": {"recent_messages": updated_history},
        }

    async def _handle_unknown_user(self, phone: str, message: str) -> dict:
        """Responde a numeros no registrados."""
        return {
            "response_text": (
                f"Hola 👋 Soy {self.tenant_config.get('agent_name', 'el Agente Comercial')} "
                f"de {self.tenant_config.get('name', 'nuestra empresa')}.\n\n"
                "Para poder ayudarte, necesitas estar registrado en nuestro sistema. "
                "Contacta a tu asesor comercial para más información."
            ),
            "new_state": ConversationState.IDLE,
            "actions": [],
            "context_update": {},
        }
