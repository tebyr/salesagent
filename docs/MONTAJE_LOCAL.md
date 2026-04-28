# Montaje Local — Sales Agent SaaS

> **Objetivo:** Levantar el agente completamente en tu Mac y probar el flujo
> WhatsApp end-to-end usando el sandbox de Meta (App IbSales Agent).
>
> **Tiempo estimado:** ~45 min en primera instalación.
> **Fecha de referencia:** Abril 2026 — credenciales sandbox activas.

---

## Credenciales Meta obtenidas (sandbox IbSales Agent)

> ⚠️ No compartir en repositorios ni chats públicos.

| Credencial | Descripción | Dónde va |
|-----------|-------------|----------|
| **App ID:** `1293745902857926` | Identificador de la app | Referencia |
| **App Secret** | Clave secreta de la app | `.env` → `WHATSAPP_APP_SECRET` |
| **Phone Number ID:** `464348050089416` | Número de prueba +1 555 135 3681 | BD tenant → `whatsapp_phone_number_id` |
| **WABA ID:** `437820632749495` | WhatsApp Business Account | Referencia |
| **Token temporal** | Expira en 24h — reemplazar por System User token | BD tenant → `whatsapp_access_token` |

> 🔑 El token temporal del sandbox se regenera en:
> developers.facebook.com → IbSales Agent → WhatsApp → Configuración de la API

---

## Fase 1 — Herramientas base

### Checklist de verificación

```bash
# Correr esto para ver el estado actual de todas las herramientas
python3 --version        # necesitamos 3.12+
docker --version         # necesitamos 24+
docker compose version   # necesitamos V2
ngrok --version          # necesitamos 3+
node --version           # necesitamos 18+
npm --version            # necesitamos 9+
brew --version           # necesitamos cualquiera
```

### 1.1 Docker Desktop

Descargar e instalar manualmente desde:
```
https://www.docker.com/products/docker-desktop/
```

> Elegir versión **macOS Apple Silicon** si tu Mac es M1/M2/M3,
> o **macOS Intel** si es Intel.

Después de instalar, abrir Docker Desktop y esperar a que el ícono de la ballena
esté verde. Luego verificar:

```bash
docker --version
docker compose version
```

### 1.2 Python 3.12

```bash
brew install python@3.12

# Verificar
python3.12 --version
# Python 3.12.x

# Crear alias temporal si es necesario
echo 'alias python3="python3.12"' >> ~/.zshrc
source ~/.zshrc
```

### 1.3 ngrok

```bash
brew install ngrok/ngrok/ngrok

# Registrarse en https://dashboard.ngrok.com y obtener el authtoken
# Luego configurarlo:
ngrok config add-authtoken TU_AUTHTOKEN_AQUI

# Verificar
ngrok --version
# ngrok version 3.x.x
```

> El authtoken está en: dashboard.ngrok.com → Getting Started → Your Authtoken

### 1.4 Node.js (para el panel admin)

```bash
brew install node

# Verificar
node --version   # v18+
npm --version    # 9+
```

---

## Fase 2 — Configuración del proyecto

### 2.0 Proveedor IA para pruebas — Groq (recomendado, gratis)

> Durante el desarrollo usamos **Groq** como proveedor IA en lugar de Anthropic.
> Es gratuito, rápido y no requiere tarjeta de crédito para empezar.
> Cuando pasemos a producción, cambiamos 3 variables en `.env` — nada más.

