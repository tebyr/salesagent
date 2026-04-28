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
| 1.3.1   | 2026-04-27 | 10     | Setup Meta: portfolio ibcaribe SAS + App IbSales Agent + sandbox WhatsApp activo. Credenciales obtenidas. |
| 1.4.0   | 2026-04-27 | 11     | LiteLLM como capa IA + AIUsageLog (modelo + migración 004) + Fase 1 montaje local + docs/MONTAJE_LOCAL.md |
| 1.5.0   | 2026-04-28 | 12     | Fase 3 montaje local completada: SAEnum native_enum=False, Docker networking fix, seed exitoso, API + Celery operativos |
| 1.6.0   | 2026-04-28 | 13     | WhatsApp e2e: 5 bugs críticos corregidos (phone_normalized, ORM serialization, ConversationRole, Groq model, force-recreate). `get_salesperson_today_context()`. Primera conversación real exitosa. |
| 1.6.1   | 2026-04-28 | 14     | Normalización completa de enums (`values_callable`). Frontend en Docker Compose (`--profile dev`). Fix @radix-ui/react-badge. Panel web operativo en localhost:3000. |

---

## 1. Resumen ejecutivo

SaaS B2B para distribuidoras colombianas del canal tradicional. Un agente supervisor multi-rol que atiende vendedores de campo por WhatsApp, envía notificaciones proactivas a los tenderos (clientes), y reporta KPIs a la gerencia por email.

**Directorio del proyecto:** `/Users/oscarmauriciogomezacevedo/claudecode/salesagent`
**Repositorio:** `https://github.com/tebyr/salesagent.git` (rama `master`)
**Último commit:** `e172e54` — feat: LiteLLM provider-agnostic + AIUsageLog + Groq dev + local stack operativo v1.5.0 *(pendiente commit sesiones 11–14)*

### Stack
| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI (async) |
| Base de datos | PostgreSQL 16 + SQLAlchemy async (asyncpg) |
| Migraciones | Alembic (4 migraciones — `alembic upgrade head`) |
| Cache / Queue | Redis + Celery (worker + beat) |
| IA — Agentes | **LiteLLM** ≥ 1.40 (provider-agnostic: Anthropic / OpenAI / Google / Mistral) |
| IA — Modelos default | Haiku (simple) · Sonnet (estándar) · Opus (complejo) — configurables en `.env` |
| IA — Embeddings | Voyage AI voyage-3 (1024 dims) + pgvector IVFFlat |
| IA — Costos | `AIUsageLog` — trazabilidad completa por tenant; umbrales mensuales alertables |
| Mensajería | WhatsApp Business Cloud API (Meta oficial) |
| Email | SendGrid |
| Encriptación | Fernet AES-128-CBC (cryptography) |
| Frontend | Next.js 14 App Router + React Query + Tailwind |
| Infra local | Docker Compose (API + Celery worker + beat + Flower + PG + Redis) |
| Infra cloud | AWS ECS Fargate + RDS + ElastiCache (pendiente) |

### Avance global: **~90%**

