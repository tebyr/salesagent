"""
Webhook de WhatsApp Business API.
Recibe mensajes entrantes y actualizaciones de estado.
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse
from app.core.config import settings
from app.core.crypto import decrypt_value
from app.services.whatsapp_service import WhatsAppService, parse_webhook_message
from app.agents.orchestrator import AgentOrchestrator
import structlog
import asyncio

logger = structlog.get_logger()
router = APIRouter()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Verificacion inicial del webhook por Meta.
    Meta envia esta solicitud al configurar el webhook por primera vez.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_webhook_verify_token:
        logger.info("webhook_verified_successfully")
        return PlainTextResponse(hub_challenge)

    logger.warning("webhook_verification_failed", token=hub_verify_token)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Recibe mensajes entrantes y actualizaciones de estado de WhatsApp.
    Procesa el mensaje y delega al orquestador correspondiente.
    """
    # Verificar firma de seguridad
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not WhatsAppService.verify_webhook_signature(body, signature):
        logger.warning("webhook_signature_invalid")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    # Procesar en background para responder rapido a Meta (< 200ms requerido)
    asyncio.create_task(_process_webhook_payload(payload))

    # Responder OK inmediatamente
    return {"status": "ok"}


async def _process_webhook_payload(payload: dict):
    """Procesa el payload del webhook de forma asincrona."""
    from app.services.tenant_service import TenantService
    from app.services.conversation_service import ConversationService

    try:
        messages = parse_webhook_message(payload)

        for message in messages:
            phone_number_id = message.get("phone_number_id")
            sender_phone = message.get("from")
            text = message.get("text", "")
            wa_message_id = message.get("id")

            if not text:
                continue

            # Identificar el tenant por el phone_number_id de destino
            tenant_service = TenantService()
            tenant = await tenant_service.get_tenant_by_phone_number_id(phone_number_id)

            if not tenant:
                logger.warning(
                    "tenant_not_found_for_phone_number_id",
                    phone_number_id=phone_number_id,
                )
                continue

            # Obtener/crear estado de conversacion
            conv_service = ConversationService(str(tenant.id))
            conversation, user_info = await conv_service.get_or_create_conversation(
                phone=sender_phone,
                tenant_id=str(tenant.id),
            )

            if not user_info:
                # Usuario no registrado
                wa_service = WhatsAppService(
                    phone_number_id=tenant.whatsapp_phone_number_id,
                    access_token=decrypt_value(tenant.whatsapp_access_token),
                    tenant_id=str(tenant.id),
                )
                await wa_service.send_text_message(
                    to=sender_phone,
                    text=(
                        f"Hola 👋 Soy {tenant.agent_name} de {tenant.name}.\n\n"
                        "Tu numero no esta registrado en nuestro sistema. "
                        "Contacta a tu asesor para activar tu cuenta."
                    )
                )
                continue

            # Procesar con el orquestador
            tenant_config = {
                "name": tenant.name,
                "agent_name": tenant.agent_name,
                "primary_color": tenant.primary_color,
            }

            orchestrator = AgentOrchestrator(str(tenant.id), tenant_config)

            result = await orchestrator.process_inbound_message(
                phone=sender_phone,
                message_text=text,
                conversation_state=conversation,
                user_info=user_info,
            )

            # Enviar respuesta
            wa_service = WhatsAppService(
                phone_number_id=tenant.whatsapp_phone_number_id,
                access_token=decrypt_value(tenant.whatsapp_access_token),
                tenant_id=str(tenant.id),
            )

            if result.get("response_text"):
                await wa_service.send_text_message(
                    to=sender_phone,
                    text=result["response_text"],
                )

            # Actualizar estado de conversacion
            await conv_service.update_conversation(
                phone=sender_phone,
                new_state=result.get("new_state"),
                context_update=result.get("context_update", {}),
            )

            # Ejecutar acciones pendientes (ej: crear pedido)
            for action in result.get("actions", []):
                await _execute_action(action, str(tenant.id))

            # Marcar mensaje como leido
            await wa_service.mark_as_read(wa_message_id)

    except Exception as e:
        logger.error("webhook_processing_error", error=str(e), exc_info=True)


async def _execute_action(action: dict, tenant_id: str):
    """Ejecuta acciones derivadas del procesamiento del mensaje."""
    from app.services.order_service import OrderService

    action_type = action.get("type")

    if action_type == "create_order":
        order_service = OrderService(tenant_id)
        order = await order_service.create_order_from_agent(
            client_id=action.get("client_id"),
            salesperson_id=action.get("salesperson_id"),
            order_data=action.get("order_data", {}),
        )
        logger.info(
            "order_created_by_agent",
            tenant_id=tenant_id,
            order_id=str(order.id) if order else None,
        )
