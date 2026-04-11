# Checklist de Avance — Roadmap IA Generativa para Consultoría

> **Cómo usar este documento:**
> Actualizar el estado de cada habilidad después de cada sesión de trabajo.
> Referencia cruzada con `guia_ia_generativa_consultoria_v1.2.md` para profundizar en cualquier concepto.

**Última actualización:** 2026-04-11
**Proyecto de validación:** Sales Agent SaaS (avance ~82%)

---

## Estados

| Símbolo | Significado |
|---------|-------------|
| ✅ | Aplicado en el proyecto con código real en producción |
| 🟡 | Conceptualizado y documentado, pendiente de implementar |
| 🔵 | Conocido teóricamente, sin aplicación en el proyecto aún |
| ⬜ | Pendiente — no iniciado |

---

## FASE 1 — Fundamentos (Mes 1–2)

| Habilidad | Estado | Dónde se aplica en el proyecto |
|-----------|--------|-------------------------------|
| Entender qué es un LLM y cómo funciona | ✅ | Selección dinámica Haiku/Sonnet/Opus por tarea |
| Diferencias entre modelos (Haiku/Sonnet/Opus) | ✅ | `app/agents/` — selección por complejidad |
| Prompt Engineering básico (zero-shot, few-shot) | ✅ | System prompts de cada sub-agente |
| Prompt Engineering avanzado (chain-of-thought) | 🟡 | Definido en arquitectura, pendiente auditoría formal |
| System prompts con roles y restricciones | ✅ | `sales_agent.py`, `client_agent.py`, `management_agent.py` |
| Confirmation-before-commit | ✅ | Todos los flujos NLDI del proyecto |
| Embeddings — concepto y uso | ✅ | `embedding_service.py` + pgvector |
| Modelos de embedding (Voyage AI, OpenAI) | ✅ | voyage-3, 1024 dims, integrado y funcionando |
| RAG — concepto básico | ✅ | `embedding_service.py` — indexación + recuperación |
| RAG — re-indexación incremental | ✅ | `index_product_task` en Celery |

**Diagnóstico Fase 1:** Completada y validada en producción. ✅

---

## FASE 2 — Construcción (Mes 3–5)

| Habilidad | Estado | Dónde se aplica en el proyecto |
|-----------|--------|-------------------------------|
| Arquitectura multi-agente con orquestador | ✅ | `app/agents/orchestrator.py` |
| Sub-agentes especializados por rol | ✅ | vendedor / cliente / gerencia |
| Selección dinámica de modelo por complejidad | ✅ | Implementado en todos los agentes |
| Intention-Based UI | ✅ | Clasificación INFORMATIONAL/TRANSACTIONAL/etc. |
| NLDI — Natural Language Data Ingestion | ✅ | Pedidos y clientes vía lenguaje natural |
| Máquina de estados conversacional | ✅ | `wa_conversations.state` + JSONB context |
| Scheduler proactivo con Celery Beat | ✅ | 8 tareas programadas implementadas |
| RAG híbrido con metadata filtering | ✅ | `search_products` con filtros estructurales + vector |
| Principio exacto vs. gradiente | ✅ | Aplicado en `build_semantic_text` |
| Semantic tags JSONB | 🟡 | Campo creado en BD, enriquecimiento pendiente |
| Query contextual cruzando historial + mensaje | 🟡 | `client_product_affinities` disponible, integración pendiente |
| Multi-tenancy con JWT | ✅ | `tenant_slug` en JWT, filtro obligatorio en toda query |
| Roles diferenciados incluyendo rol AGENT | ✅ | 5 roles implementados incluyendo vendedor virtual IA |
| Encriptación de datos sensibles (Fernet) | ✅ | `crypto.py` — tokens WhatsApp encriptados |
| Graceful degradation 5 niveles | ✅ | Documentado e implementado en agentes |
| Integración con APIs externas (WhatsApp, SendGrid) | ✅ | `whatsapp_service.py`, `email_service.py` |
| Reports API (CSV + PDF) | ✅ | `app/api/v1/reports/` — ventas, clientes, metas |
| API multi-tenant de gestión de tenants | ✅ | `/api/v1/platform/tenants/` |
| Frontend admin (Next.js + React Query) | ✅ | Panel con productos, rutas, zonas |
| LangChain / LlamaIndex | 🔵 | No usado — arquitectura propia equivalente |