```
Backend core (modelos, DB, API admin, agentes)   ████████████████████  99%
Scheduler + servicios                             ████████████████████  95%
Frontend panel admin                              ████████████████████  90%
RAG / búsqueda semántica                         █████████████████░░░  85%
Tests                                             ████████████████░░░░  75%
Infraestructura local (Docker)                   ████████████████████ 100%
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

### Backend — Modelos (15 modelos)

| Modelo | Archivo | Estado | Notas importantes |
|--------|---------|--------|-------------------|
| Tenant | `app/models/tenant.py` | ✅ | whatsapp_access_token encriptado |
| User | `app/models/user.py` | ✅ | password_hash (no hashed_password). Roles: ADMIN/MANAGER/SUPERVISOR/SALESPERSON/AGENT. SAEnum con `native_enum=False, values_callable`. Valores en BD: lowercase. |
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
| Conversation | `app/models/conversation.py` | ✅ | WhatsAppConversation, MessageLog. Fix sesión 11: `ai_tokens_used` tipo Integer. ConversationRole: SALESPERSON/CLIENT/MANAGER (no VENDOR). SAEnum con `values_callable` → valores BD lowercase. |
| Notification | `app/models/notification.py` | ✅ | NotificationSchedule |
| **AIUsageLog** | `app/models/ai_usage.py` | ✅ | Trazabilidad de cada llamada IA: provider, model, tokens, cost_usd. Umbrales mensuales por tenant. |

### Backend — Migraciones

| Migración | Estado | Descripción |
|-----------|--------|-------------|
| `001_initial_schema.py` | ✅ (desactualizada — no correr sola) | Schema base original |
| `002_add_pgvector.py` | ✅ | pgvector extension + embedding Vector(1024) + índice IVFFlat |
| `003_sync_schema_with_models.py` | ✅ | Delta: password_hash, business_name, zone_name, rotation_flag, goal_progress, etc. |
| `004_add_ai_usage_logs.py` | ✅ | Tabla `ai_usage_logs` + 3 índices (tenant, conversation, composite tenant+created). Fix `message_logs.ai_tokens_used` String→Integer. |

> ⚠️ Correr siempre `alembic upgrade head` (aplica las 4). Nunca aplicar 001 sola.

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
| Base | `agents/base.py` | ✅ | BaseAgent, `_call_ai()` via **LiteLLM** (provider-agnostic). `_persist_usage()` background. `_extract_text()`, `_extract_content_and_tools()`. MODEL_PRICING dict para cost cálculo local. |
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
| AnalyticsService | `services/analytics_service.py` | ✅ | goal_progress, route_data, recommendations, affinities. **+`get_salesperson_today_context()`** — enriquece user_info con métricas del día (month_goal_pct, today_sales, clients_today, visited_today). |
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
| Docker Compose (local) | `docker-compose.yml` | ✅ — API + Celery worker + beat + Flower + PG + Redis + **Frontend** (`--profile dev`) |
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
| `docs/DATA_DICTIONARY.md` | ✅ | v1.9.0 — tabla `ai_usage_logs` con MODEL_PRICING, índices y query SQL de ejemplo |
| `docs/ESTADO_PROYECTO.md` | ✅ | v1.4.0 (este archivo) |
| `docs/ROADMAP.md` | ✅ | v1.4.0 |
| `docs/MONTAJE_LOCAL.md` | ✅ | Guía 4 fases montaje local: herramientas, .env, servicios, WhatsApp e2e. Credenciales sandbox Meta. |
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
| **LiteLLM como capa de abstracción IA** | Todos los agentes usan `litellm.acompletion()` en vez del cliente Anthropic directo. Cambiar de proveedor = cambiar el nombre del modelo en `.env` (ej. `AI_MODEL_STANDARD=gpt-4o`). Tools en formato Anthropic (`input_schema`) se convierten internamente a formato OpenAI (`parameters`) vía `_convert_tools_to_litellm()`. Respuestas siempre en formato OpenAI: `response.choices[0].message`. | `app/agents/base.py`, `requirements.txt`, `.env.example` |
| **Groq como proveedor IA en desarrollo** | Para pruebas locales se usa Groq (tier gratuito, 6K tokens/min) con `llama-3.3-70b-versatile` (estándar/complejo) y `llama-3.1-8b-instant` (simple). `llama-3.1-70b-versatile` fue dado de baja por Groq en abril 2026. Para producción: cambiar `AI_MODEL_*` a `claude-*` y poner `ANTHROPIC_API_KEY`. Las API keys de todos los proveedores son opcionales en config — al menos una debe estar presente en runtime. Ver [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations) ante futuros cambios de modelos. | `app/core/config.py`, `.env`, `.env.example`, `docs/MONTAJE_LOCAL.md` |
| **AIUsageLog — costo por tenant** | Cada llamada IA registra en `ai_usage_logs` de forma fire-and-forget (`asyncio.create_task`). No bloquea la respuesta al usuario. Costo calculado localmente con `MODEL_PRICING` dict (USD/1M tokens). Umbrales mensuales: `AI_COST_ALERT_THRESHOLD_USD` (warning) y `AI_COST_HARD_LIMIT_USD` (error en logs). Índice compuesto `(tenant_id, created_at)` para queries de costo mensual eficientes. | `app/models/ai_usage.py`, `app/agents/base.py`, `migrations/versions/004_add_ai_usage_logs.py` |
| **SAEnum native_enum=False en todos los modelos** | asyncpg intenta hacer cast al tipo ENUM nativo de PostgreSQL (ej. `$6::userrole`). Como las migraciones crean los campos como `VARCHAR(20)`, se usa `SAEnum(Enum, native_enum=False)` en **todos** los modelos para que SQLAlchemy los trate como strings. **NUNCA** crear un `SAEnum` sin este parámetro. Afecta: UserRole, ConversationRole, ConversationState, OrderStatus, OrderSource, NotificationEventType, GoalPeriodType, RouteType, RouteStatus, VisitType, VisitStatus. | `app/models/user.py`, `app/models/conversation.py`, `app/models/order.py`, `app/models/notification.py`, `app/models/goal.py`, `app/models/route.py` |
| **Docker Compose — override de hostnames para contenedores** | El `.env` usa `localhost:5433` / `localhost:6379` para scripts locales (seed, alembic). Los servicios dentro de Docker (api, celery-worker, celery-beat) deben conectar a los hostnames de servicio: `postgres:5432` y `redis:6379`. Se sobreescriben vía sección `environment:` en `docker-compose.yml` (no en `.env`). Variables afectadas: `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`. | `docker-compose.yml`, `.env` |
| **phone_normalized para lookup de WhatsApp** | Meta envía números sin `+` (`573174003589`). El campo `phone` en User/Client tiene `+573174003589`. Siempre buscar por `phone_normalized` en queries que reciben un número de WhatsApp. Nunca usar `User.phone == phone_norm` — usar `User.phone_normalized == phone_norm`. | `app/services/conversation_service.py` |
| **ConversationRole enum — valores correctos** | `ConversationRole` tiene `SALESPERSON`, `CLIENT`, `MANAGER`. **No existe `VENDOR`**. El orquestador debe comparar contra `ConversationRole.SALESPERSON` o el string `"salesperson"`. El rol viene de `user_info["role"]` como string, no como enum, por lo que se compara contra ambos. | `app/agents/orchestrator.py`, `app/models/conversation.py` |
| **Serializar conversación ORM antes de pasar al orquestador** | `ConversationService.get_or_create_conversation()` retorna un objeto `WhatsAppConversation` ORM. El orquestador espera un `dict` con claves `state`, `recent_messages`, `context`. El webhook serializa el objeto antes de pasarlo: `{"state": conv.state.value, "recent_messages": list(conv.recent_messages or []), "context": dict(conv.context or {})}`. | `app/api/v1/webhooks/whatsapp.py` |
| **Enriquecimiento de user_info para vendedores** | Al recibir un mensaje de un vendedor, el webhook llama `AnalyticsService.get_salesperson_today_context()` antes de invocar el orquestador. Agrega a `user_info`: `month_goal_pct`, `today_sales`, `clients_today`, `visited_today`. Con try/except graceful — si falla, el agente sigue con valores "N/A". | `app/api/v1/webhooks/whatsapp.py`, `app/services/analytics_service.py` |
| **docker compose up --force-recreate para cambios en .env** | `docker compose restart` NO recarga el `.env`. Para que los contenedores lean nuevos valores de `.env`, usar `docker compose up -d --force-recreate api`. Aplica especialmente a cambios en `AI_MODEL_*`, `GROQ_API_KEY`, `VOYAGE_API_KEY`. | `docker-compose.yml`, `.env` |
| **SAEnum values_callable — enums en lowercase** | SQLAlchemy con `native_enum=False` y `str, enum.Enum` almacena el NOMBRE del enum (uppercase, ej. `DELIVERED`). Para que use el VALOR Python (lowercase, ej. `delivered`), todos los SAEnum deben incluir `values_callable=lambda obj: [e.value for e in obj]`. Sin esto, SQLAlchemy genera comparaciones uppercase que no coinciden con valores lowercase en BD. **Todos los SAEnum del proyecto ya tienen este parámetro.** Los valores en BD son canónicamente lowercase. | `app/models/user.py`, `app/models/conversation.py`, `app/models/order.py`, `app/models/goal.py`, `app/models/route.py`, `app/models/notification.py` |

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

### ✅ P2 — Completado (sesión 12)

| # | Tarea | Estado | Notas |
|---|-------|--------|-------|
| 16 | **Fase 3: servicios** | ✅ | API:8000 + Celery worker/beat operativos. Login verificado. Seed: 40 clientes, 30 productos, 221 pedidos. |

### ✅ P2 — Completado (sesión 13)

| # | Tarea | Estado | Notas |
|---|-------|--------|-------|
| 15 | **Completar Fase 2 .env** | ✅ | `VOYAGE_API_KEY` + `GROQ_API_KEY` + `WHATSAPP_APP_SECRET` configurados |
| 17 | **Fase 4: WhatsApp e2e** | ✅ | ngrok activo, webhook Meta configurado, tenant configurado, mensajes e2e funcionando (Oscar Gomez → SalesAgent) |

### ✅ P2 — Completado (sesión 14)

| # | Tarea | Estado | Notas |
|---|-------|--------|-------|
| 20 | **Normalización enums SAEnum** | ✅ | `values_callable` en 11 SAEnum de 6 modelos. BD migrada a lowercase. Frontend panel web operativo en localhost:3000. |

### P2 — Frente activo sesión 15

| # | Tarea | Qué hacer |
|---|-------|-----------|
| 18 | **Actualizar tests de integración** | Tests en `tests/integration/test_agents_*.py` mockean `agent.client.messages.create` (Anthropic). Deben migrar a mockear `litellm.acompletion`. |
| 19 | **Probar flujo tendero e2e** | Configurar un número de cliente en seed, enviar mensaje desde ese número y verificar que el `ClientAgent` responde correctamente con RAG |

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

# 1. Variables de entorno — .env ya completo:
# GROQ_API_KEY ✅  WHATSAPP_APP_SECRET ✅  VOYAGE_API_KEY ✅
# AI_MODEL_STANDARD=groq/llama-3.3-70b-versatile (llama-3.1-70b fue dado de baja)

# 2. Levantar infraestructura (Postgres en :5433, Redis en :6379)
docker compose up -d postgres redis

# 3. Aplicar migraciones (siempre las 4: 001→002→003→004)
source venv/bin/activate
alembic upgrade head

# 4. Poblar datos de prueba
python scripts/seed_tenant.py
# Admin: admin@lagarantia.co / Garantia2026!

# 5. Levantar todos los servicios
docker compose up -d api celery-worker celery-beat

# 6. Verificar
curl http://localhost:8000/docs         # Swagger UI
docker compose ps                       # Todos deben estar Up

# 7. Frontend — opción A: nativo (recomendado en Mac, hot-reload instantáneo)
cd frontend && npm run dev   # dependencias ya instaladas
# opción B: en Docker (todo en un comando, hot-reload más lento)
# docker compose --profile dev up -d
```

