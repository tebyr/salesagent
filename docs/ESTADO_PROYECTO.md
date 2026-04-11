# Estado del Proyecto — Sales Agent SaaS

> **Documento vivo.** Se actualiza al cierre de cada sesión de trabajo mediante `/actualizar-estado`.
> Es la fuente de verdad para retomar el proyecto sin releer el código.

---

## Control de versiones

| Versión | Fecha      | Sesión | Cambios |
|---------|------------|--------|---------|
| 1.0.0   | 2026-04-11 | 4      | Documento inicial. Estado al cierre del bloque 2 (seed + tests) |

---

## 1. Resumen ejecutivo

SaaS B2B para distribuidoras colombianas del canal tradicional. Un agente supervisor multi-rol que atiende vendedores de campo por WhatsApp, envía notificaciones proactivas a los tenderos (clientes), y reporta KPIs a la gerencia por email.

**Directorio del proyecto:** `/Users/oscarmauriciogomezacevedo/claudecode/salesagent`
**Repositorio:** `https://github.com/tebyr/salesagent.git` (rama `master`)
**Último commit:** `47db787` — feat: add test suite (conftest + 6 test modules) and pytest.ini

### Stack
| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI (async) |
| Base de datos | PostgreSQL 16 + SQLAlchemy async (asyncpg) |
| Migraciones | Alembic (3 migraciones aplicadas) |
| Cache / Queue | Redis + Celery (worker + beat) |
| IA — Agentes | Anthropic Claude API (Haiku / Sonnet / Opus por complejidad) |
| IA — Embeddings | Voyage AI voyage-3 (1024 dims) + pgvector IVFFlat |
| Mensajería | WhatsApp Business Cloud API (Meta oficial) |
| Email | SendGrid |
| Encriptación | Fernet AES-128-CBC (cryptography) |
| Frontend | Next.js 14 App Router + React Query + Tailwind |
| Infra local | Docker Compose (API + Celery worker + beat + Flower + PG + Redis) |
| Infra cloud | AWS ECS Fargate + RDS + ElastiCache (pendiente) |

### Avance global: **~72%**

```
Backend core (modelos, DB, API admin, agentes)   ████████████████████  95%
Scheduler + servicios                             ████████████████████  90%
Frontend panel admin                              ████████████████████  90%
RAG / búsqueda semántica                         ████████████████░░░░  80%
Tests                                             ████████████░░░░░░░░  60%
Infraestructura local (Docker)                   ████████████████████  95%
Infraestructura cloud (AWS)                       ░░░░░░░░░░░░░░░░░░░░   0%
CI/CD                                             ░░░░░░░░░░░░░░░░░░░░   0%
Documentación                                     ████████████████░░░░  80%
```

---

## 2. Mapa de componentes

### Backend — Core

| Componente | Archivo(s) clave | Estado | Notas |
|-----------|-----------------|--------|-------|
| Configuración | `app/core/config.py` | ✅ | Settings Pydantic; requiere 12+ env vars |
| Base de datos | `app/core/database.py` | ✅ | AsyncSessionLocal, get_db, init_db |
| Seguridad JWT | `app/core/security.py` | ✅ | hash_password, verify_password, require_roles |
| Encriptación | `app/core/crypto.py` | ✅ | encrypt_value / decrypt_value Fernet; tolerancia legacy |
| App principal | `app/api/main.py` | ✅ | Lifespan, CORS, routers registrados |

### Backend — Modelos (12 tablas)

| Modelo | Archivo | Estado | Notas importantes |
|--------|---------|--------|-------------------|
| Tenant | `app/models/tenant.py` | ✅ | whatsapp_access_token encriptado |
| User | `app/models/user.py` | ✅ | password_hash (no hashed_password). Roles: ADMIN/MANAGER/SUPERVISOR/SALESPERSON/AGENT |
| Client | `app/models/client.py` | ✅ | business_name (no name). zone_name=columna texto, zone=relationship FK. avg_purchase_frequency_days |
| Product | `app/models/product.py` | ✅ | sku requerido. rotation_flag (no has_low_rotation). embedding Vector(1024) |
| Zone | `app/models/route.py` | ✅ | Agrupación geográfica de clientes |
| Route | `app/models/route.py` | ✅ | operating_days JSONB (no columna date). RouteType: PRESENTIAL / AGENT_WA |
| RouteVisit | `app/models/route.py` | ✅ | VisitStatus: PENDING/VISITED_SALE/VISITED_NO_SALE/NOT_VISITED/ESCALATED |
| Order | `app/models/order.py` | ✅ | OrderSource: SALESPERSON / AGENT_WA / ADMIN |
| OrderItem | `app/models/order.py` | ✅ | |
| SalesGoal | `app/models/goal.py` | ✅ | GoalPeriodType enum (no string). target_effective_visits, target_active_clients |
| GoalProgress | `app/models/goal.py` | ✅ | Snapshot diario calculado por scheduler |
| Analytics | `app/models/analytics.py` | ✅ | ClientProductAffinity, DailySalesSnapshot |
| Conversation | `app/models/conversation.py` | ✅ | WhatsAppConversation, MessageLog |
| Notification | `app/models/notification.py` | ✅ | NotificationSchedule |

