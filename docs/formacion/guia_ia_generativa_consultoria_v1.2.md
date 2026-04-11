# Guía de IA Generativa para Consultoría
## Documento de Estudio Personal

---

**Perfil:** Consultor de IA Generativa — Perfil mixto (técnico + negocio)
**Sectores foco:** Retail / E-commerce · Salud · B2B Latinoamérica
**Proyecto de referencia:** Sales Agent SaaS — Agente comercial para distribuidoras canal tradicional

---

## Control de Versiones

| Versión | Fecha      | Descripción                                              |
|---------|------------|----------------------------------------------------------|
| 1.0.0   | 2026-04-04 | Versión inicial — Fundamentos RAG, embeddings, semantic tags |
| 1.1.0   | 2026-04-04 | Agrega indexación híbrida, metadata filtering, principio exacto/gradiente y skill RAG híbrido |
| 1.2.0   | 2026-04-11 | Agrega Fase 2 avanzada y Fase 3 inicial: scheduler, Celery Beat, encriptación Fernet, multi-tenancy con JWT, testing de sistemas IA, graceful degradation, observabilidad, CI/CD, infraestructura cloud. Nuevo archivo checklist_avance_roadmap.md |

---

## Roadmap de Aprendizaje (12 meses)

| Fase | Período   | Foco principal                                                      |
|------|-----------|---------------------------------------------------------------------|
| 1    | Mes 1–2   | Fundamentos de LLMs · RAG básico · Prompt Engineering avanzado     |
| 2    | Mes 3–5   | LangChain/LlamaIndex · Agentes · Casos de uso por sector · Caso de estudio |
| 3    | Mes 6–9   | Especialización vertical · Evaluación de sistemas IA · Governance  |
| 4    | Mes 10–12 | Posicionamiento · Paquetes de servicios · Escalado                 |

> **Nota de progreso (actualizada 2026-04-11):** El proyecto Sales Agent SaaS está al ~82% de avance con 6 sesiones de trabajo registradas. Fase 2 completamente aplicada en producción. Fase 3 iniciada con tests (75 tests), encriptación, observabilidad con Sentry y documentación de deploy. Los frentes abiertos son: tests de integración, infraestructura AWS y CI/CD.

---

## Glosario de Términos de IA Generativa

Los términos están organizados por fase del roadmap en que se introducen. Dentro de cada fase, el orden es conceptual — cada término construye sobre el anterior.

---

### FASE 1 — Fundamentos

---

#### LLM — Large Language Model

**Definición:** Modelo de lenguaje de gran escala. Sistema de inteligencia artificial entrenado sobre enormes volúmenes de texto que aprende a predecir y generar lenguaje de forma coherente y contextualmente relevante.

**Cómo funciona (nivel conceptual):** El modelo aprende representaciones estadísticas del lenguaje — no "entiende" en el sentido humano, sino que aprende patrones tan complejos que el resultado es funcionalmente similar a la comprensión.

**Modelos relevantes:**
- Claude (Anthropic) — Haiku 4.5 · Sonnet 4.6 · Opus 4.6
- GPT-4o (OpenAI)
- Gemini (Google)
- Llama (Meta) — open source

**Conexión con el proyecto:** Sales Agent SaaS usa tres modelos Claude con selección dinámica según complejidad de la tarea. Haiku para clasificación de intención y notificaciones rutinarias, Sonnet para respuestas reactivas y briefings, Opus para reportes gerenciales de alta calidad.

**Conexión con consultoría:** Saber elegir el modelo correcto para cada tarea es una decisión de diseño con impacto directo en costos operativos. Es una habilidad vendible en proyectos de implementación.

---

#### Prompt Engineering

**Definición:** Disciplina de diseño de instrucciones (prompts) para obtener respuestas precisas, consistentes y útiles de un LLM. No es solo "escribir preguntas" — es diseñar el contexto, las restricciones, el tono y el formato de las instrucciones para guiar el comportamiento del modelo.

**Técnicas principales:**

| Técnica | Descripción | Cuándo usar |
|---------|-------------|-------------|
| Zero-shot | Instrucción directa sin ejemplos | Tareas simples y bien definidas |
| Few-shot | Instrucción con 2-5 ejemplos incluidos | Cuando el formato de salida es específico |
| Chain-of-thought | Pedirle al modelo que razone paso a paso | Problemas complejos o de múltiples pasos |
| System prompt | Instrucciones de rol y comportamiento base | Siempre — es la base de cualquier agente |
| Confirmation-before-commit | El agente presenta resumen y espera confirmación | Acciones irreversibles (pedidos, registros) |

**Conexión con el proyecto:** Cada sub-agente del sistema (vendedor, cliente, gerencia) tiene su propio system prompt con tono, capacidades y restricciones definidas. El patrón Confirmation-Before-Commit está implementado para todas las acciones irreversibles.

**Conexión con consultoría:** Es el servicio más vendible en el corto plazo porque no requiere infraestructura. Una auditoría de prompts para una empresa puede ofrecerse desde el mes 1-2 del roadmap.

---

#### Embedding

**Definición:** Representación numérica (vector) del significado semántico de un texto. Convierte palabras, frases o documentos en listas de números (típicamente 1.536 o 3.072 dimensiones) que capturan relaciones de significado.

**Principio clave:** Textos con significado similar producen vectores similares, independientemente de las palabras exactas usadas. "Gaseosa Coca-Cola 350ml" y "refresco Cola lata pequeña" producen vectores cercanos en el espacio vectorial aunque no comparten palabras.

**Modelos de embedding:**
- `text-embedding-3-small` (OpenAI) — buen balance costo/calidad, soporta español
- `text-embedding-3-large` (OpenAI) — mayor calidad, mayor costo
- `embed-multilingual-v3` (Cohere) — especializado en múltiples idiomas

