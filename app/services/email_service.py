"""
EmailService — envio de emails via SendGrid.

Usado principalmente por el ManagementAgent para reportes diarios/semanales
y alertas criticas a la gerencia.
"""
import httpx
from app.core.config import settings
import structlog

logger = structlog.get_logger()

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailService:

    def __init__(self, tenant_config: dict | None = None):
        """
        tenant_config puede incluir:
            - from_name: nombre del remitente
            - from_email: email remitente (si no, usa el default de settings)
        """
        self.tenant_config = tenant_config or {}
        self.api_key = settings.sendgrid_api_key
        self.default_from_email = settings.email_from
        self.default_from_name = settings.email_from_name

    async def send_email(
        self,
        to_emails: list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """
        Envia un email via SendGrid API.
        Retorna True si fue exitoso, False si fallo.
        """
        if not self.api_key:
            logger.warning("sendgrid_not_configured_skipping_email", subject=subject)
            return False

        if not to_emails:
            logger.warning("send_email_no_recipients", subject=subject)
            return False

        from_name = self.tenant_config.get("from_name") or self.default_from_name
        from_email = self.default_from_email

        payload = {
            "personalizations": [
                {
                    "to": [{"email": email} for email in to_emails],
                    "subject": subject,
                }
            ],
            "from": {"email": from_email, "name": from_name},
            "content": [
                {"type": "text/html", "value": html_body},
            ],
        }

        if text_body:
            payload["content"].insert(0, {"type": "text/plain", "value": text_body})

        if reply_to:
            payload["reply_to"] = {"email": reply_to}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    SENDGRID_API_URL,
                    json=payload,
                    headers=headers,
                )

            if response.status_code in (200, 202):
                logger.info(
                    "email_sent",
                    to=to_emails,
                    subject=subject,
                    status=response.status_code,
                )
                return True
            else:
                logger.error(
                    "email_send_failed",
                    status=response.status_code,
                    body=response.text[:500],
                    subject=subject,
                )
                return False

        except httpx.TimeoutException:
            logger.error("email_timeout", subject=subject)
            return False
        except Exception as e:
            logger.error("email_unexpected_error", error=str(e), subject=subject)
            return False

    async def send_management_report(
        self,
        to_emails: list[str],
        subject: str,
        html_body: str,
        text_summary: str,
    ) -> bool:
        """
        Envia el reporte gerencial. Wrappea send_email con logging especifico.
        """
        if not to_emails:
            logger.warning("management_report_no_recipients", subject=subject)
            return False

        logger.info(
            "sending_management_report",
            recipients=len(to_emails),
            subject=subject,
        )
        return await self.send_email(
            to_emails=to_emails,
            subject=subject,
            html_body=html_body,
            text_body=text_summary,
        )

    async def send_alert(
        self,
        to_emails: list[str],
        alert_title: str,
        alert_body: str,
        severity: str = "warning",  # warning | critical
    ) -> bool:
        """
        Envia una alerta de bajo rendimiento o evento critico.
        Genera HTML simple para la alerta.
        """
        color = "#ef4444" if severity == "critical" else "#f59e0b"
        icon = "🚨" if severity == "critical" else "⚠️"

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;background:#f8fafc;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;
              border-left:4px solid {color};padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
    <h2 style="color:{color};margin-top:0">{icon} {alert_title}</h2>
    <div style="color:#374151;line-height:1.6;white-space:pre-line">{alert_body}</div>
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0">
    <p style="color:#9ca3af;font-size:12px;margin:0">
      Este es un mensaje automatico del sistema de agente comercial.
    </p>
  </div>
</body>
</html>"""

        subject = f"{icon} Alerta: {alert_title}"
        return await self.send_email(
            to_emails=to_emails,
            subject=subject,
            html_body=html,
            text_body=f"{alert_title}\n\n{alert_body}",
        )