### Backend — Migraciones

| Migración | Estado | Descripción |
|-----------|--------|-------------|
| `001_initial_schema.py` | ✅ (desactualizada — no correr sola) | Schema base original |
| `002_add_pgvector.py` | ✅ | pgvector extension + embedding Vector(1024) + índice IVFFlat |
| `003_sync_schema_with_models.py` | ✅ | Delta: password_hash, business_name, zone_name, rotation_flag, goal_progress, etc. |

> ⚠️ Correr siempre `alembic upgrade head` (aplica las 3). Nunca aplicar 001 sola.

### Backend — API Admin (9 endpoints)

| Router | Archivo | Estado | Endpoints |
|--------|---------|--------|-----------|
| auth | `admin/auth.py` | ✅ | POST /login |
| dashboard | `admin/dashboard.py` | ✅ | GET / (KPIs) |
| salespersons | `admin/salespersons.py` | ✅ | CRUD vendedores |
| clients | `admin/clients.py` | ✅ | CRUD clientes; filtro zone → zone_name |
| productos | `admin/productos.py` | ✅ | CRUD productos + trigger embed |
| zonas | `admin/zonas.py` | ✅ | CRUD zonas; soft delete |
| rutas | `admin/rutas.py` | ✅ | CRUD rutas; valida RouteType y días 1-6 |
| goals | `admin/goals.py` | ✅ | CRUD metas por vendedor |
| settings | `admin/settings.py` | ✅ | WhatsApp config; token encriptado con Fernet |
| reports | `api/v1/reports/__init__.py` | ⬜ | Carpeta vacía — endpoints CSV/PDF pendientes |

### Backend — Agentes IA

| Agente | Archivo | Estado | Métodos clave |
|--------|---------|--------|---------------|
| Base | `agents/base.py` | ✅ | BaseAgent, call_claude() |
| Orquestador | `agents/orchestrator.py` | ✅ | process_inbound_message → delega por rol |
| SalesAgent | `agents/sales_agent.py` | ✅ | morning_briefing, daily_summary, performance_report, respond_to_query |
| ClientAgent | `agents/client_agent.py` | ✅ | pre_visit_notification, no_visit_followup, respond_to_client, generate_order_confirmation |
| ManagementAgent | `agents/management_agent.py` | ✅ | daily_report, weekly_report, low_performance_alert, respond_to_query |

### Backend — Servicios

| Servicio | Archivo | Estado | Notas |
|----------|---------|--------|-------|
| TenantService | `services/tenant_service.py` | ✅ | get_by_phone_number_id, get_all_active_tenants |
| ConversationService | `services/conversation_service.py` | ✅ | get_or_create, update_conversation, ventana 24h |
| WhatsAppService | `services/whatsapp_service.py` | ✅ | send_text/template/interactive, verify_signature HMAC |
| EmailService | `services/email_service.py` | ✅ | SendGrid; sendgrid_api_key opcional en dev |
| OrderService | `services/order_service.py` | ✅ | create_order_from_agent, get_order, list_orders |
| AnalyticsService | `services/analytics_service.py` | ✅ | goal_progress, route_data, recommendations, affinities |
| EmbeddingService | `services/embedding_service.py` | ✅ | build_semantic_text, generate_embedding (Voyage AI, retry 3x), search_products (híbrido) |

> 🔑 EmbeddingService: brand/category/subcategory son filtros WHERE (no van en el vector). Singleton `_voyage_client` a nivel de módulo.

