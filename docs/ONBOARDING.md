# Onboarding — Sales Agent SaaS

> Para el desarrollador que acaba de hacer `git clone`. Este documento te da el modelo mental
> del sistema antes de que leas una línea de código. Léelo completo antes de tocar algo.

---

## 1. Qué es este sistema en una frase

Un agente de IA que reemplaza el trabajo manual de coordinación entre una distribuidora
y su equipo de ventas: avisa a los vendedores qué clientes visitar, avisa a los tenderos
que su vendedor va en camino, y le reporta a gerencia cómo va el equipo — todo por WhatsApp
y email, de forma proactiva y reactiva.

---

## 2. Los tres actores y cómo los atiende el sistema

```
Vendedor de campo  ──WhatsApp──▶  SalesAgent    briefings, metas, consultas
Tendero (cliente)  ──WhatsApp──▶  ClientAgent   pre-visita, pedidos, follow-up
Gerente            ──Email──────▶  ManagementAgent  reportes KPI, alertas
```

Cada actor tiene su propio sub-agente con un system prompt distinto.
El **Orchestrator** recibe todos los mensajes entrantes de WhatsApp y decide
a cuál agente delegarlos según el rol del número de teléfono.

---

## 3. Flujo de un mensaje entrante (WhatsApp → respuesta)

```
Meta Cloud API
    │  POST /api/v1/webhooks/whatsapp
    ▼
webhooks/whatsapp.py
    │  verifica firma HMAC-SHA256
    │  lanza BackgroundTask
    ▼
AgentOrchestrator.process_inbound_message()
    │  ConversationService.get_or_create_conversation()
    │  identifica rol del número (vendedor / cliente / gerente)
    ▼
    ├──(salesperson/supervisor/manager)──▶  SalesAgent.respond_to_query()
    ├──(client)──────────────────────────▶  ClientAgent.respond_to_client()
    └──(manager)─────────────────────────▶  ManagementAgent.respond_to_query()
         │
         ▼
    BaseAgent._call_ai()  →  LiteLLM  →  Groq / Anthropic / OpenAI (provider-agnostic)
         │
         ▼
    WhatsAppService.send_text()  →  Meta Cloud API  →  WhatsApp del usuario
```

**Tiempo total esperado:** < 5 segundos (la respuesta de Claude es el cuello de botella).

---

## 4. Flujo proactivo (scheduler → mensajes automáticos)

Además de responder mensajes, el sistema envía mensajes sin que nadie lo pida.
Celery Beat ejecuta tareas programadas que siguen este patrón:

```
Celery Beat (horario)
    │
    ▼
tasks.py  →  asyncio.run(_funcion_async())
    │  carga todos los tenants activos
    │  por cada tenant:
    │      carga vendedores / rutas / clientes del día
    │      llama al agente correspondiente
    │      envía mensaje vía WhatsApp / SendGrid
    ▼
Meta Cloud API / SendGrid
```

Las 11 tareas programadas están en `app/scheduler/tasks.py`.
Los horarios están en `app/scheduler/config.py` (o definidos en el mismo archivo).

---

## 5. Multi-tenancy — la regla más importante

**Cada tabla tiene `tenant_id`.** Toda query de producción debe filtrar por `tenant_id`.
No hay middleware que lo haga automáticamente — es responsabilidad del código en cada endpoint
y servicio. Nunca hagas un `SELECT` sin `WHERE tenant_id = X`.

El `tenant_id` viene del JWT del usuario autenticado:
```python
current_user = Depends(require_roles(...))
tenant_id = current_user["tenant_id"]
```

El tenant `__platform__` es especial: es el tenant del super-admin SaaS
y tiene acceso a todos los tenants vía `/api/v1/platform/tenants/`.

---

## 6. Mapa de archivos — qué tocar para qué

| Qué quiero hacer | Dónde ir |
|---|---|
| Cambiar el comportamiento de un agente | `app/agents/<nombre>_agent.py` |
| Agregar un endpoint al panel admin | `app/api/v1/admin/<router>.py` |
| Cambiar cuándo se envía una notificación | `app/scheduler/tasks.py` |
| Agregar un campo a un modelo | `app/models/<modelo>.py` + nueva migración |
| Cambiar cómo se envían mensajes WA | `app/services/whatsapp_service.py` |
| Cambiar cómo se calculan afinidades | `app/services/analytics_service.py` |
| Cambiar cómo se generan embeddings | `app/services/embedding_service.py` |
| Agregar una variable de entorno | `app/core/config.py` + `.env.example` |
| Ver todos los endpoints registrados | `app/api/main.py` (routers) |

### Archivos más importantes para entender el sistema

```
app/
├── api/
│   └── main.py                 ← punto de entrada, routers, Sentry init
├── agents/
│   ├── base.py                 ← BaseAgent: _call_ai(), _extract_text()
│   ├── orchestrator.py         ← router de mensajes por rol
│   ├── sales_agent.py          ← lógica para vendedores
│   ├── client_agent.py         ← lógica para tenderos + RAG
│   └── management_agent.py     ← lógica para gerencia
├── scheduler/
│   └── tasks.py                ← todas las tareas Celery (proactivas)
├── services/
│   ├── whatsapp_service.py     ← envío de mensajes + verificación webhook
│   ├── conversation_service.py ← estado de conversaciones
│   ├── analytics_service.py    ← KPIs, afinidades, recomendaciones
│   └── embedding_service.py    ← Voyage AI + búsqueda semántica pgvector
├── models/                     ← 15+ modelos SQLAlchemy (incluye ai_usage.py)
└── core/
    ├── config.py               ← Settings Pydantic (env vars)
    ├── database.py             ← AsyncSessionLocal, init_db
    ├── security.py             ← JWT, hash_password, require_roles
    └── crypto.py               ← encrypt/decrypt Fernet
```

