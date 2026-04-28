# Sales Agent SaaS - Arquitectura del Sistema

## Vision General

Agente supervisor de equipos comerciales para distribuidoras que atienden el canal tradicional
en Colombia. Modelo SaaS multi-tenant construido sobre Python, Claude AI y WhatsApp Business API.

El agente actúa como capa de inteligencia y comunicación entre tres actores:
- **Vendedores**: briefings, recomendaciones de ruta, reportes de rendimiento
- **Clientes**: avisos pre-visita, toma de pedidos por WhatsApp, follow-up
- **Gerencia**: reportes de KPIs, alertas, proyecciones por email

**Alcance deliberado:** El agente gestiona pedidos (pre-documentos), no facturas. La facturación electrónica queda en el ERP de cada distribuidora con su NIT y habilitación DIAN. Ver sección [Integración ERP](#integracion-erp).

---

## Stack Tecnologico

| Componente        | Tecnologia                            | Justificacion                                    |
|-------------------|---------------------------------------|--------------------------------------------------|
| Backend API       | Python 3.12 + FastAPI                 | Async nativo, alto rendimiento, tipado fuerte    |
| Base de datos     | PostgreSQL 16 + pgvector              | Multi-tenant, ACID, JSONB + búsqueda vectorial   |
| Cache / Queue     | Redis (AWS ElastiCache)               | Estado conversaciones + Celery broker            |
| AI - Capa         | **LiteLLM ≥ 1.40** (provider-agnostic)| Cambiar proveedor = cambiar env var; sin tocar código |
| AI - Simple       | `groq/llama-3.1-8b-instant` (dev) · `claude-haiku-*` (prod) | Notificaciones rutinarias (menor costo) |
| AI - Estandar     | `groq/llama-3.3-70b-versatile` (dev) · `claude-sonnet-*` (prod) | Recomendaciones, respuestas reactivas |
| AI - Complejo     | `groq/llama-3.3-70b-versatile` (dev) · `claude-opus-*` (prod) | Reportes gerenciales (máxima calidad) |
| AI - Costos       | `AIUsageLog` en BD                    | Trazabilidad por tenant; umbrales mensuales alertables |
| WhatsApp          | Meta Cloud API (oficial)              | Sin costo de plataforma, escalable               |
| Email             | SendGrid                              | Reportes gerenciales HTML                        |
| Scheduler         | Celery + Celery Beat                  | Tareas programadas y en background               |
| Infraestructura   | AWS (ECS Fargate + RDS + ElastiCache) | Escalable + control de costos                    |
| Monitoreo         | Sentry + CloudWatch                   | Errores + metricas de costo                      |
| Migraciones       | Alembic (async)                       | Versionado de esquema de BD                      |
| ORM               | SQLAlchemy 2.x async                  | Queries async nativas, tipado fuerte             |
| Busqueda semantica| pgvector (extension PostgreSQL)       | Indice IVFFlat, similitud coseno con operador `<=>` |
| Embeddings        | Voyage AI voyage-3 (1024 dims)        | Mejor soporte español y dominios B2B vs OpenAI   |

---

## Arquitectura Multi-Agente

### Diagrama general

```
Mensaje WhatsApp
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                   ORQUESTADOR                       │
│  1. Identifica tenant (por número WA del destinatario)│
│  2. Identifica rol del remitente (users / clients)  │
│  3. Carga estado de conversación (wa_conversations) │
│  4. Clasifica intención del mensaje                 │
│  5. Enruta al sub-agente correcto                   │
└──────────────┬──────────────────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌──────────┐ ┌────────┐ ┌────────────┐
│  Agente  │ │ Agente │ │   Agente   │
│ Vendedor │ │Cliente │ │  Gerencia  │
│          │ │        │ │            │
│ Briefing │ │Pre-vis.│ │ KPI Report │
│ Resumen  │ │Pedidos │ │ Alertas    │
│ Rendim.  │ │Follow-up│ │ Proyecc.  │
└──────────┘ └────────┘ └────────────┘
       │           │           │
       └───────────┴───────────┘
                   │
       ┌───────────▼──────────────┐
       │         LiteLLM          │
       │  (provider-agnostic)     │
       │  Groq / Anthropic /      │
       │  OpenAI / Google...      │
       │  (selección dinámica     │
       │   por complejidad)       │
       └───────────┬──────────────┘
                   │
       ┌───────────▼──────────────┐
       │      PostgreSQL          │
       │  (multi-tenant, todas    │
       │   las tablas con         │
       │   tenant_id)             │
       └──────────────────────────┘
```

### Responsabilidades del Orquestador

El orquestador (`app/agents/orchestrator.py`) es el único punto de entrada para mensajes WhatsApp. **No contiene lógica de negocio** — solo enruta.

- Recibe el webhook de Meta
- Valida la firma HMAC del request
- Identifica el tenant por `whatsapp_phone_number_id`
- Busca el remitente en `users` y `clients` del tenant
- Lee el estado de `wa_conversations`
- **[Solo vendedores]** Enriquece `user_info` con métricas del día vía `AnalyticsService.get_salesperson_today_context()` — agrega `month_goal_pct`, `today_sales`, `week_sales`, `priority_clients` (top 8 por días sin compra), `top_products` (top 5 por revenue 60d). Degradación graceful: si falla, el agente continúa con valores "N/A".
- Llama al sub-agente correspondiente
- Persiste la respuesta y actualiza el estado
- Maneja fallbacks si el sub-agente falla

### Responsabilidades de cada Sub-Agente

Cada sub-agente (`app/agents/sales_agent.py`, `client_agent.py`, `management_agent.py`):

- Tiene su propio system prompt con tono, capacidades y restricciones del rol
- Carga únicamente el contexto relevante para su rol (no toda la BD)
- Devuelve `(texto_respuesta, nuevo_estado)` al orquestador
- Es **stateless**: el estado lo gestiona el orquestador
- Selecciona el modelo vía LiteLLM según la complejidad de la tarea (`AI_MODEL_SIMPLE/STANDARD/COMPLEX` en `.env`)

---

## Patrones de Diseño Conversacional

### Intention-Based UI

El agente no usa menús fijos. Interpreta la intención del usuario en lenguaje natural y responde a ella. Las intenciones están clasificadas en:

| Categoría | Ejemplos |
|---|---|
| `INFORMATIONAL` | Consulta de precio, estado de pedido, historial |
| `TRANSACTIONAL` | Hacer pedido, cancelar, registrar novedad |
| `OPERATIONAL` | Confirmar visita, check-in, reporte de ruta |
| `RELATIONAL` | Saludo, queja, agradecimiento |
| `OUT_OF_SCOPE` | Solicitud fuera del alcance del agente |

El orquestador clasifica la intención antes de enrutar al sub-agente, usando un prompt ligero con Haiku para minimizar costos.

### Natural Language Data Ingestion

Los datos se capturan en lenguaje natural, no en formularios. El flujo estándar:

```
Usuario: "Agrega a Ferretería Los Pinos, don Carlos, Calle 5 con Carrera 8, tel 3154421890"
         │
         ▼ Extracción de entidades (LLM)
         │
         ▼ Validación de campos obligatorios
         │
         ▼ Presentar resumen estructurado
         │
Usuario: "SÍ" / "el teléfono es 3154422890"
         │
         ▼ Persistir / corregir campo y volver a presentar
```

**Regla:** Confirmar siempre antes de persistir. Correcciones parciales no reinician el flujo.

### Confirmation-Before-Commit

Toda acción irreversible (crear pedido, registrar visita, dar de alta cliente) requiere confirmación explícita del usuario con resumen legible de lo que se va a ejecutar.

### Máquina de Estados de Conversación

```
IDLE → GREETING → [SALESPERSON_MENU | CLIENT_MENU | MANAGER_MENU]
                        │                  │
                  TAKING_ORDER       TAKING_ORDER
                  REPORTING_VISIT    QUERY
                  QUERY
                        │
                     CLOSED
```

El estado se persiste en `wa_conversations.state` y `wa_conversations.context` (JSONB).

**Timeout de sesión:** Si el usuario no responde en 30 minutos durante un flujo activo, el estado vuelve a `IDLE` y el borrador se guarda o descarta según el tipo de flujo.

---

## Flujo Diario Programado

```
06:30 ──► VENDEDORES: Briefing matutino (Sonnet)
          - Ruta del día con clientes prioritarios
          - Meta diaria sugerida vs avance del mes
          - Promociones activas para empujar
          - Clientes en riesgo de churn o Venta 0

08:00-17:00 ──► CLIENTES: Notificación pre-visita (Haiku)
              - "Tu asesor viene hoy entre X y Y"
              - Productos recomendados para su negocio
              - Mejores ofertas del día

18:30 ──► VENDEDORES: Resumen del día (Haiku)
          - Clientes visitados vs ruta planificada
          - Total vendido del día
          - Clientes no visitados

19:00 ──► CLIENTES NO VISITADOS: Toma de pedido directa (Sonnet)
          - "Tu asesor no pudo visitarte hoy"
          - Ofrece tomar el pedido directamente
          - Si responde, inicia flujo Natural Language Data Ingestion

20:00 ──► VENDEDORES: Reporte de rendimiento (Sonnet)
          - % cumplimiento de meta
          - Proyección al cierre del mes
          - Gap y ventas necesarias por día
          - 3 acciones recomendadas

07:00 (diario) ──► GERENCIA (email, Opus): Reporte diario
                   - KPIs del equipo
                   - Semáforo por vendedor
                   - Alertas críticas

07:30 (lunes) ──► GERENCIA (email, Opus): Reporte semanal
                  - Tendencias semana anterior
                  - Proyección mensual
                  - Plan de acción sugerido
```

El scheduler usa Celery Beat (`app/scheduler/tasks.py`). La hora base es `America/Bogota`. Cada tenant puede tener su propia configuración en `tenants.schedule_config` (JSONB).

---

## Modelo de Datos Multi-Tenant

Todas las tablas tienen `tenant_id` como FK a `tenants`. Cada query del sistema filtra por `tenant_id` obligatoriamente — jamás se hace una query global entre tenants.

```
tenants
  ├── users (vendedores, gerentes, admins)
  │     └── external_id + external_source  ← integración ERP
  ├── clients (comercios del canal tradicional)
  │     ├── business_owners (propietarios - entidad separada)
  │     ├── client_typologies (catálogo configurable por tenant)
  │     └── external_id + external_source  ← integración ERP
  ├── geo_countries / departments / municipalities
  │     └── geo_populated_centers / geo_neighborhoods (DANE)
  ├── suppliers → brands → categories → subcategories
  │     └── products → product_packaging
  │           └── external_id + external_source  ← integración ERP
  ├── promotions → promotion_items
  ├── routes (con daily_schedule JSONB)
  │     ├── route_assignments (historial vendedor-ruta)
  │     └── route_clients (N:N ruta-cliente)
  ├── route_visits
  ├── orders (pre-documento; factura queda en ERP)
  │     ├── order_items
  │     ├── order_returns / order_return_items
  │     └── external_id + external_source  ← integración ERP
  ├── erp_imports (log de integraciones entrantes)
  ├── sales_goals
  │     ├── goal_progress
  │     └── goal_benefits (beneficios por nivel de cumplimiento)
  ├── wa_conversations
  │     └── message_logs
  ├── notification_schedules
  └── analytics
        ├── client_product_affinities
        └── daily_sales_snapshots
```

Para la documentación completa de cada tabla y campo, ver `docs/DATA_DICTIONARY.md`.

---

## Integración ERP

### Principio fundamental

El agente es una **capa de inteligencia y comunicación**, no un sistema de facturación. La responsabilidad fiscal (factura electrónica, DIAN, CUFE) permanece en el ERP de cada distribuidora.

### Flujo de integración

```
AGENTE (SaaS)                    ERP DEL TENANT
      │                                 │
      │─── Pedido tomado en WA          │
      │─── Asigna reference_code ──────►│
      │                                 │─── Valida stock
      │                                 │─── Aprueba/ajusta
      │                                 │─── Genera factura electrónica DIAN
      │◄── external_id + estado ────────│
      │─── Notifica al cliente          │
      │    "Tu pedido fue confirmado"   │
```

### Canales de integración soportados

| Canal | Casos de uso | Latencia |
|---|---|---|
| Webhook API REST | ERP con API moderna | Tiempo real |
| CSV upload | ERP sin API (World Office básico) | Batch (horas) |
| XML upload | Formatos heredados | Batch (horas) |

### Patrón de trazabilidad por entidad

Cada entidad sincronizada con ERP tiene:
- `external_id`: ID que el ERP asigna al registro (nace NULL, ERP lo llena)
- `external_source`: nombre del sistema (`siesa`, `world_office`, `sap`, `helisa`)
- Restricción única `(tenant_id, external_id)` para evitar duplicados

Aplica a: `users`, `clients`, `products`, `orders`.

---

## Gestión de WhatsApp

### Ventana de conversación de 24 horas

WhatsApp solo permite enviar mensajes libres dentro de una ventana de 24h desde el último mensaje del usuario. Fuera de esa ventana se requiere un Template Message pre-aprobado por Meta.

**Estrategia de costos:** Si el usuario respondió el briefing de la mañana, aprovechar esa ventana para el resumen de la tarde sin abrir una nueva sesión.

### Templates requeridos por tenant

| Template | Tipo | Cuándo se usa |
|---|---|---|
| `briefing_matutino` | Utility | Iniciar conversación con vendedor cada mañana |
| `pre_visita_cliente` | Utility | Notificar cliente antes de la visita |
| `pedido_confirmado` | Utility | Confirmar que el ERP procesó el pedido |
| `reporte_rendimiento` | Utility | Reporte nocturno al vendedor |
| `follow_up_no_visita` | Utility | Cliente no visitado en el día |

Cada tenant configura sus propios templates en `tenants.whatsapp_phone_number_id` y el acceso en `tenants.whatsapp_access_token`.

### Configuración por tenant

```python
{
  "whatsapp_phone_number_id": "...",     # ID del número en Meta
  "whatsapp_business_account_id": "...", # WABA ID
  "whatsapp_access_token": "...",        # Token de acceso (cifrado en BD)
  "whatsapp_phone_display": "+57 300..." # Número visible al usuario
}
```

---

## Control de Costos AI

### Selección de modelo por tarea

La capa es **LiteLLM** — el nombre del modelo se configura en `.env` (`AI_MODEL_SIMPLE/STANDARD/COMPLEX`). Por defecto en desarrollo se usa Groq (gratuito). En producción apuntar a Claude.

| Tarea | Tier | Modelo dev (Groq) | Modelo prod (Anthropic) |
|---|---|---|---|
| Notificación pre-visita | Simple | llama-3.1-8b-instant | claude-haiku-* |
| Resumen diario vendedor | Simple | llama-3.1-8b-instant | claude-haiku-* |
| Clasificación de intención | Simple | llama-3.1-8b-instant | claude-haiku-* |
| Briefing matutino vendedor | Estándar | llama-3.3-70b-versatile | claude-sonnet-* |
| Reporte rendimiento vendedor | Estándar | llama-3.3-70b-versatile | claude-sonnet-* |
| Respuesta reactiva compleja | Estándar | llama-3.3-70b-versatile | claude-sonnet-* |
| Reporte gerencial email | Complejo | llama-3.3-70b-versatile | claude-opus-* |

**Estimación mensual por tenant en producción (40 vendedores, 3.000 clientes, con Claude):**
- Proactivo diario: ~$15-25/mes en AI
- Mensajes reactivos (estimado): ~$5-10/mes
- Reportes gerenciales: ~$2-5/mes
- **Total AI: ~$25-40/mes por tenant**

Todos los costos se registran en `ai_usage_logs` por tenant. Umbrales configurables: `AI_COST_ALERT_THRESHOLD_USD` (warning) y `AI_COST_HARD_LIMIT_USD` (error en logs).

### Regla de fallback de modelo

```
Si el modelo estándar falla → reintentar con el modelo simple (respuesta degradada pero entregada)
Si el modelo complejo falla → reintentar con el estándar (reporte menos profundo pero disponible)
Registrar toda degradación en logs para análisis de calidad
```

---

## Infraestructura AWS

```
Tier de arranque (2-3 tenants):
├── ECS Fargate: 0.5 vCPU / 1GB RAM × 3 servicios = ~$25/mes
├── RDS PostgreSQL db.t3.micro = ~$15/mes
├── ElastiCache Redis cache.t3.micro = ~$13/mes
├── ALB = ~$16/mes
├── CloudWatch + Logs = ~$5/mes
└── Total infra: ~$74/mes

Meta Cloud API (WhatsApp):
├── Colombia: ~$0.024/conversación (ventana de 24h)
├── Estimado 3.000 clientes × 4 conversaciones/mes = ~$288/mes por tenant
└── Optimización clave: consolidar mensajes en ventanas abiertas
```

---

## Seguridad

### Aislamiento multi-tenant

- Todo query incluye `WHERE tenant_id = :tenant_id` como condición obligatoria
- Los tokens de WhatsApp y API keys de terceros se almacenan cifrados en BD
- Ningún endpoint del API retorna datos de otro tenant, incluso con token válido

### Autenticación

- **Panel admin:** JWT con expiración corta + refresh token
- **WhatsApp:** El número de teléfono identifica al usuario. Acciones sensibles requieren verificación adicional.
- **Webhooks entrantes (Meta):** Validación de firma HMAC-SHA256 con `WHATSAPP_VERIFY_TOKEN`

### Datos sensibles

- `whatsapp_access_token`: cifrado en BD con Fernet (AES-128-CBC + HMAC-SHA256) via `app/core/crypto.py`. Nunca expuesto en logs ni respuestas API
- `password_hash`: bcrypt via `passlib`, nunca expuesto
- PII (nombre, teléfono, dirección): acceso restringido por rol y tenant

### Encripción simétrica en BD (`app/core/crypto.py`)

Todo valor sensible que se persista en BD se cifra con Fernet antes de almacenarse. La llave (`ENCRYPTION_KEY`) vive exclusivamente en variables de entorno, nunca en la BD.

```
encrypt_value(plaintext)  →  token Fernet  →  columna Text en BD
decrypt_value(ciphertext) →  plaintext     →  usado en servicios / scheduler
```

`decrypt_value` es tolerante a valores legacy (texto plano previos al cifrado), lo que permite activar la encripción en producción sin downtime ni migración de datos.

**Campos actualmente cifrados:**

| Tabla | Campo | Cifrado desde |
|---|---|---|
| `tenants` | `whatsapp_access_token` | v1.9.0 |

---

## Graceful Degradation

```
Nivel 1 — No entendí el mensaje
  → Respuesta amigable pidiendo reformular. No escalar.

Nivel 2 — Datos insuficientes para completar la acción
  → Pedir el campo faltante específico. Continuar el flujo.

Nivel 3 — Falla del modelo de IA
  → Reintentar con modelo más ligero. Registrar en Sentry.

Nivel 4 — Falla de BD o servicio externo
  → Informar demora al usuario. Guardar intención en cola Celery.

Nivel 5 — Falla crítica
  → Derivar a canal alternativo. Alertar equipo técnico.
```

Nunca exponer al usuario: stack traces, errores HTTP, nombres de tablas o campos internos.

---

## Estructura de Archivos

```
app/
├── agents/
│   ├── orchestrator.py      # Punto de entrada mensajes WA
│   ├── sales_agent.py       # Lógica agente vendedores
│   ├── client_agent.py      # Lógica agente clientes
│   └── management_agent.py  # Lógica agente gerencia
├── api/
│   └── v1/
│       ├── webhooks/
│       │   └── whatsapp.py  # Endpoint webhook Meta (GET verify + POST mensajes)
│       ├── platform/
│       │   └── tenants.py   # API super-admin SaaS (gestión de tenants)
│       ├── reports/         # Reports CSV + PDF (ventas, clientes, metas)
│       └── admin/           # Panel de administración
│           ├── auth.py
│           ├── dashboard.py
│           ├── salespersons.py
│           ├── clients.py
│           ├── goals.py
│           └── settings.py
├── models/                  # SQLAlchemy models (16 tablas)
│   ├── tenant.py
│   ├── user.py
│   ├── client.py
│   ├── product.py
│   ├── order.py
│   ├── route.py
│   ├── goal.py
│   ├── conversation.py
│   ├── notification.py
│   ├── analytics.py
│   └── ai_usage.py          # AIUsageLog — trazabilidad de costos IA por tenant
├── scheduler/
│   └── tasks.py             # Tareas Celery programadas (11 tareas)
├── services/
│   ├── whatsapp_service.py  # Meta Cloud API
│   ├── analytics_service.py # KPIs y recomendaciones
│   ├── embedding_service.py # Voyage AI + pgvector
│   ├── conversation_service.py # Estado de conversaciones WA
│   ├── order_service.py     # Creación y consulta de pedidos
│   ├── tenant_service.py    # Lookup de tenants por número WA
│   └── email_service.py     # SendGrid
└── core/
    ├── config.py            # Settings desde .env (API keys opcionales)
    ├── database.py          # Engine async SQLAlchemy
    ├── security.py          # JWT, hash_password, require_roles
    └── crypto.py            # encrypt/decrypt Fernet

docs/
├── ARCHITECTURE.md          # Este documento
└── DATA_DICTIONARY.md       # Diccionario completo de tablas y campos

migrations/
└── versions/
    └── 001_initial_schema.py

frontend/
└── src/
    ├── app/                 # Next.js pages
    └── components/          # React components
```

---

## Configuración de WhatsApp Business por Tenant

Para cada tenant se necesita:
1. Cuenta de Meta Business Manager verificada
2. WhatsApp Business Account (WABA) — una por empresa distribuidora
3. Número de teléfono verificado y habilitado para mensajería
4. App en Meta for Developers con permisos `whatsapp_business_messaging`
5. Templates de mensajes pre-aprobados (proceso: 1-3 días hábiles)

---

## Roadmap

### v1.0 (Actual)
- Agentes: vendedor, cliente, gerencia
- WhatsApp bidireccional (Intention-Based UI)
- Natural Language Data Ingestion para pedidos y clientes
- Scheduler de notificaciones (Celery Beat)
- Analytics básicos (afinidad cliente-producto, KPIs)
- Multi-tenant completo
- Integración ERP via external_id/external_source

### v2.0 (Siguiente)
- ✅ Panel web de administración (Next.js) — operativo en localhost:3000
- Integración ERP en tiempo real (Siesa, World Office) via webhook
- Georeferenciación y optimización de rutas
- Gestión de cartera y cobros
- ML para predicción de churn

### v3.0 (Futuro)
- Llamadas de voz con IA
- App móvil para vendedores (offline-first)
- Integración plataformas de pago
- Marketplace B2B
- Expansión a otros países de la región