**Conexión con el proyecto:** Los embeddings son la base del sistema RAG del catálogo de productos. Cada producto se convierte en un vector que permite búsqueda semántica — el agente encuentra "bebidas frías" aunque el cliente escriba "algo para tomar".

**Conexión con consultoría:** Explicar embeddings a un cliente no técnico con la metáfora del espacio vectorial (productos similares se agrupan naturalmente) es una habilidad de comunicación diferenciadora.

---

### FASE 2 — Construcción

---

#### RAG — Retrieval-Augmented Generation

**Significado de las siglas:**
- **Retrieval** — Recuperación: buscar información relevante en una fuente externa
- **Augmented** — Aumentada: enriquecer el contexto que se le da al modelo con esa información
- **Generation** — Generación: el LLM produce la respuesta usando ese contexto enriquecido

**Definición:** Patrón arquitectónico que permite a un LLM acceder a información externa y actualizada en el momento de generar una respuesta, sin necesidad de reentrenar el modelo. El modelo no "sabe" todo de antemano — se le da la información relevante justo antes de responder.

**Por qué existe:** Los LLMs tienen una fecha de corte de conocimiento y no pueden acceder a información privada (catálogos, historiales de clientes, bases de datos internas). RAG resuelve ambos problemas.

**Los dos momentos del RAG:**

**Momento 1 — Indexación** (ocurre una vez o al actualizar datos):
1. Tomar los documentos/registros a indexar (catálogo de productos)
2. Convertir cada uno en texto semántico enriquecido
3. Generar el embedding de cada texto
4. Almacenar los vectores en un vector store

**Momento 2 — Recuperación** (ocurre en cada interacción):
1. Recibir la consulta del usuario
2. Convertir la consulta en embedding
3. Buscar los vectores más similares (top-k) en el vector store
4. Incluir esos documentos recuperados en el contexto del prompt
5. El LLM genera la respuesta usando ese contexto

**Re-indexación incremental:** No es necesario re-indexar todo el catálogo al agregar un producto. Cada producto tiene su propio vector como registro independiente:
- Producto nuevo → `INSERT` del nuevo vector
- Producto modificado (nombre/descripción) → `UPDATE` del vector
- Producto desactivado → `DELETE` del vector o filtro por `is_active`
- Re-indexación total → solo cuando cambia el modelo de embedding o el esquema del texto semántico

**Vector stores disponibles:**
| Opción | Cuándo usar |
|--------|-------------|
| `pgvector` | Ya tienes PostgreSQL, catálogo < 100k registros, multi-tenant |
| Pinecone | Catálogos masivos, búsqueda a escala, equipo dedicado |
| Weaviate | Necesidades avanzadas de filtrado y clasificación |
| Chroma | Prototipos y desarrollo local |

**Conexión con el proyecto:** RAG resuelve el Gap 1 identificado en el diagnóstico del proyecto. El agente cliente necesita recomendar productos del catálogo sin pasar los 500+ SKUs completos en cada prompt. La recomendación es usar `pgvector` dado que PostgreSQL ya está en el stack (AWS RDS).

**Conexión con consultoría:** RAG es el componente técnico más demandado en proyectos de implementación de IA para empresas. Dominarlo es el núcleo de la propuesta de valor técnica en Fase 2.

---

#### Query Contextual en RAG

**Definición:** La consulta de recuperación que se convierte en embedding para buscar en el vector store. En sistemas avanzados, la query no es solo lo que el usuario escribió — se construye combinando múltiples fuentes de contexto para obtener una recuperación más precisa.

**Ejemplo en el proyecto (agente cliente):**
```
Cliente: Tienda de barrio en Magangué
Historial reciente: gaseosas, snacks, productos de aseo
Objetivo: recomendación de pedido semanal
Promociones activas: 2x1 en bebidas carbonatadas
```
Este texto compuesto produce un embedding que recupera exactamente los productos relevantes para ese cliente en ese momento — no una búsqueda genérica.

**Principio clave:** La calidad de la recuperación depende directamente de la calidad de la query. Una query pobre recupera productos irrelevantes aunque el índice sea perfecto.

---

#### Semantic Tags — Etiquetas Semánticas

**Definición:** Campo estructurado (típicamente JSONB en PostgreSQL) que almacena palabras clave, sinónimos, términos del dominio y atributos cualitativos de una entidad, con el propósito de enriquecer el texto semántico que se vectoriza para RAG.

**Estructura recomendada:**
```json
{
  "synonyms": ["rojita", "gaseosa roja", "colombiana"],
  "channel_terms": ["infaltable", "ancla", "alta rotación"],
  "use_context": ["tienda de barrio", "cafetería", "fin de semana"],
  "strategy": ["siembra", "producto estrella"],
  "attributes": ["frío", "carbonatado", "individual"]
}
```

**Mejores prácticas para construcción dinámica:**

1. **Separar por categorías** — no usar array plano. Permite búsquedas filtradas y mantenimiento más claro.

2. **Generación automática como base** — el sistema genera tags iniciales desde campos existentes (nombre, categoría, marca, tipología). El operador enriquece manualmente sobre esa base.

3. **Tags heredados desde jerarquía** — un producto hereda tags de su categoría y subcategoría. Reduce trabajo manual.

4. **Nunca sobreescribir lo manual con lo automático** — el conocimiento humano del dominio tiene prioridad sobre la inferencia automática.

5. **Versionado de tags** — registrar cuándo se agregó cada tag y si fue el sistema o un operador. Permite auditoría y trazabilidad.

6. **Tags relacionales entre entidades** — un cliente puede tener tags inferidos de su historial (`"comprador_habitual_bebidas"`). Un proveedor puede tener tags cualitativos (`"respuesta_rapida"`). Estas capas se cruzan en la query contextual.

