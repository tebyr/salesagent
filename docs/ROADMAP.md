# Roadmap — Sales Agent SaaS

> Plan de fases y prioridades de implementación.
> Para el estado detallado actual ver `docs/ESTADO_PROYECTO.md`.

---

## Control de versiones

| Versión | Fecha      | Cambios |
|---------|------------|---------|
| 1.0.0   | 2026-04-11 | Plan inicial basado en estado 72% al cierre sesión 4 |
| 1.1.0   | 2026-04-11 | Fase 1 completada — P1 todos los ítems ✅ |
| 1.2.0   | 2026-04-11 | Fase 2: ítems 7 y 9 completados — API tenants + Reports API |
| 1.2.1   | 2026-04-11 | +docs/formacion/ y docs/go_to_market/ — documentación estratégica y de producto |
| 1.2.2   | 2026-04-11 | RAG integration en ClientAgent — `_build_rag_recommendations` con graceful degradation |
| 1.3.0   | 2026-04-12 | Tests de integración completados (ítem 8) + suite completa de documentación técnica |

---

## Estado actual: ~87%

Fase 1 completada. En Fase 2: ítems 7, 9 y 8 completados (API tenants, Reports API, tests de integración). Documentación técnica 100% completa. Pendiente: infraestructura AWS y CI/CD (requieren decisiones externas — cuenta AWS, dominio, región).

**Frente activo: Fase 2** — próximos ítems: infra AWS (ítem 5) + CI/CD (ítem 6).
**Para producción multi-tenant escalable: 100%** (Fase 2 + Fase 3 completa).

---

## ✅ Fase 1 — Staging con primer tenant real (COMPLETADA — sesión 5)
**Objetivo:** levantar el sistema con datos reales de una distribuidora piloto.
**Criterio de salida:** vendedor recibe briefing por WhatsApp, tendero hace un pedido, gerente recibe reporte por email.

| # | Ítem | Estado | Commit |
|---|------|--------|--------|
| 1 | Task Celery de indexación RAG al crear/actualizar producto | ✅ | `be73138` |
| 2 | Inicializar Sentry en `app/api/main.py` | ✅ | `907602b` |
| 3 | Runbook de deploy a staging (`docs/DEPLOY.md`) | ✅ | `907602b` |
| 4 | Script de desarrollo con ngrok (`scripts/start_dev.sh`) | ✅ | `907602b` |

**% al completar Fase 1: ~75%** ✅

---

## Fase 2 — Producción multi-tenant (EN CURSO — sesión 6)
**Objetivo:** infraestructura cloud lista, CI/CD automatizado, gestión de tenants desde plataforma.
**Criterio de salida:** se puede incorporar un nuevo tenant sin tocar código.

| # | Ítem | Estado | Commit |
|---|------|--------|--------|
| 7 | API gestión de tenants (crear/configurar/suspender desde panel) | ✅ | `7c5f50a` |
| 9 | Reports API — exportación CSV/PDF ventas, clientes, metas | ✅ | `7682fad` |
| 8 | Tests de integración contra BD real + cobertura agentes | ✅ | `1c0e4a0` |
| 5 | Infraestructura AWS (ECS Fargate + RDS + ElastiCache + ALB) | ⬜ | — |
| 6 | Pipeline CI/CD GitHub Actions (lint → test → build → deploy) | ⬜ | — |

**% al completar Fase 2: ~95%**

---

## Fase 3 — Escalabilidad y producto
**Objetivo:** hardening, observabilidad y funcionalidades de producto diferenciador.

| # | Ítem | Descripción |
|---|------|-------------|
| 10 | Cobertura de tests ≥ 80% | Agentes, ConversationService, AnalyticsService |
| 11 | Rate limiting por tenant | Throttle WhatsApp + endpoints admin |
| 12 | Observabilidad (Grafana / CloudWatch) | Métricas mensajes, costos AI, latencia endpoints |
| 13 | Panel super-admin multi-tenant | Vista consolidada para el equipo SaaS |
| 14 | Soporte multi-país | Internacionalización frontend (Venezuela, Ecuador) |
| 15 | Integración ERP bidireccional | Conectores Siesa / World Office / SAP vía external_id |

**% al completar Fase 3: 100%**

---

## Dependencias críticas (externas)

| Dependencia | Estado | Impacto si falla |
|-------------|--------|-----------------|
| Cuenta Meta Business + WABA aprobada | Por gestionar | Bloquea todo el flujo WhatsApp |
| Anthropic API key de producción | Por gestionar | Bloquea agentes IA |
| Voyage AI API key de producción | Por gestionar | Bloquea búsqueda semántica |
| SendGrid account verificada | Por gestionar | Bloquea reportes a gerencia |
| Dominio + SSL para webhook | Por gestionar | Meta requiere HTTPS para webhook |
