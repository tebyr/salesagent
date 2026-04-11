#!/usr/bin/env bash
# =============================================================================
# start_dev.sh — Entorno de desarrollo local con ngrok
#
# Uso:
#   chmod +x scripts/start_dev.sh
#   ./scripts/start_dev.sh
#
# Que hace:
#   1. Verifica que los servicios Docker esten corriendo
#   2. Levanta ngrok en puerto 8000
#   3. Obtiene la URL publica de ngrok via la API local
#   4. Muestra las instrucciones para configurar el webhook en Meta
#
# Requiere:
#   - ngrok instalado y autenticado (ngrok config add-authtoken TU_TOKEN)
#   - Docker Compose con postgres + redis + api corriendo
#   - jq instalado (brew install jq / apt install jq)
# =============================================================================

set -euo pipefail

# ---- Colores para output ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ---- Config ----
API_PORT=8000
NGROK_API_PORT=4040
WEBHOOK_PATH="/api/v1/webhooks/whatsapp"
ENV_FILE=".env"
WAIT_SECONDS=3

log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "\n${BOLD}${BLUE}▶ $1${NC}"; }

# ---- Verificar que estamos en la raiz del proyecto ----
if [ ! -f "docker-compose.yml" ]; then
    log_error "Ejecutar desde la raiz del proyecto (donde esta docker-compose.yml)"
    exit 1
fi

# ---- Verificar dependencias ----
log_section "Verificando dependencias"

for cmd in docker ngrok curl; do
    if command -v "$cmd" &>/dev/null; then
        log_info "$cmd ✓"
    else
        log_error "$cmd no encontrado. Instalarlo antes de continuar."
        exit 1
    fi
done

if ! command -v jq &>/dev/null; then
    log_warn "jq no encontrado — se mostrara la URL de ngrok sin parsear"
    JQ_AVAILABLE=false
else
    log_info "jq ✓"
    JQ_AVAILABLE=true
fi

# ---- Leer VERIFY_TOKEN del .env ----
log_section "Leyendo configuracion"

VERIFY_TOKEN=""
if [ -f "$ENV_FILE" ]; then
    VERIFY_TOKEN=$(grep -E "^WHATSAPP_WEBHOOK_VERIFY_TOKEN=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
fi

if [ -z "$VERIFY_TOKEN" ]; then
    log_warn "WHATSAPP_WEBHOOK_VERIFY_TOKEN no encontrado en .env"
    log_warn "Configura la variable antes de registrar el webhook en Meta"
    VERIFY_TOKEN="<TU_VERIFY_TOKEN>"
fi

log_info "Verify token: ${VERIFY_TOKEN:0:8}****"

# ---- Verificar servicios Docker ----
log_section "Verificando servicios Docker"

if ! docker info &>/dev/null; then
    log_error "Docker no esta corriendo. Iniciar Docker Desktop."
    exit 1
fi

API_RUNNING=$(docker compose ps --status running --services 2>/dev/null | grep -c "^api$" || true)
if [ "$API_RUNNING" -eq 0 ]; then
    log_warn "El servicio 'api' no esta corriendo. Levantando..."
    docker compose up -d postgres redis api
    log_info "Esperando ${WAIT_SECONDS}s que la API inicie..."
    sleep "$WAIT_SECONDS"
fi

# Verificar health de la API
if curl -sf "http://localhost:${API_PORT}/health" &>/dev/null; then
    log_info "API respondiendo en puerto ${API_PORT} ✓"
else
    log_error "La API no responde en http://localhost:${API_PORT}/health"
    log_error "Revisar logs: docker compose logs api --tail=30"
    exit 1
fi

# ---- Matar instancias previas de ngrok ----
log_section "Iniciando ngrok"

if pgrep ngrok &>/dev/null; then
    log_warn "Cerrando instancia previa de ngrok..."
    pkill ngrok || true
    sleep 1
fi

# Levantar ngrok en background
ngrok http "${API_PORT}" --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
log_info "ngrok iniciado (PID: ${NGROK_PID})"

# Esperar a que ngrok levante su API interna
log_info "Esperando que ngrok establezca el tunel..."
MAX_WAIT=15
ELAPSED=0
NGROK_URL=""

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))

    if $JQ_AVAILABLE; then
        NGROK_URL=$(curl -sf "http://localhost:${NGROK_API_PORT}/api/tunnels" 2>/dev/null \
            | jq -r '.tunnels[] | select(.proto=="https") | .public_url' 2>/dev/null || true)
    else
        NGROK_URL=$(curl -sf "http://localhost:${NGROK_API_PORT}/api/tunnels" 2>/dev/null \
            | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4 || true)
    fi

    if [ -n "$NGROK_URL" ]; then
        break
    fi
