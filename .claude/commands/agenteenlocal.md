# Comando: /agenteenlocal

Levanta todos los servicios necesarios para que el agente funcione en local,
presenta los datos para configurar Meta y guía al usuario para actualizar el token de WhatsApp.

---

## Pasos a ejecutar

### 1. Levantar infraestructura Docker

```bash
cd /Users/oscarmauriciogomezacevedo/claudecode/salesagent
docker compose up -d postgres redis api celery-worker celery-beat
```

Esperar 5 segundos y verificar estado:

```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

Si algún servicio no está `Up`, mostrar sus logs:

```bash
docker compose logs <servicio-caído> --tail=30
```

Y detener con error descriptivo para que el usuario lo resuelva.

---

### 2. Verificar que la API responde

```bash
curl -s http://localhost:8000/health
```

Debe devolver `{"status":"ok",...}`. Si no, el contenedor `api` necesita más tiempo — reintentar una vez con pausa de 5 segundos.

---

### 3. Levantar Frontend Next.js

Verificar si ya está corriendo:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Si devuelve `200` → ya está arriba, continuar.
Si no → lanzar en background:

```bash
cd /Users/oscarmauriciogomezacevedo/claudecode/salesagent/frontend
npm run dev > /tmp/frontend.log 2>&1 &
cd /Users/oscarmauriciogomezacevedo/claudecode/salesagent
```

Esperar 6 segundos y verificar de nuevo.

---

### 4. Levantar ngrok

Verificar si ya está corriendo:

```bash
curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
urls = [t['public_url'] for t in d.get('tunnels', []) if t['public_url'].startswith('https')]
print(urls[0] if urls else 'NO_TUNNEL')
"
```

Si devuelve `NO_TUNNEL` → lanzar ngrok:

```bash
ngrok http 8000 > /tmp/ngrok.log 2>&1 &
```

Esperar 4 segundos y obtener la URL:

```bash
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
d = json.load(sys.stdin)
urls = [t['public_url'] for t in d.get('tunnels', []) if t['public_url'].startswith('https')]
print(urls[0] if urls else '')
")
echo $NGROK_URL
```

---

### 5. Verificar que el webhook responde correctamente

```bash
curl -s "${NGROK_URL}/api/v1/webhook?hub.mode=subscribe&hub.verify_token=ibcaribe-webhook-2026&hub.challenge=TEST_OK"
```

Debe devolver `TEST_OK`. Si devuelve otra cosa o error, hay un problema con el routing — reportar al usuario.

---

### 6. Presentar datos de configuración al usuario

Mostrar este resumen con los valores reales obtenidos:

```
🚀 Agente en local — Todos los servicios operativos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱  META — Actualizar webhook en developers.facebook.com
    App: IbSales Agent → WhatsApp → Configuración → Webhooks

    URL callback : {NGROK_URL}/api/v1/webhook
    Token verif. : ibcaribe-webhook-2026

🌐  Panel administrativo
    URL   : http://localhost:3000
    Email : admin@lagarantia.co
    Pass  : Garantia2026!

📲  Números registrados para pruebas (sandbox Meta)
    · Oscar Gomez      +573174003589  (salesperson)
    · Danilo Juvinao   +573162460168  (salesperson)
    · Leslie Blanco    +573173715849  (salesperson)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  El token de acceso de Meta dura 24 horas.
    Debes renovarlo cada vez que arranques el entorno.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 7. Guiar al usuario para obtener el nuevo token de Meta

Indicar al usuario:

> **Paso 1:** Ve a [developers.facebook.com](https://developers.facebook.com)
> **Paso 2:** Selecciona la app **IbSales Agent**
> **Paso 3:** En el menú izquierdo → **WhatsApp** → **Configuración de la API**
> **Paso 4:** En la sección **"Token de acceso temporal"** → copia el token completo (empieza con `EAA...`)
>
> **Pégalo aquí cuando lo tengas.**

Esperar a que el usuario pegue el token en el chat.

---

### 8. Actualizar el token automáticamente via API

Con el token que proporcionó el usuario, ejecutar:

```bash
# Obtener JWT del admin
JWT=$(curl -s -X POST http://localhost:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lagarantia.co","password":"Garantia2026!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Actualizar el access token en el tenant
RESULT=$(curl -s -X PUT http://localhost:8000/api/v1/admin/settings/whatsapp \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{\"access_token\": \"<TOKEN_DEL_USUARIO>\"}")

echo $RESULT
```

Verificar que la respuesta no contiene `"detail"` de error.

---

### 9. Confirmar todo operativo

Mostrar resumen final:

```
✅ ¡Agente completamente operativo!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Docker (API + Celery + DB + Redis) : ✅
  Frontend Next.js :3000             : ✅
  ngrok activo                       : ✅  {NGROK_URL}
  Token Meta actualizado             : ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ya puedes enviar mensajes de prueba desde:
  · +573174003589  (Oscar Gomez)
  · +573162460168  (Danilo Juvinao)
  · +573173715849  (Leslie Blanco)

Recuerda que en sandbox de Meta los números
deben estar agregados como "test recipients".
```

---

## Notas importantes

- **ngrok cambia la URL cada vez que se reinicia** → siempre hay que actualizar el webhook en Meta.
- **El token de Meta dura 24 horas** en sandbox → renovar cada sesión de pruebas.
- Si el frontend no levanta, revisar `/tmp/frontend.log` para el error.
- Si Docker no levanta algún servicio, revisar con `docker compose logs <servicio>`.
- Para ver mensajes en tiempo real: `docker compose logs -f api | grep -v "sqlalchemy"`.