7. **Validación antes de indexar** — verificar longitud mínima del texto semántico (~50-80 tokens) antes de generar el embedding. Textos pobres contaminan el índice.

8. **Feedback loop desde el agente** — cuando el cliente acepta o rechaza una recomendación, esa señal puede usarse para evaluar y mejorar los tags.

**Conexión con el proyecto:** Campo `semantic_tags JSONB` a agregar en la tabla `products` (próxima versión del diccionario de datos). Aplicación futura a entidades `clients` y `suppliers` para enriquecer consultas de agentes especializados.

**Visión de ecosistema:** El patrón semantic_tags es un skill reutilizable que puede aplicarse a cualquier entidad clave del modelo de datos, habilitando un ecosistema de agentes especializados con recuperación semántica de alta calidad sobre múltiples dominios.

**Conexión con consultoría:** El enriquecimiento semántico es donde la experiencia de dominio de 20+ años en distribución se convierte en ventaja técnica directa. Los términos del canal tradicional colombiano (Infaltable, Siembra, Tendero, Codificar) que un desarrollador externo no conoce son exactamente el tipo de conocimiento que hace que el RAG funcione bien en este contexto.

---

#### Intention-Based UI

**Definición:** Paradigma de interfaz conversacional donde el sistema interpreta la intención del usuario en lenguaje natural y responde a ella, en lugar de requerir que el usuario siga menús fijos o protocolos predefinidos.

**Categorías de intención:**

| Categoría | Ejemplos |
|-----------|----------|
| `INFORMATIONAL` | "¿cuánto llevo vendido este mes?" · "¿cuál es el precio del aceite?" |
| `TRANSACTIONAL` | "quiero hacer un pedido" · "cancela la última orden" |
| `OPERATIONAL` | "ya llegué donde el cliente" · "el señor no estaba" |
| `RELATIONAL` | "buenos días" · "gracias" · "tengo un problema" |
| `OUT_OF_SCOPE` | Solicitudes fuera del alcance del agente |

**Conexión con el proyecto:** El orquestador usa Haiku para clasificar la intención de cada mensaje antes de enrutar al sub-agente correcto. Esto minimiza costos (clasificación barata) y maximiza calidad (sub-agente especializado responde).

**Relación con RAG:** Intention-Based UI opera en la entrada (interpreta lo que el usuario quiere). RAG opera en la recuperación (encuentra la información correcta para responder a esa intención). Los dos se potencian mutuamente — una intención bien interpretada produce una query de recuperación más precisa.

---

#### NLDI — Natural Language Data Ingestion

**Definición:** Patrón de captura de datos estructurados a través de lenguaje natural conversacional, eliminando la necesidad de formularios. El sistema extrae entidades del texto libre, las valida, las presenta para confirmación y las persiste.

**Flujo estándar:**
```
Usuario: "Agrega a Ferretería Los Pinos, don Carlos, Calle 5 con 
          Carrera 8, tel 3154421890"
         ↓
  Extracción de entidades (LLM)
         ↓
  Validación de campos obligatorios
         ↓
  Presentar resumen estructurado al usuario
         ↓
Usuario: "SÍ" / "el teléfono es 3154422890"
         ↓
  Persistir / corregir campo específico
```

**Regla fundamental:** Confirmar siempre antes de persistir. Las correcciones parciales no reinician el flujo completo.

**Conexión con el proyecto:** Implementado para registro de clientes nuevos, toma de pedidos en lenguaje natural y registro de novedades de visita. Especialmente valioso para vendedores en campo que operan desde el celular con poco tiempo.

**Visión futura:** NLDI en el panel administrativo para enriquecer entidades clave (productos, clientes, proveedores) con semantic_tags a través de conversación natural.

---

#### Arquitectura Multi-Agente

**Definición:** Sistema donde múltiples agentes de IA especializados colaboran, cada uno con un rol, contexto y capacidades acotadas, coordinados por un orquestador central.

**Patrón del proyecto:**
```
Mensaje entrante
      ↓
  Orquestador (clasifica intención, identifica tenant y rol)
      ↓
  Sub-agente especializado (vendedor / cliente / gerencia)
      ↓
  Claude API (modelo seleccionado dinámicamente)
      ↓
  Respuesta al usuario
```

**Principios de diseño:**
- El orquestador no tiene lógica de negocio — solo enruta
- Cada sub-agente es stateless — el estado lo gestiona el orquestador
- Cada sub-agente carga únicamente el contexto relevante para su rol
- La selección de modelo ocurre por complejidad de tarea, no por sub-agente

**Conexión con consultoría:** La arquitectura multi-agente es el patrón más solicitado en proyectos empresariales complejos. Documentar cómo se diseñó en este proyecto es material directo para propuestas futuras.

---

#### Knowledge Graph Enrichment

**Definición:** Estrategia de enriquecimiento semántico aplicada a múltiples entidades relacionadas en un modelo de datos, donde cada entidad clave tiene su propia capa de metadata semántica que se conecta con las demás para habilitar recuperación contextual cruzada.

**Diferencia con RAG simple:** En RAG simple se vectoriza una sola colección de documentos. En Knowledge Graph Enrichment, se vectorizan múltiples entidades (productos, clientes, proveedores) y las queries de recuperación pueden cruzar información de varias entidades simultáneamente.

**Ejemplo de recuperación cruzada:**
- El agente sabe que el cliente es "tienda de barrio de alta rotación" (tag del cliente)
- Busca productos con tag "alta rotación" + "tienda de barrio" (tag del producto)
- Filtra proveedores con tag "entrega rápida" (tag del proveedor)
- El resultado es una recomendación que considera las tres dimensiones

