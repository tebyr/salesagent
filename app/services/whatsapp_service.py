"""
Servicio de integracion con la API oficial de WhatsApp Business (Meta Cloud API).
Maneja envio/recepcion de mensajes y gestion del webhook.
"""
import httpx
import json
import hashlib
import hmac
from datetime import datetime, timezone
from app.core.config import settings
import structlog

logger = structlog.get_logger()

META_API_BASE = "https://graph.facebook.com/v20.0"


class WhatsAppService:
    """
    Servicio para enviar mensajes via la Cloud API de Meta.
    Cada tenant tiene sus propias credenciales de WhatsApp.
    """

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        tenant_id: str,
    ):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.tenant_id = tenant_id
        self.base_url = f"{META_API_BASE}/{phone_number_id}/messages"

    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> dict:
        """
        Envia un mensaje de texto simple.
        El numero 'to' debe incluir codigo de pais sin + (ej: 573001234567)
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            }
        }
        return await self._send(payload)

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "es",
        components: list = None,
    ) -> dict:
        """
        Envia un mensaje de plantilla pre-aprobada por Meta.
        Necesario para iniciar conversaciones (fuera de la ventana de 24h).
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components or [],
            }
        }
        return await self._send(payload)

    async def send_interactive_message(
        self,
        to: str,
        body_text: str,
        buttons: list,
        header: str = None,
        footer: str = None,
    ) -> dict:
        """
        Envia mensaje con botones interactivos (max 3 botones).
        Util para confirmaciones de pedidos o menus rapidos.
        """
        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["title"][:20],  # Max 20 chars
                        }
                    }
                    for btn in buttons[:3]  # Max 3 botones
                ]
            }
        }

        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._send(payload)

    async def send_list_message(
        self,
        to: str,
        body_text: str,
        button_text: str,
        sections: list,
        header: str = None,
    ) -> dict:
        """
        Envia mensaje con lista de opciones (para mostrar productos/categorias).
        Sections: [{"title": str, "rows": [{"id": str, "title": str, "description": str}]}]
        """
        interactive = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text[:20],
                "sections": sections[:10],  # Max 10 secciones
            }
        }

        if header:
            interactive["header"] = {"type": "text", "text": header}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self._normalize_phone(to),
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._send(payload)

    async def mark_as_read(self, message_id: str) -> dict:
        """Marca un mensaje como leido."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._send(payload)

    async def _send(self, payload: dict) -> dict:
        """Envia la solicitud a la API de Meta."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    "whatsapp_message_sent",
                    tenant_id=self.tenant_id,
                    to=payload.get("to"),
                    type=payload.get("type"),
                    message_id=result.get("messages", [{}])[0].get("id"),
                )
                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "whatsapp_send_failed",
                tenant_id=self.tenant_id,
                status_code=e.response.status_code,
                response_body=e.response.text,
                payload_type=payload.get("type"),
            )
            raise
        except Exception as e:
            logger.error(
                "whatsapp_send_error",
                tenant_id=self.tenant_id,
                error=str(e),
            )
            raise

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normaliza el numero de telefono (solo digitos, sin +)."""
        normalized = "".join(filter(str.isdigit, phone))
        # Si es colombiano sin codigo de pais, agregar 57
        if len(normalized) == 10 and normalized.startswith("3"):
            normalized = "57" + normalized
        return normalized

    @staticmethod
    def verify_webhook_signature(
        payload_body: bytes,
        signature_header: str,
    ) -> bool:
        """
        Verifica la firma del webhook de Meta para seguridad.
        signature_header format: "sha256=<hex>"
        """
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_signature = signature_header[7:]  # Remove "sha256="
        actual_signature = hmac.new(
            settings.whatsapp_app_secret.encode(),
            payload_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(actual_signature, expected_signature)


def parse_webhook_message(webhook_data: dict) -> list:
    """
    Parsea el payload del webhook de WhatsApp y extrae los mensajes.
    Retorna lista de mensajes normalizados.
    """
    messages = []

    entries = webhook_data.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Mensajes entrantes
            for msg in value.get("messages", []):
                parsed = {
                    "id": msg.get("id"),
                    "from": msg.get("from"),  # Numero del remitente
                    "timestamp": msg.get("timestamp"),
                    "type": msg.get("type"),
                    "text": None,
                    "interactive_reply": None,
                    "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
                }

                if msg.get("type") == "text":
                    parsed["text"] = msg.get("text", {}).get("body", "")
                elif msg.get("type") == "interactive":
                    interactive = msg.get("interactive", {})
                    if interactive.get("type") == "button_reply":
                        parsed["interactive_reply"] = interactive.get("button_reply", {})
                        parsed["text"] = interactive["button_reply"].get("title", "")
                    elif interactive.get("type") == "list_reply":
                        parsed["interactive_reply"] = interactive.get("list_reply", {})
                        parsed["text"] = interactive["list_reply"].get("title", "")

                if parsed["text"]:
                    messages.append(parsed)

            # Actualizaciones de estado de mensajes enviados
            for status in value.get("statuses", []):
                # Estos se pueden usar para actualizar el log de mensajes
                pass

    return messages
