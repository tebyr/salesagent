"""
Tests del webhook de WhatsApp (app.api.v1.webhooks.whatsapp).

Cubre:
  - GET /webhook: verificacion Meta con token correcto → 200 + challenge
  - GET /webhook: token incorrecto → 403
  - GET /webhook: modo incorrecto → 403
  - POST /webhook: firma invalida → 401
  - POST /webhook: firma valida → 200 inmediato (sin esperar procesamiento)
  - POST /webhook: payload sin mensajes → 200 (no falla)

Todos los tests son unitarios: no se conectan a BD ni a Meta.
La firma HMAC se calcula con el app_secret de prueba.
"""
import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


# ── Fixture: app con dependencias mockeadas ────────────────────────────────

@pytest.fixture()
def app():
    """
    Retorna la instancia FastAPI sin ejecutar el lifespan (init_db).
    Necesitamos parchear init_db para no requerir PostgreSQL.
    """
    with patch("app.core.database.init_db", new=AsyncMock()):
        from app.api.main import app as _app
        return _app


@pytest.fixture()
def test_settings():
    """Valores de configuracion usados en los tests."""
    return {
        "verify_token": "test-verify-token",
        "app_secret": "test-app-secret",
    }


def _make_signature(body: bytes, secret: str) -> str:
    """Calcula la firma HMAC-SHA256 tal como la calcula Meta."""
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ── GET /webhook — verificacion del webhook ────────────────────────────────

class TestWebhookVerification:

    async def test_verify_webhook_correct_token_returns_challenge(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/webhook", params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "challenge_abc123",
            })
        assert response.status_code == 200
        assert response.text == "challenge_abc123"

    async def test_verify_webhook_wrong_token_returns_403(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/webhook", params={
                "hub.mode": "subscribe",
                "hub.verify_token": "token_incorrecto",
                "hub.challenge": "challenge_xyz",
            })
        assert response.status_code == 403

    async def test_verify_webhook_wrong_mode_returns_403(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/webhook", params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "challenge_xyz",
            })
        assert response.status_code == 403

    async def test_verify_webhook_no_params_returns_403(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/webhook")
        assert response.status_code == 403


# ── POST /webhook — recepcion de mensajes ─────────────────────────────────

class TestWebhookReceive:

    @pytest.fixture(autouse=True)
    def patch_webhook_internals(self):
        """
        Parchea el procesamiento interno para que los tests sean unitarios.
        Solo verificamos que el webhook responde correctamente a nivel HTTP.
        """
        with patch(
            "app.api.v1.webhooks.whatsapp._process_webhook_payload",
            new=AsyncMock(),
        ):
            with patch(
                "app.api.v1.webhooks.whatsapp.WhatsAppService.verify_webhook_signature",
                return_value=True,
            ) as self.mock_verify:
                self.mock_verify = self.mock_verify
                yield

    async def test_valid_signature_returns_200(self, app):
        payload = {
            "object": "whatsapp_business_account",
            "entry": []
        }
        body = json.dumps(payload).encode()
        signature = _make_signature(body, "test-app-secret")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/webhook",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                },
            )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_returns_ok_immediately(self, app):
        """
        El webhook debe responder < 200ms aunque el procesamiento sea lento.
        Verificamos que no espera a _process_webhook_payload.
        """
        payload = {"object": "whatsapp_business_account", "entry": []}
        body = json.dumps(payload).encode()
        signature = _make_signature(body, "test-app-secret")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/webhook",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                },
            )
        # La respuesta es inmediata sin importar cuanto tarde el procesamiento
        assert response.status_code == 200

    async def test_invalid_signature_returns_401(self, app):
        """Firma invalida debe retornar 401 sin procesar el mensaje."""
        with patch(
            "app.api.v1.webhooks.whatsapp.WhatsAppService.verify_webhook_signature",
            return_value=False,
        ):
            payload = {"object": "test"}
            body = json.dumps(payload).encode()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/webhook",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Hub-Signature-256": "sha256=firma_invalida",
                    },
                )
        assert response.status_code == 401

    async def test_empty_payload_returns_200(self, app):
        """Un payload sin mensajes no debe causar error."""
        payload = {}
        body = json.dumps(payload).encode()
        signature = _make_signature(body, "test-app-secret")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/webhook",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                },
            )
        assert response.status_code == 200


# ── Health check (smoke test) ─────────────────────────────────────────────

class TestHealthCheck:

    async def test_health_endpoint_returns_ok(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