**Conexión con el proyecto:** Visión de largo plazo del ecosistema. La implementación de `semantic_tags` en `products` es el primer paso. La extensión a `clients` y `suppliers` habilita el Knowledge Graph completo.

---

#### Indexación Híbrida con Metadata Filtering

**Definición:** Patrón de arquitectura RAG donde la búsqueda semántica por vector se combina con filtros SQL exactos aplicados previamente sobre atributos estructurales de la entidad. Reduce el espacio de búsqueda antes de calcular similitud, produciendo resultados más precisos y consultas más eficientes.

**El principio fundamental — exacto vs. gradiente:**

> Los atributos que identifican o clasifican una entidad de forma exacta y discreta son filtros estructurales y nunca deben incluirse en el texto semántico vectorizado. Solo se vectoriza aquello que tiene gradiente de significado — lo que puede ser "más o menos parecido" a una consulta en lenguaje natural.

| Tipo | Naturaleza | Dónde va | Ejemplos |
|------|-----------|----------|---------|
| Estructural | Exacto, discreto, sin gradiente | Filtro SQL `WHERE` | `brand_id`, `category_id`, `tenant_id`, `is_active`, `price` |
| Semántico | Difuso, contextual, con gradiente | Texto vectorizado → embedding | `semantic_tags`, `description`, `synonyms`, `use_context` |

**Por qué importa esta separación:**

Mezclar ambos tipos en un solo vector produce un embedding que intenta capturar demasiado y pierde precisión en lo semántico. "Marca: Coca-Cola" o es Coca-Cola o no lo es — no tiene sentido buscar algo "parecido a Coca-Cola" en el vector cuando puedes filtrar exactamente por `brand_id`.

**Patrón de query híbrida:**
```sql
SELECT * FROM products
WHERE tenant_id = :tenant_id          -- filtro estructural obligatorio
  AND category_id = :category_id      -- filtro estructural opcional
  AND is_active = true                -- filtro estructural obligatorio
  AND embedding IS NOT NULL           -- solo productos indexados
ORDER BY embedding <=> :query_vector  -- similitud semántica sobre el espacio reducido
LIMIT 10
```

**Cómo el agente construye la query híbrida:**

El agente combina dos fuentes de contexto antes de llamar a `search_products`:
- **Filtros estructurales** — inferidos del historial del cliente (`client_product_affinities`): las categorías que más compra determinan el `category_id` del filtro
- **Query semántica** — construida desde la conversación en curso: "algo para surtir el fin de semana" se convierte en el vector de búsqueda

El resultado es una recomendación categorialmente pertinente para ese cliente Y semánticamente relevante para ese momento — sin recorrer los 500 SKUs completos.

**Conexión con el proyecto:** Cambio de diseño aplicado a `embedding_service.py`. `build_semantic_text` excluye `brand`, `category` y `subcategory` del texto vectorizado. `search_products` recibe `category_id`, `subcategory_id` y `brand_id` como filtros opcionales aplicados antes del `ORDER BY embedding`.

**Conexión con consultoría:** Este patrón es aplicable a cualquier sistema RAG empresarial donde las entidades tienen atributos de clasificación bien definidos — productos en retail, expedientes en salud, proveedores en B2B. Es una decisión de arquitectura que diferencia implementaciones amateur de implementaciones de producción.

---

#### Query Híbrida Contextual

**Definición:** Query de recuperación RAG que combina filtros estructurales derivados del perfil y comportamiento del usuario con una consulta semántica derivada de la conversación en curso. Es la forma más precisa de recuperación en sistemas multi-entidad.

**Componentes:**

| Componente | Fuente | Tipo |
|-----------|--------|------|
| `tenant_id` | Sesión autenticada | Filtro estructural obligatorio |
| `category_id` | `client_product_affinities` del cliente | Filtro estructural opcional |
| `brand_id` | Preferencias históricas del cliente | Filtro estructural opcional |
| Query semántica | Mensaje actual del usuario en la conversación | Vector de búsqueda |

**Principio:** La calidad de la recuperación depende de cuánto contexto se integra en la query. Una query que solo usa el texto del mensaje del usuario es básica. Una query que cruza historial del cliente, filtros de categoría y texto semántico es avanzada.

---

#### Scheduler de Tareas Programadas — Celery Beat

**Definición:** Componente de un sistema de agentes que ejecuta acciones proactivas en momentos predefinidos, sin esperar a que el usuario inicie una interacción. En sistemas de IA conversacional, el scheduler es lo que separa un agente reactivo (solo responde) de un agente proactivo (actúa por iniciativa propia).

**Celery Beat** es el componente de Celery que actúa como planificador de tareas periódicas — equivalente a un cron job pero integrado con el ecosistema async de Python.

**Patrón de implementación en el proyecto:**
```python
# Tarea pública registrada en Celery
@celery_app.task(bind=True, max_retries=3, name="morning_briefing_task")
def morning_briefing_task(self) -> None:
    asyncio.run(_morning_briefing())

# Función privada async con la lógica real
async def _morning_briefing() -> None:
    # lógica del briefing
```

**Las 8 tareas del scheduler en el proyecto:**

| Hora | Tarea | Modelo | Actor |
|------|-------|--------|-------|
| 06:30 | Briefing matutino | Sonnet | Vendedores |
| 08:00–17:00 | Notificación pre-visita | Haiku | Clientes |
| 18:30 | Resumen del día | Haiku | Vendedores |
| 19:00 | Toma de pedido clientes no visitados | Sonnet | Clientes |
| 20:00 | Reporte de rendimiento | Sonnet | Vendedores |
| 07:00 diario | Reporte KPIs | Opus | Gerencia (email) |
| 07:30 lunes | Reporte semanal | Opus | Gerencia (email) |
| Continuo | Indexación RAG background | — | Sistema |

