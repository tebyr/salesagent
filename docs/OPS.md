# Runbook Operacional — Sales Agent SaaS

> Para el equipo técnico que opera el sistema en producción o staging.
> Cubre el día a día: monitoreo, diagnóstico, operaciones manuales y mantenimiento.
> Para el deploy inicial ver `docs/DEPLOY.md`. Para seguridad ver `docs/SECURITY.md`.

---

## 1. Verificación de salud del sistema

### Checklist de salud (correr en cualquier momento)

```bash
# 1. API respondiendo
curl https://tu-dominio/health
# Esperado: {"status":"ok","version":"...","env":"production"}

# 2. Celery workers activos
docker exec salesagent-celery-worker celery -A app.scheduler.celery_app inspect active
# o vía Flower: https://tu-dominio:5555

# 3. BD conectada (desde el contenedor de la API)
docker exec salesagent-api python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text
async def check():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text('SELECT count(*) FROM tenants'))
        print('Tenants en BD:', r.scalar())
asyncio.run(check())
"

# 4. Redis accesible
docker exec salesagent-redis redis-cli ping
# Esperado: PONG

# 5. Cola de Celery sin tareas atascadas
docker exec salesagent-celery-worker celery -A app.scheduler.celery_app inspect reserved
# Si hay tareas en reserved hace mucho tiempo, puede haber un worker colgado
```

### Métricas clave a monitorear

| Métrica | Umbral de alerta | Cómo ver |
|---|---|---|
| Latencia API P95 | > 3s | CloudWatch / Sentry Performance |
| Errores API (5xx) | > 1% de requests | Sentry / CloudWatch |
| Cola Celery pendientes | > 50 tareas | Flower |
| Tareas Celery fallidas | > 0 en 1h | Flower / Sentry |
| Costo IA mensual por tenant | > umbral config | `ai_usage_logs` (query por `tenant_id + created_at`) · structlog `ai_call_completed` |
| Conexiones BD activas | > 80% del pool | RDS CloudWatch |

---

## 2. Logs — dónde buscar qué

El sistema usa `structlog` para logs estructurados en formato JSON.

```bash
# Logs de la API en tiempo real
docker-compose logs -f api

# Logs del worker Celery
docker-compose logs -f celery-worker

# Filtrar errores de Claude
docker-compose logs api | grep "ai_call_failed"

# Filtrar errores de RAG
docker-compose logs api | grep "rag_recommendations_failed"

# Ver un tenant específico en logs
docker-compose logs api | grep '"tenant_id": "uuid-del-tenant"'

# En producción (AWS CloudWatch)
aws logs tail /ecs/salesagent-api --follow --filter-pattern "ERROR"
```

### Eventos de log más importantes

| Evento | Qué significa |
|---|---|
| `ai_call_completed` | Claude respondió OK — incluye `input_tokens`, `output_tokens` |
| `ai_call_failed` | Error llamando a Claude — revisar API key o límites |
| `rag_recommendations_failed` | Voyage AI falló — el agente continuó sin RAG |
| `message_processed` | Mensaje de WhatsApp procesado correctamente |
| `tenant_not_found` | Llegó un webhook de un número de teléfono no registrado |
| `whatsapp_send_failed` | Error enviando mensaje — revisar token del tenant |
| `salesperson_context_enrichment_failed` | `AnalyticsService.get_salesperson_today_context()` falló — el agente continuó sin métricas enriquecidas. Verificar BD y revisar el stack trace en Sentry. |

---

## 3. Operaciones manuales frecuentes

### 3.1 Forzar el reenvío de un briefing matutino

Si la tarea de briefing falló o un vendedor reporta que no recibió el mensaje:

```bash
# Abrir shell Python con el contexto de la app
docker exec -it salesagent-api python

# Dentro del shell:
import asyncio
from app.scheduler.tasks import send_salesperson_morning_briefings
asyncio.run(send_salesperson_morning_briefings.__wrapped__())
# O llamar la función async privada directamente para un vendedor específico
```

### 3.2 Re-indexar productos de un tenant (RAG)

Si se cargaron muchos productos en batch y quieres indexarlos sin esperar el trigger:

```bash
docker exec -it salesagent-api python
# Dentro del shell:
import asyncio
from app.scheduler.tasks import index_product_task
from app.core.database import AsyncSessionLocal
from app.models.product import Product
from sqlalchemy import select

async def reindex_all(tenant_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,
            )
        )
        products = result.scalars().all()
        for p in products:
            index_product_task.delay(str(p.id), str(p.tenant_id))
            print(f"Encolado: {p.name}")

asyncio.run(reindex_all("uuid-del-tenant"))
```

