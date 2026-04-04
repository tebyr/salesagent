"""
Agente de Vendedores.

Responsabilidades:
- Briefing matutino: ruta del dia, clientes prioritarios, tips
- Recomendaciones de productos/ofertas por cliente
- Resumen diario de resultados
- Reporte de rendimiento vs meta + proyeccion
- Atencion de consultas reactivas del vendedor
"""
from app.agents.base import BaseAgent
from app.core.config import settings
from typing import Optional
import structlog

logger = structlog.get_logger()


VENDOR_SYSTEM_PROMPT = """Eres {agent_name}, asistente comercial inteligente para {company_name}.

Tu rol es apoyar a los vendedores del equipo comercial de una empresa distribuidora en Colombia
que atiende el canal tradicional (tiendas de barrio, minimercados).

PERSONALIDAD:
- Proactivo, directo y positivo
- Hablas en espanol colombiano natural, sin ser informal en exceso
- Eres motivador pero realista en las proyecciones
- Conoces profundamente el negocio de distribución y logística

CAPACIDADES:
1. Analizar rutas y priorizar clientes por potencial de venta
2. Recomendar productos especificos por cliente basado en historial
3. Alertar sobre clientes en riesgo de inactividad
4. Calcular y comunicar rendimiento vs meta con proyecciones
5. Sugerir estrategias para cerrar brechas con la meta

REGLAS:
- Siempre incluye datos especificos (montos, porcentajes, nombres de clientes)
- Los mensajes de WhatsApp deben ser concisos y usar emojis con moderacion
- Prioriza la informacion mas accionable para el vendedor
- Cuando des recomendaciones de productos, explica el POR QUE para ese cliente especifico
"""


class SalesAgent(BaseAgent):

    def get_system_prompt(self) -> str:
        return VENDOR_SYSTEM_PROMPT.format(
            agent_name=self.agent_name,
            company_name=self.tenant_config.get("name", "la empresa"),
        )

    async def generate_morning_briefing(
        self,
        salesperson_name: str,
        route_data: dict,
        goal_progress: dict,
        top_recommendations: list,
    ) -> str:
        """
        Genera el mensaje de briefing matutino para el vendedor.
        Incluye: ruta del dia, clientes prioritarios, ofertas clave, meta del dia.
        """
        context = f"""
VENDEDOR: {salesperson_name}
FECHA: {route_data.get('date')}
RUTA: {route_data.get('zone', 'Sin zona asignada')}
CLIENTES EN RUTA HOY: {route_data.get('total_clients', 0)}

META DEL MES:
- Meta: {self._format_cop(goal_progress.get('target_amount', 0))}
- Acumulado: {self._format_cop(goal_progress.get('actual_amount', 0))} ({self._format_pct(goal_progress.get('pct_amount', 0))})
- Dias restantes: {goal_progress.get('days_remaining', 0)}
- Meta diaria recomendada hoy: {self._format_cop(goal_progress.get('suggested_daily_target', 0))}

CLIENTES PRIORITARIOS HOY:
{self._format_priority_clients(route_data.get('priority_clients', []))}

OFERTAS Y PROMOCIONES ACTIVAS:
{self._format_promotions(route_data.get('active_promotions', []))}

RECOMENDACIONES TOP POR CLIENTE:
{self._format_recommendations(top_recommendations)}

ALERTAS:
{self._format_alerts(route_data.get('alerts', []))}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Genera el briefing matutino de WhatsApp para este vendedor.

Debe ser motivador, concreto y accionable. Maximo 300 palabras.
Incluye los emojis necesarios para hacerlo facil de leer en WhatsApp.
Termina con un tip o estrategia especifica para hoy.

DATOS:
{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_standard,
            max_tokens=600,
        )
        return self._extract_text(response)

    async def generate_client_recommendations(
        self,
        salesperson_name: str,
        client_name: str,
        client_history: dict,
        available_products: list,
        active_promotions: list,
    ) -> str:
        """
        Genera recomendaciones de productos especificas para un cliente.
        Usado antes de la visita y como sugerencia al vendedor.
        """
        context = f"""