done

if [ -z "$NGROK_URL" ]; then
    log_error "No se pudo obtener la URL de ngrok despues de ${MAX_WAIT}s"
    log_error "Verifica que ngrok este autenticado: ngrok config add-authtoken TU_TOKEN"
    log_error "Logs de ngrok: cat /tmp/ngrok.log"
    exit 1
fi

WEBHOOK_URL="${NGROK_URL}${WEBHOOK_PATH}"
log_info "URL publica: ${NGROK_URL} ✓"

# ---- Verificar que el webhook responde ----
log_section "Verificando endpoint del webhook"

CHALLENGE="test_$(date +%s)"
WEBHOOK_RESPONSE=$(curl -sf \
    "${WEBHOOK_URL}?hub.mode=subscribe&hub.verify_token=${VERIFY_TOKEN}&hub.challenge=${CHALLENGE}" \
    2>/dev/null || true)

if [ "$WEBHOOK_RESPONSE" = "$CHALLENGE" ]; then
    log_info "Webhook verificado correctamente ✓"
else
    log_warn "El webhook no respondio el challenge. Verifica WHATSAPP_WEBHOOK_VERIFY_TOKEN en .env"
fi

# ---- Instrucciones para Meta ----
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  CONFIGURAR WEBHOOK EN META FOR DEVELOPERS${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  1. Abrir: ${BLUE}https://developers.facebook.com${NC}"
echo -e "     Tu App → WhatsApp → Configuration → Webhook → Edit"
echo ""
echo -e "  2. ${BOLD}Callback URL:${NC}"
echo -e "     ${GREEN}${WEBHOOK_URL}${NC}"
echo ""
echo -e "  3. ${BOLD}Verify Token:${NC}"
echo -e "     ${GREEN}${VERIFY_TOKEN}${NC}"
echo ""
echo -e "  4. Clic en ${BOLD}Verify and Save${NC}"
echo -e "     Suscribir al evento: ${BOLD}messages${NC}"
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Panel admin:    ${BLUE}http://localhost:3000${NC}"
echo -e "  API docs:       ${BLUE}http://localhost:${API_PORT}/docs${NC}"
echo -e "  Flower (tasks): ${BLUE}http://localhost:5555${NC}"
echo -e "  ngrok inspect:  ${BLUE}http://localhost:${NGROK_API_PORT}${NC}"
echo ""
echo -e "${YELLOW}  Recuerda: la URL de ngrok cambia con cada reinicio (plan gratuito).${NC}"
echo -e "${YELLOW}  Actualizar Callback URL en Meta cada vez que reinicies el script.${NC}"
echo ""
echo -e "  Para detener ngrok: ${BOLD}pkill ngrok${NC}"
echo ""

# ---- Mantener el script vivo mientras ngrok corre ----
log_info "Entorno listo. Presiona Ctrl+C para detener ngrok y salir."
echo ""

cleanup() {
    echo ""
    log_info "Deteniendo ngrok (PID: ${NGROK_PID})..."
    kill "$NGROK_PID" 2>/dev/null || true
    log_info "ngrok detenido. Los servicios Docker siguen corriendo."
    exit 0
}

trap cleanup INT TERM

wait "$NGROK_PID" 2>/dev/null || true
