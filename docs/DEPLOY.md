# Runbook — Deploy a Staging (Local / VPS)

> **Audiencia:** desarrolladores del equipo que necesiten levantar el entorno por primera vez
> o hacer un reset completo. Asume acceso al repositorio y credenciales de las APIs externas.
>
> **Tiempo estimado:** 20–30 minutos en primera instalación, ~5 min en reinicios posteriores.

---

## Prerrequisitos

| Herramienta | Versión mínima | Verificar |
|-------------|---------------|-----------|
| Docker Desktop | 24+ | `docker --version` |
| Docker Compose | V2 (plugin) | `docker compose version` |
| Python | 3.12 | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| ngrok | 3+ | `ngrok --version` |
| git | cualquiera | `git --version` |

> **macOS:** instalar con `brew install python@3.12 node ngrok` + Docker Desktop desde docker.com
> **Ubuntu 22.04:** ver apéndice al final del documento

---

## 1. Clonar el repositorio

```bash
git clone https://github.com/tebyr/salesagent.git
cd salesagent
```

---

## 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con las credenciales reales. Tabla de referencia:

| Variable | Descripción | Dónde conseguirla |
|----------|-------------|-------------------|
| `APP_ENV` | `development` / `staging` / `production` | Editar manualmente |
| `APP_SECRET_KEY` | Llave aleatoria para firmado interno | `openssl rand -hex 32` |
| `DATABASE_URL` | Conexión asyncpg a PostgreSQL | Dejar valor por defecto para Docker local |
| `GROQ_API_KEY` | Llave Groq para dev gratuito (reemplaza Anthropic en dev) | [console.groq.com](https://console.groq.com) — tier gratuito disponible |
| `ANTHROPIC_API_KEY` | Llave Claude para producción (opcional en dev) | [console.anthropic.com](https://console.anthropic.com) |
| `VOYAGE_API_KEY` | Llave para embeddings RAG | [dash.voyageai.com](https://dash.voyageai.com) |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Token arbitrario para verificar webhook Meta | Inventar (ej. `openssl rand -hex 16`) |
| `WHATSAPP_APP_SECRET` | App Secret de la app Meta | Meta for Developers → App → Settings → Basic |
| `SENDGRID_API_KEY` | API key de SendGrid para emails gerencia | [app.sendgrid.com](https://app.sendgrid.com) — opcional en dev |
| `JWT_SECRET_KEY` | Llave para firmar tokens JWT | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | Llave Fernet para encriptar tokens WA en BD | Ver nota abajo |
| `SENTRY_DSN` | DSN del proyecto en Sentry | [sentry.io](https://sentry.io) — opcional |

> ⚠️ **ENCRYPTION_KEY — generar una sola vez:**
> ```bash
> python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```
> Una vez que existan datos en la BD, **nunca cambiar esta llave** sin un proceso de re-encriptación
> o los tokens de WhatsApp guardados quedarán ilegibles.

---

## 3. Levantar infraestructura base (PostgreSQL + Redis)

```bash
docker compose up -d postgres redis
```

Esperar healthchecks verdes (máx. 30 s):

```bash
docker compose ps
# postgres   running (healthy)
# redis      running (healthy)
```

Si alguno queda en `starting`, revisar logs:
```bash
docker compose logs postgres
docker compose logs redis
```

---

## 4. Aplicar migraciones

```bash
# Instalar dependencias Python localmente (para ejecutar alembic fuera de Docker)
pip install -r requirements.txt

# Aplicar las 4 migraciones en orden
alembic upgrade head
```

Output esperado:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002_add_pgvector
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003_sync_schema_with_models
INFO  [alembic.runtime.migration] Running upgrade 003 -> 004_add_ai_usage_logs
```

> ⚠️ Siempre correr `alembic upgrade head` (las 4 migraciones). Nunca aplicar `001` sola;
> las migraciones 003 y 004 contienen deltas críticos para el schema actual.

Verificar que la extensión pgvector está activa:
```bash
docker compose exec postgres psql -U salesagent -d salesagent_db -c "\dx pgvector"
```

---

## 5. Poblar datos de prueba (seed)

```bash
python scripts/seed_tenant.py
```

El script crea:
- 1 tenant: **Distribuciones La Garantía** (Magangué, Bolívar)
- 1 usuario admin / 1 manager / 3 vendedores / 1 usuario AGENT (IA)
- 3 zonas geográficas + 6 rutas (3 presenciales, 3 de agente WA)
- 40 clientes con datos completos (phone_normalized, avg_purchase_frequency_days, etc.)
- 30 productos con SKU, embedding semántico y rotation_flag
- 90 días de historial de órdenes (~221 órdenes / ~800 items)
- Metas de ventas mensuales para cada vendedor

> El seed es idempotente para el tenant: si ya existe "Distribuciones La Garantía",
> elimina y recrea todos sus datos. Seguro de correr múltiples veces.

---

## 6. Levantar todos los servicios

```bash
# Construir imagen (solo en primera vez o si cambió requirements.txt / Dockerfile)
docker compose build

# Levantar API + workers (sin frontend)
docker compose up -d api celery-worker celery-beat

# Con Flower + Frontend Next.js (perfil dev — incluye ambos)
docker compose --profile dev up -d
```

Puertos expuestos:

| Servicio | Puerto | URL |
|----------|--------|-----|
| API FastAPI | 8000 | http://localhost:8000 |
| Docs Swagger | 8000 | http://localhost:8000/docs |
| Frontend Admin | 3000 | http://localhost:3000 (nativo o `--profile dev`) |
| Flower (Celery) | 5555 | http://localhost:5555 (`--profile dev`) |
| PostgreSQL | **5433** | `postgresql://salesagent:password@localhost:5433/salesagent_db` |
| Redis | 6379 | `redis://localhost:6379` |

> ⚠️ **PostgreSQL corre en el puerto 5433** (no 5432) para evitar conflicto con instalaciones locales de PostgreSQL (ej. Postgres.app v14 que usa :5432). El `.env` ya tiene `localhost:5433`. Los contenedores Docker usan internamente `postgres:5432` (hostname del servicio).

Verificar que la API está viva:
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0","env":"development"}
```

---

## 7. Levantar el frontend (panel admin)

**Opción A — Nativo (recomendado en macOS, hot-reload instantáneo):**
```bash
cd frontend
npm install        # solo la primera vez
npm run dev
```

**Opción B — En Docker (todo en un comando, hot-reload más lento en Mac):**
```bash
# Desde la raíz del proyecto:
docker compose --profile dev up -d
# Levanta API + Celery + Flower + Frontend en un solo comando
```

El panel admin queda disponible en: **http://localhost:3000**

Credenciales de acceso (creadas por el seed):
| Campo | Valor |
|-------|-------|
| Email | `admin@lagarantia.co` |
| Contraseña | `Garantia2026!` |

---

## 8. Configurar webhook de WhatsApp (ngrok)

Para recibir mensajes de WhatsApp en desarrollo se necesita una URL pública.
Usar el script incluido:

```bash
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

El script:
1. Levanta ngrok en el puerto 8000
2. Obtiene la URL pública generada (ej. `https://abc123.ngrok-free.app`)
3. Muestra instrucciones para actualizar el webhook en Meta

**Actualizar webhook en Meta for Developers:**
1. Ir a [developers.facebook.com](https://developers.facebook.com) → tu App → WhatsApp → Configuration
2. En **Webhook**, hacer clic en **Edit**
3. **Callback URL:** `https://TU-URL-NGROK.ngrok-free.app/api/v1/webhooks/whatsapp`
4. **Verify Token:** el valor de `WHATSAPP_WEBHOOK_VERIFY_TOKEN` en tu `.env`
5. Hacer clic en **Verify and Save**
6. Suscribir al evento `messages`

Verificar que el webhook responde correctamente:
```bash
curl "http://localhost:8000/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=test123"
# Debe responder: test123
```

> ⚠️ La URL de ngrok cambia con cada reinicio (plan gratuito). Al reiniciar ngrok,
> actualizar la Callback URL en Meta. Con el plan pago de ngrok se puede fijar un dominio estático.

---

## 9. Smoke tests — checklist de verificación

Ejecutar después de cada deploy para confirmar que todo funciona:

- [ ] `GET /health` → `{"status":"ok"}`
- [ ] `POST /api/v1/admin/auth/login` con `admin@lagarantia.co` / `Garantia2026!` → token JWT
- [ ] `GET /api/v1/admin/dashboard` con token → KPIs con datos
- [ ] `GET /api/v1/admin/clientes` → lista con 40 clientes
- [ ] `GET /api/v1/admin/productos` → lista con 30 productos
- [ ] Panel admin en http://localhost:3000 carga correctamente
- [ ] Flower en http://localhost:5555 muestra workers activos
- [ ] Webhook verificación (paso 8 arriba)

---

## 10. Detener el entorno

```bash
# Detener servicios (conserva datos en volúmenes)
docker compose down

# Detener y eliminar todos los datos (reset completo)
docker compose down -v
```

---

## Troubleshooting

### Error: `ENCRYPTION_KEY is not a valid Fernet key`
La variable `ENCRYPTION_KEY` en `.env` está vacía o es el valor de ejemplo. Generarla con:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Error: `relation "tenants" does not exist`
Las migraciones no se aplicaron o se aplicaron contra otra base de datos. Verificar `DATABASE_URL`
en `.env` y correr `alembic upgrade head` nuevamente.

### Error: `pgvector extension not found`
La imagen de PostgreSQL debe ser `pgvector/pgvector:pg16` (no `postgres:16-alpine`).
La imagen `postgres:*-alpine` no incluye pgvector. Verificar que `docker-compose.yml` dice:
```yaml
image: pgvector/pgvector:pg16
```
Después de corregir la imagen, recrear el contenedor (`docker compose down -v && docker compose up -d postgres`) y volver a aplicar las migraciones.

### API responde 500 en todos los endpoints
Revisar logs de la API:
```bash
docker compose logs api --tail=50
```
Los errores más comunes son variables de entorno faltantes. En desarrollo se requiere al menos `GROQ_API_KEY` (gratuita). Para RAG se necesita `VOYAGE_API_KEY`. En producción: `ANTHROPIC_API_KEY`.

### Celery worker no procesa tareas
```bash
docker compose logs celery-worker --tail=50
```
Si el error es de conexión a Redis, verificar `CELERY_BROKER_URL` en `.env`.

### Frontend no puede conectarse a la API
Verificar que `NEXT_PUBLIC_API_URL` en `frontend/.env.local` apunta a
`http://localhost:8000/api/v1`. En staging/producción reemplazar con la URL real.

### ngrok muestra `ERR_NGROK_108` (túnel ya abierto)
El plan gratuito de ngrok solo permite 1 túnel simultáneo. Cerrar la sesión anterior:
```bash
pkill ngrok
```

---

## Apéndice — Ubuntu 22.04

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip

# Node 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# ngrok
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc > /dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
ngrok config add-authtoken TU_AUTHTOKEN
```