---

## 7. Convenciones del proyecto

### Nombres que NO son intuitivos (errores comunes)

| Lo que podrías asumir | Lo correcto |
|---|---|
| `user.hashed_password` | `user.password_hash` |
| `client.name` | `client.business_name` (nombre del negocio) |
| `product.has_low_rotation` | `product.rotation_flag` |
| `route.date` | `route.operating_days` (JSONB de enteros ISO) |
| `goal.period_type = "monthly"` | `goal.period_type = GoalPeriodType.MONTHLY` (enum) |
| `client.zone` (texto) | `client.zone_name` (texto) / `client.zone` (FK a Zone) |
| `hash_password = get_password_hash(...)` | `hash_password = hash_password(...)` en security.py |
| `Column(SAEnum(MiEnum))` | `Column(SAEnum(MiEnum, native_enum=False))` — **siempre** `native_enum=False` o asyncpg fallará con `type "xxx" does not exist` |
| `User.phone == phone_norm` en queries | `User.phone_normalized == phone_norm` — Meta envía números sin `+` (`573174003589`). El campo `phone` tiene `+573174003589`. Usar siempre `phone_normalized` para buscar por número entrante de WhatsApp |
| `ConversationRole.VENDOR` | `ConversationRole.SALESPERSON` — el enum tiene `SALESPERSON`, `CLIENT`, `MANAGER`. No existe `VENDOR` |

### Patrones recurrentes

**Nuevo endpoint admin:**
```python
# 1. Crear en app/api/v1/admin/mi_recurso.py
router = APIRouter(prefix="/mi-recurso", tags=["mi-recurso"])

@router.get("/")
async def list_recursos(current_user = Depends(require_roles("admin", "manager")), ...):
    tenant_id = current_user["tenant_id"]  # siempre filtrar por tenant
    ...

# 2. Registrar en app/api/v1/admin/__init__.py
router.include_router(mi_recurso.router)
```

**Nueva tarea Celery:**
```python
# Función pública sync (llama la async)
@celery_app.task(bind=True, max_retries=3)
def mi_nueva_tarea(self):
    asyncio.run(_mi_nueva_tarea_async())

# Función privada async (lógica real)
async def _mi_nueva_tarea_async():
    async with AsyncSessionLocal() as db:
        ...
```

**Campo sensible en BD:**
```python
# Al guardar
tenant.whatsapp_access_token = encrypt_value(raw_token)

# Al leer
raw_token = decrypt_value(tenant.whatsapp_access_token)
```

**Filtro de ruta por día de la semana:**
```python
weekday = date.today().isoweekday()  # 1=Lun, 6=Sáb
sa_text(f"routes.operating_days @> '[{weekday}]'::jsonb")
```

---

## 8. Stack de desarrollo — lo que necesitas instalado

```bash
# Requisitos mínimos
Python 3.12
Docker Desktop (para PostgreSQL + Redis)
Node.js 18+ (para el frontend Next.js)
ngrok (para recibir webhooks de WhatsApp en local)

# Instalar dependencias Python
pip install -r requirements.txt

# Levantar infraestructura local (Postgres en :5433, no :5432)
docker compose up -d postgres redis

# Aplicar migraciones (siempre las 4, nunca parcial)
alembic upgrade head

# Poblar datos de prueba
python scripts/seed_tenant.py

# Levantar API
docker-compose up api

# Frontend (separado)
cd frontend && npm install && npm run dev
```

Para el paso a paso completo: ver **`docs/DEPLOY.md`**.

---

## 9. Orden de lectura recomendado del código

1. `app/core/config.py` — qué variables de entorno existen y para qué sirven
2. `app/api/main.py` — cómo arranca la aplicación, qué routers están registrados
3. `app/models/` (todos los archivos) — estructura de datos, entender las 12 tablas
4. `app/agents/orchestrator.py` — flujo central de mensajes entrantes
5. `app/scheduler/tasks.py` — flujo proactivo programado
6. Un agente completo (`sales_agent.py`) — entender el patrón BaseAgent
7. `app/services/analytics_service.py` — cómo se calculan los KPIs

---

## 10. Dónde pedir ayuda

| Duda sobre | Revisar |
|---|---|
| Estado actual del proyecto | `docs/ESTADO_PROYECTO.md` |
| Plan de fases y pendientes | `docs/ROADMAP.md` |
| Decisiones técnicas ya tomadas | Sección 3 de `docs/ESTADO_PROYECTO.md` |
| Schema completo de BD | `docs/DATA_DICTIONARY.md` |
| Cómo hacer deploy | `docs/DEPLOY.md` |
| Cómo correr tests | `docs/TESTING.md` |
| Seguridad y encriptación | `docs/SECURITY.md` |
| Operaciones en producción | `docs/OPS.md` |
