# API Reference — Sales Agent SaaS

> Referencia de todos los endpoints del sistema. Complementa la documentación interactiva
> disponible en `/docs` (Swagger UI) cuando el servidor está corriendo.
>
> **Base URL:** `https://tu-dominio/api/v1`
> **Autenticación:** Bearer token JWT en header `Authorization: Bearer {token}`

---

## Autenticación

### POST `/admin/auth/login`

Genera un JWT para acceder a los endpoints del panel admin.

**Request:**
```json
{
  "email": "admin@lagarantia.com",
  "password": "mi-password"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errores:** `401` credenciales incorrectas · `400` tenant inactivo

---

## Dashboard

### GET `/admin/dashboard/kpis`

KPIs del tenant en tiempo real: ventas del mes, visitas, efectividad.

**Roles:** admin, manager, supervisor

**Response 200:**
```json
{
  "total_sales_month": 45200000.0,
  "total_orders_month": 87,
  "active_clients": 142,
  "total_clients": 160,
  "avg_effectiveness": 72.5,
  "team_month_pct": 64.2,
  "team_projected_pct": 89.1
}
```

### GET `/admin/dashboard/salespersons-performance`

Rendimiento individual de cada vendedor en el mes actual.

**Roles:** admin, manager

**Response 200:**
```json
[
  {
    "id": "uuid",
    "name": "Carlos Méndez",
    "actual_amount": 8500000.0,
    "target_amount": 15000000.0,
    "pct_amount": 56.7,
    "visits_today": 5,
    "effectiveness": 80.0
  }
]
```

---

## Vendedores

### GET `/admin/salespersons`

Lista todos los vendedores activos del tenant.

**Roles:** admin, manager

**Query params:** ninguno

### POST `/admin/salespersons`

Crea un nuevo usuario (vendedor, supervisor, gerente o admin).

**Roles:** admin, manager

**Request:**
```json
{
  "name": "Carlos Méndez",
  "email": "carlos@lagarantia.com",
  "phone": "+573001111111",
  "role": "salesperson",
  "password": "password-seguro"
}
```

**Valores válidos para `role`:** `admin` · `manager` · `supervisor` · `salesperson`

**Response 201:** objeto del usuario creado

### GET `/admin/salespersons/{salesperson_id}`

Detalle de un vendedor.

**Roles:** admin, manager

### PATCH `/admin/salespersons/{salesperson_id}`

Actualiza datos de un vendedor. Solo enviar los campos a modificar.

**Roles:** admin, manager

**Request (parcial):**
```json
{
  "name": "Carlos A. Méndez",
  "phone": "+573001112222"
}
```

### DELETE `/admin/salespersons/{salesperson_id}`

Desactiva el vendedor (soft delete — `is_active = false`).

**Roles:** admin

**Response:** `204 No Content`

---

## Clientes

### GET `/admin/clients`

Lista clientes con filtros opcionales.

**Roles:** admin, manager, supervisor

**Query params:**
| Param | Tipo | Descripción |
|---|---|---|
| `salesperson_id` | UUID | Filtrar por vendedor asignado |
| `zone_name` | string | Filtrar por nombre de zona |
| `segment` | string | A, B o C |
| `is_active` | bool | Default: true |
| `whatsapp_opt_in` | bool | Filtrar por consentimiento WA |
| `skip` | int | Paginación (default: 0) |
| `limit` | int | Paginación (default: 100) |

### POST `/admin/clients`

Crea un nuevo cliente (tendero).

**Roles:** admin, manager

**Request:**
```json
{
  "business_name": "Tienda El Progreso",
  "owner_name": "Pedro Gómez",
  "phone": "+573011000101",
  "address": "Cra 5 # 12-34",
  "zone_name": "Zona Norte",
  "salesperson_id": "uuid-del-vendedor",
  "segment": "A",
  "channel_type": "tradicional",
  "whatsapp_opt_in": true,
  "avg_purchase_frequency_days": 14
}
```

**Valores válidos para `segment`:** `A` · `B` · `C`

### GET `/admin/clients/{client_id}`
### PATCH `/admin/clients/{client_id}`
### DELETE `/admin/clients/{client_id}` → soft delete, `204 No Content`

---

## Productos

### GET `/admin/productos`

Lista productos con filtros opcionales.

**Roles:** admin, manager

**Query params:** `category`, `brand`, `is_active`, `is_featured`, `rotation_flag`, `skip`, `limit`

### POST `/admin/productos`

Crea un producto. **Dispara automáticamente `index_product_task` en Celery** para generar
el embedding semántico con Voyage AI.

**Roles:** admin, manager

**Request:**
```json
{
  "sku": "GRA-001",
  "name": "Arroz Diana x 5Kg",
  "brand": "Diana",
  "category": "granos",
  "subcategory": "arroz",
  "unit": "Bulto",
  "unit_content": "10 bolsas x 500g",
  "price": 220000.0,
  "price_promo": null,
  "description": "Arroz de alta calidad para el canal tradicional",
  "semantic_tags": ["alta rotación", "canal tradicional"],
  "is_featured": false,
  "rotation_flag": null
}
```

**Valores válidos para `rotation_flag`:** `null` · `"slow"` · `"critical"`

**Response 201:** objeto del producto con `id` asignado

### GET `/admin/productos/{producto_id}`
### PATCH `/admin/productos/{producto_id}` → también dispara re-indexación RAG
### DELETE `/admin/productos/{producto_id}` → soft delete, `204 No Content`

---

## Zonas

### GET `/admin/zonas`

**Roles:** admin, manager, supervisor

### POST `/admin/zonas`

**Roles:** admin, manager

**Request:**
```json
{
  "name": "Zona Norte",
  "description": "Barrios norte de la ciudad"
}
```

### GET `/admin/zonas/{zona_id}` → incluye lista de clientes de la zona
### PATCH `/admin/zonas/{zona_id}`
### DELETE `/admin/zonas/{zona_id}` → falla si tiene clientes activos

---

## Rutas

### GET `/admin/rutas`

Lista rutas con filtros opcionales.

**Roles:** admin, manager, supervisor

**Query params:** `salesperson_id`, `zone_id`, `route_type`, `is_active`

### POST `/admin/rutas`

**Roles:** admin, manager

**Request:**
```json
{
  "name": "Ruta Norte Lunes-Miércoles",
  "zone_id": "uuid-de-zona",
  "salesperson_id": "uuid-de-vendedor",
  "route_type": "PRESENTIAL",
  "operating_days": [1, 3],
  "visit_order": [
    {"client_id": "uuid-cliente-1", "order": 1},
    {"client_id": "uuid-cliente-2", "order": 2}
  ]
}
```

**Valores válidos para `route_type`:** `PRESENTIAL` · `AGENT_WA`

**`operating_days`:** array de enteros ISO — `1`=Lunes … `6`=Sábado

### GET `/admin/rutas/{ruta_id}`
### PATCH `/admin/rutas/{ruta_id}`
### DELETE `/admin/rutas/{ruta_id}` → soft delete, `204 No Content`

---

## Metas

### GET `/admin/goals`

Lista metas con filtros opcionales.

**Roles:** admin, manager

**Query params:** `salesperson_id`, `period_type`, `year`, `month`, `is_active`

### POST `/admin/goals`

Crea una meta individual.

**Roles:** admin, manager

**Request:**
```json
{
  "salesperson_id": "uuid-de-vendedor",
  "period_type": "monthly",
  "period_start": "2026-05-01",
  "period_end": "2026-05-31",
  "target_amount": 15000000.0,
  "target_visits": 100,
  "target_effective_visits": 70,
  "target_active_clients": 35
}
```

**Valores válidos para `period_type`:** `monthly` · `weekly`

### POST `/admin/goals/bulk`

Crea metas para múltiples vendedores en un solo request.

**Request:**
```json
[
  {"salesperson_id": "uuid-1", "period_type": "monthly", "period_start": "2026-05-01", "period_end": "2026-05-31", "target_amount": 15000000},
  {"salesperson_id": "uuid-2", "period_type": "monthly", "period_start": "2026-05-01", "period_end": "2026-05-31", "target_amount": 12000000}
]
```

### DELETE `/admin/goals/{goal_id}` → soft delete, `204 No Content`

---

## Configuración del tenant

### GET `/admin/settings`

Retorna la configuración actual del tenant (horarios, WhatsApp, emails).

**Roles:** admin

### PATCH `/admin/settings`

Actualiza configuración general (nombre del agente, color, etc.).

**Roles:** admin

### PUT `/admin/settings/whatsapp`

Configura o actualiza las credenciales de WhatsApp Business.
El `access_token` se encripta con Fernet antes de guardarse.

**Roles:** admin

**Request:**
```json
{
  "phone_number_id": "123456789012345",
  "business_account_id": "987654321098765",
  "access_token": "EAABs...",
  "app_secret": "abc123...",
  "phone_display": "+573001234567"
}
```

### PUT `/admin/settings/schedule`

Actualiza los horarios de notificaciones automáticas.

**Roles:** admin

**Request:**
```json
{
  "morning_briefing": "06:30",
  "pre_visit_start": "08:00",
  "pre_visit_end": "17:00",
  "daily_summary": "18:30",
  "performance_report": "20:00",
  "timezone": "America/Bogota"
}
```

### POST `/admin/settings/test-whatsapp`

Envía un mensaje de prueba al número especificado para verificar la conexión.

**Roles:** admin

**Request:**
```json
{
  "phone": "+573001111111",
  "message": "Mensaje de prueba del agente."
}
```

---

## Reportes (descarga de archivos)

Todos los endpoints de reportes retornan archivos descargables con `Content-Disposition: attachment`.

**Roles:** admin, manager

**Filtros comunes disponibles en todos:**

| Param | Tipo | Descripción |
|---|---|---|
| `date_from` | date | Fecha inicio (YYYY-MM-DD) |
| `date_to` | date | Fecha fin (YYYY-MM-DD) |
| `salesperson_id` | UUID | Filtrar por vendedor |

### GET `/admin/reports/ventas` → CSV

Exporta todas las órdenes en el rango con detalle de items.

**Filtros adicionales:** `status` (PENDING, CONFIRMED, DISPATCHED, DELIVERED, CANCELLED)

**Columnas CSV:** `fecha`, `orden_id`, `cliente`, `vendedor`, `producto`, `sku`, `cantidad`, `precio_unit`, `subtotal`, `total_orden`, `estado`

### GET `/admin/reports/ventas/pdf` → PDF

Reporte PDF con resumen por vendedor + tabla de detalle (máx. 200 órdenes).

### GET `/admin/reports/clientes` → CSV

Exporta todos los clientes con KPIs de compra.

**Filtros adicionales:** `is_active`, `zone_name`, `segment`, `whatsapp_opt_in`

**Columnas CSV:** `nombre_negocio`, `propietario`, `telefono`, `zona`, `segmento`, `vendedor`, `ultima_compra`, `ticket_promedio`, `frecuencia_dias`, `opt_in_whatsapp`

### GET `/admin/reports/metas` → CSV

Exporta metas con el último snapshot de progreso.

### GET `/admin/reports/metas/pdf` → PDF

Reporte PDF con semáforo de cumplimiento (🟢 ≥ 90% · 🟡 60-89% · 🔴 < 60%).

---

## Plataforma (super-admin SaaS)

> Acceso exclusivo: usuario con `role=admin` y `tenant_slug=__platform__`.
> Crear con: `python scripts/seed_platform.py --email x --password y`

### GET `/platform/tenants`

Lista todos los tenants activos (excluye `__platform__`).

### POST `/platform/tenants`

Crea un nuevo tenant.

**Request:**
```json
{
  "name": "Distribuciones El Norte",
  "slug": "distribuciones-el-norte",
  "nit": "9001234567",
  "plan": "starter",
  "agent_name": "AgenteNorte",
  "primary_color": "#DC2626",
  "email_config": {"management_emails": ["gerente@elnorte.com"]}
}
```

**Valores válidos para `plan`:** `starter` · `professional` · `enterprise`

### GET `/platform/tenants/{tenant_id}`

Detalle de un tenant con KPIs: usuarios, clientes, productos, órdenes (últimos 30 días).

### PATCH `/platform/tenants/{tenant_id}`

Actualiza nombre, plan, configuración del agente o emails de gerencia.

### POST `/platform/tenants/{tenant_id}/suspend`

Desactiva el tenant y todos sus usuarios. Los datos se conservan.

### POST `/platform/tenants/{tenant_id}/activate`

Reactiva el tenant y su usuario ADMIN.

### POST `/platform/tenants/{tenant_id}/reset-token`

Rota el token de WhatsApp del tenant. El nuevo token se encripta con Fernet.

**Request:**
```json
{
  "new_token": "EAABs_nuevo_token_de_meta..."
}
```

---

## Webhook WhatsApp

### GET `/webhooks/whatsapp`

Verificación del webhook por Meta (challenge de suscripción).

**Query params:** `hub.mode`, `hub.verify_token`, `hub.challenge`

**No requiere autenticación.** Responde el `hub.challenge` si el `verify_token` es correcto.

### POST `/webhooks/whatsapp`

Recibe mensajes y eventos de WhatsApp. Verifica firma HMAC-SHA256 (`X-Hub-Signature-256`).

**No requiere autenticación JWT** (la seguridad es la firma HMAC).

Procesa el mensaje en background (retorna `200 OK` inmediatamente a Meta).

---

## Códigos de error comunes

| Código | Significado | Acción |
|---|---|---|
| `400` | Payload inválido o regla de negocio violada | Ver `detail` en el body |
| `401` | Token JWT ausente, inválido o expirado | Hacer login nuevamente |
| `403` | Rol insuficiente o tenant incorrecto | Verificar permisos del usuario |
| `404` | Recurso no encontrado (o de otro tenant) | Verificar el ID y el tenant |
| `409` | Conflicto (ej. slug duplicado) | Ver `detail` en el body |
| `422` | Error de validación de campos | Ver `detail` con lista de errores |
| `500` | Error interno del servidor | Revisar logs y Sentry |

---

## Ejemplos de uso con curl

```bash
# Variable de conveniencia
TOKEN="eyJ..."
BASE="https://tu-dominio/api/v1"

# Listar clientes del vendedor X
curl "$BASE/admin/clients?salesperson_id=uuid-vendedor" \
  -H "Authorization: Bearer $TOKEN"

# Crear producto y esperar indexación RAG
curl -X POST "$BASE/admin/productos" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sku":"TEST-001","name":"Producto Test","brand":"Marca","category":"test","unit":"Caja","price":50000}'

# Descargar reporte de ventas del mes actual en CSV
curl "$BASE/admin/reports/ventas?date_from=2026-05-01&date_to=2026-05-31" \
  -H "Authorization: Bearer $TOKEN" \
  -o reporte_ventas_mayo.csv

# Descargar reporte de metas en PDF
curl "$BASE/admin/reports/metas/pdf?date_from=2026-05-01&date_to=2026-05-31" \
  -H "Authorization: Bearer $TOKEN" \
  -o reporte_metas_mayo.pdf
```
