# Seguridad — Sales Agent SaaS

> Documento de referencia para el equipo técnico. Cubre las decisiones de seguridad
> implementadas, políticas operacionales y procedimientos de respuesta ante incidentes.
> Leer antes de hacer cualquier deploy a producción.

---

## 1. Superficie de ataque — resumen ejecutivo

| Vector | Protección implementada | Estado |
|---|---|---|
| Autenticación de usuarios | JWT firmado (HS256) + bcrypt | ✅ |
| Autorización por tenant | `tenant_id` en JWT + filtro en cada query | ✅ |
| Autorización por rol | `require_roles()` en cada endpoint | ✅ |
| Tokens WhatsApp en BD | Fernet AES-128-CBC (simétrico) | ✅ |
| Webhook WhatsApp | Verificación firma HMAC-SHA256 | ✅ |
| Inyección SQL | SQLAlchemy ORM (queries parametrizadas) | ✅ |
| CORS | Configurado en `app/api/main.py` | ✅ |
| Secretos en código fuente | Variables de entorno, nunca hardcoded | ✅ |
| Rate limiting | ⚠️ Pendiente (ítem P3) | ⬜ |
| Auditoría de accesos | ⚠️ Parcial (Sentry + structlog) | 🟡 |

---

## 2. Autenticación y JWT

### Flujo de login

```
POST /api/v1/admin/auth/login
    │  email + password
    ▼
Busca User + Tenant en BD (JOIN)
    │  verify_password(plain, user.password_hash)  ← bcrypt
    ▼
create_access_token({
    "sub": user_id,
    "tenant_id": tenant_id,
    "tenant_slug": tenant.slug,
    "role": user.role.value,
    "name": user.name,
})
    │  firmado con JWT_SECRET_KEY (HS256)
    │  expiración: configurable en Settings (default: 24h en dev, 8h en prod recomendado)
    ▼
{"access_token": "eyJ...", "token_type": "bearer"}
```

### Payload del JWT

```json
{
  "sub": "uuid-del-usuario",
  "tenant_id": "uuid-del-tenant",
  "tenant_slug": "distribuciones-la-garantia",
  "role": "salesperson",
  "name": "Carlos Mendez",
  "exp": 1712345678
}
```

### Validación en endpoints

```python
# Uso en endpoints
current_user = Depends(require_roles("admin", "manager"))
tenant_id = current_user["tenant_id"]  # extraído del JWT, no del body

# require_roles valida:
# 1. Token válido y no expirado
# 2. Rol del usuario está en la lista permitida
```

### Super-admin de plataforma

El super-admin tiene `role=admin` y `tenant_slug=__platform__`.
La función `require_platform_admin` valida **ambas** condiciones.
Un admin de tenant normal con `tenant_slug != __platform__` no puede acceder a `/platform/`.

```python
# require_platform_admin (security.py) valida:
if current_user["role"] != "admin":
    raise HTTPException(403)
if current_user["tenant_slug"] != "__platform__":
    raise HTTPException(403)
```

### ⚠️ Buenas prácticas para JWT en producción

- `JWT_SECRET_KEY` mínimo 32 caracteres aleatorios: `openssl rand -hex 32`
- En producción reducir `ACCESS_TOKEN_EXPIRE_MINUTES` a 480 (8 horas)
- **Nunca** poner el `JWT_SECRET_KEY` en el repositorio
- Rotar el secreto requiere que todos los usuarios vuelvan a hacer login

---

## 3. Encriptación de tokens de WhatsApp (Fernet)

### Por qué se encriptan

Los `whatsapp_access_token` de cada tenant son tokens de acceso a Meta Cloud API.
Si la BD es comprometida, estos tokens no deben ser legibles. Se encriptan con
Fernet (AES-128-CBC + HMAC-SHA256) antes de guardar en la columna `whatsapp_access_token`.

### Implementación

```python
# Al guardar (settings.py, tenants.py)
tenant.whatsapp_access_token = encrypt_value(raw_token)

# Al leer (tasks.py, webhooks)
raw_token = decrypt_value(tenant.whatsapp_access_token)
```