### 3.3 Suspender un tenant de urgencia

Si un tenant tiene problemas de pago o comportamiento inapropiado:

```bash
# Vía API de plataforma (recomendado):
curl -X POST https://tu-dominio/api/v1/platform/tenants/{tenant_id}/suspend \
  -H "Authorization: Bearer {platform_admin_jwt}"
# Esto desactiva el tenant Y todos sus usuarios

# O directo en BD (emergencia sin API disponible):
docker exec salesagent-postgres psql -U postgres -d salesagent_db -c "
  UPDATE tenants SET is_active = false WHERE id = 'uuid-del-tenant';
  UPDATE users SET is_active = false WHERE tenant_id = 'uuid-del-tenant';
"
```

### 3.4 Verificar y rotar token de WhatsApp de un tenant

```bash
# Verificar que el token actual funciona
curl -X GET "https://graph.facebook.com/v19.0/{phone_number_id}" \
  -H "Authorization: Bearer {token_del_tenant}"
# Si responde 200: token OK. Si responde 401: token expirado/inválido.

# Rotar via API de plataforma:
curl -X POST https://tu-dominio/api/v1/platform/tenants/{tenant_id}/reset-token \
  -H "Authorization: Bearer {platform_admin_jwt}" \
  -H "Content-Type: application/json" \
  -d '{"new_token": "NUEVO_TOKEN_DE_META"}'
```

### 3.5 Calcular afinidades manualmente

Si la tarea nocturna de afinidades falló:

```bash
docker exec -it salesagent-celery-worker celery -A app.scheduler.celery_app call \
  app.scheduler.tasks.calculate_product_affinities
```

### 3.6 Resetear conversación de un usuario atascado

Si un tendero quedó atascado en un estado de conversación (ej. `taking_order`) y no puede salir:

```bash
docker exec -it salesagent-api python
# Dentro del shell:
import asyncio
from app.services.conversation_service import ConversationService

async def reset(tenant_id, phone):
    svc = ConversationService(tenant_id=tenant_id)
    await svc.reset_conversation(phone=phone)
    print("Conversación reseteada a IDLE")

asyncio.run(reset("uuid-del-tenant", "+573011000101"))
```

---

## 4. Mantenimiento de la base de datos

### 4.1 Backup manual

```bash
# En desarrollo (Docker local)
docker exec salesagent-postgres pg_dump -U postgres salesagent_db \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# En producción (RDS — usar pg_dump contra el endpoint de RDS)
PGPASSWORD=tu_password pg_dump \
  -h tu-rds-endpoint.amazonaws.com \
  -U salesagent \
  -d salesagent_db \
  --no-password \
  > backup_prod_$(date +%Y%m%d).sql
```

### 4.2 Aplicar una migración nueva

```bash
# Siempre usar upgrade head (nunca parcial)
alembic upgrade head

# Verificar estado de migraciones
alembic current
alembic history

# En producción: hacer backup antes de aplicar
# Nunca aplicar migraciones destructivas en hora pico
```

### 4.3 Limpiar datos de prueba en staging

```bash
# Recrear datos frescos (seed es idempotente)
python scripts/seed_tenant.py
# Esto limpia y recrea el tenant de prueba
```

### 4.4 Monitorear tamaño de tablas

```bash
docker exec salesagent-postgres psql -U postgres -d salesagent_db -c "
SELECT
    relname AS tabla,
    pg_size_pretty(pg_total_relation_size(relid)) AS tamaño_total,
    pg_size_pretty(pg_relation_size(relid)) AS tamaño_datos,
    n_live_tup AS filas_activas
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 15;
"
```

Las tablas que crecen más rápido: `message_logs`, `wa_conversations`, `daily_sales_snapshots`.
Considerar particionado o archivado si superan 10M de filas.

---

## 5. Mantenimiento de Redis

```bash
# Ver memoria usada
docker exec salesagent-redis redis-cli info memory | grep used_memory_human

# Ver colas de Celery y cuántas tareas hay
docker exec salesagent-redis redis-cli llen celery

# Limpiar cola atascada (⚠️ borra todas las tareas pendientes)
docker exec salesagent-redis redis-cli del celery

# Ver TTL de una clave
docker exec salesagent-redis redis-cli ttl "nombre-de-la-clave"
```

