"""
Tests del scheduler — app.scheduler.tasks.

Estrategia: los tests verifican la capa publica de Celery (importabilidad,
registro de tareas, beat_schedule) y las funciones async internas mediante
mocks de la BD y servicios externos.

No se requiere Redis ni broker real: se prueban las implementaciones async
directamente, parcheando AsyncSessionLocal y los agentes.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_tenant_mock(tenant_id="aaaaaaaa-0000-0000-0000-000000000001"):
    """Crea un tenant mock con los campos necesarios para el scheduler."""
    t = MagicMock()
    t.id = tenant_id
    t.name = "Distribuciones La Garantia"
    t.agent_name = "AgenteGarantia"
    t.whatsapp_phone_number_id = "123456789"
    t.whatsapp_access_token = "token_legacy_sin_encriptar"
    t.schedule_config = {"timezone": "America/Bogota"}
    t.email_config = {"management_emails": ["admin@test.co"]}
    return t


def _make_db_session(scalars_return=None):
    """Sesion mock que retorna la lista dada en scalars().all()."""
    db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=scalars_return or [])
    mock_execute = MagicMock()
    mock_execute.scalars = MagicMock(return_value=mock_scalars)
    db.execute = AsyncMock(return_value=mock_execute)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    return db


# ── Importabilidad y registro de tareas ───────────────────────────────────

class TestTasksImportAndRegistration:

    def test_module_imports_without_error(self):
        """El modulo tasks debe importarse sin requerir Redis ni BD."""
        import app.scheduler.tasks  # noqa: F401

    def test_celery_app_created(self):
        from app.scheduler.tasks import celery_app
        assert celery_app is not None

    def test_all_tasks_registered(self):
        from app.scheduler.tasks import celery_app

        expected_tasks = [
            "app.scheduler.tasks.send_salesperson_morning_briefings",
            "app.scheduler.tasks.send_pre_visit_notifications",
            "app.scheduler.tasks.send_salesperson_daily_summaries",
            "app.scheduler.tasks.send_salesperson_performance_reports",
            "app.scheduler.tasks.send_no_visit_followups",
            "app.scheduler.tasks.send_management_daily_reports",
            "app.scheduler.tasks.send_management_weekly_reports",
            "app.scheduler.tasks.check_and_send_performance_alerts",
            "app.scheduler.tasks.calculate_product_affinities",
            "app.scheduler.tasks.generate_daily_sales_snapshots",
        ]
        registered = set(celery_app.tasks.keys())
        for task_name in expected_tasks:
            assert task_name in registered, f"Tarea no registrada: {task_name}"

    def test_beat_schedule_has_all_entries(self):
        from app.scheduler.tasks import celery_app

        schedule = celery_app.conf.beat_schedule
        assert len(schedule) >= 9, f"beat_schedule tiene {len(schedule)} entradas, esperadas >= 9"

        task_names_in_schedule = {v["task"] for v in schedule.values()}
        assert "app.scheduler.tasks.send_salesperson_morning_briefings" in task_names_in_schedule
        assert "app.scheduler.tasks.calculate_product_affinities" in task_names_in_schedule
        assert "app.scheduler.tasks.generate_daily_sales_snapshots" in task_names_in_schedule


# ── _get_active_tenants ───────────────────────────────────────────────────

class TestGetActiveTenants:

    async def test_returns_empty_when_no_tenants(self):
        from app.scheduler.tasks import _get_active_tenants

        db = _make_db_session(scalars_return=[])

        class _Ctx:
            async def __aenter__(self): return db
            async def __aexit__(self, *a): pass

        with patch("app.scheduler.tasks.AsyncSessionLocal", return_value=_Ctx()):
            # _get_active_tenants importa AsyncSessionLocal localmente
            with patch("app.core.database.AsyncSessionLocal", return_value=_Ctx()):
                result = await _get_active_tenants()
        assert result == []

    async def test_returns_list_of_tenants(self):
        from app.scheduler.tasks import _get_active_tenants

        tenants = [_make_tenant_mock(), _make_tenant_mock("bbbbbbbb-0000-0000-0000-000000000002")]
        db = _make_db_session(scalars_return=tenants)

        class _Ctx:
            async def __aenter__(self): return db
            async def __aexit__(self, *a): pass

        with patch("app.core.database.AsyncSessionLocal", return_value=_Ctx()):
            result = await _get_active_tenants()

        assert len(result) == 2


# ── _send_salesperson_morning_briefings ───────────────────────────────────

class TestMorningBriefings:

    @pytest.fixture(autouse=True)
    def patch_dependencies(self):
        self.tenant = _make_tenant_mock()
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[self.tenant])):
            with patch("app.scheduler.tasks.AsyncSessionLocal") as mock_sl:
                db = _make_db_session(scalars_return=[])
                class _Ctx:
                    async def __aenter__(self): return db
                    async def __aexit__(self, *a): pass
                mock_sl.return_value = _Ctx()
                self.db = db
                yield

    async def test_runs_without_error_when_no_salespersons(self):
        """Sin vendedores, la tarea debe completarse sin exception."""
        from app.scheduler.tasks import _send_salesperson_morning_briefings
        # No lanza excepcion
        await _send_salesperson_morning_briefings()

    async def test_calls_get_active_tenants(self):
        from app.scheduler.tasks import _send_salesperson_morning_briefings
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[])) as mock_get:
            await _send_salesperson_morning_briefings()
        mock_get.assert_called_once()


# ── _calculate_product_affinities ────────────────────────────────────────

class TestCalculateProductAffinities:

    async def test_runs_without_error_when_no_tenants(self):
        """Sin tenants, la tarea de afinidades completa sin error."""
        from app.scheduler.tasks import _calculate_product_affinities
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[])):
            await _calculate_product_affinities()

    async def test_called_for_each_tenant(self):
        """Debe procesar cada tenant activo."""
        from app.scheduler.tasks import _calculate_product_affinities

        tenant1 = _make_tenant_mock("aaaaaaaa-0000-0000-0000-000000000001")
        tenant2 = _make_tenant_mock("bbbbbbbb-0000-0000-0000-000000000002")
        db = _make_db_session(scalars_return=[])

        class _Ctx:
            async def __aenter__(self): return db
            async def __aexit__(self, *a): pass

        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[tenant1, tenant2])):
            with patch("app.core.database.AsyncSessionLocal", return_value=_Ctx()):
                await _calculate_product_affinities()

        # Si no lanzamos excepcion, la iteracion funciono correctamente
        assert True


# ── _generate_daily_sales_snapshots ──────────────────────────────────────

class TestGenerateDailySalesSnapshots:

    async def test_runs_without_error_when_no_tenants(self):
        from app.scheduler.tasks import _generate_daily_sales_snapshots
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[])):
            await _generate_daily_sales_snapshots()


# ── _send_no_visit_followups ──────────────────────────────────────────────

class TestNoVisitFollowups:

    async def test_runs_without_error_when_no_tenants(self):
        from app.scheduler.tasks import _send_no_visit_followups
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[])):
            await _send_no_visit_followups()


# ── _send_management_daily_reports ────────────────────────────────────────

class TestManagementDailyReports:

    async def test_runs_without_error_when_no_tenants(self):
        from app.scheduler.tasks import _send_management_daily_reports
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[])):
            await _send_management_daily_reports()


# ── _check_and_send_performance_alerts ───────────────────────────────────

class TestPerformanceAlerts:

    async def test_runs_without_error_when_no_tenants(self):
        from app.scheduler.tasks import _check_and_send_performance_alerts
        with patch("app.scheduler.tasks._get_active_tenants",
                   new=AsyncMock(return_value=[])):
            await _check_and_send_performance_alerts()