**Diagnóstico Fase 2:** ~90% completada. Los gaps son la integración de la query contextual con `client_product_affinities` y el enriquecimiento de `semantic_tags`. LangChain no aplica porque se construyó arquitectura propia equivalente.

---

## FASE 3 — Especialización (Mes 6–9)

| Habilidad | Estado | Dónde se aplica en el proyecto |
|-----------|--------|-------------------------------|
| Testing de sistemas IA — unit tests | ✅ | 75 tests con mocking de AsyncSessionLocal |
| Testing de sistemas IA — integration tests | 🟡 | Identificado como bloqueante P1, pendiente implementar |
| Estrategia de mocking para LLMs | ✅ | `tests/conftest.py` — patrón `_Ctx` |
| Evaluación de sistemas RAG (métricas) | 🟡 | Tablas de analytics disponibles, dashboard pendiente |
| Métricas de comportamiento de agente | 🟡 | Datos en BD, cálculo y visualización pendiente |
| Observabilidad con Sentry | ✅ | Inicializado con integraciones FastAPI+SQLAlchemy+Celery |
| Logging estructurado | ✅ | `logger.info("event", key=value)` en todo el proyecto |
| Infraestructura cloud AWS (ECS + RDS + Redis) | ⬜ | Pendiente — bloqueante para producción |
| Infrastructure as Code (Terraform / CDK) | ⬜ | Pendiente junto con ítem anterior |
| CI/CD con GitHub Actions | ⬜ | Pendiente — depende de infraestructura AWS |
| Runbook de deploy | ✅ | `docs/DEPLOY.md` — documentado |
| Governance de IA — riesgos y alucinaciones | 🔵 | Conceptualizado, sin implementación formal |
| Rate limiting por tenant | ⬜ | Identificado en P3 del backlog |
| Especialización vertical salud | 🔵 | Sector objetivo, sin implementación específica aún |
| Especialización vertical retail | 🔵 | Sector objetivo, sin implementación específica aún |

**Diagnóstico Fase 3:** ~35% completada. Tests unitarios y observabilidad aplicados. Los tres ítems críticos pendientes son: tests de integración, infraestructura AWS y CI/CD.

---

## FASE 4 — Escala (Mes 10–12)

| Habilidad | Estado | Evidencia |
|-----------|--------|-----------|
| Caso de estudio documentado | 🟡 | Resumen semántico del proyecto disponible |
| Resumen ejecutivo para clientes | ✅ | `Agente_Comercial_IA_Resumen_Ejecutivo.docx` generado |
| Pricing de proyectos de IA | 🔵 | Estimados de costo disponibles, pricing formal pendiente |
| Paquetes de servicios repetibles | ⬜ | Pendiente definir formalmente |
| Estrategia de contenido (LinkedIn) | ⬜ | Pendiente |
| Alianzas estratégicas | ⬜ | Pendiente |
| Panel multi-tenant (super admin) | ⬜ | Identificado en P3 del backlog |
| Internacionalización (Venezuela, Ecuador) | ⬜ | Identificado en P3 del backlog |

**Diagnóstico Fase 4:** ~10% completada. El resumen ejecutivo es el primer entregable de posicionamiento. El caso de estudio formal se puede construir cuando el primer tenant esté activo.

---

## Resumen de posición actual

```
Fase 1 — Fundamentos        ████████████████████  100%  ✅ Completada
Fase 2 — Construcción       ██████████████████░░   90%  🟡 Gaps menores
Fase 3 — Especialización    ███████░░░░░░░░░░░░░   35%  🟡 En progreso
Fase 4 — Escala             ██░░░░░░░░░░░░░░░░░░   10%  ⬜ Iniciada
```

**Posición global en el roadmap: Mes 6–7 equivalente**
El proyecto ha comprimido el aprendizaje de 12 meses a ~6 meses gracias a la validación en producción real.

---

## Próximos tres pasos concretos

1. **Integrar `search_products` en el agente cliente** — conectar `client_product_affinities` con la query contextual. Cierra el último gap de Fase 2.

2. **Tests de integración** — implementar tests contra BD real para agentes, `ConversationService` y `AnalyticsService`. Desbloquea la preparación para producción.

3. **Infraestructura AWS con CDK** — Fargate + RDS + ElastiCache. Habilita CI/CD y primer despliegue real.

---

*Checklist mantenido como parte del proyecto Sales Agent SaaS*
*Referencia: `guia_ia_generativa_consultoria_v1.2.md`*
