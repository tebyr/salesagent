"""
Tests de integración para AnalyticsService.

Cubre:
  1. get_salesperson_goal_progress retorna zeros cuando no hay meta
  2. get_salesperson_goal_progress calcula porcentaje correcto con meta y órdenes reales
  3. get_salesperson_goal_progress calcula proyección lineal correctamente
  4. get_client_product_recommendations retorna lista vacía sin afinidades
  5. get_client_product_recommendations ordena por affinity_score descendente
  6. get_active_promotions_for_client filtra solo promociones vigentes

Todos los tests usan BD real vía fixture db_session + patch_db.
"""
import uuid
from datetime import date, timedelta

import pytest

from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.integration


class TestGoalProgress:

    @pytest.mark.asyncio
    async def test_retorna_zeros_cuando_no_hay_meta(
        self, tenant_db, salesperson_db, patch_db
    ):
        """Si el vendedor no tiene meta en el mes actual, target_amount y actual_amount son 0."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        result = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        assert result["target_amount"] == 0.0
        assert result["actual_amount"] == 0.0
        assert result["pct_amount"] == 0.0

    @pytest.mark.asyncio
    async def test_calcula_porcentaje_correcto_con_meta_y_ordenes(
        self, tenant_db, salesperson_db, goal_db, order_db, patch_db
    ):
        """
        Meta: $10.000.000 — Orden del día: $440.000.
        Porcentaje esperado: 4.4%
        """
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        result = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        assert result["target_amount"] == 10_000_000.0
        assert result["actual_amount"] == pytest.approx(440_000.0, rel=0.01)
        assert result["pct_amount"] == pytest.approx(4.4, rel=0.01)

    @pytest.mark.asyncio
    async def test_calcula_proyeccion_lineal(
        self, tenant_db, salesperson_db, goal_db, order_db, patch_db
    ):
        """
        La proyección al cierre = (actual / días_transcurridos) × días_en_periodo.
        Validamos que sea > 0 y coherente con el ritmo actual.
        """
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        result = await svc.get_salesperson_goal_progress(
            salesperson_id=str(salesperson_db.id),
        )

        today = date.today()
        period_start = today.replace(day=1)
        days_elapsed = (today - period_start).days + 1

        expected_daily_rate = 440_000.0 / days_elapsed
        next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        days_in_period = ((next_month - timedelta(days=1)) - period_start).days + 1
        expected_projection = expected_daily_rate * days_in_period

        assert result["projected_amount"] == pytest.approx(expected_projection, rel=0.01)
        assert result["days_elapsed"] == days_elapsed
        assert result["gap_amount"] == pytest.approx(10_000_000.0 - 440_000.0, rel=0.01)


class TestClientRecommendations:

    @pytest.mark.asyncio
    async def test_retorna_vacio_sin_afinidades(
        self, tenant_db, client_db, patch_db
    ):
        """Si no hay registros en client_product_affinities, retorna lista vacía."""
        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        result = await svc.get_client_product_recommendations(
            client_id=str(client_db.id),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_ordena_por_affinity_score_descendente(
        self, tenant_db, client_db, product_db, db_session, patch_db
    ):
        """Con múltiples afinidades, el resultado viene ordenado por score de mayor a menor."""
        from app.models.analytics import ClientProductAffinity
        from app.models.product import Product

        # Crear un segundo producto
        p2 = Product(
            id=uuid.uuid4(),
            tenant_id=tenant_db.id,
            sku=f"ACE-{uuid.uuid4().hex[:6]}",
            name="Aceite Gourmet x 3L",
            brand="Gourmet",
            category="aceites",
            unit="Caja",
            price=180_000.0,
            is_active=True,
        )
        db_session.add(p2)

        # Afinidad alta para product_db
        a1 = ClientProductAffinity(
            id=uuid.uuid4(),
            tenant_id=tenant_db.id,
            client_id=client_db.id,
            product_id=product_db.id,
            affinity_score=0.85,
            total_purchases=5,
        )
        # Afinidad baja para p2
        a2 = ClientProductAffinity(
            id=uuid.uuid4(),
            tenant_id=tenant_db.id,
            client_id=client_db.id,
            product_id=p2.id,
            affinity_score=0.30,
            total_purchases=1,
        )
        db_session.add(a1)
        db_session.add(a2)
        await db_session.flush()

        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        result = await svc.get_client_product_recommendations(
            client_id=str(client_db.id),
            limit=4,
        )

        assert len(result) == 2
        assert result[0]["affinity_score"] >= result[1]["affinity_score"]
        assert result[0]["name"] == "Arroz Diana x 5Kg"


class TestActivePromotions:

    @pytest.mark.asyncio
    async def test_filtra_solo_promociones_vigentes(
        self, tenant_db, client_db, db_session, patch_db
    ):
        """Solo se retornan promociones cuya fecha fin es >= hoy."""
        from app.models.product import Promotion

        today = date.today()

        promo_vigente = Promotion(
            id=uuid.uuid4(),
            tenant_id=tenant_db.id,
            title="2x1 en Arroz",
            promo_type="descuento",
            discount_percent=50.0,
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=5),
            is_active=True,
        )
        promo_vencida = Promotion(
            id=uuid.uuid4(),
            tenant_id=tenant_db.id,
            title="Promo Vencida",
            promo_type="descuento",
            discount_percent=10.0,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=1),
            is_active=True,
        )
        db_session.add(promo_vigente)
        db_session.add(promo_vencida)
        await db_session.flush()

        svc = AnalyticsService(tenant_id=str(tenant_db.id))
        result = await svc.get_active_promotions_for_client(
            client_id=str(client_db.id),
        )

        titles = [p["title"] for p in result]
        assert "2x1 en Arroz" in titles
        assert "Promo Vencida" not in titles