**Principio clave:** Cada tarea Celery es pública y registrada (para que el broker la encuentre), pero delega la lógica async a una función privada. Esto evita mezclar el sistema de colas con la lógica de negocio.

**Conexión con consultoría:** El scheduler proactivo es uno de los diferenciadores más visibles para el cliente final — convierte un chatbot pasivo en un agente que "trabaja solo". Es un argumento de venta directo.

---

#### Graceful Degradation en Sistemas de IA

**Definición:** Capacidad de un sistema de IA para mantener un nivel de servicio aceptable cuando uno o más componentes fallan, degradando la calidad de la respuesta en lugar de fallar completamente.

**Los 5 niveles implementados en el proyecto:**

| Nivel | Condición | Respuesta del sistema |
|-------|-----------|----------------------|
| 1 | No entendió el mensaje | Respuesta amigable pidiendo reformular |
| 2 | Datos insuficientes | Pedir el campo faltante específico |
| 3 | Falla del modelo IA | Reintentar con modelo más ligero + log en Sentry |
| 4 | Falla de BD o servicio externo | Informar demora + guardar intención en cola Celery |
| 5 | Falla crítica | Derivar a canal alternativo + alertar equipo técnico |

**Regla de fallback de modelos:**
```
Sonnet falla → reintentar con Haiku (respuesta degradada pero entregada)
Opus falla   → reintentar con Sonnet (reporte menos profundo pero disponible)
```

**Principio clave:** Nunca exponer al usuario errores técnicos internos (stack traces, nombres de tablas, errores HTTP). El usuario siempre recibe una respuesta en lenguaje natural.

**Conexión con consultoría:** La graceful degradation es un criterio de madurez de sistemas IA que los clientes empresariales exigen antes de confiar en producción. Documentarla en una propuesta demuestra experiencia en sistemas críticos.

---

#### Encriptación de Datos Sensibles en Sistemas IA

**Definición:** Proceso de proteger datos confidenciales almacenados en la base de datos mediante algoritmos criptográficos, de forma que sean ilegibles para cualquier agente que no tenga la clave de descifrado.

**Fernet (AES-128-CBC):** Algoritmo de encriptación simétrica usado en el proyecto para proteger tokens de WhatsApp y API keys de terceros. Garantiza que incluso si alguien accede directamente a la base de datos, los tokens son ilegibles.

**Patrón de implementación:**
```python
# Al guardar un dato sensible
token_encriptado = encrypt_value(whatsapp_access_token)
tenant.whatsapp_access_token = token_encriptado

# Al leer un dato sensible
token_real = decrypt_value(tenant.whatsapp_access_token)
```

**Qué se encripta en el proyecto:**
- `whatsapp_access_token` en la tabla `tenants`
- API keys de servicios de terceros
- Nunca: contraseñas (esas van como hash bcrypt, no encriptadas)

**Diferencia importante:** Las contraseñas se hashean (proceso unidireccional — no se pueden recuperar). Los tokens se encriptan (proceso bidireccional — se pueden recuperar con la clave). Esta distinción es fundamental para el diseño de seguridad.

**Conexión con consultoría:** En proyectos de salud (HIPAA) y finanzas, la encriptación de datos sensibles es obligatoria por regulación. Conocer el patrón correcto es un requisito para ofrecer consultoría en esos sectores.

---

#### Multi-Tenancy con JWT

**Definición:** Arquitectura donde múltiples clientes (tenants) comparten la misma infraestructura pero con aislamiento completo de sus datos. JWT (JSON Web Token) es el mecanismo de autenticación que transporta la identidad del tenant en cada request.

**Cómo funciona en el proyecto:**
- El JWT incluye `tenant_slug` además del `user_id` y `role`
- Cada endpoint extrae el `tenant_id` del JWT antes de cualquier consulta
- Toda query a la base de datos filtra obligatoriamente por `tenant_id`
- Ningún endpoint puede retornar datos de otro tenant, incluso con token válido

**Roles implementados:**

| Rol | Descripción |
|-----|-------------|
| `ADMIN` | Administrador del tenant — gestión completa |
| `MANAGER` | Gerente comercial — reportes y configuración |
| `SUPERVISOR` | Supervisor de zona — monitoreo de rutas |
| `SALESPERSON` | Vendedor de campo — operación diaria |
| `AGENT` | Vendedor virtual IA — evaluado con los mismos KPIs que un humano |

**El rol AGENT es la decisión de diseño más disruptiva:** el agente IA es un usuario del sistema con las mismas métricas que un vendedor humano, lo que permite comparar rendimiento canal presencial vs. canal WhatsApp con datos reales.

**Conexión con consultoría:** El diseño multi-tenant es el requisito técnico central de cualquier SaaS B2B. Saber explicarlo y auditarlo en proyectos de clientes es una habilidad de Fase 2 avanzada.

---

### FASE 3 — Especialización

---

#### Testing de Sistemas de IA — Unit Tests vs. Integration Tests

**Definición general:** Los tests son código que verifica que otro código funciona correctamente. En sistemas con LLMs, el testing tiene particularidades importantes porque las respuestas del modelo no son deterministas.

**Test unitario:** Prueba una función o componente aislado, mockeando (simulando) todas las dependencias externas. Rápido, sin conexión a BD ni a APIs externas.

**Test de integración:** Prueba la interacción entre múltiples componentes reales — incluyendo la base de datos real, servicios reales y flujos completos. Más lento pero verifica que el sistema funciona de punta a punta.

**El reto específico de los LLMs:** Los modelos de lenguaje no son deterministas — la misma pregunta puede tener respuestas ligeramente distintas. Esto hace que los tests clásicos de "respuesta exacta esperada" no funcionen. Las estrategias correctas son:

