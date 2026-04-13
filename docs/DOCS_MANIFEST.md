# Manifiesto de Documentación — Sales Agent SaaS

> Archivo de configuración para el skill `/mantener-docs`.
> Define qué documentos existen, qué cubren y qué archivos de código los invalidan.
> Actualizar este manifiesto cuando se agregue un documento nuevo o se mueva un archivo clave.

---

## Documentos técnicos del proyecto

| Doc | Scope | Archivos que lo invalidan | Actualización |
|-----|-------|--------------------------|---------------|
| `docs/ARCHITECTURE.md` | Stack, flujo de agentes, decisiones de diseño | `app/api/main.py`, `app/agents/*.py`, `app/core/*.py`, `docker-compose.yml`, `requirements.txt` | Cuando cambie el stack, se agregue un agente o cambie el flujo de mensajes |
| `docs/DATA_DICTIONARY.md` | Schema completo de las 12 tablas | `app/models/*.py`, `migrations/versions/*.py` | Cuando se agregue/modifique un campo, tabla o migración |
| `docs/DEPLOY.md` | Runbook de deploy local y staging | `docker-compose.yml`, `Dockerfile`, `.env.example`, `scripts/start_dev.sh`, `alembic.ini` | Cuando cambie la infraestructura Docker, variables de entorno o proceso de deploy |
| `docs/TESTING.md` | Cómo correr tests, convenciones, cobertura | `tests/**`, `pytest.ini`, `Makefile` | Cuando se agreguen módulos de tests, cambie la configuración o la cobertura |
| `docs/ONBOARDING.md` | Modelo mental, mapa de archivos, convenciones | `app/models/*.py`, `app/core/*.py`, `app/agents/*.py`, `app/api/v1/admin/__init__.py` | Cuando cambie la estructura de carpetas, se agreguen convenciones o cambien los nombres de campos clave |
| `docs/SECURITY.md` | JWT, Fernet, HMAC, roles, multi-tenancy | `app/core/security.py`, `app/core/crypto.py`, `app/api/v1/admin/auth.py`, `app/api/v1/platform/tenants.py` | Cuando cambie el modelo de autenticación, encriptación o permisos por rol |
| `docs/OPS.md` | Operaciones, comandos de mantenimiento, Celery | `app/scheduler/tasks.py`, `docker-compose.yml`, `app/services/*.py` | Cuando se agreguen tareas Celery, servicios o comandos operacionales nuevos |
| `docs/TENANT_ONBOARDING.md` | Proceso de incorporar un nuevo tenant | `scripts/seed_platform.py`, `app/api/v1/platform/tenants.py`, `app/api/v1/admin/*.py` | Cuando cambie el proceso de onboarding, los endpoints de configuración o los scripts de seed |
| `docs/API_REFERENCE.md` | Todos los endpoints REST del sistema | `app/api/v1/admin/*.py`, `app/api/v1/platform/*.py`, `app/api/v1/reports/*.py`, `app/api/v1/webhooks/*.py` | Cuando se agregue, modifique o elimine un endpoint |
| `docs/ESTADO_PROYECTO.md` | Estado vivo del proyecto | — | Actualizado automáticamente por `/actualizar-estado` al cierre de sesión |
| `docs/ROADMAP.md` | Plan de fases y pendientes | — | Actualizado automáticamente por `/actualizar-estado` al cierre de sesión |

---

## Documentos no técnicos (no sujetos a revisión automática)

| Doc | Descripción |
|-----|-------------|
| `docs/formacion/guia_ia_generativa_consultoria_v1.2.md` | Material de formación — actualizar manualmente cuando cambie la estrategia de IA |
| `docs/formacion/checklist_avance_roadmap.md` | Checklist de formación — actualizar manualmente |
| `docs/go_to_market/Agente_Comercial_IA_Resumen_Ejecutivo.docx` | Presentación ejecutiva — actualizar manualmente con nuevas features |
| `docs/go_to_market/bateria_indicadores_kpi.md` | KPIs del producto — actualizar manualmente |
| `docs/go_to_market/marco_roi_monetizacion.md` | Marco de ROI — actualizar manualmente |

---

## Reglas de actualización

1. **No tocar** `docs/ESTADO_PROYECTO.md` ni `docs/ROADMAP.md` — son responsabilidad exclusiva de `/actualizar-estado`.
2. **No tocar** los documentos de `formacion/` y `go_to_market/` — solo se actualizan manualmente.
3. **Actualizar con precisión quirúrgica** — solo las secciones afectadas por los cambios detectados, nunca reescribir el doc completo.
4. **Verificar antes de actualizar** — leer el doc actual y los archivos de código referenciados antes de proponer cambios.
5. **Reportar siempre** — al terminar, listar exactamente qué se cambió y en qué documento.
