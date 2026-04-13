# Estado del Proyecto — Sales Agent SaaS

> **Documento vivo.** Se actualiza al cierre de cada sesión de trabajo mediante `/actualizar-estado`.
> Es la fuente de verdad para retomar el proyecto sin releer el código.

---

## Control de versiones

| Versión | Fecha      | Sesión | Cambios |
|---------|------------|--------|---------|
| 1.0.0   | 2026-04-11 | 4      | Documento inicial. Estado al cierre del bloque 2 (seed + tests) |
| 1.0.1   | 2026-04-11 | 4      | +CLAUDE.md, +/actualizar-estado command, +ROADMAP.md, +skill 09_project_state_management |
| 1.1.0   | 2026-04-11 | 5      | P1 completo: index_product_task, Sentry init, docs/DEPLOY.md, scripts/start_dev.sh |
| 1.2.0   | 2026-04-11 | 6      | API platform/tenants (ítem 7) + Reports API CSV/PDF (ítem 9) + seed_platform.py |
| 1.2.1   | 2026-04-11 | 7      | +docs/formacion/ (guía IA generativa v1.2 + checklist) + docs/go_to_market/ (resumen ejecutivo, KPIs, ROI) |
| 1.2.2   | 2026-04-11 | 8      | RAG integration en ClientAgent: `_build_rag_recommendations` + firmas backward-compatible + docx actualizado |
| 1.3.0   | 2026-04-12 | 9      | Tests de integración (ítem 8, 28 tests) + suite completa de docs técnicos + skill `/mantener-docs` |

---

## 1. Resumen ejecutivo

SaaS B2B para distribuidoras colombianas del canal tradicional. Un agente supervisor multi-rol que atiende vendedores de campo por WhatsApp, envía notificaciones proactivas a los tenderos (clientes), y reporta KPIs a la gerencia por email.

**Directorio del proyecto:** `/Users/oscarmauriciogomezacevedo/claudecode/salesagent`
**Repositorio:** `https://github.com/tebyr/salesagent.git` (rama `master`)
**Último commit:** `7608082` — docs: add full documentation suite + mantener-docs skill

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

### Avance global: **~87%**

```
Backend core (modelos, DB, API admin, agentes)   ████████████████████  98%
Scheduler + servicios                             ████████████████████  95%
Frontend panel admin                              ████████████████████  90%
RAG / búsqueda semántica                         █████████████████░░░  85%
Tests                                             ████████████████░░░░  75%
Infraestructura local (Docker)                   ████████████████████  95%
Infraestructura cloud (AWS)                       ░░░░░░░░░░░░░░░░░░░░   0%
CI/CD                                             ░░░░░░░░░░░░░░░░░░░░   0%
Documentación                                     ████████████████████ 100%
```

---

## 2. Mapa de componentes

### Backend — Core

| Componente | Archivo(s) clave | Estado | Notas |
|-----------|-----------------|--------|-------|
| Configuración | `app/core/config.py` | ✅ | Settings Pydantic; requiere 12+ env vars |
| Base de datos | `app/core/database.py` | ✅ | AsyncSessionLocal, get_db, init_db |
| Seguridad JWT | `app/core/security.py` | ✅ | hash_password, verify_password, require_roles, require_platform_admin. JWT incluye tenant_slug |
| Encriptación | `app/core/crypto.py` | ✅ | encrypt_value / decrypt_value Fernet; tolerancia legacy |
| App principal | `app/api/main.py` | ✅ | Lifespan, CORS, routers registrados. Sentry init con FastApi/SQLAlchemy/CeleryIntegration |

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
| reports | `api/v1/reports/` | ✅ | 5 endpoints: ventas CSV+PDF, clientes CSV, metas CSV+PDF. Filtros: date_from/to, salesperson_id |

### Backend — API Platform (super-admin SaaS)

| Router | Archivo | Estado | Endpoints |
|--------|---------|--------|-----------|
| tenants | `platform/tenants.py` | ✅ | GET / · POST / · GET {id} · PATCH {id} · POST {id}/suspend · POST {id}/activate · POST {id}/reset-token |

