# Onboarding de Nuevo Tenant — Sales Agent SaaS

> Guía paso a paso para incorporar una nueva distribuidora al sistema.
> Aplica tanto para el equipo técnico que hace el setup como para el primer contacto
> con el cliente. Tiempo estimado: 2-4 horas en la primera implementación.

---

## Resumen del proceso

```
1. Crear tenant en la plataforma          (~10 min)
2. Configurar WhatsApp Business           (~30-60 min — depende de Meta)
3. Cargar catálogo de productos           (~30 min)
4. Crear usuarios (vendedores, gerentes)  (~15 min)
5. Configurar zonas y rutas               (~30 min)
6. Cargar clientes                        (~20 min)
7. Configurar metas                       (~15 min)
8. Prueba end-to-end                      (~30 min)
```

---

## Prerequisitos

Antes de empezar, tener listos:

| Dato | Quién lo provee | Ejemplo |
|---|---|---|
| Nombre de la empresa | Cliente | "Distribuciones La Garantía" |
| NIT | Cliente | 900.123.456-7 |
| Número WhatsApp Business | Cliente | +573001234567 |
| Whatsapp Phone Number ID | Meta for Developers | "123456789012345" |
| WhatsApp Access Token | Meta for Developers | "EAABs..." |
| WhatsApp App Secret | Meta for Developers | "abc123..." |
| Emails de gerencia | Cliente | ["gerente@lagarantia.com"] |
| Color corporativo | Cliente | "#1D4ED8" |
| Logo URL | Cliente | https://... (opcional) |
| Listado de productos (CSV/Excel) | Cliente | Ver plantilla en `tests/data/` |
| Listado de clientes (CSV/Excel) | Cliente | Ver plantilla en `tests/data/` |
| Listado de vendedores | Cliente | Nombre, celular, email |

---

## Paso 1 — Crear el tenant en la plataforma

### 1.1 Obtener el JWT del super-admin

```bash
curl -X POST https://tu-dominio/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "superadmin@salesagent.io",
    "password": "tu-password-plataforma"
  }'
# Guardar el access_token retornado
PLATFORM_TOKEN="eyJ..."
```

### 1.2 Crear el tenant

```bash
curl -X POST https://tu-dominio/api/v1/platform/tenants/ \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Distribuciones La Garantía",
    "slug": "distribuciones-la-garantia",
    "nit": "9001234567",
    "plan": "starter",
    "agent_name": "AgenteGarantía",
    "primary_color": "#1D4ED8",
    "email_config": {
      "management_emails": ["gerente@lagarantia.com"],
      "from_name": "AgenteGarantía"
    }
  }'
# Guardar el "id" del tenant retornado
TENANT_ID="uuid-del-tenant-nuevo"
```

> El `slug` debe ser único, en minúsculas, sin espacios (usar guiones).
> No puede ser `__platform__` ni contener caracteres especiales.

### 1.3 Crear el usuario admin del tenant

```bash
# Primero hacer login como admin del tenant (aún no existe, usar el endpoint de plataforma)
# El tenant recién creado necesita su primer usuario admin:
curl -X POST https://tu-dominio/api/v1/admin/salespersons \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Administrador La Garantía",
    "email": "admin@lagarantia.com",
    "phone": "+573009876543",
    "role": "admin",
    "password": "password-seguro-temporal"
  }'
```

> Comunicar al cliente que debe cambiar la contraseña en el primer login.

---

## Paso 2 — Configurar WhatsApp Business

### 2.1 Requisitos en Meta for Developers

El cliente necesita:
- Una **Meta Business Account** verificada
- Una **WhatsApp Business App** creada en developers.facebook.com
- El número de teléfono agregado y verificado en la app

### 2.2 Obtener las credenciales de Meta

En Meta for Developers → tu App → WhatsApp → API Setup:

| Dato | Dónde encontrarlo |
|---|---|
| Phone Number ID | Listado de números de teléfono |
| WhatsApp Business Account ID | En la misma sección |
| Access Token | "Temporary access token" (para pruebas) o generar token permanente con System User |
| App Secret | App → Settings → Basic → App Secret |

