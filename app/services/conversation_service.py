"""
ConversationService — manejo de estado de conversaciones WhatsApp.

Cada numero de telefono tiene una fila en wa_conversations que persiste
su estado (idle, taking_order, etc.) y el contexto del flujo actual.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.conversation import WhatsAppConversation, ConversationState, ConversationRole
from app.models.user import User
from app.models.client import Client
import structlog

logger = structlog.get_logger()

# Ventana de sesion de conversacion WhatsApp: 24h desde el ultimo mensaje del usuario
WA_WINDOW_HOURS = 24

# Maximo de mensajes recientes a guardar en el contexto (para el agente)
MAX_RECENT_MESSAGES = 10


def _normalize_phone(phone: str) -> str:
    """Normaliza el numero: elimina +, espacios y guiones."""
    return phone.replace("+", "").replace(" ", "").replace("-", "").strip()


class ConversationService:

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def get_or_create_conversation(
        self,
        phone: str,
        tenant_id: str,
    ) -> tuple[WhatsAppConversation | None, dict | None]:
        """
        Busca la conversacion activa para este numero.
        Si no existe, la crea.

        Retorna (conversation, user_info) donde user_info es un dict con:
            {"role": "salesperson"|"client"|"manager", "id": str, "name": str, ...}
        o None si el numero no esta registrado en el sistema.
        """
        phone_norm = _normalize_phone(phone)

        async with AsyncSessionLocal() as db:
            # Buscar conversacion existente
            result = await db.execute(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.tenant_id == tenant_id,
                    WhatsAppConversation.phone_normalized == phone_norm,
                )
            )
            conversation = result.scalar_one_or_none()

            # Identificar quien es este numero: usuario (vendedor/gerente) o cliente
            user_info = await self._identify_contact(db, phone_norm, tenant_id)

            if not user_info:
                return None, None

            now = datetime.now(timezone.utc)

            if not conversation:
                # Primera vez que escribe: crear conversacion
                conversation = WhatsAppConversation(
                    tenant_id=tenant_id,
                    phone_normalized=phone_norm,
                    role=ConversationRole(user_info["role"]),
                    user_id=user_info.get("user_id"),
                    client_id=user_info.get("client_id"),
                    state=ConversationState.IDLE,
                    context={},
                    recent_messages=[],
                    last_message_at=now,
                    wa_window_expires_at=now + timedelta(hours=WA_WINDOW_HOURS),
                    is_window_open=True,
                )
                db.add(conversation)
            else:
                # Actualizar ventana de 24h y timestamp
                conversation.last_message_at = now
                conversation.wa_window_expires_at = now + timedelta(hours=WA_WINDOW_HOURS)
                conversation.is_window_open = True

            await db.commit()
            await db.refresh(conversation)

        return conversation, user_info

    async def update_conversation(
        self,
        phone: str,
        new_state: str | None,
        context_update: dict,
        outbound_message: str | None = None,
        inbound_message: str | None = None,
    ) -> None:
        """
        Actualiza el estado y contexto de la conversacion despues de procesar un mensaje.
        Tambien mantiene el historial reciente de mensajes para el agente.
        """
        phone_norm = _normalize_phone(phone)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.tenant_id == self.tenant_id,
                    WhatsAppConversation.phone_normalized == phone_norm,
                )
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                return

            # Actualizar estado si se especifica uno nuevo
            if new_state and new_state in ConversationState.__members__.values():
                conversation.state = ConversationState(new_state)

            # Merge del contexto (no reemplazar, actualizar keys)
            current_context = dict(conversation.context or {})
            current_context.update(context_update)
            conversation.context = current_context

            # Agregar mensajes al historial reciente
            recent = list(conversation.recent_messages or [])
            now_iso = datetime.now(timezone.utc).isoformat()

            if inbound_message:
                recent.append({"role": "user", "content": inbound_message, "ts": now_iso})
            if outbound_message:
                recent.append({"role": "assistant", "content": outbound_message, "ts": now_iso})

            # Mantener solo los ultimos N mensajes
            conversation.recent_messages = recent[-MAX_RECENT_MESSAGES:]

            if outbound_message:
                conversation.last_outbound_at = datetime.now(timezone.utc)

            await db.commit()

    async def reset_conversation(self, phone: str) -> None:
        """Resetea la conversacion a IDLE (ej: usuario escribe 'salir' o 'cancelar')."""
        phone_norm = _normalize_phone(phone)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.tenant_id == self.tenant_id,
                    WhatsAppConversation.phone_normalized == phone_norm,
                )
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.state = ConversationState.IDLE
                conversation.context = {}
                await db.commit()

    async def get_recent_messages(self, phone: str) -> list[dict]:
        """Retorna el historial reciente de mensajes para pasar al agente."""
        phone_norm = _normalize_phone(phone)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.tenant_id == self.tenant_id,
                    WhatsAppConversation.phone_normalized == phone_norm,
                )
            )
            conv = result.scalar_one_or_none()
            if not conv:
                return []
            # Retornar sin el campo 'ts' que es interno
            return [
                {"role": m["role"], "content": m["content"]}
                for m in (conv.recent_messages or [])
            ]

    # --- Helpers privados ---

    async def _identify_contact(
        self,
        db,
        phone_norm: str,
        tenant_id: str,
    ) -> dict | None:
        """
        Determina si el numero pertenece a un usuario (vendedor/gerente)
        o a un cliente (tendero).

        Retorna dict con informacion del contacto o None si no existe.
        """
        # 1. Buscar en usuarios (vendedores, gerentes, supervisores)
        # Comparar contra phone_normalized (sin +) que es el formato que envia Meta
        user_result = await db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.phone_normalized == phone_norm,
                User.is_active == True,
            )
        )
        user = user_result.scalar_one_or_none()

        if user:
            return {
                "role": user.role.value,   # salesperson | supervisor | manager | admin
                "user_id": str(user.id),
                "client_id": None,
                "name": user.name,
                "phone": user.phone,
                "salesperson_id": str(user.id),  # alias para compatibilidad con agente
            }

        # 2. Buscar en clientes (tenderos)
        # Comparar contra phone_normalized (sin +) que es el formato que envia Meta
        client_result = await db.execute(
            select(Client).where(
                Client.tenant_id == tenant_id,
                Client.phone_normalized == phone_norm,
                Client.is_active == True,
            )
        )
        client = client_result.scalar_one_or_none()

        if client:
            return {
                "role": "client",
                "user_id": None,
                "client_id": str(client.id),
                "name": client.name,
                "phone": client.phone,
                "salesperson_id": str(client.salesperson_id) if client.salesperson_id else None,
            }

        return None
