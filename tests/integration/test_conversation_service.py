"""
Tests de integración para ConversationService.

Cubre:
  1. get_or_create crea conversación nueva para cliente conocido
  2. get_or_create retorna (None, None) para número desconocido
  3. get_or_create reutiliza conversación existente (no duplica filas)
  4. update_conversation persiste nuevo estado e historial en BD
  5. update_conversation hace merge de contexto (no sobreescribe keys previas)
  6. reset_conversation deja estado IDLE y contexto vacío
  7. get_recent_messages respeta el límite MAX_RECENT_MESSAGES (10)

Todos los tests usan BD real (PostgreSQL) vía fixture db_session + patch_db.
"""
import pytest
from sqlalchemy import select

from app.models.conversation import WhatsAppConversation, ConversationState, ConversationRole
from app.services.conversation_service import ConversationService, MAX_RECENT_MESSAGES

pytestmark = pytest.mark.integration


class TestGetOrCreate:

    @pytest.mark.asyncio
    async def test_crea_conversacion_para_cliente_conocido(
        self, client_db, tenant_db, patch_db
    ):
        """get_or_create crea una fila nueva en wa_conversations para un cliente registrado."""
        svc = ConversationService(tenant_id=str(tenant_db.id))
        conv, user_info = await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )

        assert conv is not None
        assert user_info is not None
        assert user_info["role"] == "client"
        assert user_info["client_id"] == str(client_db.id)
        assert conv.role == ConversationRole.CLIENT
        assert conv.state == ConversationState.IDLE
        assert conv.is_window_open is True

    @pytest.mark.asyncio
    async def test_crea_conversacion_para_vendedor_conocido(
        self, salesperson_db, tenant_db, patch_db
    ):
        """get_or_create identifica correctamente a un vendedor por su phone."""
        svc = ConversationService(tenant_id=str(tenant_db.id))
        conv, user_info = await svc.get_or_create_conversation(
            phone=salesperson_db.phone,
            tenant_id=str(tenant_db.id),
        )

        assert conv is not None
        assert user_info is not None
        assert user_info["role"] == "salesperson"
        assert user_info["user_id"] == str(salesperson_db.id)

    @pytest.mark.asyncio
    async def test_retorna_none_para_numero_desconocido(
        self, tenant_db, patch_db
    ):
        """get_or_create retorna (None, None) si el número no existe en el sistema."""
        svc = ConversationService(tenant_id=str(tenant_db.id))
        conv, user_info = await svc.get_or_create_conversation(
            phone="+573099999999",
            tenant_id=str(tenant_db.id),
        )

        assert conv is None
        assert user_info is None

    @pytest.mark.asyncio
    async def test_reutiliza_conversacion_existente(
        self, client_db, tenant_db, patch_db, db_session
    ):
        """Llamar dos veces get_or_create con el mismo número no duplica la fila."""
        svc = ConversationService(tenant_id=str(tenant_db.id))

        await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )
        await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )

        result = await db_session.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_normalized == client_db.phone_normalized,
                WhatsAppConversation.tenant_id == tenant_db.id,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1


class TestUpdateConversation:

    @pytest.mark.asyncio
    async def test_persiste_nuevo_estado_e_historial(
        self, client_db, tenant_db, patch_db, db_session
    ):
        """update_conversation guarda el nuevo estado y agrega mensajes al historial."""
        svc = ConversationService(tenant_id=str(tenant_db.id))

        # Primero crear la conversación
        await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )

        # Actualizar
        await svc.update_conversation(
            phone=client_db.phone,
            new_state=ConversationState.TAKING_ORDER.value,
            context_update={"order_step": "items"},
            inbound_message="quiero pedir arroz",
            outbound_message="Claro, ¿cuántas unidades necesita?",
        )

        result = await db_session.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_normalized == client_db.phone_normalized,
                WhatsAppConversation.tenant_id == tenant_db.id,
            )
        )
        conv = result.scalar_one()

        assert conv.state == ConversationState.TAKING_ORDER
        assert conv.context.get("order_step") == "items"
        assert len(conv.recent_messages) == 2
        assert conv.recent_messages[0]["role"] == "user"
        assert conv.recent_messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_merge_de_contexto_no_sobreescribe_keys_previas(
        self, client_db, tenant_db, patch_db, db_session
    ):
        """update_conversation hace merge del contexto, no reemplaza el dict completo."""
        svc = ConversationService(tenant_id=str(tenant_db.id))

        await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )

        # Primera actualización: agrega key "step"
        await svc.update_conversation(
            phone=client_db.phone,
            new_state=None,
            context_update={"step": "inicio"},
        )
        # Segunda actualización: agrega key "items", NO debe borrar "step"
        await svc.update_conversation(
            phone=client_db.phone,
            new_state=None,
            context_update={"items": ["arroz", "aceite"]},
        )

        result = await db_session.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_normalized == client_db.phone_normalized,
                WhatsAppConversation.tenant_id == tenant_db.id,
            )
        )
        conv = result.scalar_one()

        assert conv.context.get("step") == "inicio"
        assert conv.context.get("items") == ["arroz", "aceite"]


class TestResetConversation:

    @pytest.mark.asyncio
    async def test_reset_deja_idle_y_contexto_vacio(
        self, client_db, tenant_db, patch_db, db_session
    ):
        """reset_conversation lleva el estado a IDLE y borra el contexto."""
        svc = ConversationService(tenant_id=str(tenant_db.id))

        await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )
        await svc.update_conversation(
            phone=client_db.phone,
            new_state=ConversationState.TAKING_ORDER.value,
            context_update={"order_step": "confirm", "items": ["arroz"]},
        )

        await svc.reset_conversation(phone=client_db.phone)

        result = await db_session.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.phone_normalized == client_db.phone_normalized,
                WhatsAppConversation.tenant_id == tenant_db.id,
            )
        )
        conv = result.scalar_one()

        assert conv.state == ConversationState.IDLE
        assert conv.context == {}


class TestGetRecentMessages:

    @pytest.mark.asyncio
    async def test_respeta_limite_max_recent_messages(
        self, client_db, tenant_db, patch_db
    ):
        """get_recent_messages nunca retorna más de MAX_RECENT_MESSAGES mensajes."""
        svc = ConversationService(tenant_id=str(tenant_db.id))

        await svc.get_or_create_conversation(
            phone=client_db.phone,
            tenant_id=str(tenant_db.id),
        )

        # Insertar más mensajes del límite (12 inbound = 12 entradas)
        for i in range(MAX_RECENT_MESSAGES + 2):
            await svc.update_conversation(
                phone=client_db.phone,
                new_state=None,
                context_update={},
                inbound_message=f"mensaje {i}",
            )

        messages = await svc.get_recent_messages(phone=client_db.phone)

        assert len(messages) <= MAX_RECENT_MESSAGES
        # El último mensaje debe ser el más reciente
        assert messages[-1]["content"] == f"mensaje {MAX_RECENT_MESSAGES + 1}"
