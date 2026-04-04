"""
Agente de Gerencia.

Responsabilidades:
- Reportes diarios y semanales por email
- Alertas cuando vendedores estan bajo meta
- Alertas de clientes en riesgo de perdida
- KPIs del equipo completo
- Responder consultas gerenciales via WhatsApp
"""
from app.agents.base import BaseAgent
from app.core.config import settings
import structlog

logger = structlog.get_logger()


MANAGEMENT_SYSTEM_PROMPT = """Eres {agent_name}, asistente de inteligencia comercial para la gerencia de {company_name}.

Tu rol es proporcionar informacion ejecutiva clara, precisa y accionable sobre el desempeno
del equipo comercial.

PERSONALIDAD:
- Ejecutivo, preciso y orientado a datos
- Lenguaje profesional y formal
- Destaca lo relevante y urgente sin perder detalle
- Siempre proporciona contexto y recomendaciones

CAPACIDADES:
1. Reportes de equipo: rendimiento global, por zona, por vendedor
2. Alertas de riesgo: vendedores bajo meta, clientes inactivos
3. Analisis de tendencias: proyecciones, comparativos periodo anterior
4. Identificacion de oportunidades: productos en promo sin rotar, clientes con potencial
5. Respuestas a consultas sobre el negocio

FORMATO DE REPORTES:
- Comenzar con resumen ejecutivo de 3-5 puntos clave
- Luego detalle por seccion
- Terminar con acciones recomendadas priorizadas
"""