| Estrategia | Descripción | Cuándo usar |
|-----------|-------------|-------------|
| Mock del LLM | Reemplazar la llamada al API por una respuesta fija | Tests unitarios — verificar lógica de flujo |
| Assertion semántica | Verificar que la respuesta contiene ciertos elementos, no que sea exacta | Tests de integración ligeros |
| Eval con LLM juez | Usar otro LLM para evaluar si la respuesta es correcta | Tests de calidad de prompts |
| Métricas de comportamiento | Medir tasa de confirmaciones rechazadas, pedidos completados, etc. | Evaluación en producción |

**Estado en el proyecto:** 75 tests unitarios implementados con mocking de `AsyncSessionLocal`. Tests de integración (contra BD real) son el próximo frente — están identificados como bloqueante para producción.

**Patrón de mocking en el proyecto:**
```python
# Los tests mockean AsyncSessionLocal vía context manager _Ctx
# Ver tests/conftest.py para el patrón completo
```

**Conexión con consultoría:** Saber diseñar una estrategia de testing para sistemas con LLMs es una habilidad de Fase 3 muy poco común. La mayoría de los implementadores no testean sus agentes — diferenciarte con esto es un argumento de calidad técnica.

---

#### Evaluación de Sistemas RAG — Métricas y Evals

**Definición:** Conjunto de métricas y procesos para medir si un sistema RAG está funcionando bien — tanto en la calidad de la recuperación como en la calidad de las respuestas generadas.

**Por qué es crítico:** Un sistema RAG puede parecer que funciona en demos pero fallar silenciosamente en producción. Sin métricas, no hay forma de detectar degradación ni de demostrarle al cliente que el sistema mejora con el tiempo.

**Las métricas clave para el proyecto:**

| Métrica | Qué mide | Cómo calcularla |
|---------|----------|-----------------|
| Precisión de recuperación | ¿Los productos recuperados son relevantes para la query? | Revisión manual de muestras o LLM juez |
| Tasa de confirmación aceptada | ¿El cliente acepta la recomendación del agente? | `order_items` aceptados / recomendaciones enviadas |
| Tasa de pedidos completados | ¿Los flujos de pedido se completan sin abandono? | `orders` con status CONFIRMED / flujos iniciados |
| Tasa de confirmaciones rechazadas | ¿El agente malinterpretó la intención? | Correcciones en flujo NLDI / total flujos |
| Fill rate de recomendaciones | ¿El cliente compró lo que el agente sugirió? | Cruce `order_items` vs. productos recomendados |

**Frameworks de evaluación disponibles:**
- **Ragas** — framework open source específico para evaluar sistemas RAG
- **LangSmith** — plataforma de observabilidad para aplicaciones LLM
- **Evaluación manual con muestreo** — revisar N conversaciones por semana manualmente

**Estado en el proyecto:** Las tablas `ClientProductAffinity` y `DailySalesSnapshot` capturan señales de comportamiento que son la base para calcular estas métricas. El framework formal de evals está pendiente (P3 del backlog).

**Conexión con consultoría:** Poder presentarle a un cliente un dashboard de métricas de su agente IA — no solo "funciona" sino "funciona con 87% de tasa de aceptación" — es lo que convierte una implementación en un servicio gestionado con valor continuo.

---

#### Observabilidad en Sistemas de IA — Sentry y Logging Estructurado

**Definición:** Capacidad de entender el estado interno de un sistema a partir de sus salidas externas. En sistemas de IA, la observabilidad incluye monitoreo de errores, latencia, costos de API, calidad de respuestas y comportamiento de los agentes en producción.

**Sentry:** Plataforma de monitoreo de errores que captura excepciones, las agrupa, las prioriza y las envía con contexto completo (stack trace, variables, usuario, tenant). En el proyecto está integrado con FastAPI, SQLAlchemy y Celery simultáneamente.

**Integraciones de Sentry en el proyecto:**
```python
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
        CeleryIntegration(),
    ]
)
```

**Logging estructurado:** En lugar de logs de texto libre ("Error al procesar mensaje"), se usa logging con campos clave-valor que permiten búsquedas y agregaciones:
```python
logger.info("product_indexed",
    product_id=str(product_id),
    token_count=len(semantic_text.split()),
    tenant_id=str(tenant_id))
```

**Qué monitorear en un sistema de agentes IA:**

| Capa | Qué monitorear | Herramienta |
|------|---------------|-------------|
| Errores de aplicación | Excepciones, fallos de agentes | Sentry |
| Costos de API | Tokens consumidos por modelo/tenant | CloudWatch + logs |
| Latencia | Tiempo de respuesta por tipo de mensaje | CloudWatch |
| Calidad de agente | Métricas de comportamiento (ver Evals) | Dashboard propio |
| Infraestructura | CPU, memoria, conexiones BD | CloudWatch |

**Conexión con consultoría:** Los clientes empresariales exigen observabilidad antes de confiar en un sistema en producción. Saber diseñar e implementar una estrategia de monitoreo para sistemas IA es un diferenciador de Fase 3.

---

#### Infraestructura Cloud para Sistemas de IA — AWS

**Definición:** Conjunto de servicios de nube que alojan, escalan y protegen una aplicación de IA en producción. Para sistemas con LLMs, la infraestructura debe manejar cargas variables, latencias altas (los LLMs son lentos) y costos dinámicos.

**Stack AWS del proyecto (pendiente de implementar):**

| Servicio | Propósito | Costo estimado arranque |
|---------|-----------|------------------------|
| ECS Fargate | Ejecutar contenedores Docker (API + Celery) sin gestionar servidores | ~$25/mes |
| RDS PostgreSQL 16 | Base de datos con pgvector | ~$15/mes |
| ElastiCache Redis | Cache y broker de Celery | ~$13/mes |
| ALB | Balanceador de carga | ~$16/mes |
| ECR | Registro de imágenes Docker | ~$1/mes |
| S3 | Almacenamiento de reportes PDF/CSV | ~$1/mes |
| CloudWatch | Logs y métricas | ~$5/mes |
| **Total arranque** | | **~$76/mes** |