La función `decrypt_value` tiene **tolerancia legacy**: si el valor no es Fernet válido
(ej. tokens guardados antes de implementar encriptación), retorna el valor tal cual.
Esto permite migraciones sin downtime.

### ENCRYPTION_KEY — la llave maestra

```bash
# Generar (una sola vez por entorno)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Reglas absolutas:**
- ❌ Nunca commitear `ENCRYPTION_KEY` en el repositorio
- ❌ Nunca usar la misma llave en dev y producción
- ❌ Nunca cambiar la llave sin re-encriptar todos los tokens primero
- ✅ Guardar en AWS Secrets Manager / 1Password en producción
- ✅ Una llave por entorno (dev, staging, production)

### Rotación de ENCRYPTION_KEY

Si la llave debe rotarse (compromiso de seguridad o política de rotación periódica):

```python
# Script de re-encriptación (ejecutar con acceso a BD)
from app.core.crypto import decrypt_value, encrypt_value
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from sqlalchemy import select

# 1. Con la LLAVE VIEJA en el entorno, ejecutar:
async with AsyncSessionLocal() as db:
    tenants = (await db.execute(select(Tenant))).scalars().all()
    for t in tenants:
        if t.whatsapp_access_token:
            plain = decrypt_value(t.whatsapp_access_token)  # descifra con llave vieja
            t.whatsapp_access_token = plain  # guarda en plano temporalmente
    await db.commit()

# 2. Cambiar ENCRYPTION_KEY en el entorno a la nueva llave

# 3. Con la LLAVE NUEVA, ejecutar:
async with AsyncSessionLocal() as db:
    tenants = (await db.execute(select(Tenant))).scalars().all()
    for t in tenants:
        if t.whatsapp_access_token:
            t.whatsapp_access_token = encrypt_value(t.whatsapp_access_token)
    await db.commit()
```

---

## 4. Verificación del webhook de WhatsApp

Cada mensaje entrante de Meta incluye una firma `X-Hub-Signature-256`.
El sistema la verifica antes de procesar el payload:

```python
# whatsapp_service.py
def verify_webhook_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Si la firma no coincide → `HTTP 403`. El payload no se procesa.

**`WHATSAPP_APP_SECRET`** es el App Secret de la app en Meta for Developers.
No confundir con el `whatsapp_access_token` del tenant (que es el token de acceso a la API).

---

## 5. Aislamiento multi-tenant

### Regla fundamental

**Toda query de producción debe filtrar por `tenant_id`.**
No existe middleware que lo haga automáticamente — es responsabilidad explícita del código.

```python
# ✅ Correcto
result = await db.execute(
    select(Client).where(
        Client.tenant_id == tenant_id,
        Client.id == client_id,
    )
)

# ❌ Incorrecto — expone datos de otros tenants
result = await db.execute(
    select(Client).where(Client.id == client_id)
)
```

### Checklist para nuevos endpoints

Antes de hacer merge de un PR con un nuevo endpoint, verificar:

- [ ] Todos los `SELECT`, `UPDATE`, `DELETE` filtran por `tenant_id`
- [ ] El `tenant_id` viene del JWT (`current_user["tenant_id"]`), nunca del body del request
- [ ] Los endpoints de plataforma (`/platform/`) usan `require_platform_admin`
- [ ] Los endpoints admin usan `require_roles(...)` con los roles apropiados
- [ ] No hay queries que crucen tenant_ids

### Matriz de roles y permisos

| Endpoint | admin | manager | supervisor | salesperson |
|---|---|---|---|---|
| `/admin/dashboard` | ✅ | ✅ | ✅ | ❌ |
| `/admin/salespersons` CRUD | ✅ | ✅ | ❌ | ❌ |
| `/admin/clients` CRUD | ✅ | ✅ | ✅ | ❌ |
| `/admin/productos` CRUD | ✅ | ✅ | ❌ | ❌ |
| `/admin/zonas` CRUD | ✅ | ✅ | ❌ | ❌ |
| `/admin/rutas` CRUD | ✅ | ✅ | ✅ | ❌ |
| `/admin/goals` CRUD | ✅ | ✅ | ❌ | ❌ |
| `GET/PATCH /admin/settings` | ✅ | ✅ | ❌ | ❌ |
| `PUT /admin/settings/whatsapp` | ✅ | ✅ | ❌ | ❌ |
| `PUT /admin/settings/security` | ✅ | ✅ | ❌ | ❌ |
| `/admin/reports/*` | ✅ | ✅ | ❌ | ❌ |
| `/platform/tenants/*` | solo `__platform__` admin | ❌ | ❌ | ❌ |
| `/webhooks/whatsapp` | público (verificación HMAC) | — | — | — |