**Obtener la API key de Groq:**
1. Ir a [console.groq.com](https://console.groq.com) → Sign up (Google o GitHub)
2. Menú izquierdo → **API Keys** → **Create API Key**
3. Copiar la key (empieza con `gsk_...`)

> ✅ El free tier incluye 6,000 tokens/min con `llama-3.1-70b-versatile` — suficiente para
> todas las pruebas del agente. No se factura mientras estés dentro del límite.

**Modelos activos en pruebas:**
| Nivel | Modelo Groq | Equivalente Anthropic | Uso |
|-------|------------|----------------------|-----|
| Simple | `llama-3.1-8b-instant` | claude-haiku-4-5 | Notificaciones |
| Estándar | `llama-3.1-70b-versatile` | claude-sonnet-4-6 | Agente conversacional |
| Complejo | `llama-3.1-70b-versatile` | claude-opus-4-6 | Reportes gerenciales |

**Cambiar a Anthropic en producción** (editar solo `.env`):
```env
GROQ_API_KEY=           # dejar vacío o comentar
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL_SIMPLE=claude-haiku-4-5
AI_MODEL_STANDARD=claude-sonnet-4-6
AI_MODEL_COMPLEX=claude-opus-4-6
```

---

### 2.1 Crear el archivo .env

```bash
cd /Users/oscarmauriciogomezacevedo/claudecode/salesagent
cp .env.example .env
```

Editar `.env` con estos valores — los que tienen `★` son críticos para arrancar:

```env
# ★ App
APP_ENV=development
APP_SECRET_KEY=         # openssl rand -hex 32
APP_DEBUG=true

# ★ Database (dejar así para Docker local)
DATABASE_URL=postgresql+asyncpg://salesagent:password@localhost:5432/salesagent_db

# Redis (dejar así para Docker local)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ★ Groq (proveedor IA para pruebas — gratis)
GROQ_API_KEY=gsk_...    # console.groq.com — ver paso 2.0
AI_MODEL_SIMPLE=groq/llama-3.1-8b-instant
AI_MODEL_STANDARD=groq/llama-3.1-70b-versatile
AI_MODEL_COMPLEX=groq/llama-3.1-70b-versatile

# Voyage AI (embeddings RAG — necesario solo para búsqueda semántica)
VOYAGE_API_KEY=         # dash.voyageai.com — puede dejarse vacío en primeras pruebas

# ★ WhatsApp — del sandbox IbSales Agent
WHATSAPP_APP_SECRET=    # Clave secreta de la app (Meta Developers → IbSales Agent → Settings → Basic)
WHATSAPP_WEBHOOK_VERIFY_TOKEN=ibcaribe-webhook-2026

# Email (opcional en dev)
SENDGRID_API_KEY=       # dejar vacío — no bloquea en development

# ★ JWT
JWT_SECRET_KEY=         # openssl rand -hex 32

# ★ Fernet — generar UNA SOLA VEZ y nunca cambiar con datos en BD
ENCRYPTION_KEY=         # ver comando abajo

# Sentry (opcional)
SENTRY_DSN=             # dejar vacío
```

Generar las llaves aleatorias:
```bash
# APP_SECRET_KEY y JWT_SECRET_KEY
echo "APP_SECRET_KEY=$(openssl rand -hex 32)"
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"

# ENCRYPTION_KEY — requiere el venv activo (cryptography debe estar instalado)
# Crear venv primero si no existe (ver paso 2.3), luego:
source venv/bin/activate
python3.12 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

> ⚠️ **ENCRYPTION_KEY:** una vez que el sistema tenga datos en BD, esta llave
> **nunca debe cambiarse**. Perderla = tokens de WhatsApp de todos los tenants ilegibles.

### 2.2 Levantar PostgreSQL + Redis

```bash
docker compose up -d postgres redis

# Esperar ~15s y verificar
docker compose ps
# postgres   running (healthy)
# redis      running (healthy)
```

### 2.3 Crear entorno virtual e instalar dependencias

> ⚠️ Python 3.12 instalado con Homebrew es "externally-managed" — **siempre usar venv**.
> No instalar paquetes con `pip install` fuera del venv o el sistema se corrompe.

```bash
# Crear entorno virtual (solo la primera vez)
python3.12 -m venv venv

# Activar (ejecutar esto cada vez que abras una terminal nueva)
source venv/bin/activate

# Verificar que estamos en el venv
which python   # debe mostrar .../salesagent/venv/bin/python

# Instalar dependencias del proyecto
pip install -r requirements.txt
```

### 2.4 Aplicar migraciones

```bash
# Con el venv activado
alembic upgrade head
```

Output esperado:
```
INFO  [alembic] Running upgrade  -> 001_initial_schema
INFO  [alembic] Running upgrade 001 -> 002_add_pgvector
INFO  [alembic] Running upgrade 002 -> 003_sync_schema_with_models
```

### 2.5 Poblar datos de prueba

```bash
python scripts/seed_tenant.py
```

Crea: 1 tenant (Distribuciones La Garantía) + 40 clientes + 30 productos +
3 vendedores + 90 días de historial de órdenes.

---

## Fase 3 — Levantar servicios

### 3.1 API + Workers

```bash
# Construir imagen Docker (solo primera vez)
docker compose build

# Levantar API + Celery
docker compose up -d api celery-worker celery-beat
```

### 3.2 Verificar API

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0","env":"development"}

# Ver Swagger con todos los endpoints
open http://localhost:8000/docs
```

### 3.3 Frontend (opcional para hoy)

```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1' > .env.local
npm run dev
# Panel admin en http://localhost:3000
# Usuario: admin@lagarantia.com / admin123
```

---

## Fase 4 — WhatsApp sandbox end-to-end

### 4.1 Levantar ngrok

```bash
cd /Users/oscarmauriciogomezacevedo/claudecode/salesagent
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

El script muestra la URL pública. Ejemplo:
```
Ngrok URL: https://abc123.ngrok-free.app
Webhook:   https://abc123.ngrok-free.app/api/v1/webhooks/whatsapp
```

### 4.2 Configurar webhook en Meta

1. Ir a developers.facebook.com → **IbSales Agent** → **WhatsApp** → **Configuración**
2. En sección **Webhook** → **Editar**
3. **Callback URL:** `https://TU-URL-NGROK.ngrok-free.app/api/v1/webhooks/whatsapp`
4. **Verify Token:** `ibcaribe-webhook-2026`
5. **Verificar y guardar**
6. Suscribir campo: `messages` ✅

Verificar manualmente:
```bash
curl "http://localhost:8000/api/v1/webhooks/whatsapp\
?hub.mode=subscribe\
&hub.verify_token=ibcaribe-webhook-2026\
&hub.challenge=test123"
# Debe responder: test123
```

### 4.3 Configurar tenant con credenciales sandbox

Una vez con la API corriendo, crear el tenant de prueba con las credenciales
del sandbox Meta via la API de platform:

```bash
# 1. Crear super-admin (si no existe)
python scripts/seed_platform.py --email admin@ibcaribe.com --password admin2026

# 2. Login como super-admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ibcaribe.com","password":"admin2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Configurar WhatsApp del tenant de prueba
# (usar el tenant_id que generó el seed_tenant.py)
curl -X PUT http://localhost:8000/api/v1/admin/settings/whatsapp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number_id": "464348050089416",
    "access_token": "TOKEN_TEMPORAL_DEL_SANDBOX",
    "webhook_verify_token": "ibcaribe-webhook-2026"
  }'
```

> ⚠️ El token temporal del sandbox expira en 24h. Para pruebas continuas,
> crear un System User en Meta Business → Usuarios del sistema → Generar token permanente.

### 4.4 Test end-to-end

Envía un mensaje de WhatsApp desde tu celular al número de prueba:
```
+1 (555) 135-3681
```

Flujos a probar:
| Mensaje | Respuesta esperada |
|---------|-------------------|
| `Hola` | Saludo del agente + menú |
| `¿Cuáles son mis metas?` | El agente consulta analytics y responde |
| `Quiero hacer un pedido` | El agente inicia flujo de toma de pedido |

Monitorear logs en tiempo real:
```bash
docker compose logs api -f
docker compose logs celery-worker -f
```

---

## Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `ENCRYPTION_KEY is not a valid Fernet key` | .env vacío o ejemplo | Generar con el comando python3.12 del paso 2.1 |
| `relation "tenants" does not exist` | Migraciones no aplicadas | `alembic upgrade head` |
| Webhook 403 | WHATSAPP_WEBHOOK_VERIFY_TOKEN no coincide | Verificar que el token en .env == el configurado en Meta |
| Webhook no recibe mensajes | ngrok no está corriendo | `./scripts/start_dev.sh` |
| API 500 en todos los endpoints | API key faltante | `docker compose logs api --tail=30` |
| Token sandbox expirado (401 de Meta) | Token de 24h vencido | Regenerar en Meta Developers → Configuración de la API |
| `AuthenticationError` al llamar IA | GROQ_API_KEY vacío o incorrecto | Verificar key en console.groq.com → API Keys |
| `RateLimitError` de Groq | Free tier superado (6K tokens/min) | Esperar 1 min o reducir frecuencia de pruebas |
| `voyage_api_key field required` | config.py no actualizado | Asegurarse de tener la versión con `Optional[str] = None` |

---

## Notas importantes

- **ngrok plan gratuito:** La URL cambia con cada reinicio — actualizar en Meta cada vez.
  Para URL fija, suscribirse a ngrok plan personal (~$10/mes).
- **Token sandbox temporal:** Expira en 24h. Para desarrollo continuo, crear System User
  en Meta Business Manager → Usuarios del sistema → `salesagent-api` → Generar token permanente.
- **Número de prueba:** El sandbox solo puede enviar mensajes a números registrados
  (hasta 5). Registrar números adicionales en Meta Developers → WhatsApp → Primeros pasos.