### Backend — Scheduler (Celery)

| Tarea | Horario | Estado |
|-------|---------|--------|
| send_salesperson_morning_briefings | Lun-Sáb 6:30 AM | ✅ |
| send_pre_visit_notifications | Lun-Sáb 8-17h (c/hora) | ✅ |
| send_salesperson_daily_summaries | Lun-Sáb 6:30 PM | ✅ |
| send_salesperson_performance_reports | Lun-Sáb 8:00 PM | ✅ |
| send_no_visit_followups | Lun-Sáb 7:00 PM | ✅ |
| send_management_daily_reports | Lun-Sáb 7:00 AM | ✅ |
| send_management_weekly_reports | Lunes 7:30 AM | ✅ |
| check_and_send_performance_alerts | Lun-Sáb 11AM y 4PM | ✅ |
| calculate_product_affinities | Diario 2:00 AM | ✅ |
| generate_daily_sales_snapshots | Diario 11:55 PM | ✅ |

> 🔑 Filtro de rutas del día: `operating_days @> '[{weekday}]'::jsonb` (no `Route.date`).
> 🔑 Todas las tareas usan `decrypt_value(tenant.whatsapp_access_token)` al instanciar WhatsAppService.

### Backend — Webhook WhatsApp

| Componente | Archivo | Estado |
|-----------|---------|--------|
| Verificación GET | `webhooks/whatsapp.py` | ✅ |
| Recepción POST | `webhooks/whatsapp.py` | ✅ |
| Firma HMAC-SHA256 | `services/whatsapp_service.py` | ✅ |
| Procesamiento async (background task) | `webhooks/whatsapp.py` | ✅ |

### Frontend — Panel Admin (Next.js)

| Página | Ruta | Estado | Líneas |
|--------|------|--------|--------|
| Login | `/login` | ✅ | 93 |
| Dashboard | `/dashboard` | ✅ | 218 |
| Vendedores | `/salespersons` | ✅ | 260 |
| Clientes | `/clients` | ✅ | 390 |
| Productos | `/productos` | ✅ | 376 |
| Rutas + Zonas | `/rutas` | ✅ | 525 |
| Metas | `/goals` | ✅ | 572 |
| Configuración | `/settings` | ✅ | 527 |

> API client en: `frontend/src/lib/api.ts` — 30+ funciones para todos los endpoints.

### Infraestructura

| Componente | Archivo | Estado |
|-----------|---------|--------|
| Dockerfile (API) | `Dockerfile` | ✅ |
| Docker Compose (local) | `docker-compose.yml` | ✅ — API + Celery worker + beat + Flower + PG + Redis |
| Variables de entorno | `.env.example` | ✅ — incluye ENCRYPTION_KEY |
| Migraciones Alembic | `alembic.ini` + `migrations/` | ✅ |
| AWS ECS Fargate | — | ⬜ Pendiente |
| AWS RDS + ElastiCache | — | ⬜ Pendiente |

### Tests

| Módulo | Tests | Estado |
|--------|-------|--------|
| `tests/conftest.py` | — fixtures | ✅ |
| `tests/test_models/test_constraints.py` | 21 | ✅ |
| `tests/test_services/test_crypto.py` | 9 | ✅ |
| `tests/test_services/test_embedding_service.py` | 15 | ✅ |
| `tests/test_services/test_order_service.py` | 8 | ✅ |
| `tests/test_api/test_webhook.py` | 9 | ✅ |
| `tests/test_scheduler/test_tasks.py` | 13 | ✅ |
| Agentes (SalesAgent, ClientAgent, ManagementAgent) | — | ⬜ |
| ConversationService | — | ⬜ |
| AnalyticsService | — | ⬜ |
| Tests de integración (BD real) | — | ⬜ |

### Documentación

| Documento | Estado | Versión |
|-----------|--------|---------|
| `docs/ARCHITECTURE.md` | ✅ | Incluye pgvector, Voyage AI, crypto |
| `docs/DATA_DICTIONARY.md` | ✅ | v1.8.0 — semantic_tags, embedding |
| `docs/ESTADO_PROYECTO.md` | ✅ | v1.0.0 (este archivo) |
| `docs/ROADMAP.md` | ✅ | v1.0.0 |

### Scripts

| Script | Estado | Uso |
|--------|--------|-----|
| `scripts/seed_tenant.py` | ✅ | `python scripts/seed_tenant.py` — crea tenant completo con 40 clientes, 30 productos, 90 días historial |