> ⚠️ El "Temporary access token" expira en 24h. Para producción usar un **System User**
> con token permanente. Ver: [Meta docs — System Users](https://developers.facebook.com/docs/whatsapp/business-management-api/system-users)

### 2.3 Guardar credenciales en el sistema

```bash
# Login como admin del tenant
curl -X POST https://tu-dominio/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@lagarantia.com", "password": "password-temporal"}'
TENANT_TOKEN="eyJ..."

# Configurar WhatsApp
curl -X POST https://tu-dominio/api/v1/admin/settings/whatsapp \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number_id": "123456789012345",
    "business_account_id": "987654321098765",
    "access_token": "EAABs...",
    "app_secret": "abc123...",
    "phone_display": "+573001234567"
  }'
# El token se encripta automáticamente con Fernet antes de guardarse
```

### 2.4 Configurar el webhook en Meta

```bash
# 1. Obtener la URL del webhook
WEBHOOK_URL="https://tu-dominio/api/v1/webhooks/whatsapp"
VERIFY_TOKEN="el-valor-de-WHATSAPP_WEBHOOK_VERIFY_TOKEN-en-.env"

# 2. En Meta for Developers → WhatsApp → Configuration → Webhooks:
#    Callback URL: $WEBHOOK_URL
#    Verify Token: $VERIFY_TOKEN
#    Clic en "Verify and Save"
#    Suscribir al evento: messages

# 3. Verificar que el webhook responde:
curl "${WEBHOOK_URL}?hub.mode=subscribe&hub.verify_token=${VERIFY_TOKEN}&hub.challenge=test123"
# Debe responder: test123
```

### 2.5 Verificar envío de mensajes

```bash
# Enviar un mensaje de prueba al número del cliente
curl -X POST https://tu-dominio/api/v1/admin/settings/test-whatsapp \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+57NUMERO_DE_PRUEBA", "message": "Hola, esto es una prueba del agente."}'
```

---

## Paso 3 — Cargar el catálogo de productos

### 3.1 Formato esperado

| Campo | Requerido | Ejemplo |
|---|---|---|
| `sku` | ✅ | GRA-001 |
| `name` | ✅ | Arroz Diana x 5Kg |
| `brand` | ✅ | Diana |
| `category` | ✅ | granos |
| `subcategory` | ❌ | arroz |
| `unit` | ✅ | Bulto |
| `unit_content` | ❌ | 10 bolsas x 500g |
| `price` | ✅ | 220000 |
| `price_promo` | ❌ | 198000 |
| `description` | ❌ | Texto libre para RAG |
| `semantic_tags` | ❌ | ["bajo en costo", "alta rotación"] |

### 3.2 Cargar vía API (uno a uno o en script)

```bash
# Cargar un producto
curl -X POST https://tu-dominio/api/v1/admin/productos \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "GRA-001",
    "name": "Arroz Diana x 5Kg",
    "brand": "Diana",
    "category": "granos",
    "subcategory": "arroz",
    "unit": "Bulto",
    "price": 220000,
    "description": "Arroz de alta calidad para tiendas de barrio"
  }'
# Al crear/actualizar un producto, se encola automáticamente index_product_task
# para generar su embedding y dejarlo disponible en búsqueda semántica
```

### 3.3 Carga masiva (script Python)

```python
# Ejemplo de script de carga masiva desde CSV
import asyncio, csv, httpx

TENANT_TOKEN = "eyJ..."
API_URL = "https://tu-dominio/api/v1/admin/productos"

async def cargar_productos(csv_path: str):
    async with httpx.AsyncClient() as client:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                r = await client.post(
                    API_URL,
                    json={
                        "sku": row["sku"],
                        "name": row["nombre"],
                        "brand": row["marca"],
                        "category": row["categoria"],
                        "unit": row["unidad"],
                        "price": float(row["precio"]),
                    },
                    headers={"Authorization": f"Bearer {TENANT_TOKEN}"},
                )
                print(f"{'✅' if r.status_code == 201 else '❌'} {row['sku']}: {r.status_code}")
                await asyncio.sleep(0.1)  # respetar rate limits

asyncio.run(cargar_productos("productos.csv"))
```

> Después de la carga masiva, esperar ~5 minutos para que `index_product_task`
> procese todos los embeddings en Celery.

---

## Paso 4 — Crear usuarios (vendedores y gerentes)

```bash
# Crear un vendedor
curl -X POST https://tu-dominio/api/v1/admin/salespersons \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carlos Méndez",
    "email": "carlos@lagarantia.com",
    "phone": "+573001111111",
    "role": "salesperson",
    "password": "password-temporal-123"
  }'

# Crear un gerente
curl -X POST https://tu-dominio/api/v1/admin/salespersons \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ana Gerente",
    "email": "ana@lagarantia.com",
    "phone": "+573009999999",
    "role": "manager",
    "password": "password-temporal-456"
  }'
```

> Los números de celular deben incluir el código de país (+57 para Colombia).
> El sistema normaliza el número (elimina +, espacios) para identificar mensajes entrantes de WhatsApp.

---

## Paso 5 — Configurar zonas y rutas

### 5.1 Crear zonas geográficas

```bash
curl -X POST https://tu-dominio/api/v1/admin/zonas \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Zona Norte", "description": "Barrios norte de la ciudad"}'
```

### 5.2 Crear rutas

```bash
# Ruta presencial (vendedor físico)
curl -X POST https://tu-dominio/api/v1/admin/rutas \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ruta Norte Lunes",
    "zone_id": "uuid-de-la-zona",
    "salesperson_id": "uuid-del-vendedor",
    "route_type": "PRESENTIAL",
    "operating_days": [1, 3, 5]
  }'
# operating_days: 1=Lun, 2=Mar, 3=Mié, 4=Jue, 5=Vie, 6=Sáb

# Ruta de agente WA (solo el agente IA, sin vendedor físico)
curl -X POST https://tu-dominio/api/v1/admin/rutas \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ruta Digital Martes",
    "zone_id": "uuid-de-la-zona",
    "salesperson_id": "uuid-del-agente-ia",
    "route_type": "AGENT_WA",
    "operating_days": [2, 4]
  }'
```

---

## Paso 6 — Cargar clientes

```bash
curl -X POST https://tu-dominio/api/v1/admin/clients \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Tienda El Progreso",
    "owner_name": "Pedro Gómez",
    "phone": "+573011000101",
    "email": "pedro@gmail.com",
    "address": "Cra 5 # 12-34, Barrio El Centro",
    "zone_name": "Zona Norte",
    "salesperson_id": "uuid-del-vendedor",
    "segment": "A",
    "channel_type": "tradicional",
    "whatsapp_opt_in": true,
    "avg_purchase_frequency_days": 14
  }'
```

> `whatsapp_opt_in: true` es requerido para que el agente envíe notificaciones al tendero.
> Solo activar si el tendero dio consentimiento explícito.

---

## Paso 7 — Configurar metas de ventas

```bash
# Meta mensual para un vendedor
curl -X POST https://tu-dominio/api/v1/admin/goals \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "salesperson_id": "uuid-del-vendedor",
    "period_type": "monthly",
    "period_start": "2026-05-01",
    "period_end": "2026-05-31",
    "target_amount": 15000000,
    "target_visits": 100,
    "target_effective_visits": 70,
    "target_active_clients": 35
  }'
```

---

## Paso 8 — Prueba end-to-end

### Checklist de verificación

**Panel admin:**
- [ ] Login con `admin@lagarantia.com` → dashboard muestra KPIs
- [ ] Lista de clientes muestra los clientes cargados
- [ ] Lista de productos muestra el catálogo
- [ ] Lista de vendedores y sus rutas correctas

**WhatsApp — vendedor:**
- [ ] Enviar "hola" desde el celular del vendedor → agente responde
- [ ] Verificar que el sistema identifica el rol correcto (vendedor)
- [ ] Pedir el briefing manualmente: "¿cómo va mi meta?"

**WhatsApp — tendero:**
- [ ] Enviar "hola" desde el celular de un tendero con `whatsapp_opt_in=true`
- [ ] Verificar que el agente responde como ClientAgent
- [ ] Probar toma de pedido: "quiero pedir arroz"

**Notificaciones proactivas (manual):**
```bash
# Forzar briefing matutino para verificar sin esperar al horario
docker exec -it salesagent-celery-worker celery -A app.scheduler.celery_app call \
  app.scheduler.tasks.send_salesperson_morning_briefings
```

**Reporte de gerencia:**
- [ ] Forzar reporte diario y verificar que llega al email configurado:
```bash
docker exec -it salesagent-celery-worker celery -A app.scheduler.celery_app call \
  app.scheduler.tasks.send_management_daily_reports
```

---

## Notas para el cliente

### Qué esperar en los primeros días

- **Día 1:** Embeddings de productos se indexan en background. Búsqueda semántica disponible en ~30 min.
- **Días 1-7:** El agente no tiene historial de compras real, las recomendaciones son genéricas.
  Con el tiempo mejoran a medida que se registran órdenes.
- **Semana 2+:** `calculate_product_affinities` (tarea diaria 2 AM) empieza a producir afinidades
  reales cliente-producto. Las recomendaciones se vuelven personalizadas.

### Horarios de notificaciones automáticas (zona horaria Colombia)

| Notificación | Horario | Para quién |
|---|---|---|
| Briefing matutino | Lun-Sáb 6:30 AM | Vendedores |
| Pre-visita tenderos | Lun-Sáb 8:00 AM – 5:00 PM (c/hora) | Clientes en ruta |
| Resumen diario | Lun-Sáb 6:30 PM | Vendedores |
| Reporte rendimiento | Lun-Sáb 8:00 PM | Vendedores |
| Follow-up no visitados | Lun-Sáb 7:00 PM | Clientes no visitados |
| Reporte diario gerencia | Lun-Sáb 7:00 AM | Gerentes (email) |
| Reporte semanal gerencia | Lunes 7:30 AM | Gerentes (email) |

Los horarios son configurables en `tenant.schedule_config` vía el endpoint de settings.
