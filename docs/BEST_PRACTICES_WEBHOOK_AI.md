# Best Practices — Webhook WhatsApp & Agentes IA

> **Audiencia:** equipo técnico que mantiene o escala el sistema.  
> **Objetivo:** maximizar la calidad de las respuestas y minimizar el costo de tokens en producción.  
> **Fecha:** 2026-04-28 | Versión 1.0

---

## Índice

1. [Selección de modelo por intención](#1-selección-de-modelo-por-intención)
2. [Gestión del historial de conversación](#2-gestión-del-historial-de-conversación)
3. [Diseño del contexto: qué incluir y cuándo](#3-diseño-del-contexto-qué-incluir-y-cuándo)
4. [Prompts eficientes para WhatsApp](#4-prompts-eficientes-para-whatsapp)
5. [Caché de contexto analítico](#5-caché-de-contexto-analítico)
6. [Webhook: procesamiento asíncrono y latencia](#6-webhook-procesamiento-asíncrono-y-latencia)
7. [Monitoreo de costos con AIUsageLog](#7-monitoreo-de-costos-con-aiusagelog)
8. [Degradación graceful](#8-degradación-graceful)
9. [Límites de tokens por tipo de respuesta](#9-límites-de-tokens-por-tipo-de-respuesta)
10. [Consideraciones de escalabilidad multi-tenant](#10-consideraciones-de-escalabilidad-multi-tenant)

---

## 1. Selección de modelo por intención

Usar el modelo más potente para todo es el error más caro. Cada llamada debe usar el modelo mínimo suficiente para la tarea.

### Tabla de asignación actual

| Tarea | Modelo | Razón |
|-------|--------|-------|
| Briefing matutino (proactivo) | `ai_model_standard` | Genera resumen estructurado con datos reales |
| Respuesta a consulta del vendedor | `ai_model_standard` | Razonamiento + contexto extenso |
| Resumen diario | `ai_model_standard` | Síntesis de múltiples métricas |
| Generación de recomendaciones cliente | `ai_model_standard` | Necesita inferencia sobre historial |
| Notificación pre-visita (simple) | `ai_model_simple` | Texto corto, template-like |
| Reporte de rendimiento | `ai_model_standard` | Proyecciones y cálculos |
| Reporte gerencial (email) | `ai_model_complex` | Análisis estratégico multi-vendedor |
| Alertas de bajo rendimiento | `ai_model_simple` | Mensaje corto con datos ya calculados |

### Regla práctica

```
simple  → confirmaciones, saludos, mensajes cortos (< 100 tokens output)
standard → conversación contextual, recomendaciones, resúmenes
complex  → análisis estratégico, comparativas multi-período, reportes ejecutivos
```

### Implementación en código

```python
# En el agente, detectar intención antes de llamar al modelo:
SIMPLE_INTENTS = ["gracias", "ok", "listo", "recibido", "entendido", "adiós", "hasta luego"]
COMPLEX_INTENTS = ["análisis", "estrategia", "comparar", "proyección anual", "tendencia"]

def _detect_model(self, message: str) -> str:
    msg_lower = message.lower()
    if any(w in msg_lower for w in SIMPLE_INTENTS):
        return settings.ai_model_simple
    if any(w in msg_lower for w in COMPLEX_INTENTS):
        return settings.ai_model_complex
    return settings.ai_model_standard
```

---

## 2. Gestión del historial de conversación

El historial es el principal driver de tokens de entrada. Cada mensaje acumulado se re-envía en cada llamada.

### Reglas actuales del sistema

- **Máximo 20 mensajes** en `recent_messages` (ventana deslizante con `[-20:]`)
- La ventana de 24h de WhatsApp resetea el contexto naturalmente

### Mejoras recomendadas para producción

**a) Comprimir historial antiguo** — en vez de 20 mensajes completos, resumir los primeros 10:

```python
async def _compress_history(self, history: list) -> list:
    """Si el historial supera 16 mensajes, resumir los primeros 8 en uno."""
    if len(history) <= 16:
        return history
    old_messages = history[:8]
    recent_messages = history[8:]
    # Resumir los mensajes antiguos con el modelo simple
    summary = await self._call_ai(
        messages=old_messages,
        model=settings.ai_model_simple,
        max_tokens=150,
        system="Resume en máximo 2 oraciones los puntos clave de esta conversación.",
    )
    summary_msg = {"role": "assistant", "content": f"[Resumen conversación anterior: {self._extract_text(summary)}]"}
    return [summary_msg] + recent_messages
```

**b) No incluir historial en mensajes proactivos** — los briefings matutinos y notificaciones no son respuestas a una conversación:

```python
# ✅ Correcto — sin historial en proactivos
response = await self.sales_agent.morning_briefing(
    salesperson_name=name,
    route_data=route_data,
    top_recommendations=recs,
    # sin conversation_history
)
```

**c) Truncar mensajes muy largos del historial** — si un mensaje anterior tiene más de 500 caracteres, resumirlo al guardarlo:

```python
MAX_HISTORY_MESSAGE_CHARS = 500

updated_history = (history + [
    {"role": "user",      "content": message[:MAX_HISTORY_MESSAGE_CHARS]},
    {"role": "assistant", "content": response_text[:MAX_HISTORY_MESSAGE_CHARS]},
])[-20:]
```

---

## 3. Diseño del contexto: qué incluir y cuándo

El `context_data` que se pasa al agente es el segundo driver de tokens. Más datos ≠ mejores respuestas; datos relevantes sí.

### Principio: carga diferida por intención

No siempre se necesitan todos los datos. Detectar la intención primero y cargar solo lo necesario:

```python
NEEDS_CLIENT_DATA   = ["cliente", "visita", "ruta", "tienda", "recomend"]
NEEDS_PRODUCT_DATA  = ["producto", "catálogo", "oferta", "vender", "llevar"]
NEEDS_GOAL_DATA     = ["meta", "objetivo", "resultado", "rendimiento", "avance"]

def _needs_clients(self, message: str) -> bool:
    return any(w in message.lower() for w in NEEDS_CLIENT_DATA)
```

### Qué siempre incluir (costo bajo, alto valor)

```python
context_data = {
    "Fecha y día":            f"{today} ({day_name})",
    "Meta mensual (% avance)": month_goal_pct,
    "Ventas mes actual":       month_sales,
    "Ventas semana actual":    week_sales,
    "Ventas hoy":              today_sales,
}
```

### Qué incluir solo si la consulta lo amerita

```python
# Solo si pregunta por clientes o recomendaciones
if _needs_clients(message):
    context_data["Clientes sin compra reciente"] = priority_clients_formatted

# Solo si pregunta por productos o qué vender
if _needs_product_data(message):
    context_data["Productos más vendidos (60d)"] = top_products_formatted
```

### Qué nunca incluir en el contexto

| Campo | Razón |
|-------|-------|
| IDs de base de datos (UUIDs) | El modelo no los necesita, solo aumentan tokens |
| Historial completo de pedidos (> 5) | Resumir como total/promedio |
| Embeddings o datos técnicos internos | No son información accionable |
| Campos `null` o vacíos | Usar `or "No disponible"` antes de incluir |
| Datos de otros vendedores | Cada conversación es privada y por `salesperson_id` |

### Formato eficiente del contexto

Usar texto plano estructurado en vez de JSON o dicts anidados:

```python
# ❌ Ineficiente — JSON anidado ocupa más tokens y confunde al modelo
context_data = {"clients": [{"id": "uuid", "name": "...", "metrics": {"days": 25, ...}}]}

# ✅ Eficiente — texto directo y accionable
"Clientes sin compra reciente":
  • Tienda San Miguel — 25d | ticket: $250,000
  • Tienda Don Aurelio — 23d | ticket: $250,000
```

---

## 4. Prompts eficientes para WhatsApp

WhatsApp tiene restricciones naturales: mensajes largos se cortan, los usuarios leen en diagonal.

### Reglas de formato

1. **Respuestas ≤ 300 palabras** para consultas conversacionales
2. **Usar bullet points** (`•`) en vez de listas numeradas largas
3. **Máximo 3 recomendaciones** por respuesta — más opciones = parálisis de decisión
4. **Un emoji por párrafo** como máximo — no decorar cada línea
5. **Datos concretos siempre** — nombres, montos, días; nunca "algunos clientes" o "varios productos"

### System prompt — buenas prácticas

```python
VENDOR_SYSTEM_PROMPT = """Eres {agent_name}, asistente comercial para {company_name}.

REGLAS DE RESPUESTA:
- Mensajes WhatsApp: máximo 250 palabras
- Siempre menciona datos específicos del contexto (nombres, montos, fechas)
- Máximo 3 recomendaciones por respuesta
- Si no tienes datos suficientes para responder con precisión, dilo claramente
- NO inventes cifras ni nombres de clientes — usa solo los datos del contexto

TONO: directo, positivo, colombiano natural. No formal en exceso.
"""
```

### Instrucción de concisión en el prompt de contexto

Agregar siempre al final del `context_prompt` del agente:

```python
context_prompt += """

IMPORTANTE: Esta respuesta es para WhatsApp. Sé conciso (máximo 200 palabras).
Prioriza la información más accionable. Si hay datos en el contexto, úsalos directamente.
"""
```

---

## 5. Caché de contexto analítico

Las consultas analíticas (metas, ventas, clientes) son costosas en BD pero cambian poco durante el día.

### Caché en memoria por vendedor (Redis recomendado)

```python
import json
from app.core.config import settings
import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url)
    return _redis

CONTEXT_CACHE_TTL = 5 * 60   # 5 minutos — el contexto del día cambia poco

async def get_cached_salesperson_context(salesperson_id: str, tenant_id: str) -> dict:
    redis = await get_redis()
    key = f"sp_ctx:{tenant_id}:{salesperson_id}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    # Calcular y cachear
    svc = AnalyticsService(tenant_id)
    ctx = await svc.get_salesperson_today_context(salesperson_id)
    await redis.setex(key, CONTEXT_CACHE_TTL, json.dumps(ctx, default=str))
    return ctx
```

### Invalidación proactiva del caché

```python
# En el webhook, si se detecta un nuevo pedido en la conversación, invalidar
async def invalidate_salesperson_context(salesperson_id: str, tenant_id: str):
    redis = await get_redis()
    await redis.delete(f"sp_ctx:{tenant_id}:{salesperson_id}")
```

### Prompt caching de LiteLLM (Anthropic)

Claude soporta caché de prefijos en el `system_prompt`. Si el system prompt es estático (no cambia con cada request), marcarlo como cacheable:

```python
# En _call_ai() de base.py, cuando el proveedor es Anthropic:
if "claude" in model:
    kwargs["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
    # El system prompt se envía como bloque con cache_control
    kwargs["system"] = [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"}   # TTL 5 min en Anthropic
        }
    ]
```

**Ahorro estimado:** 90% de los tokens del system prompt en conversaciones recurrentes (mismo vendedor, múltiples mensajes).

---

## 6. Webhook: procesamiento asíncrono y latencia

### Arquitectura actual (correcta)

```
Meta Cloud API → POST /webhook
    → verificar firma HMAC (síncrono, < 1ms)
    → return 200 OK  ← inmediato, antes de procesar
    → background_task: procesar_mensaje()
        → buscar usuario en BD
        → calcular contexto
        → llamar agente IA
        → enviar respuesta por WhatsApp API
```

Meta requiere respuesta en < 20 segundos. El `200 OK` inmediato y el `BackgroundTasks` de FastAPI garantizan esto.

### Tiempo máximo aceptable por etapa

| Etapa | Objetivo | Alerta si supera |
|-------|----------|-----------------|
| Verificación HMAC | < 5ms | 20ms |
| Lookup usuario en BD | < 50ms | 200ms |
| Cálculo de contexto analítico | < 300ms | 1s |
| Llamada al modelo IA | < 3s | 8s |
| Envío por WhatsApp API | < 500ms | 2s |
| **Total end-to-end** | **< 5s** | **15s** |

### Monitoreo de latencia

```python
import time

async def process_inbound_message(...):
    t0 = time.monotonic()
    
    # ... procesamiento ...
    
    elapsed = time.monotonic() - t0
    logger.info("message_processed",
        elapsed_ms=round(elapsed * 1000),
        phone=phone_number,
        model_used=model_name,
    )
    if elapsed > 10:
        logger.warning("slow_message_processing", elapsed_ms=round(elapsed * 1000))
```

### Deduplicación de mensajes

Meta puede reenviar el mismo webhook si no recibe `200 OK` a tiempo. Guardar el `message_id` en Redis para evitar respuestas duplicadas:

```python
async def is_duplicate_message(message_id: str, tenant_id: str) -> bool:
    redis = await get_redis()
    key = f"msg_dedup:{tenant_id}:{message_id}"
    was_set = await redis.set(key, "1", ex=300, nx=True)  # nx=True → solo si no existe
    return not was_set   # True si ya existía (duplicado)
```

---

## 7. Monitoreo de costos con AIUsageLog

El sistema ya registra cada llamada en `ai_usage_logs`. En producción, usar estos datos activamente.

### Queries útiles

```sql
-- Costo total por tenant este mes
SELECT
    t.name,
    COUNT(*) AS llamadas,
    SUM(input_tokens + output_tokens) AS tokens_totales,
    ROUND(SUM(cost_usd)::numeric, 4) AS costo_usd
FROM ai_usage_logs l
JOIN tenants t ON t.id = l.tenant_id
WHERE l.created_at >= date_trunc('month', now())
GROUP BY t.name
ORDER BY costo_usd DESC;

-- Modelos más costosos
SELECT model, COUNT(*), SUM(cost_usd), AVG(input_tokens), AVG(output_tokens)
FROM ai_usage_logs
WHERE created_at >= now() - interval '7 days'
GROUP BY model ORDER BY SUM(cost_usd) DESC;

-- Conversaciones más costosas (posibles loops o sesiones largas)
SELECT conversation_id, COUNT(*), SUM(cost_usd), SUM(input_tokens)
FROM ai_usage_logs
WHERE created_at >= now() - interval '24 hours'
GROUP BY conversation_id
ORDER BY SUM(cost_usd) DESC
LIMIT 10;
```

### Alertas de costo (ya implementadas en `.env`)

```env
AI_COST_ALERT_THRESHOLD_USD=10.0   # warning en logs
AI_COST_HARD_LIMIT_USD=50.0        # error en logs — considerar bloqueo de llamadas
```

Para producción, conectar estas alertas a un canal de Slack/PagerDuty cuando se alcancen los umbrales.

### Estimación de costo mensual en producción

Asumiendo 20 vendedores × 15 mensajes/día × 25 días hábiles = **7,500 llamadas/mes**:

| Escenario | Modelo | Input avg | Output avg | Costo/llamada | Total mes |
|-----------|--------|-----------|------------|---------------|-----------|
| Desarrollo | `groq/llama-3.3-70b` | 800 tokens | 300 tokens | ~$0.0007 | ~$5 |
| Producción mínima | `claude-haiku-4-5` | 800 tokens | 300 tokens | ~$0.0016 | ~$12 |
| Producción estándar | `claude-sonnet-4-6` | 800 tokens | 300 tokens | ~$0.0069 | ~$52 |

> 💡 **Recomendación:** usar Haiku para `ai_model_simple` (60% de las llamadas) y Sonnet solo para `ai_model_standard`/`complex` reduce el costo en ~65% vs usar Sonnet para todo.

---

## 8. Degradación graceful

El sistema debe responder aunque el modelo IA falle o tarde demasiado.

### Patrón actual (conservar y extender)

```python
try:
    ctx = await svc.get_salesperson_today_context(salesperson_id)
    user_info.update(ctx)
except Exception as enrich_err:
    logger.warning("context_enrichment_failed", error=str(enrich_err))
    # Continúa con user_info básico — el agente responde sin métricas
```

### Timeout en llamadas al modelo IA

```python
import asyncio

async def _call_ai_with_timeout(self, *args, timeout: float = 15.0, **kwargs):
    try:
        return await asyncio.wait_for(
            self._call_ai(*args, **kwargs),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("ai_call_timeout", model=kwargs.get("model"))
        # Respuesta de fallback predefinida
        return self._fallback_response()

def _fallback_response(self) -> str:
    return (
        "En este momento estoy experimentando lentitud. "
        "Por favor intenta de nuevo en unos segundos. 🙏"
    )
```

### Fallback de modelo

Si el modelo primario falla (rate limit, error de proveedor), intentar con el secundario:

```python
async def _call_ai_with_fallback(self, messages, model, **kwargs):
    FALLBACK_MODELS = {
        "groq/llama-3.3-70b-versatile": "groq/llama-3.1-8b-instant",
        "claude-sonnet-4-6":            "claude-haiku-4-5",
    }
    try:
        return await self._call_ai(messages=messages, model=model, **kwargs)
    except Exception as e:
        fallback = FALLBACK_MODELS.get(model)
        if fallback:
            logger.warning("model_fallback", primary=model, fallback=fallback, error=str(e))
            return await self._call_ai(messages=messages, model=fallback, **kwargs)
        raise
```

---

## 9. Límites de tokens por tipo de respuesta

Configurar `max_tokens` con precisión evita tokens "de sobra" que nunca se usan pero se facturan como salida potencial en algunos proveedores.

| Tipo de mensaje | `max_tokens` actual | Recomendado prod | Razón |
|----------------|---------------------|-----------------|-------|
| Briefing matutino | 600 | 500 | Resumen estructurado, no largo |
| Respuesta a consulta | 400 | 350 | WhatsApp: < 300 palabras |
| Resumen diario | 500 | 450 | Similar al briefing |
| Reporte rendimiento | 700 | 600 | Incluye proyecciones |
| Notificación pre-visita | 300 | 200 | Mensaje corto al tendero |
| Reporte gerencial (email) | 1024 | 800 | Email no necesita > 600 palabras |
| Alerta bajo rendimiento | 300 | 150 | Solo datos clave + acción recomendada |

### Instrucción de longitud en el prompt

Siempre incluir la restricción de longitud **en el system prompt**, no solo en `max_tokens`:

```python
system = f"""...
LONGITUD MÁXIMA DE RESPUESTA: {max_words} palabras.
Sé conciso. Si tienes que elegir entre completitud y brevedad, elige brevedad.
"""
```

---

## 10. Consideraciones de escalabilidad multi-tenant

### Aislamiento de contexto

Cada llamada al agente incluye `tenant_id` para garantizar que los datos de un tenant nunca se mezclen con otro. Verificar siempre en los filtros de BD:

```python
# ✅ Siempre filtrar por tenant_id
select(Client).where(
    and_(
        Client.tenant_id == self.tenant_id,   # ← obligatorio
        Client.salesperson_id == salesperson_id,
    )
)
```

### Umbrales de costo por tenant

Cada tenant puede tener sus propios umbrales en `ai_usage_logs`. Para tenants en plan `starter`, considerar limitar a `ai_model_simple` para consultas reactivas.

### Cooldown por usuario

Para evitar abuso (usuario enviando spam al agente), implementar rate limiting por `phone_normalized`:

```python
async def check_rate_limit(phone: str, tenant_id: str) -> bool:
    """Máximo 10 mensajes por minuto por número."""
    redis = await get_redis()
    key = f"rl:{tenant_id}:{phone}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    return count > 10
```

### Procesamiento paralelo de tareas Celery

El scheduler envía briefings a todos los vendedores al mismo tiempo. Para tenants con 40+ vendedores, usar `group()` de Celery para paralelizar:

```python
from celery import group

# En vez de un loop síncrono:
tasks = group(
    send_morning_briefing_task.s(sp.id, tenant.id)
    for sp in salespersons
)
tasks.apply_async()
```

---

## Resumen ejecutivo — checklist de producción

### Antes del go-live

- [ ] Configurar `AI_COST_ALERT_THRESHOLD_USD` y `AI_COST_HARD_LIMIT_USD` en `.env`
- [ ] Cambiar `ai_model_simple` a `claude-haiku-4-5` (o `gpt-4o-mini`)
- [ ] Cambiar `ai_model_standard` a `claude-sonnet-4-6` (o `gpt-4o`)
- [ ] Implementar caché Redis para `get_salesperson_today_context()` (TTL 5 min)
- [ ] Implementar deduplicación de mensajes por `message_id`
- [ ] Agregar timeout de 15s en todas las llamadas al modelo IA
- [ ] Configurar alerta de Sentry para `slow_message_processing` (> 10s)

### Monitoreo continuo

- [ ] Dashboard de costo por tenant (query sobre `ai_usage_logs`)
- [ ] Alerta si `avg(input_tokens)` sube > 30% semana a semana (indica context drift)
- [ ] Revisar `ai_usage_logs` semanalmente para detectar conversaciones anómalas
- [ ] Rotar token de WhatsApp antes de que expire (actualmente caduca cada 24h en sandbox)

### Optimizaciones futuras (P3)

| Mejora | Impacto en tokens | Complejidad |
|--------|-------------------|-------------|
| Detección de intención antes del modelo | -40% llamadas a `standard` | Media |
| Compresión de historial antiguo | -30% tokens de entrada | Baja |
| Prompt caching (Anthropic) | -60% tokens system prompt | Baja |
| Fallback automático de modelo | 0 tokens extra, +resiliencia | Media |
| Rate limiting por teléfono | -X% llamadas abusivas | Baja |

---

## Historial de actualizaciones

> Esta sección es mantenida automáticamente por el skill `/mantener-docs`.
> Cada entrada corresponde a una lección aprendida durante el desarrollo o debugging.

| Sesión | Fecha | Sección | Lección incorporada |
|--------|-------|---------|---------------------|
| 15 | 2026-04-28 | §3 Diseño del contexto | Contexto inicial con solo métricas numéricas — el agente decía "no tengo datos" ante preguntas de recomendaciones |
| 15 | 2026-04-28 | §3 Diseño del contexto | Seed no generaba pedidos para la semana actual (`randint(2, freq)`) — agente reportaba $0 semana aunque el mes fuera exitoso |
| 15 | 2026-04-28 | §4 Prompts para WhatsApp | Contexto sin día de semana causaba que el agente alarmara con "$0 esta semana" sin saber que era lunes |

---

*Documento mantenido por el equipo técnico y actualizado automáticamente por `/mantener-docs` al detectar cambios en agentes, webhook o analytics.*