> ⚠️ **Postgres.app local v14 corre en :5432** — Docker usa :5433 para evitar conflicto.
> ⚠️ Las variables `DATABASE_URL` y `CELERY_BROKER_URL` en `.env` usan `localhost` (para scripts).
>    Los contenedores Docker las sobreescriben vía `environment:` en `docker-compose.yml`.

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
| 10 | 2026-04-27 | Setup Meta externo: portfolio ibcaribe SAS + App IbSales Agent + WhatsApp sandbox activo. Credenciales obtenidas (App ID, App Secret, Phone Number ID, WABA ID). Sin cambios de código. | `70ce3c9` |
| 11 | 2026-04-28 | LiteLLM como capa IA (provider-agnostic). AIUsageLog + migración 004 (trazabilidad costos). Fix MessageLog.ai_tokens_used. docs/MONTAJE_LOCAL.md (4 fases). Fase 1 local validada. DATA_DICTIONARY tabla ai_usage_logs. Groq integrado como proveedor de pruebas gratuito. | pendiente commit |
| 12 | 2026-04-28 | **Fase 3 montaje local completada.** SAEnum `native_enum=False` en 6 modelos (fix asyncpg cast). Docker networking fix (localhost→service hostnames en compose). docker-compose.yml corregido. Seed exitoso: 40 clientes, 30 prods, 3 vendedores (Oscar Gomez, Sandra Gutierrez, Danilo Juvinao), 221 pedidos. API:8000 + Celery worker/beat operativos. Login verificado. | pendiente commit |
| 13 | 2026-04-28 | **Fase 4 WhatsApp e2e completada.** 5 bugs corregidos en el flujo conversacional: (1) `phone_normalized` para lookup, (2) serializar ORM conversation a dict, (3) `ConversationRole.SALESPERSON` no `VENDOR`, (4) modelo Groq decommissioned → `llama-3.3-70b-versatile`, (5) `docker compose --force-recreate` para recargar .env. Nuevo `AnalyticsService.get_salesperson_today_context()`. Enriquecimiento user_info en webhook. Primera conversación e2e exitosa: Oscar Gomez → SalesAgent respondiendo con métricas reales. | pendiente commit |
| 14 | 2026-04-28 | **Normalización enums + panel web.** `values_callable=lambda obj: [e.value for e in obj]` en 11 SAEnum de 6 modelos. BD migrada a lowercase (221 órdenes, 6 rutas, 5 usuarios, 3 metas, 1 conversación). `docker-compose.yml` +servicio `frontend` con `--profile dev`. Fix `@radix-ui/react-badge` (paquete inexistente). Panel admin Next.js operativo en `localhost:3000`. | pendiente commit |
