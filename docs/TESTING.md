# Guía de Testing — Sales Agent SaaS

> Documento de referencia para ejecutar, entender y extender la suite de tests del proyecto.

---

## 1. Tipos de tests

El proyecto tiene dos niveles de tests con estrategias distintas:

| Tipo | Ubicación | BD real | Dependencias externas | Velocidad |
|---|---|---|---|---|
| **Unitarios** | `tests/` (raíz) | ❌ Mock | ❌ Mock | ⚡ Rápido (~2s) |
| **Integración** | `tests/integration/` | ✅ PostgreSQL real | ❌ Mock | 🐢 Moderado (~15-30s) |

### Tests unitarios
No requieren ninguna infraestructura corriendo. La sesión de BD es un `AsyncMock` inyectado.
Cubren: modelos, crypto, embedding_service, order_service, webhook, tareas Celery.

### Tests de integración
Se conectan a PostgreSQL real y ejecutan queries reales. Cada test corre dentro de una
transacción con `SAVEPOINT` que se revierte al terminar → la BD queda limpia sin truncar tablas.
Cubren: ConversationService, AnalyticsService, SalesAgent, ClientAgent, ManagementAgent.

Las dependencias externas (Claude API, Voyage AI, WhatsApp, SendGrid) **siempre se mockean**
en los tests de integración. El objetivo es validar la lógica de negocio y las queries,
no el comportamiento de terceros.

---

## 2. Prerequisitos para tests de integración

### 2.1 Docker corriendo

```bash
# Levantar solo PostgreSQL (no hace falta el stack completo)
docker-compose up -d postgres

# Verificar que está corriendo
docker-compose ps postgres
```

### 2.2 Crear la base de datos de test

Los tests usan una base de datos separada `salesagent_test` para no afectar los datos de desarrollo.

**Opción A — con psql:**
```bash
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE salesagent_test;"
```

**Opción B — entrando al contenedor:**
```bash
docker exec -it salesagent-postgres-1 psql -U postgres -c "CREATE DATABASE salesagent_test;"
```

**Opción C — con Docker puro (sin psql instalado localmente):**
```bash
docker run --rm --network host postgres:16 \
  psql -U postgres -h localhost -c "CREATE DATABASE salesagent_test;"
```

> ⚠️ La extensión `pgvector` debe estar disponible. El contenedor `pgvector/pgvector:pg16`
> ya la incluye. Si usas `postgres:16` estándar, ejecuta también:
> ```sql
> \c salesagent_test
> CREATE EXTENSION IF NOT EXISTS vector;
> ```

### 2.3 Aplicar migraciones a la BD de test

```bash
# Apuntar Alembic a la BD de test y aplicar las 3 migraciones
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/salesagent_test" \
  alembic upgrade head
```

> El `conftest.py` de integración también llama `Base.metadata.create_all` al inicio de la
> sesión, pero se recomienda tener las migraciones aplicadas para que el schema sea idéntico
> al de producción.

### 2.4 Variable de entorno TEST_DATABASE_URL

Por defecto los tests apuntan a:
```
postgresql+asyncpg://postgres:postgres@localhost:5432/salesagent_test
```

Si tu configuración local es diferente (otro usuario, password o puerto), sobrescribe:

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://mi_usuario:mi_pass@localhost:5433/salesagent_test"
```

O créala en un archivo `.env.test` y cárgala antes de correr:
```bash
export $(cat .env.test | xargs) && make test-integration
```

---

## 3. Comandos de ejecución

### Makefile (recomendado)

```bash
# Solo tests unitarios — no requiere BD, corre siempre
make test

# Solo tests de integración — requiere PostgreSQL corriendo
make test-integration

# Toda la suite (unitarios + integración)
make test-all

# Lint con ruff
make lint
```

### pytest directo (más control)

```bash
# Un archivo específico
pytest tests/integration/test_conversation_service.py -v

# Un test específico por nombre
pytest tests/integration/test_analytics_service.py -k "test_calcula_porcentaje" -v

# Solo tests de integración con marcador
pytest -m integration -v

# Detener al primer fallo
pytest tests/integration/ -x -v

# Ver print() y logs en consola (útil para debug)
pytest tests/integration/ -s -v

# Correr en paralelo (requiere pytest-xdist)
pytest tests/integration/ -n auto
```

### Combinaciones útiles

```bash
# Solo los tests de agentes
pytest tests/integration/test_agents_*.py -v