> 🔑 Acceso exclusivo: `role=admin` + `tenant_slug=__platform__` (validado por `require_platform_admin`).
> 🔑 Crear super-admin con: `python scripts/seed_platform.py --email x --password y`
> 🔑 El tenant `__platform__` nunca aparece en listados de tenants del panel admin.

### Backend — Agentes IA

| Agente | Archivo | Estado | Métodos clave |
|--------|---------|--------|---------------|
| Base | `agents/base.py` | ✅ | BaseAgent, call_claude() |
| Orquestador | `agents/orchestrator.py` | ✅ | process_inbound_message → delega por rol |
| SalesAgent | `agents/sales_agent.py` | ✅ | morning_briefing, daily_summary, performance_report, respond_to_query |
| ClientAgent | `agents/client_agent.py` | ✅ | pre_visit_notification, no_visit_followup, respond_to_client, generate_order_confirmation. **RAG integrado:** `_build_rag_recommendations` (top-3 categorías por affinity_score + búsqueda semántica). Firmas backward-compatible (`client_id=None, db=None`). |
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
| **index_product_task** | On-demand (trigger en create/update producto) | ✅ |

> 🔑 `index_product_task`: bind=True, max_retries=3, delay=60s. ValueError (texto insuficiente) → log warn sin retry. Recibe `product_id` y `tenant_id`.
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
| `tests/integration/conftest.py` | — fixtures BD real (SAVEPOINT) | ✅ |
| `tests/integration/test_conversation_service.py` | 7 | ✅ |
| `tests/integration/test_analytics_service.py` | 6 | ✅ |
| `tests/integration/test_agents_sales.py` | 5 | ✅ |
| `tests/integration/test_agents_client.py` | 6 | ✅ |
| `tests/integration/test_agents_management.py` | 4 | ✅ |

### Documentación

| Documento | Estado | Versión |
|-----------|--------|---------|
| `docs/ARCHITECTURE.md` | ✅ | Incluye pgvector, Voyage AI, crypto |
| `docs/DATA_DICTIONARY.md` | ✅ | v1.8.0 — semantic_tags, embedding |
| `docs/ESTADO_PROYECTO.md` | ✅ | v1.3.0 (este archivo) |
| `docs/ROADMAP.md` | ✅ | v1.3.0 |
| `docs/DEPLOY.md` | ✅ | Runbook completo: clonar, .env, migraciones, seed, Docker, ngrok, smoke tests |
| `docs/TESTING.md` | ✅ | Guía completa: unitarios, integración, SAVEPOINT, convenciones |
| `docs/ONBOARDING.md` | ✅ | Modelo mental, flujos, mapa de archivos, convenciones |
| `docs/SECURITY.md` | ✅ | JWT, Fernet, HMAC, roles, multi-tenancy, LFPDP Colombia |
| `docs/OPS.md` | ✅ | Runbook operacional: logs, operaciones manuales, Celery, Sentry |
| `docs/TENANT_ONBOARDING.md` | ✅ | 8 pasos para incorporar nueva distribuidora |
| `docs/API_REFERENCE.md` | ✅ | Todos los endpoints con request/response y ejemplos |
| `docs/DOCS_MANIFEST.md` | ✅ | Manifiesto docs ↔ código para skill /mantener-docs |
| `docs/formacion/guia_ia_generativa_consultoria_v1.2.md` | ✅ | Guía de estudio IA generativa para consultoría |
| `docs/formacion/checklist_avance_roadmap.md` | ✅ | Checklist de avance del roadmap |
| `docs/go_to_market/Agente_Comercial_IA_Resumen_Ejecutivo.docx` | ✅ | Resumen ejecutivo del producto para stakeholders |
| `docs/go_to_market/bateria_indicadores_kpi.md` | ✅ | Batería de indicadores KPI |
| `docs/go_to_market/marco_roi_monetizacion.md` | ✅ | Marco de ROI y monetización |
| `CLAUDE.md` | ✅ | Arranque automático con @import |
| `.claude/commands/actualizar-estado.md` | ✅ | Slash command /actualizar-estado (incluye paso 3c) |
| `~/.claude/commands/mantener-docs.md` | ✅ | Skill global reutilizable /mantener-docs |

### Scripts