CLIENTE: {client_name}
HISTORIAL DE COMPRAS:
- Ticket promedio: {self._format_cop(client_history.get('avg_ticket', 0))}
- Frecuencia: cada {client_history.get('purchase_frequency_days', 'N/A')} dias
- Ultima compra: {client_history.get('last_purchase_date', 'N/A')}
- Categorias mas compradas: {', '.join(client_history.get('top_categories', []))}
- Productos frecuentes: {', '.join(client_history.get('frequent_products', []))}

PRODUCTOS CON ALTA AFINIDAD PARA ESTE CLIENTE:
{self._format_affinity_products(client_history.get('affinity_products', []))}

PROMOCIONES ACTIVAS RELEVANTES:
{self._format_promotions(active_promotions)}

PRODUCTOS CON PROBLEMAS DE ROTACION EN GONDOLA:
{self._format_slow_rotation_products(available_products)}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Como asesor comercial, genera 3-5 recomendaciones especificas
de productos para ofrecer al cliente {client_name} en la proxima visita.

Para cada recomendacion explica BREVEMENTE por que ese producto es ideal para ESTE cliente especifico.
Incluye precio y si hay promo activa.
Formato para WhatsApp (conciso, con emojis si ayuda).

DATOS:
{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_standard,
            max_tokens=500,
        )
        return self._extract_text(response)

    async def generate_daily_summary(
        self,
        salesperson_name: str,
        day_results: dict,
        goal_progress: dict,
    ) -> str:
        """Genera el resumen del dia (cierre de jornada)."""
        context = f"""
RESULTADOS DEL DIA - {salesperson_name}:
- Clientes visitados: {day_results.get('visited', 0)} de {day_results.get('total_planned', 0)}
- Ventas cerradas: {day_results.get('sales_count', 0)} clientes
- Total vendido: {self._format_cop(day_results.get('total_amount', 0))}
- Efectividad: {self._format_pct(day_results.get('effectiveness_rate', 0))}
- Clientes no visitados: {day_results.get('not_visited', 0)}

ACUMULADO DEL MES:
- Vendido: {self._format_cop(goal_progress.get('actual_amount', 0))} de {self._format_cop(goal_progress.get('target_amount', 0))} ({self._format_pct(goal_progress.get('pct_amount', 0))})
- Dias restantes: {goal_progress.get('days_remaining', 0)}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Genera el resumen del dia para el vendedor {salesperson_name}.
Debe ser positivo y motivador, reconocer logros del dia.
Maximo 150 palabras. Incluye 1-2 emojis relevantes.

{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_simple,
            max_tokens=300,
        )
        return self._extract_text(response)

    async def generate_performance_report(
        self,
        salesperson_name: str,
        goal_progress: dict,
        detailed_metrics: dict,
    ) -> str:
        """
        Genera el reporte nocturno de rendimiento vs meta + proyeccion + recomendaciones.
        Este es el mensaje mas completo del dia.
        """
        context = f"""
REPORTE DE RENDIMIENTO - {salesperson_name}

PERIODO: {goal_progress.get('period_start')} al {goal_progress.get('period_end')}
DIAS: {goal_progress.get('days_elapsed')} transcurridos, {goal_progress.get('days_remaining')} restantes

VENTAS:
- Meta: {self._format_cop(goal_progress.get('target_amount', 0))}
- Actual: {self._format_cop(goal_progress.get('actual_amount', 0))} ({self._format_pct(goal_progress.get('pct_amount', 0))})
- Proyeccion al cierre: {self._format_cop(goal_progress.get('projected_amount', 0))} ({self._format_pct(goal_progress.get('projected_pct', 0))})
- Gap para cumplir: {self._format_cop(goal_progress.get('gap_amount', 0))}

VISITAS:
- Meta visitas: {goal_progress.get('target_visits', 'N/A')}
- Realizadas: {goal_progress.get('actual_visits', 0)} ({self._format_pct(goal_progress.get('pct_visits', 0))})
- Efectividad: {self._format_pct(detailed_metrics.get('effectiveness_rate', 0))}

CLIENTES:
- Activos este periodo: {detailed_metrics.get('active_clients', 0)}
- Inactivos (no han comprado): {detailed_metrics.get('inactive_clients', 0)}
- Nuevos: {detailed_metrics.get('new_clients', 0)}

TOP 3 CLIENTES DEL PERIODO:
{self._format_top_clients(detailed_metrics.get('top_clients', []))}

