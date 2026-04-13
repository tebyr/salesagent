"""
Tests de integración para SalesAgent.

Cubre:
  1. generate_morning_briefing construye prompt con datos reales del vendedor
  2. generate_daily_summary incluye métricas del día correctamente
  3. respond_to_query retorna respuesta con contexto de meta
  4. generate_performance_report incluye proyección calculada por AnalyticsService
  5. Agente no crashea si el vendedor no tiene meta asignada (goal=vacío)

Claude API y WhatsApp se mockean. BD real vía patch_db.

Mock de Claude: self.client.messages.create → retorna objeto con content[0].text fijo.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.sales_agent import SalesAgent
from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.integration


def _make_claude_response(text: str):
    """Construye un objeto de respuesta de Claude fake."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return response


@pytest.fixture()
def sales_agent(tenant_db, tenant_config):
    agent = SalesAgent(
        tenant_id=str(tenant_db.id),
        tenant_config=tenant_config,
    )
    # Mockear el cliente de Anthropic para no hacer llamadas reales
    agent.client = AsyncMock()
    agent.client.messages.create = AsyncMock(
        return_value=_make_claude_response("¡Buenos días Carlos! Hoy tienes 5 clientes en ruta.")
    )
    return agent


class TestMorningBriefing:

    @pytest.mark.asyncio
    async def test_genera_briefing_con_datos_reales(
        self, sales_agent, tenant_db, salesperson_db, goal_db, patch_db
    ):
        """
        generate_morning_briefing llama a Claude con un prompt que incluye
        los datos del vendedor; retorna el texto generado.
        """
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        goal_progress = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        route_data = {
            "date": str(date.today()),
            "zone": "Zona Norte",
            "total_clients": 8,
            "priority_clients": [{"name": "Tienda El Progreso", "priority_reason": "Segmento A"}],
            "active_promotions": [],
            "alerts": [],
        }

        result = await sales_agent.generate_morning_briefing(
            salesperson_name=salesperson_db.name,
            route_data=route_data,
            goal_progress=goal_progress,
            top_recommendations=[],
        )

        # Verificar que se llamó a Claude
        assert sales_agent.client.messages.create.called
        # Verificar que retornó texto
        assert isinstance(result, str)
        assert len(result) > 0

        # Verificar que el prompt incluyó datos del vendedor
        call_kwargs = sales_agent.client.messages.create.call_args
        prompt_messages = call_kwargs.kwargs.get("messages", call_kwargs.args[0] if call_kwargs.args else [])
        prompt_text = str(prompt_messages)
        assert salesperson_db.name in prompt_text
        assert "10" in prompt_text  # target_amount en millones implica "10"


class TestDailySummary:

    @pytest.mark.asyncio
    async def test_genera_resumen_con_metricas_del_dia(
        self, sales_agent, salesperson_db, tenant_db, goal_db, order_db, patch_db
    ):
        """generate_daily_summary construye el prompt con ventas y visitas reales del día."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        goal_progress = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        day_results = {
            "visited": 6,
            "total_planned": 8,
            "sales_count": 4,
            "total_amount": goal_progress["actual_amount"],
            "effectiveness_rate": 66.7,
            "not_visited": 2,
        }

        result = await sales_agent.generate_daily_summary(
            salesperson_name=salesperson_db.name,
            day_results=day_results,
            goal_progress=goal_progress,
        )

        assert isinstance(result, str)
        assert len(result) > 0

        call_kwargs = sales_agent.client.messages.create.call_args
        prompt_text = str(call_kwargs)
        assert "6" in prompt_text   # visited
        assert "8" in prompt_text   # total_planned


class TestRespondToQuery:

    @pytest.mark.asyncio
    async def test_responde_consulta_con_contexto_de_meta(
        self, sales_agent, salesperson_db, tenant_db, goal_db, patch_db
    ):
        """respond_to_query incluye los datos de meta en el contexto enviado a Claude."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        goal_progress = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        result = await sales_agent.respond_to_query(
            salesperson_name=salesperson_db.name,
            query="¿Cuánto me falta para la meta?",
            conversation_history=[],
            context_data={
                "meta_actual": goal_progress["pct_amount"],
                "gap": goal_progress["gap_amount"],
            },
        )

        assert isinstance(result, str)
        assert sales_agent.client.messages.create.called


class TestPerformanceReport:

    @pytest.mark.asyncio
    async def test_genera_reporte_con_proyeccion_de_analytics(
        self, sales_agent, salesperson_db, tenant_db, goal_db, order_db, patch_db
    ):
        """generate_performance_report usa los datos calculados por AnalyticsService."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        goal_progress = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        detailed_metrics = {
            "effectiveness_rate": 75.0,
            "active_clients": 15,
            "inactive_clients": 3,
            "new_clients": 1,
            "top_clients": [{"name": "Tienda El Progreso", "amount": 440_000}],
            "category_performance": {},
        }

        result = await sales_agent.generate_performance_report(
            salesperson_name=salesperson_db.name,
            goal_progress=goal_progress,
            detailed_metrics=detailed_metrics,
        )

        assert isinstance(result, str)

        call_kwargs = sales_agent.client.messages.create.call_args
        prompt_text = str(call_kwargs)
        # La proyección calculada por AnalyticsService debe estar en el prompt
        assert "proyeccion" in prompt_text.lower() or "projected" in prompt_text.lower()


class TestSinMeta:

    @pytest.mark.asyncio
    async def test_no_crashea_sin_meta_asignada(
        self, sales_agent, salesperson_db, tenant_db, patch_db
    ):
        """El agente debe funcionar aunque el vendedor no tenga meta asignada (target=0)."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        # Sin fixture goal_db → no hay meta en BD
        goal_progress = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        assert goal_progress["target_amount"] == 0.0

        # No debe lanzar excepción
        result = await sales_agent.generate_morning_briefing(
            salesperson_name=salesperson_db.name,
            route_data={"date": str(date.today()), "total_clients": 0,
                        "priority_clients": [], "active_promotions": [], "alerts": [], "zone": ""},
            goal_progress=goal_progress,
            top_recommendations=[],
        )
        assert isinstance(result, str)