**Conceptos clave que debes dominar:**

- **ECS Fargate:** Ejecuta contenedores sin gestionar instancias EC2. Ideal para APIs con carga variable.
- **Task Definition:** Especificación del contenedor (imagen, CPU, RAM, variables de entorno).
- **Service:** Garantiza que N instancias del contenedor estén siempre corriendo.
- **ALB Target Group:** Distribuye tráfico entre instancias del servicio.

**Herramientas de Infrastructure as Code (IaC):**
- **Terraform:** Estándar de la industria, agnóstico de nube, amplia comunidad
- **AWS CDK:** IaC con Python/TypeScript, más natural para desarrolladores Python
- **Recomendación para el proyecto:** AWS CDK dado que el equipo ya usa Python

**Conexión con consultoría:** Saber estimar costos de infraestructura AWS para un sistema de agentes IA es una habilidad que pocos consultores tienen. Con el estimado de $76/mes de infra + $25-40/mes de IA para 40 vendedores, puedes construir propuestas económicas creíbles.

---

#### CI/CD para Sistemas de IA — GitHub Actions

**Definición:** Continuous Integration / Continuous Deployment. Pipeline automatizado que ejecuta tests, construye la aplicación y la despliega cada vez que se hace un commit al repositorio.

**Por qué es crítico en sistemas con LLMs:** Los agentes de IA son especialmente propensos a regresiones silenciosas — un cambio en un prompt puede degradar la calidad de las respuestas sin producir ningún error. Un pipeline de CI/CD con tests automatizados detecta estos problemas antes de que lleguen a producción.

**Pipeline propuesto para el proyecto:**

```
Push a main
    ↓
1. Lint (ruff) — verifica estilo y errores de código
    ↓
2. Tests unitarios (pytest) — verificación rápida sin BD
    ↓
3. Tests de integración (pytest + PostgreSQL real) — verificación completa
    ↓
4. Build imagen Docker — construye el contenedor de producción
    ↓
5. Push a ECR — sube la imagen al registro de AWS
    ↓
6. Deploy a ECS — actualiza el servicio en producción
```

**Conceptos clave de GitHub Actions:**

```yaml
# Estructura básica de un workflow
name: Deploy
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest tests/
  deploy:
    needs: test  # Solo si los tests pasan
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: aws ecs update-service ...
```

**Dependencia con el proyecto:** El CI/CD depende de que la infraestructura AWS esté implementada primero (ítem 5 del backlog). Es el último paso antes de considerar el sistema listo para producción real.

**Conexión con consultoría:** Implementar CI/CD en proyectos de clientes es un servicio de valor continuo — no solo entregas el sistema sino que entregas el proceso para mantenerlo actualizado y confiable.

---

#### Reports API — Generación de Reportes Estructurados

**Definición:** Endpoints que generan reportes en formatos descargables (CSV, PDF) a partir de datos del sistema. En sistemas de agentes IA, los reportes son el puente entre la inteligencia del agente y las decisiones humanas.

**Lo que está implementado en el proyecto:**
- Reportes de ventas (CSV + PDF) con filtros por período y vendedor
- Reportes de clientes con métricas de actividad
- Reportes de metas con seguimiento de cumplimiento

**Decisión de diseño clave:** Los reportes se generan bajo demanda vía API, no se pre-calculan. Para reportes complejos que toman tiempo, se dispara una tarea Celery y se notifica al usuario cuando está listo — mismo patrón que la indexación RAG.

**Formatos y sus casos de uso:**

| Formato | Caso de uso | Ventaja |
|---------|-------------|---------|
| CSV | Análisis en Excel por el gerente | Flexible, editable |
| PDF | Presentación formal, archivo | Formato fijo, profesional |
| JSON (API) | Integración con otros sistemas | Programable |

**Conexión con consultoría:** La capacidad de generar reportes estructurados es uno de los primeros requerimientos que hacen los gerentes cuando ven un demo. Tenerlo implementado desde el inicio es un argumento de cierre de ventas.

---

### FASE 3 — Próximas entradas

> *Temas pendientes de desarrollar en sesiones futuras:*

- Governance de IA — riesgos, alucinaciones, auditoría, IA responsable
- Especialización vertical en salud — regulación colombiana, datos clínicos, consentimiento
- Especialización vertical en retail — personalización avanzada, demand forecasting con IA
- Rate limiting y seguridad avanzada en APIs de agentes

> *Esta sección se completará en sesiones futuras al avanzar en el roadmap.*

Temas pendientes:
- Posicionamiento como consultor especializado en LATAM
- Diseño de paquetes de servicios repetibles
- Estrategia de contenido y generación de demanda

---

## Decisiones de Arquitectura Documentadas

Esta sección registra decisiones técnicas tomadas en el proyecto con su justificación — material directo para futuras propuestas de consultoría.

### DA-001 — Selección de vector store: pgvector sobre Pinecone

**Decisión:** Usar la extensión `pgvector` de PostgreSQL en lugar de un servicio externo como Pinecone.

**Justificación:**
- PostgreSQL ya está en el stack (AWS RDS) — sin servicio adicional
- Aislamiento multi-tenant con `tenant_id` ya existente en todas las tablas
- Integración directa con SQLAlchemy async ya configurado
- Catálogos de distribuidoras colombianas típicamente < 10k SKUs — pgvector es suficiente

**Cuándo revisar esta decisión:** Si un tenant supera 100k productos o si la latencia de búsqueda supera 200ms en producción.