# Excluir un test lento mientras desarrollas
pytest tests/integration/ -v --deselect tests/integration/test_agents_management.py::TestWeeklyReport

# Mostrar los 10 tests más lentos
pytest tests/integration/ --durations=10
```

---

## 4. Salida esperada

### Run exitoso

```
================================ test session starts ================================
platform darwin -- Python 3.12.x
asyncio_mode: auto
collected 28 items

tests/integration/test_conversation_service.py::TestGetOrCreate::test_crea_conversacion_para_cliente_conocido PASSED
tests/integration/test_conversation_service.py::TestGetOrCreate::test_crea_conversacion_para_vendedor_conocido PASSED
...
tests/integration/test_agents_management.py::TestSinDatos::test_no_crashea_sin_datos_del_dia PASSED

========================= 28 passed in 18.42s ===================================
```

### Fallo típico — AssertionError

```
FAILED tests/integration/test_analytics_service.py::TestGoalProgress::test_calcula_porcentaje_correcto_con_meta_y_ordenes
AssertionError: assert 0.0 == approx(4.4 ± 4.4e-02)
  Left:  0.0   ← actual_amount es 0, la orden no se insertó correctamente
  Right: 4.4
```

**Qué revisar:** la fixture `order_db` no fue incluida en los parámetros del test,
o la orden tiene un `status` diferente a `CONFIRMED/DISPATCHED/DELIVERED`.

### Fallo típico — Connection refused

```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError)
  Connection refused to localhost:5432
```

**Solución:**
```bash
docker-compose up -d postgres
# Esperar ~3 segundos y volver a correr
```

### Fallo típico — BD no existe

```
asyncpg.exceptions.InvalidCatalogNameError: database "salesagent_test" does not exist
```

**Solución:** crear la BD de test (ver sección 2.2).

### Fallo típico — Tabla no existe

```
asyncpg.exceptions.UndefinedTableError: relation "wa_conversations" does not exist
```

**Solución:** aplicar migraciones a la BD de test (ver sección 2.3).

---

## 5. Aislamiento de tests (patrón SAVEPOINT)

Cada test de integración opera dentro de una transacción anidada que garantiza
aislamiento sin limpiar tablas manualmente.

### Flujo de ejecución por test

```
pytest inicia
    │
    ▼
setup_database (scope=session)
    └─ CREATE TABLE IF NOT EXISTS ... (una vez por sesión)
    │
    ▼
db_session (scope=function)        ← una por cada test
    │
    ├─ BEGIN                        ← transacción externa
    │   │
    │   ├─ SAVEPOINT sp1            ← punto de restauración
    │   │   │
    │   │   ├─ [fixtures insertan datos]
    │   │   ├─ [test ejecuta]
    │   │   └─ ROLLBACK TO sp1      ← BD vuelve al estado pre-test
    │   │
    └─ ROLLBACK                     ← transacción externa también revierte
    │
    ▼
Próximo test → BD siempre limpia ✅
```

### Por qué no usamos `TRUNCATE`

- `TRUNCATE` requiere permisos adicionales y es más lento en tablas con FKs.
- El patrón SAVEPOINT es más rápido y funciona dentro del mismo motor async.
- Cada test es completamente independiente: el orden de ejecución no importa.

### Importante: `patch_db` vs `db_session`

- **`db_session`**: sesión directa para insertar datos en fixtures o hacer asserts con `SELECT`.
- **`patch_db`**: reemplaza `AsyncSessionLocal` en los servicios para que usen la misma sesión
  transaccional. **Siempre usar `patch_db` cuando el test llama a un servicio** que abre su
  propia sesión internamente.

```python
# ✅ Correcto
async def test_algo(self, client_db, tenant_db, patch_db):
    svc = ConversationService(tenant_id=str(tenant_db.id))
    await svc.get_or_create_conversation(...)   # usa patch_db internamente

# ❌ Incorrecto — el servicio abre su propia sesión fuera de la transacción de test
async def test_algo(self, client_db, tenant_db, db_session):
    svc = ConversationService(tenant_id=str(tenant_db.id))
    await svc.get_or_create_conversation(...)   # crea una sesión nueva, fuera del SAVEPOINT