class ManagementAgent(BaseAgent):

    def get_system_prompt(self) -> str:
        return MANAGEMENT_SYSTEM_PROMPT.format(
            agent_name=self.agent_name,
            company_name=self.tenant_config.get("name", "la empresa"),
        )

    async def generate_daily_report(
        self,
        report_date: str,
        team_summary: dict,
        salesperson_details: list,
        top_alerts: list,
    ) -> dict:
        """
        Genera el reporte diario para gerencia.
        Retorna: {"subject": str, "text_summary": str, "html_body": str}
        """
        context = f"""
REPORTE DIARIO: {report_date}

RESUMEN DEL EQUIPO:
- Vendedores activos hoy: {team_summary.get('active_salespersons', 0)} de {team_summary.get('total_salespersons', 0)}
- Total ventas del dia: {self._format_cop(team_summary.get('total_sales', 0))}
- Clientes visitados: {team_summary.get('total_visits', 0)}
- Efectividad promedio: {self._format_pct(team_summary.get('avg_effectiveness', 0))}
- Meta acumulada mes: {self._format_pct(team_summary.get('team_month_pct', 0))}
- Proyeccion al cierre: {self._format_pct(team_summary.get('team_projected_pct', 0))}

DETALLE POR VENDEDOR:
{self._format_salesperson_table(salesperson_details)}

ALERTAS CRITICAS:
{self._format_management_alerts(top_alerts)}
"""
        # Generar resumen de texto (para WhatsApp)
        text_response = await self._call_ai(
            messages=[{
                "role": "user",
                "content": f"""Genera el resumen ejecutivo diario para gerencia en maximo 250 palabras.
Prioriza: 1) Resultado global del equipo 2) Situacion critica si la hay 3) 2-3 acciones recomendadas.

{context}"""
            }],
            model=settings.ai_model_standard,
            max_tokens=500,
        )
        text_summary = self._extract_text(text_response)

        # Generar HTML para email
        html_response = await self._call_ai(
            messages=[{
                "role": "user",
                "content": f"""Genera el reporte diario completo en formato HTML para email corporativo.

Estructura:
1. Header con fecha y logo placeholder
2. KPIs principales en cards
3. Tabla de vendedores con semaforo (verde/amarillo/rojo segun % de meta)
4. Seccion de alertas
5. Recomendaciones priorizadas

Usa CSS inline. Colores: primario={self.tenant_config.get('primary_color', '#2563EB')}.
El HTML debe verse bien en clientes de email.

{context}"""
            }],
            model=settings.ai_model_complex,
            max_tokens=3000,
        )
        html_body = self._extract_text(html_response)

        return {
            "subject": f"📊 Reporte Diario {report_date} - {team_summary.get('company_name', '')}",
            "text_summary": text_summary,
            "html_body": html_body,
        }

    async def generate_weekly_report(
        self,
        week_label: str,
        team_summary: dict,
        salesperson_details: list,
        kpi_trends: dict,
        recommendations: list,
    ) -> dict:
        """Genera el reporte semanal completo para gerencia."""
        context = f"""
REPORTE SEMANAL: {week_label}

RESUMEN SEMANA:
- Ventas totales: {self._format_cop(team_summary.get('total_sales', 0))}
- vs Semana anterior: {self._format_pct(team_summary.get('wow_change', 0))} {'↑' if team_summary.get('wow_change', 0) >= 0 else '↓'}
- Acumulado del mes: {self._format_pct(team_summary.get('month_pct', 0))}
- Proyeccion mensual: {self._format_pct(team_summary.get('projected_pct', 0))}

TENDENCIAS:
- Efectividad de visitas: {self._format_pct(kpi_trends.get('effectiveness_trend', 0))}
- Ticket promedio: {self._format_cop(kpi_trends.get('avg_ticket', 0))}
- Clientes activos: {kpi_trends.get('active_clients', 0)} ({self._format_pct(kpi_trends.get('active_clients_pct', 0))} del total)
- Clientes en riesgo: {kpi_trends.get('at_risk_clients', 0)}

DETALLE POR VENDEDOR:
{self._format_salesperson_table(salesperson_details)}

RECOMENDACIONES ESTRATEGICAS:
{self._format_recommendations_list(recommendations)}
"""
        text_response = await self._call_ai(
            messages=[{
                "role": "user",
                "content": f"""Genera el resumen ejecutivo semanal en maximo 300 palabras.
Incluye analisis de tendencias y 3 acciones prioritarias para la proxima semana.

{context}"""
            }],
            model=settings.ai_model_standard,
            max_tokens=600,
        )
        text_summary = self._extract_text(text_response)

        html_response = await self._call_ai(
            messages=[{
                "role": "user",
                "content": f"""Genera el reporte semanal completo en HTML para email.

Incluye:
1. Resumen ejecutivo con KPIs clave
2. Grafico de barras simple (HTML/CSS) con ventas por vendedor
3. Tabla comparativa semana actual vs anterior
4. Semaforo de cumplimiento por vendedor
5. Top 5 oportunidades identificadas
6. Plan de accion recomendado para la proxima semana

CSS inline. Colores corporativos: {self.tenant_config.get('primary_color', '#2563EB')}.

{context}"""
            }],
            model=settings.ai_model_complex,
            max_tokens=4000,
        )
        html_body = self._extract_text(html_response)

        return {
            "subject": f"📈 Reporte Semanal {week_label} - {team_summary.get('company_name', '')}",
            "text_summary": text_summary,
            "html_body": html_body,
        }

    async def generate_low_performance_alert(
        self,
        salesperson_name: str,
        performance_data: dict,
        root_cause_hints: list,
    ) -> str:
        """Genera alerta cuando un vendedor esta significativamente bajo meta."""
        context = f"""
ALERTA DE RENDIMIENTO BAJO - {salesperson_name}

- Cumplimiento actual: {self._format_pct(performance_data.get('pct_amount', 0))}
- Meta mes: {self._format_cop(performance_data.get('target_amount', 0))}
- Actual: {self._format_cop(performance_data.get('actual_amount', 0))}
- Dias restantes: {performance_data.get('days_remaining', 0)}
- Proyeccion: {self._format_pct(performance_data.get('projected_pct', 0))}
- Para alcanzar la meta necesita vender: {self._format_cop(performance_data.get('required_daily', 0))}/dia

POSIBLES CAUSAS:
{chr(10).join([f'- {h}' for h in root_cause_hints])}
"""
        response = await self._call_ai(
            messages=[{
                "role": "user",
                "content": f"""Genera una alerta breve para gerencia sobre el bajo rendimiento de {salesperson_name}.

Incluye:
1. Estado actual (1-2 frases)
2. Que tan critica es la situacion
3. 2-3 acciones especificas recomendadas

Maximo 150 palabras. Tono ejecutivo.

{context}"""
            }],
            model=settings.ai_model_standard,
            max_tokens=300,
        )
        return self._extract_text(response)

    async def respond_to_query(
        self,
        manager_name: str,
        query: str,
        conversation_history: list,
        context_data: dict,
    ) -> str:
        """Responde consultas reactivas del gerente via WhatsApp."""
        messages = conversation_history + [
            {"role": "user", "content": query}
        ]

        system_with_context = self.get_system_prompt() + f"""

CONTEXTO DISPONIBLE:
{self._format_management_context(context_data)}

Responde de forma ejecutiva y precisa. Si no tienes el dato exacto, indícalo.
"""
        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_standard,
            max_tokens=500,
            system=system_with_context,
        )
        return self._extract_text(response)

    # --- Helpers ---

    def _format_salesperson_table(self, salespersons: list) -> str:
        if not salespersons:
            return "- Sin datos de vendedores"
        lines = []
        for v in salespersons:
            pct = v.get('pct_amount', 0)
            flag = "🟢" if pct >= 80 else ("🟡" if pct >= 60 else "🔴")
            lines.append(
                f"{flag} {v.get('name')}: {self._format_cop(v.get('actual', 0))} "
                f"/ {self._format_cop(v.get('target', 0))} ({self._format_pct(pct)}) "
                f"| {v.get('visits', 0)} visitas | {self._format_pct(v.get('effectiveness', 0))} efectividad"
            )
        return "\n".join(lines)

    def _format_management_alerts(self, alerts: list) -> str:
        if not alerts:
            return "- Sin alertas criticas"
        return "\n".join([f"🚨 {a}" for a in alerts])

    def _format_recommendations_list(self, recs: list) -> str:
        if not recs:
            return "- Sin recomendaciones"
        return "\n".join([f"{i+1}. {r}" for i, r in enumerate(recs)])

    def _format_management_context(self, data: dict) -> str:
        lines = []
        for key, value in data.items():
            if isinstance(value, float):
                lines.append(f"- {key}: {value:,.0f}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "Sin contexto adicional"