---

## 3. Decisiones técnicas tomadas (no reabrir)

Estas decisiones están implementadas y documentadas. No requieren revisión salvo cambio de requisitos mayor.

| Decisión | Contexto | Archivos afectados |
|----------|----------|--------------------|
| **Fernet para encriptación simétrica** | AES-128-CBC + HMAC-SHA256. Llave en env var `ENCRYPTION_KEY`, nunca en BD. Tolerancia legacy: `decrypt_value` retorna plaintext si el token no es Fernet válido (migración sin downtime). | `app/core/crypto.py`, `app/api/v1/admin/settings.py`, `app/api/v1/webhooks/whatsapp.py`, `app/scheduler/tasks.py` |
| **Separación estructural/semántica en embeddings** | brand, category, subcategory son filtros WHERE exactos. No se incluyen en el vector para no degradar precisión del embedding. Se filtran con `.ilike()` en `search_products`. | `app/services/embedding_service.py` |
| **zone_name vs zone en Client** | La columna texto libre se llama `zone_name`. El relationship FK a Zone se llama `zone`. Evita conflicto de nombres en SQLAlchemy mapper. | `app/models/client.py`, `app/api/v1/admin/clients.py` |
| **operating_days JSONB en Route** | `Route` no tiene columna `date`. Los días de operación se almacenan como array JSONB de enteros ISO (1=Lun…6=Sáb). Filtro del día actual: `operating_days @> '[{weekday}]'::jsonb`. | `app/models/route.py`, `app/scheduler/tasks.py` |
| **Soft delete** | Nunca hard delete. `is_active = False` para desactivar registros. Las queries de producción siempre filtran `is_active == True`. | Todos los modelos con is_active |
| **UserRole.AGENT** | Usuario virtual asignado a rutas `AGENT_WA`. No tiene password. El orquestador lo usa para diferenciar si el contacto lo inicia el agente IA o un vendedor humano. | `app/models/user.py`, `app/models/route.py` |
| **asyncio.run() en Celery** | Puente sync→async para tareas Celery. Cada tarea pública llama `asyncio.run(_funcion_async())`. | `app/scheduler/tasks.py` |
| **Singleton _voyage_client** | Cliente Voyage AI instanciado a nivel de módulo para evitar overhead de conexión por llamada. | `app/services/embedding_service.py:40` |
| **password_hash (no hashed_password)** | Migración 003 renombró el campo. Usar siempre `password_hash` en el modelo User. La función es `hash_password()` en security.py (no `get_password_hash`). | `app/models/user.py`, `app/core/security.py` |
| **GoalPeriodType enum** | El campo `period_type` en SalesGoal es un enum SA (`GoalPeriodType.MONTHLY`), no string. | `app/models/goal.py` |

---

## 4. Trabajo pendiente (priorizado)

### P1 — Bloqueante para staging con tenant real

| # | Tarea | Qué hacer | Archivo(s) a tocar | Dependencias |
|---|-------|-----------|-------------------|--------------|
| 1 | **Task de indexación RAG en background** | Crear tarea Celery `index_product_task` que dispare automáticamente cuando se crea/actualiza un producto. Hoy el embedding se genera manualmente. | `app/scheduler/tasks.py` + `app/api/v1/admin/productos.py` | EmbeddingService ✅ |
| 2 | **Inicializar Sentry en main.py** | `sentry_sdk.init(dsn=settings.sentry_dsn, ...)` en el lifespan de `app/api/main.py`. Está configurado en settings pero nunca se llama. | `app/api/main.py` | Settings ✅ |
| 3 | **Runbook de deploy a staging** | Script shell + guía paso a paso: clonar repo, configurar `.env`, correr `alembic upgrade head`, levantar Docker Compose, ejecutar seed, verificar webhook ngrok. | `docs/DEPLOY.md` (nuevo) | Docker ✅ |
| 4 | **Script ngrok para desarrollo** | Script que levanta ngrok y actualiza automáticamente el webhook URL en la configuración de Meta. | `scripts/start_dev.sh` (nuevo) | — |

### P2 — Necesario para producción