| Script | Estado | Uso |
|--------|--------|-----|
| `scripts/seed_tenant.py` | ✅ | `python scripts/seed_tenant.py` — crea tenant completo con 40 clientes, 30 productos, 90 días historial |
| `scripts/start_dev.sh` | ✅ | `./scripts/start_dev.sh` — levanta ngrok, obtiene URL pública, muestra instrucciones para configurar webhook en Meta |
| `scripts/seed_platform.py` | ✅ | `python scripts/seed_platform.py` — crea tenant `__platform__` y super-admin SaaS. Idempotente. |

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
| **RAG graceful degradation en ClientAgent** | `_build_rag_recommendations` captura toda excepción, loguea `rag_recommendations_failed` con structlog y retorna `[]`. El caller sigue usando las `recommendations` originales. `ClientProductAffinity` NO tiene `total_net_value` ni `category` directa — se usa `affinity_score` como proxy y se hace JOIN con `Product` para obtener categoría. | `app/agents/client_agent.py` |

---

## 4. Trabajo pendiente (priorizado)

### ✅ P1 — Completado (sesión 4–5)

| # | Tarea | Estado | Commit |
|---|-------|--------|--------|
| 1 | Task de indexación RAG en background (`index_product_task`) | ✅ | `be73138` |
| 2 | Inicializar Sentry en `app/api/main.py` | ✅ | pendiente commit |
| 3 | Runbook de deploy a staging (`docs/DEPLOY.md`) | ✅ | pendiente commit |
| 4 | Script ngrok para desarrollo (`scripts/start_dev.sh`) | ✅ | pendiente commit |

### ✅ P1 ex-P2 — Ítems independientes completados (sesión 6)

| # | Tarea | Estado | Commit |
|---|-------|--------|--------|
| 7 | API gestión de tenants (`/api/v1/platform/tenants/`) | ✅ | `7c5f50a` |
| 9 | Reports API — ventas/clientes/metas CSV+PDF | ✅ | `7682fad` |

### ✅ P1 ex-P2 — Tests de integración completados (sesión 9)

| # | Tarea | Estado | Commit |
|---|-------|--------|--------|
| 8 | Tests de integración (28 tests, BD real, agentes, servicios) | ✅ | `1c0e4a0` |

### P1 — Bloqueante para producción (frente activo)

| # | Tarea | Qué hacer | Archivo(s) a tocar |
|---|-------|-----------|-------------------|
| 5 | **Infraestructura AWS** | Terraform o CDK: ECS Fargate (API + Celery), RDS PostgreSQL 16 con pgvector, ElastiCache Redis, ALB, S3. Requiere decisiones externas (cuenta AWS, dominio, región). | `infra/` (nuevo) |
| 6 | **CI/CD GitHub Actions** | Pipeline: lint (ruff), tests (pytest), build Docker, push ECR, deploy ECS. Depende de ítem 5. | `.github/workflows/` (nuevo) |

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
| 4b | 2026-04-11 | Seed reescrito (40 clientes, 30 productos, 90d historia), migración 003, suite tests (75 tests) | `6e4b670` `47db787` |
| 4c | 2026-04-11 | CLAUDE.md + ESTADO_PROYECTO.md + ROADMAP.md + /actualizar-estado + skill 09_project_state_management | `3d765fe` |
| 5  | 2026-04-11 | P1 completo: index_product_task (RAG), Sentry init en main.py, DEPLOY.md runbook, scripts/start_dev.sh ngrok | `be73138` `907602b` |
| 6  | 2026-04-11 | API platform/tenants CRUD (ítem 7) + Reports API CSV+PDF ventas/clientes/metas (ítem 9) + seed_platform.py | `7c5f50a` `7682fad` |
| 7  | 2026-04-11 | docs/formacion/ + docs/go_to_market/ — 5 archivos de estrategia y formación | `377c7f6` |
| 8  | 2026-04-11 | RAG integration ClientAgent: `_build_rag_recommendations` (top-3 cat + search_products), backward-compat, graceful degradation. Docx go_to_market actualizado. | `a86cb8c` |
| 9  | 2026-04-12 | Tests de integración (ítem 8, 28 tests): ConversationService, AnalyticsService, SalesAgent, ClientAgent, ManagementAgent. Suite completa de docs técnicos (7 docs). Skill `/mantener-docs` global. | `1c0e4a0` `7608082` |