---

## 6. Celery — diagnóstico y control

```bash
# Estado de los workers
celery -A app.scheduler.celery_app inspect ping

# Tareas activas en este momento
celery -A app.scheduler.celery_app inspect active

# Tareas registradas
celery -A app.scheduler.celery_app inspect registered

# Ver schedule de tareas periódicas (beat)
celery -A app.scheduler.celery_app inspect scheduled

# Revocar una tarea específica por ID
celery -A app.scheduler.celery_app revoke TASK_ID --terminate

# Reiniciar workers (sin downtime si hay múltiples)
celery -A app.scheduler.celery_app control pool_restart
```

### Síntomas y soluciones comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| Tareas acumulándose en cola | Worker caído o saturado | `docker-compose restart celery-worker` |
| Tarea lleva > 10 min activa | Worker colgado en llamada externa | `celery revoke TASK_ID --terminate` |
| Beat no dispara tareas | beat caído o configuración incorrecta | `docker-compose restart celery-beat` |
| `SoftTimeLimitExceeded` | Tarea tardó demasiado | Investigar cuello de botella en la tarea |
| `ConnectionRefusedError` a Redis | Redis caído | `docker-compose restart redis` |

---

## 7. Sentry — gestión de errores

### Configuración en producción

- `SENTRY_DSN`: DSN del proyecto en sentry.io
- `APP_ENV=production`: Sentry agrupa errores por entorno
- `traces_sample_rate=0.1` en producción (10% de transacciones trazadas)

### Errores frecuentes y qué hacer

| Error en Sentry | Causa | Acción |
|---|---|---|
| `litellm.exceptions.AuthenticationError` | API key del proveedor IA inválida o faltante | Verificar `GROQ_API_KEY` (dev) o `ANTHROPIC_API_KEY` (prod) en `.env` |
| `litellm.exceptions.RateLimitError` | Límite de tokens/min en el proveedor IA | Groq: 6K tokens/min en tier gratuito. Anthropic: verificar cuota |
| `litellm.BadRequestError: model_decommissioned` | El modelo Groq fue dado de baja | Actualizar `AI_MODEL_STANDARD` y `AI_MODEL_COMPLEX` en `.env`. Modelo actual: `groq/llama-3.3-70b-versatile`. Ver [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations) |
| `anthropic.APIStatusError` | (Anthropic directo — raro) Límite de rate o API key inválida | Verificar cuota en console.anthropic.com |
| `asyncpg.TooManyConnectionsError` | Pool de BD agotado | Aumentar `DATABASE_POOL_SIZE` o investigar leaks |
| `whatsapp_send_failed` | Token expirado del tenant | Rotar token (sección 3.4) |
| `rag_recommendations_failed` | Voyage AI caído o key inválida | Verificar en dash.voyageai.com |
| `422 Unprocessable Entity` | Payload inválido en webhook | Revisar si Meta cambió el formato del webhook |

---

## 8. Escalamiento

### Cuándo escalar horizontalmente

- **API (ECS Fargate):** cuando CPU > 70% sostenido o latencia P95 > 2s
- **Celery workers:** cuando la cola tiene > 100 tareas pendientes por más de 5 min
- **Redis:** cuando la memoria supere el 80%
- **RDS:** cuando las conexiones activas superen el 80% de `max_connections`

### Cuándo NO escalar

- El costo de Claude AI sube con el volumen de mensajes, no con las instancias.
  Si el costo de IA sube, investigar si algún tenant está generando volumen anormal.
- `pgvector` con índice IVFFlat no escala bien con > 1M vectores por tenant.
  Migrar a HNSW si se llega a ese volumen.

---

## 9. Contactos y escalamiento de incidentes

> Completar con datos reales antes del go-live.

| Rol | Responsable | Contacto |
|---|---|---|
| Lead técnico | — | — |
| Soporte AWS | — | Plan de soporte AWS |
| Anthropic (API issues) | — | support.anthropic.com |
| Meta WhatsApp Business | — | developers.facebook.com/support |
| Voyage AI | — | support@voyageai.com |

### Severidades

| Nivel | Descripción | Tiempo de respuesta |
|---|---|---|
| P0 | Sistema caído para todos los tenants | 15 min |
| P1 | Un tenant sin servicio o datos incorrectos | 1 hora |
| P2 | Funcionalidad degradada (ej. RAG sin responder) | 4 horas |
| P3 | Problema cosmético o de rendimiento menor | Siguiente sprint |