| # | Tarea | Qué hacer | Archivo(s) a tocar |
|---|-------|-----------|-------------------|
| 5 | **Infraestructura AWS** | Terraform o CDK: ECS Fargate (API + Celery), RDS PostgreSQL 16 con pgvector, ElastiCache Redis, ALB, S3. | `infra/` (nuevo) |
| 6 | **CI/CD GitHub Actions** | Pipeline: lint (ruff), tests (pytest), build Docker, push ECR, deploy ECS. | `.github/workflows/` (nuevo) |
| 7 | **Gestión de tenants (admin SaaS)** | Endpoints para crear/suspender/configurar tenants desde la plataforma. Hoy se hace con seed manual. | `app/api/v1/admin/tenants.py` (nuevo) |
| 8 | **Tests de integración** | Tests contra BD real (PostgreSQL), cobertura de agentes, ConversationService, AnalyticsService. | `tests/integration/` (nuevo) |
| 9 | **Reports API** | Endpoints de exportación CSV/PDF para reportes de ventas, clientes, metas. | `app/api/v1/reports/` (carpeta vacía) |

### P3 — Mejoras y escalabilidad

| # | Tarea | Descripción |
|---|-------|-------------|
| 10 | Cobertura de tests al 80% | Agentes, ConversationService, AnalyticsService sin cobertura hoy |
| 11 | Rate limiting en API | Throttle por tenant para WhatsApp y endpoints admin |
| 12 | Observabilidad | Dashboards Grafana/CloudWatch para métricas de mensajes, costos AI, latencia |
| 13 | Panel multi-tenant (super admin) | Vista consolidada de todos los tenants para el equipo SaaS |
| 14 | Internacionalización frontend | Soporte para otros países (Venezuela, Ecuador) |

---

## 5. Guía de retoma (para nueva sesión)

### Qué leer primero (en orden)
1. **Este documento** — estado completo del proyecto
2. `app/core/config.py` — todas las variables de entorno requeridas
3. `app/api/main.py` — punto de entrada de la aplicación
4. `app/agents/orchestrator.py` — flujo central de mensajes
5. `app/scheduler/tasks.py` — flujo proactivo programado

### Levantar el entorno local
```bash
cd /Users/oscarmauriciogomezacevedo/claudecode/salesagent

# 1. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales reales

# 2. Levantar infraestructura
docker-compose up -d postgres redis

# 3. Aplicar migraciones (siempre las 3)
alembic upgrade head

# 4. Poblar datos de prueba
python scripts/seed_tenant.py

# 5. Levantar API
docker-compose up api

# 6. Frontend
cd frontend && npm install && npm run dev
```

### Reglas de trabajo (preferencias del usuario)
- **Idioma:** español colombiano
- **Flujo:** mostrar resumen del plan → esperar "autorizado" → ejecutar
- **Commits:** solo cuando el usuario lo pide explícitamente
- **Commits automáticos:** NUNCA

### Convención de nombres
| Qué | Convención |
|----|-----------|
| Nuevo endpoint admin | Agregar al router en `app/api/v1/admin/__init__.py` |
| Nuevo campo sensible en BD | Usar `encrypt_value()` al guardar, `decrypt_value()` al leer. Ver `app/core/crypto.py` |
| Nueva tarea Celery | Función pública `@celery_app.task` + función privada `async def _nombre()` |
| Filtro de rutas del día actual | `sa_text(f"routes.operating_days @> '[{weekday}]'::jsonb")` |
| Nuevo campo en User/Client/Product | Crear migración en `migrations/versions/00N_descripcion.py` |
| Tests nuevos | Mockear `AsyncSessionLocal` vía context manager `_Ctx`. Ver `tests/conftest.py` |

---

## 6. Historial de sesiones

| Sesión | Fecha | Trabajo realizado | Commit(s) |
|--------|-------|-------------------|-----------|
| 1-2 | 2026-03-25 | Schema inicial, modelos, API admin base, agentes, scheduler esqueleto | `e311eb4` |
| 3 | 2026-04-04 | RAG + pgvector + Voyage AI (embedding_service), migración 002 | `e311eb4` |
| 4a | 2026-04-10 | Scheduler completo (8 tareas), encriptación Fernet, zonas/rutas endpoints, frontend productos/rutas | `11d2c58` `6197e35` |
| 4b | 2026-04-11 | Seed reescrito (40 clientes, 30 productos, 90d historia), migración 003, suite tests (75 tests), CLAUDE.md + docs | `6e4b670` `47db787` |