---

## 6. Gestión de secretos

### Variables de entorno críticas

| Variable | Sensibilidad | Dónde guardar en prod |
|---|---|---|
| `JWT_SECRET_KEY` | 🔴 Crítica | AWS Secrets Manager |
| `ENCRYPTION_KEY` | 🔴 Crítica | AWS Secrets Manager |
| `ANTHROPIC_API_KEY` | 🔴 Crítica | AWS Secrets Manager |
| `VOYAGE_API_KEY` | 🔴 Crítica | AWS Secrets Manager |
| `WHATSAPP_APP_SECRET` | 🔴 Crítica | AWS Secrets Manager |
| `SENDGRID_API_KEY` | 🟠 Alta | AWS Secrets Manager |
| `DATABASE_URL` | 🟠 Alta | AWS Secrets Manager / ECS Task Definition |
| `SENTRY_DSN` | 🟡 Media | ECS Task Definition |
| `APP_ENV` | 🟢 Baja | ECS Task Definition |

### Reglas para el repositorio

```
# .gitignore debe incluir (verificar antes de cada commit):
.env
.env.*
*.pem
*.key
secrets/
```

---

## 7. Procedimientos ante incidentes de seguridad

### Escenario 1: Token de WhatsApp de un tenant comprometido

```bash
# 1. Rotar el token en Meta for Developers (genera uno nuevo)
# 2. Actualizar en el sistema via API de plataforma:
curl -X POST https://tu-dominio/api/v1/platform/tenants/{tenant_id}/reset-token \
  -H "Authorization: Bearer {platform_admin_jwt}" \
  -H "Content-Type: application/json" \
  -d '{"new_token": "NUEVO_TOKEN_DE_META"}'
# El endpoint re-encripta el token con Fernet antes de guardarlo
```

### Escenario 2: JWT_SECRET_KEY o ENCRYPTION_KEY comprometida

```
1. Coordinar ventana de mantenimiento (usuarios no podrán autenticarse)
2. Generar nueva llave: openssl rand -hex 32
3. Si es ENCRYPTION_KEY: ejecutar script de re-encriptación (ver sección 3)
4. Actualizar en AWS Secrets Manager
5. Redeploy del servicio (los contenedores toman la nueva variable)
6. Todos los usuarios deberán volver a hacer login (JWT_SECRET_KEY)
```

### Escenario 3: Brecha en la base de datos

```
1. Revocar credenciales de BD de inmediato (AWS RDS → modify instance)
2. Evaluar qué datos fueron expuestos:
   - tokens WhatsApp: encriptados con Fernet → rotar todas las ENCRYPTION_KEY
   - password_hash: bcrypt → bajo riesgo inmediato, notificar usuarios de todos modos
   - datos de clientes/tenderos: evaluar obligación de notificación LFPDP Colombia
3. Rotar todas las variables críticas (sección 6)
4. Redeploy completo
5. Documentar incidente (fecha, alcance, acciones tomadas)
```

---

## 8. Consideraciones legales — Colombia

El sistema maneja datos personales de tenderos (nombre, teléfono, historial de compras).
Aplica la **Ley 1581 de 2012 (LFPDP Colombia)**:

- Los tenderos deben dar consentimiento explícito para recibir mensajes del agente.
  → Implementado: `client.whatsapp_opt_in = True` (requerido para enviar notificaciones).
- Los datos no deben transferirse a terceros sin consentimiento.
  → Voyage AI recibe texto de productos para embeddings (no datos de clientes).
  → Anthropic recibe contexto de conversaciones para generar respuestas.
  → Revisar términos de datos de Anthropic y Voyage AI antes del go-live.
- Derecho al olvido: un tenant puede desactivar clientes (`is_active = False`).
  No hay hard delete — si un tendero solicita eliminación total, requiere proceso manual.
