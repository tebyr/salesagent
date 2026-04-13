"""
Tests de integración para ClientAgent.

Cubre:
  1. generate_pre_visit_notification construye prompt con datos reales del cliente
  2. generate_pre_visit_notification incluye recomendaciones RAG cuando hay afinidades
  3. generate_pre_visit_notification funciona sin client_id (backward compat)
  4. respond_to_client incluye productos disponibles en el contexto
  5. _build_rag_recommendations retorna [] con graceful degradation cuando Voyage falla
  6. generate_order_confirmation incluye detalle de items del pedido

Claude API se mockea. Voyage AI se mockea para _build_rag_recommendations.
BD real vía patch_db.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.client_agent import ClientAgent
from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.integration


def _make_claude_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=80, output_tokens=40)
    return response


@pytest.fixture()
def client_agent(tenant_db, tenant_config):
    agent = ClientAgent(
        tenant_id=str(tenant_db.id),
        tenant_config=tenant_config,
    )
    agent.client = AsyncMock()
    agent.client.messages.create = AsyncMock(
        return_value=_make_claude_response("¡Hola Pedro! Hoy su vendedor Carlos viene a visitarlo.")
    )
    return agent


class TestPreVisitNotification:

    @pytest.mark.asyncio
    async def test_genera_notificacion_con_datos_reales(
        self, client_agent, client_db, tenant_db, patch_db
    ):
        """generate_pre_visit_notification llama a Claude con datos reales del cliente."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        recommendations = await svc.get_client_product_recommendations(
            client_id=str(client_db.id),
        )

        result = await client_agent.generate_pre_visit_notification(
            client_name=client_db.business_name,
            salesperson_name="Carlos Mendez",
            visit_time="10:00 AM",
            recommendations=recommendations,
            active_promotions=[],
            client_id=client_db.id,
            db=patch_db,
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert client_agent.client.messages.create.called

    @pytest.mark.asyncio
    async def test_incluye_recomendaciones_rag_cuando_hay_afinidades(
        self, client_agent, client_db, tenant_db, affinity_db, product_db, patch_db
    ):
        """
        Cuando existen afinidades en BD, _build_rag_recommendations enriquece
        el prompt con productos semánticamente relevantes.
        """
        # Mockear Voyage AI para que search_products devuelva el product_db
        with patch("app.services.embedding_service.generate_embedding") as mock_emb, \
             patch("app.services.embedding_service.search_products") as mock_search:

            mock_emb.return_value = [0.1] * 1024
            mock_search.return_value = [product_db]

            svc = AnalyticsService(tenant_id=str(tenant_db.id))
            recommendations = await svc.get_client_product_recommendations(
                client_id=str(client_db.id),
            )

            result = await client_agent.generate_pre_visit_notification(
                client_name=client_db.business_name,
                salesperson_name="Carlos Mendez",
                visit_time="10:00 AM",
                recommendations=recommendations,
                active_promotions=[],
                client_id=client_db.id,
                db=patch_db,
            )

        assert isinstance(result, str)
        # Verificar que search_products fue llamado (RAG activado)
        mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_backward_compat_sin_client_id(
        self, client_agent, client_db, patch_db
    ):
        """Sin client_id ni db, generate_pre_visit_notification debe funcionar igual."""
        result = await client_agent.generate_pre_visit_notification(
            client_name=client_db.business_name,
            salesperson_name="Carlos Mendez",
            visit_time="11:00 AM",
            recommendations=[],
            active_promotions=[],
            # client_id y db omitidos → backward compat
        )

        assert isinstance(result, str)
        assert client_agent.client.messages.create.called


class TestRespondToClient:

    @pytest.mark.asyncio
    async def test_incluye_productos_en_contexto(
        self, client_agent, client_db, tenant_db, product_db, patch_db
    ):
        """respond_to_client incluye la lista de productos disponibles en el prompt."""
        available_products = [
            {"name": product_db.name, "price": product_db.price, "sku": product_db.sku}
        ]

        result = await client_agent.respond_to_client(
            client_name=client_db.business_name,
            message="¿Tienen arroz Diana?",
            conversation_history=[],
            context_data={"available_products": available_products},
            client_id=client_db.id,
            db=patch_db,
        )

        assert isinstance(result, str)
        call_kwargs = client_agent.client.messages.create.call_args
        prompt_text = str(call_kwargs)
        assert "Arroz Diana" in prompt_text or "arroz" in prompt_text.lower()


class TestBuildRagRecommendations:

    @pytest.mark.asyncio
    async def test_graceful_degradation_cuando_voyage_falla(
        self, client_agent, client_db, tenant_db, affinity_db, patch_db
    ):
        """
        Si generate_embedding o search_products lanza excepción,
        _build_rag_recommendations debe retornar [] sin propagar el error.
        """
        with patch("app.agents.client_agent.search_products") as mock_search:
            mock_search.side_effect = RuntimeError("Voyage API timeout")

            result = await client_agent._build_rag_recommendations(
                client_id=client_db.id,
                tenant_id=tenant_db.id,
                context_hint="productos para reabastecer",
                db=patch_db,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_retorna_productos_cuando_voyage_ok(
        self, client_agent, client_db, tenant_db, affinity_db, product_db, patch_db
    ):
        """Con afinidades en BD y Voyage AI disponible, retorna lista de productos."""
        with patch("app.agents.client_agent.search_products") as mock_search:
            mock_search.return_value = [product_db]

            result = await client_agent._build_rag_recommendations(
                client_id=client_db.id,
                tenant_id=tenant_db.id,
                context_hint="productos para reabastecer",
                db=patch_db,
            )

        assert len(result) > 0
        assert result[0]["name"] == product_db.name
        assert result[0]["sku"] == product_db.sku


class TestOrderConfirmation:

    @pytest.mark.asyncio
    async def test_genera_confirmacion_con_detalle_de_items(
        self, client_agent, client_db, product_db, patch_db
    ):
        """generate_order_confirmation incluye los items del pedido en el mensaje."""
        order_data = {
            "order_id": "ORD-001",
            "items": [
                {"name": product_db.name, "quantity": 2, "unit_price": product_db.price,
                 "subtotal": product_db.price * 2}
            ],
            "total": product_db.price * 2,
            "salesperson_name": "Carlos Mendez",
        }

        result = await client_agent.generate_order_confirmation(
            client_name=client_db.business_name,
            order_data=order_data,
        )

        assert isinstance(result, str)
        call_kwargs = client_agent.client.messages.create.call_args
        prompt_text = str(call_kwargs)
        assert "Arroz Diana" in prompt_text or product_db.name in prompt_text