---

### DA-002 — Texto semántico compuesto para indexación de productos

**Decisión:** No vectorizar solo el campo `name` del producto. Construir un texto semántico compuesto que incluye categoría, marca, embalajes, tipologías de cliente objetivo y `semantic_tags`.

**Formato:**
```
Producto: {name}
Categoría: {category} > {subcategory}
Marca: {brand} | Proveedor: {supplier}
Embalajes: {packaging_units}
Tipologías objetivo: {client_typologies}
Tags: {semantic_tags flattened}
```

**Justificación:** Un embedding de solo el nombre captura poco significado. El texto compuesto permite que consultas en lenguaje natural del canal tradicional ("algo para tienda pequeña de barrio") recuperen productos relevantes aunque no coincidan en palabras exactas.

---

### DA-003 — Re-indexación incremental de catálogo

**Decisión:** La indexación de embeddings ocurre por producto individual, no por catálogo completo.

**Implementación:** Tarea Celery disparada por los eventos `POST /products` y `PATCH /products/{id}`. La re-indexación total solo ocurre al cambiar el modelo de embedding o el esquema del texto semántico compuesto.

---

## Skills para Implementación Futura

### SKILL: semantic_tags_enrichment

```
Nombre: semantic_tags_enrichment
Versión: 0.1.0 (pendiente implementación)
Aplica a: products · clients · suppliers · [cualquier entidad futura]

Inputs:
  - entidad_tipo: str
  - entidad_id: UUID
  - campos_base: dict

Outputs:
  - semantic_tags: JSONB estructurado por categorías

Capas:
  - auto_generated: inferido de campos existentes
  - operator_enriched: enriquecido manualmente por el operador
  - agent_inferred: inferido por el agente desde comportamiento observado

Características:
  - Herencia desde jerarquía (categoría → subcategoría → producto)
  - Versionado con autor y timestamp por tag
  - Feedback loop desde resultados de recuperación
  - Validación de longitud mínima antes de indexar
```

---

### SKILL: hybrid_rag_indexing

```
Nombre: hybrid_rag_indexing
Versión: 1.0.0
Aplica a: cualquier entidad con atributos mixtos (estructurales + semánticos)

Principio rector:
  Los atributos exactos y discretos de una entidad son filtros estructurales
  (WHERE SQL). Solo los atributos con gradiente de significado se vectorizan.
  Nunca mezclar ambos tipos en el texto semántico.

Proceso de clasificación de atributos (aplicar antes de diseñar el índice):
  Para cada atributo de la entidad, responder:
  ¿Este atributo puede ser "más o menos parecido" a una consulta?
    → SÍ: va al texto semántico vectorizado
    → NO (es exacto o discreto): va al filtro SQL

Ejemplos de clasificación:

  Entidad: Product
  ├── brand_id        → Filtro SQL    (exacto: es esa marca o no lo es)
  ├── category_id     → Filtro SQL    (exacto: pertenece a esa categoría o no)
  ├── subcategory_id  → Filtro SQL    (exacto)
  ├── tenant_id       → Filtro SQL    (exacto, obligatorio siempre)
  ├── is_active       → Filtro SQL    (booleano, sin gradiente)
  ├── price           → Filtro SQL    (numérico exacto, rangos via WHERE)
  ├── name            → Semántico     (tiene sinónimos, variantes coloquiales)
  ├── description     → Semántico     (texto libre con gradiente)
  └── semantic_tags   → Semántico     (enriquecimiento contextual)

  Entidad: Client (uso futuro)
  ├── tenant_id       → Filtro SQL
  ├── zone_id         → Filtro SQL
  ├── typology_id     → Filtro SQL    (tipo de establecimiento)
  ├── classification  → Filtro SQL    (Oro/Plata/Bronce)
  └── semantic_tags   → Semántico     (comportamiento, preferencias, contexto)

  Entidad: Supplier (uso futuro)
  ├── tenant_id       → Filtro SQL
  ├── country_id      → Filtro SQL
  └── semantic_tags   → Semántico     (especialización, reputación, términos)

Patrón de función search_{entidad}:
  Parámetros obligatorios: query: str, tenant_id: UUID, top_k: int, db: AsyncSession
  Parámetros opcionales:   atributos estructurales como UUID | None = None
  Construcción WHERE:      aplicar filtros estructurales antes del ORDER BY vector
  Orden:                   embedding <=> :query_vector (distancia coseno)
  Exclusión:               WHERE embedding IS NOT NULL

Patrón de función build_semantic_text_{entidad}:
  Incluir:  name/title, description, semantic_tags (todas las categorías)
  Excluir:  cualquier atributo clasificado como Filtro SQL en la tabla anterior
  Validar:  longitud mínima ~50 tokens antes de generar embedding
```

---

## Referencias y Recursos

### Documentación oficial
- [Anthropic Docs](https://docs.anthropic.com) — API Claude, prompt engineering
- [pgvector GitHub](https://github.com/pgvector/pgvector) — extensión de vectores para PostgreSQL
- [LangChain Docs](https://docs.langchain.com) — framework para agentes y RAG
- [LlamaIndex Docs](https://docs.llamaindex.ai) — alternativa a LangChain, fuerte en RAG

### Conceptos para profundizar (Fase 2)
- Similitud coseno — métrica de distancia entre vectores
- top-k retrieval — cuántos documentos recuperar por query
- Chunking strategies — cómo dividir documentos largos para indexar
- Hybrid search — combinar búsqueda semántica con búsqueda por palabras clave

---

*Documento mantenido como parte del proyecto Sales Agent SaaS*
*Versión actual: 1.2.0 — Próxima actualización: al avanzar en tests de integración, infraestructura AWS y CI/CD*