CATEGORIAS - Ventas vs meta:
{self._format_category_performance(detailed_metrics.get('category_performance', {}))}
"""
        messages = [
            {
                "role": "user",
                "content": f"""Genera el reporte de rendimiento nocturno para el vendedor {salesperson_name}.

Debe incluir:
1. Resumen ejecutivo del rendimiento (1-2 frases)
2. Analisis del gap vs meta y si la proyeccion es alcanzable
3. 3 acciones concretas y especificas para los proximos dias
4. Mensaje motivacional al final

Maximo 400 palabras. Usa formato claro con secciones para WhatsApp.

{context}"""
            }
        ]

        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_standard,
            max_tokens=700,
        )
        return self._extract_text(response)

    async def respond_to_query(
        self,
        salesperson_name: str,
        query: str,
        conversation_history: list,
        context_data: dict,
    ) -> str:
        """Responde una consulta reactiva del vendedor."""
        messages = conversation_history + [
            {"role": "user", "content": query}
        ]

        context_prompt = f"""
CONTEXTO DEL VENDEDOR {salesperson_name}:
{self._format_context_data(context_data)}

Responde la consulta del vendedor de forma concisa y util.
Si no tienes la informacion exacta, indícalo claramente.
"""
        response = await self._call_ai(
            messages=messages,
            model=settings.ai_model_standard,
            max_tokens=400,
            system=self.get_system_prompt() + "\n\n" + context_prompt,
        )
        return self._extract_text(response)

    # --- Helpers de formateo ---

    def _format_priority_clients(self, clients: list) -> str:
        if not clients:
            return "- Sin clientes prioritarios especiales hoy"
        lines = []
        for i, c in enumerate(clients[:5], 1):
            reason = c.get('priority_reason', '')
            lines.append(f"{i}. {c.get('name')} - {reason}")
        return "\n".join(lines)

    def _format_promotions(self, promotions: list) -> str:
        if not promotions:
            return "- Sin promociones activas"
        lines = []
        for p in promotions[:5]:
            lines.append(f"- {p.get('title')}: {p.get('description', '')} (hasta {p.get('end_date', '')})")
        return "\n".join(lines)

    def _format_recommendations(self, recommendations: list) -> str:
        if not recommendations:
            return "- Sin recomendaciones especificas"
        lines = []
        for r in recommendations[:5]:
            lines.append(f"- Para {r.get('client_name')}: {r.get('product_name')} ({r.get('reason', '')})")
        return "\n".join(lines)

    def _format_alerts(self, alerts: list) -> str:
        if not alerts:
            return "- Sin alertas"
        return "\n".join([f"- {a}" for a in alerts])

    def _format_affinity_products(self, products: list) -> str:
        if not products:
            return "- Sin datos de afinidad"
        lines = []
        for p in products[:5]:
            score = p.get('affinity_score', 0)
            lines.append(f"- {p.get('name')} (score: {score:.0%}, ultimo pedido: {p.get('last_purchase_date', 'nunca')})")
        return "\n".join(lines)

    def _format_slow_rotation_products(self, products: list) -> str:
        slow = [p for p in products if p.get('rotation_flag') in ('slow', 'critical')]
        if not slow:
            return "- Sin productos con rotacion lenta"
        lines = []
        for p in slow[:3]:
            lines.append(f"- {p.get('name')}: rotacion {p.get('rotation_flag')} ({p.get('rotation_days', 'N/A')} dias)")
        return "\n".join(lines)

    def _format_top_clients(self, clients: list) -> str:
        if not clients:
            return "- Sin datos"
        lines = []
        for i, c in enumerate(clients[:3], 1):
            lines.append(f"{i}. {c.get('name')}: {self._format_cop(c.get('amount', 0))}")
        return "\n".join(lines)

    def _format_category_performance(self, categories: dict) -> str:
        if not categories:
            return "- Sin datos por categoria"
        lines = []
        for cat, data in list(categories.items())[:5]:
            actual = self._format_cop(data.get('actual', 0))
            target = self._format_cop(data.get('target', 0))
            pct = self._format_pct(data.get('pct', 0))
            lines.append(f"- {cat}: {actual} de {target} ({pct})")
        return "\n".join(lines)

    def _format_context_data(self, data: dict) -> str:
        lines = []
        for key, value in data.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "Sin contexto adicional"