```

---

## 6. Convenciones para agregar nuevos tests

### 6.1 Dónde va cada test

| Qué estoy probando | Dónde |
|---|---|
| Lógica pura, sin BD (cálculos, validaciones, transformaciones) | `tests/test_services/` o `tests/test_models/` |
| Un servicio que hace queries a BD | `tests/integration/test_<servicio>.py` |
| Un agente IA (llama a Claude + BD) | `tests/integration/test_agents_<nombre>.py` |
| Un endpoint de API (FastAPI) | `tests/test_api/` (unitario con httpx mock) |
| Una tarea Celery | `tests/test_scheduler/` (unitario con mocks) |

### 6.2 Marcador obligatorio

Todos los tests de integración deben llevar:

```python
import pytest
pytestmark = pytest.mark.integration
```

Esto permite correrlos por separado con `make test-integration` y excluirlos
del pipeline rápido con `make test`.

### 6.3 Fixtures disponibles en `tests/integration/conftest.py`

| Fixture | Tipo | Qué crea |
|---|---|---|
| `db_session` | `AsyncSession` | Sesión con SAVEPOINT — para SELECT directos |
| `patch_db` | `AsyncSession` | Parchea AsyncSessionLocal en servicios |
| `tenant_db` | `Tenant` | Tenant activo en BD |
| `salesperson_db` | `User` | Vendedor (role=SALESPERSON) |
| `manager_db` | `User` | Gerente (role=MANAGER) |
| `client_db` | `Client` | Cliente tendero ligado al vendedor |
| `product_db` | `Product` | Producto activo con precio |
| `goal_db` | `SalesGoal` | Meta mensual del vendedor ($10M) |
| `order_db` | `Order` | Orden CONFIRMED con 1 item ($440K) |
| `affinity_db` | `ClientProductAffinity` | Afinidad 0.85 entre client_db y product_db |
| `tenant_config` | `dict` | Config del tenant para instanciar agentes |

### 6.4 Cómo mockear dependencias externas

**Claude API (en agentes):**
```python
from unittest.mock import AsyncMock, MagicMock

agent.client = AsyncMock()
agent.client.messages.create = AsyncMock(
    return_value=_make_claude_response("Texto de respuesta fijo")
)

def _make_claude_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return response
```

**Voyage AI / search_products:**
```python
from unittest.mock import patch

with patch("app.agents.client_agent.search_products") as mock_search:
    mock_search.return_value = [product_db]
    result = await agent._build_rag_recommendations(...)

# O para mockear generate_embedding directamente:
with patch("app.services.embedding_service.generate_embedding") as mock_emb:
    mock_emb.return_value = [0.1] * 1024
    ...
```

**WhatsApp:**
```python
with patch("app.services.whatsapp_service.WhatsAppService.send_text") as mock_wa:
    mock_wa.return_value = {"messages": [{"id": "wamid.test"}]}
    await scheduler_task(...)
```

**SendGrid / EmailService:**
```python
with patch("app.services.email_service.EmailService.send_email") as mock_email:
    mock_email.return_value = True
    await mgmt_agent.generate_daily_report(...)
```

### 6.5 Estructura mínima de un test nuevo

```python
"""
Tests de integración para MiServicio.

Cubre:
  1. caso_de_uso_1
  2. caso_de_uso_2
"""
import pytest
from app.services.mi_servicio import MiServicio

pytestmark = pytest.mark.integration


class TestMiGrupo:

    @pytest.mark.asyncio
    async def test_caso_de_uso_1(self, tenant_db, patch_db):
        svc = MiServicio(tenant_id=str(tenant_db.id))
        result = await svc.mi_metodo(...)
        assert result is not None
```

---

## 7. Cobertura actual

| Módulo | Tests unitarios | Tests integración | Total |
|---|---|---|---|
| Modelos / constraints | 21 | — | 21 |
| crypto | 9 | — | 9 |
| embedding_service | 15 | — | 15 |
| order_service | 8 | — | 8 |
| webhook | 9 | — | 9 |
| scheduler tasks | 13 | — | 13 |
| ConversationService | — | 7 | 7 |
| AnalyticsService | — | 6 | 6 |
| SalesAgent | — | 5 | 5 |
| ClientAgent | — | 6 | 6 |
| ManagementAgent | — | 4 | 4 |
| **Total** | **75** | **28** | **103** |

> Cobertura estimada: ~65%. Meta P3: 80% (faltan endpoints de API y scheduler tasks con BD real).
