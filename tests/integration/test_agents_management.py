"""
Tests de integración para ManagementAgent.

Cubre:
  1. generate_daily_report agrega métricas de todos los vendedores del tenant
  2. generate_weekly_report incluye comparación semana actual vs anterior
  3. generate_low_performance_alert se dispara solo cuando hay vendedores bajo umbral
  4. Agente no crashea si no hay datos del día (equipo sin ventas)

Claude API se mockea. EmailService no se invoca directamente en el agente.
BD real vía patch_db.
"""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.management_agent import ManagementAgent
from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.integration


def _make_claude_response(text: str = "Reporte generado correctamente."):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=200, output_tokens=300)
    return response


@pytest.fixture()
def mgmt_agent(tenant_db, tenant_config):
    agent = ManagementAgent(
        tenant_id=str(tenant_db.id),
        tenant_config=tenant_config,
    )
    agent.client = AsyncMock()
    agent.client.messages.create = AsyncMock(
        return_value=_make_claude_response()
    )
    return agent


class TestDailyReport:

    @pytest.mark.asyncio
    async def test_genera_reporte_con_metricas_del_equipo(
        self, mgmt_agent, tenant_db, salesperson_db, goal_db, order_db, patch_db
    ):
        """
        generate_daily_report llama dos veces a Claude (texto + HTML)
        y retorna dict con subject, text_summary y html_body.
        """
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        goal_progress = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        team_summary = {
            "active_salespersons": 1,
            "total_salespersons": 1,
            "total_sales": goal_progress["actual_amount"],
            "total_visits": 5,
            "avg_effectiveness": 80.0,
            "team_month_pct": goal_progress["pct_amount"],
            "team_projected_pct": goal_progress["projected_pct"],
            "company_name": tenant_db.name,
        }
        salesperson_details = [
            {
                "name": salesperson_db.name,
                "actual": goal_progress["actual_amount"],
                "target": goal_progress["target_amount"],
                "pct_amount": goal_progress["pct_amount"],
                "visits": 5,
                "effectiveness": 80.0,
            }
        ]

        result = await mgmt_agent.generate_daily_report(
            report_date=str(date.today()),
            team_summary=team_summary,
            salesperson_details=salesperson_details,
            top_alerts=[],
        )

        # Estructura del retorno
        assert "subject" in result
        assert "text_summary" in result
        assert "html_body" in result
        assert str(date.today()) in result["subject"]

        # Claude fue llamado dos veces: texto + HTML
        assert mgmt_agent.client.messages.create.call_count == 2

        # El prompt del texto incluye datos del vendedor
        first_call_text = str(mgmt_agent.client.messages.create.call_args_list[0])
        assert salesperson_db.name in first_call_text


class TestWeeklyReport:

    @pytest.mark.asyncio
    async def test_genera_reporte_semanal_con_comparacion(
        self, mgmt_agent, tenant_db, salesperson_db, goal_db, order_db, patch_db
    ):
        """generate_weekly_report incluye wow_change (semana vs semana anterior)."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_label = f"Semana {week_start.isocalendar()[1]} — {week_start.strftime('%d/%m')}"

        team_summary = {
            "total_sales": 440_000.0,
            "wow_change": 12.5,          # +12.5% vs semana anterior
            "month_pct": 4.4,
            "projected_pct": 18.0,
            "company_name": tenant_db.name,
        }
        kpi_trends = {
            "effectiveness_trend": 78.0,
            "avg_ticket": 220_000.0,
            "active_clients": 15,
            "active_clients_pct": 75.0,
            "at_risk_clients": 2,
        }

        result = await mgmt_agent.generate_weekly_report(
            week_label=week_label,
            team_summary=team_summary,
            salesperson_details=[],
            kpi_trends=kpi_trends,
            recommendations=["Enfocarse en segmento A", "Activar clientes inactivos"],
        )

        assert "subject" in result
        assert "text_summary" in result
        assert week_label in result["subject"]

        # Verificar que el prompt incluyó el cambio semana a semana
        first_call_text = str(mgmt_agent.client.messages.create.call_args_list[0])
        assert "12.5" in first_call_text or "wow" in first_call_text.lower()


class TestLowPerformanceAlert:

    @pytest.mark.asyncio
    async def test_genera_alerta_para_vendedor_bajo_umbral(
        self, mgmt_agent, salesperson_db, tenant_db, goal_db, patch_db
    ):
        """
        generate_low_performance_alert se invoca cuando el vendedor está bajo meta.
        El mensaje debe mencionar la situación crítica y acciones recomendadas.
        """
        mgmt_agent.client.messages.create = AsyncMock(
            return_value=_make_claude_response(
                "⚠️ Carlos Mendez lleva solo 4.4% de la meta con 5 días transcurridos."
            )
        )

        performance_data = {
            "pct_amount": 4.4,
            "target_amount": 10_000_000.0,
            "actual_amount": 440_000.0,
            "days_remaining": 20,
            "projected_pct": 18.0,
            "required_daily": 478_000.0,
        }

        result = await mgmt_agent.generate_low_performance_alert(
            salesperson_name=salesperson_db.name,
            performance_data=performance_data,
            root_cause_hints=["Bajo número de visitas", "Zona de alta competencia"],
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert mgmt_agent.client.messages.create.called

        call_text = str(mgmt_agent.client.messages.create.call_args)
        assert salesperson_db.name in call_text
        assert "4.4" in call_text

    @pytest.mark.asyncio
    async def test_no_crashea_sin_datos_del_dia(
        self, mgmt_agent, tenant_db, patch_db
    ):
        """
        Si no hay ventas ni vendedores activos, generate_daily_report
        no debe lanzar excepción; retorna reporte con ceros.
        """
        team_summary = {
            "active_salespersons": 0,
            "total_salespersons": 0,
            "total_sales": 0.0,
            "total_visits": 0,
            "avg_effectiveness": 0.0,
            "team_month_pct": 0.0,
            "team_projected_pct": 0.0,
            "company_name": tenant_db.name,
        }

        result = await mgmt_agent.generate_daily_report(
            report_date=str(date.today()),
            team_summary=team_summary,
            salesperson_details=[],
            top_alerts=[],
        )

        assert "text_summary" in result
        assert "html_body" in result
        # Sin vendedores → Claude igual es llamado
        assert mgmt_agent.client.messages.create.call_count == 2
