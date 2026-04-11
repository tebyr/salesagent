# Marco de ROI y Monetización — Sales Agent SaaS

> **Propósito:** Traducir los indicadores de la batería KPI en argumentos de precio,
> modelos de cobro y proyecciones financieras para la estrategia comercial.
>
> **Audiencia primaria:** Uso interno — para construir propuestas, fijar precios y
> diseñar paquetes de servicio.

---

## Control de Versiones

| Versión | Fecha      | Descripción |
|---------|------------|-------------|
| 1.0.0   | 2026-04-11 | Versión inicial — marco completo con estimados basados en arquitectura real |

---

## 1. El Argumento Central de ROI

El valor del sistema se puede expresar en una sola frase que el gerente entiende:

> *"Por cada $X que paga mensualmente, el agente recupera $Y en ventas que antes se perdían — más la visibilidad en tiempo real que antes no tenía."*

Los tres componentes del ROI son:

**Componente 1 — Venta recuperada:** Pedidos generados por el agente en visitas no realizadas. Es venta incremental pura que sin el sistema sería cero.

**Componente 2 — Venta acelerada:** Incremento en frecuencia de compra por cliente activo. La misma base de clientes compra más seguido.

**Componente 3 — Costo evitado:** El agente cubre rutas de baja densidad o días intermedios sin necesidad de contratar un vendedor adicional.

---

## 2. Modelo de Cálculo de ROI para el Piloto

Este modelo usa los supuestos mínimos conservadores para presentarle al gerente durante la venta del piloto.

### Supuestos base (distribuidora mediana colombiana)

| Variable | Valor supuesto | Fuente |
|----------|---------------|--------|
| Clientes activos en la zona piloto | 200–300 | Scope del piloto |
| Venta neta mensual de la zona | $80–150M COP | Promedio sector |
| Frecuencia de compra actual | Cada 8–12 días | Benchmark sector |
| % de visitas no realizadas por mes | 15–25% | Benchmark sector |
| Ticket promedio por pedido | $180–350K COP | Benchmark sector |
| % de clientes en Venta 0 | 15–25% de la base | Benchmark sector |

### Cálculo de venta recuperada (Componente 1)

```
Visitas planificadas/mes (200 clientes, 2 visitas/semana) = ~1.600 contactos
Visitas no realizadas (20%) = 320 contactos perdidos
Tasa de respuesta WA esperada (35%) = 112 clientes que responden al agente
Tasa de conversión a pedido (60%) = 67 pedidos adicionales
Ticket promedio = $250.000 COP

VENTA RECUPERADA MENSUAL = 67 × $250.000 = $16.750.000 COP/mes
```

### Cálculo de venta acelerada (Componente 2)

```
Base de clientes activos = 200
Frecuencia actual = cada 10 días → 3 pedidos/cliente/mes
Incremento esperado = 15% → frecuencia cada 8.5 días → 3.5 pedidos/cliente/mes
Pedidos adicionales = 200 × 0.5 = 100 pedidos adicionales
Ticket promedio = $250.000 COP

VENTA ACELERADA MENSUAL = 100 × $250.000 = $25.000.000 COP/mes
```

### ROI total estimado del piloto

```
Venta recuperada:     $16.750.000 COP/mes
Venta acelerada:      $25.000.000 COP/mes
─────────────────────────────────────────
IMPACTO TOTAL:        ~$41.750.000 COP/mes

Costo del sistema (ver pricing):  $3.500.000–6.000.000 COP/mes
─────────────────────────────────────────
ROI mínimo estimado:  ~7x
```

**Argumento de venta:** "Si el sistema genera el 3% de incremento en su venta mensual, ya se paga solo. Lo que hemos visto en proyectos similares es un incremento de 15–25%."

---

## 3. Modelo de Pricing

### Principios de fijación de precio

El precio debe cumplir tres condiciones simultáneamente: ser creíble (sustentado en valor real), ser asequible (no bloquear la decisión en distribuidoras medianas), y ser escalable (crecer con el tamaño del tenant).

### Estructura de precios recomendada

**Variable de escala principal:** número de clientes activos en la base de datos del tenant.

| Tier | Clientes activos | Precio mensual (COP) | Precio mensual (USD) |
|------|-----------------|---------------------|---------------------|
| Starter | Hasta 200 clientes | $2.800.000 | ~$700 |
| Growth | 201–500 clientes | $4.500.000 | ~$1.125 |
| Scale | 501–1.000 clientes | $7.200.000 | ~$1.800 |
| Enterprise | +1.000 clientes | A convenir | ~$2.500+ |

**Incluido en todos los tiers:**
- Agentes WhatsApp (vendedor, cliente, gerencia)
- Scheduler proactivo (8 tareas diarias)
- Briefings matutinos ilimitados
- Reports API (CSV + PDF)
- Panel administrativo web
- Soporte por WhatsApp en horario hábil
- Hasta 5 usuarios (vendedores + gerentes)

**Costo adicional por uso (pass-through al cliente):**
- WhatsApp Business API: ~$0.024 USD/conversación (Meta cobra directo)
- Usuarios adicionales: $150.000 COP/usuario/mes sobre el límite del tier

### Pricing del piloto

El piloto de 90 días se ofrece con condiciones especiales para reducir la fricción de entrada:

| Condición | Valor |
|-----------|-------|
| Duración | 90 días calendario |
| Precio piloto | 60% del precio del tier correspondiente |
| Compromiso posterior | Sin obligación — a renovar si hay resultados |
| Alcance | 1 zona, hasta 5 vendedores, hasta 300 clientes |
| Setup incluido | Sí — carga de datos, configuración, capacitación |

**Precio piloto Starter (referencia):** $1.680.000 COP/mes durante 3 meses = $5.040.000 COP total.

---

## 4. Estructura de Paquetes de Servicio

Más allá del SaaS mensual, hay tres paquetes de consultoría que pueden ofrecerse de forma complementaria:

### Paquete 1 — Diagnóstico Comercial con IA

**Qué incluye:**
- Análisis de la base de datos actual del cliente (Excel o ERP)
- Identificación de clientes Venta 0, clientes en riesgo y oportunidades de frecuencia
- Reporte ejecutivo con los 5 indicadores clave de su operación
- Recomendación de zonas piloto con mayor potencial

**Duración:** 2 semanas
**Precio:** $4.500.000 COP (one-time)
**Aplica como:** Primer paso para vender el piloto. El diagnóstico justifica la inversión con datos del propio cliente.

---

### Paquete 2 — Implementación y Piloto

**Qué incluye:**
- Setup completo del sistema (configuración de tenant, carga de datos)
- Capacitación del equipo de ventas y gerencia
- Acompañamiento durante los 90 días del piloto
- Reporte de resultados al cierre con caso de estudio

**Duración:** 90 días
**Precio:** Precio del tier + $2.000.000 COP de setup (one-time)
**Entregable clave:** Caso de estudio documentado con métricas reales

---

### Paquete 3 — Servicio Gestionado Mensual

**Qué incluye:**
- Licencia SaaS mensual (tier según tamaño)
- Revisión mensual de indicadores con el gerente (30 min)
- Optimización continua de prompts y recomendaciones
- Soporte técnico prioritario
- Expansión a nuevas zonas sin costo adicional de setup

**Duración:** Contrato mínimo 6 meses
**Precio:** Tier correspondiente + $800.000 COP/mes por el servicio gestionado
**Propuesta de valor:** No solo compra el sistema — compra el acompañamiento para que funcione bien.

---

## 5. Argumentos de Precio por Perfil de Objeción

### Objeción: "Es muy caro"

**Respuesta con datos:**
"Entiendo la preocupación. Miremos los números de su operación: si tiene 250 clientes y el 20% de las visitas no se realizan, estamos hablando de ~50 visitas perdidas al mes. Si el agente recupera la mitad de esas visitas con un ticket de $250.000, son $6.250.000 en venta recuperada. El sistema cuesta $2.800.000. El margen en esa venta recuperada paga el sistema."

### Objeción: "Ya tenemos un CRM"

**Respuesta:**
"El agente no reemplaza su CRM — se conecta. El CRM guarda los datos, el agente los convierte en acciones: le habla al cliente, toma el pedido, le reporta al gerente. Son capas distintas."

### Objeción: "Mis vendedores no van a querer"

**Respuesta:**
"El agente no compite con el vendedor — lo potencia. El vendedor llega a la visita con un briefing que le dice exactamente qué ofrecer y cuánto le falta para su bono. Y cuando no puede visitar a un cliente, el agente lo cubre para que la venta no se pierda. Los vendedores que lo han usado lo defienden."

### Objeción: "¿Cómo sé que va a funcionar para mi empresa?"

**Respuesta:**
"Por eso proponemos el piloto de 90 días en una sola zona. Al final del piloto tiene números reales de su propia operación — no proyecciones, no promesas. Si los números no justifican la inversión, no renueva. Si los justifican, la conversación es distinta."

---

## 6. Estimado de Ingresos por Escenario

### Escenario conservador — 12 meses

| Mes | Tenants activos | Ingreso mensual (COP) | Ingreso acumulado |
|-----|----------------|----------------------|-------------------|
| 1–3 | 1 (piloto) | $1.680.000 | $5.040.000 |
| 4–6 | 2 | $5.600.000 | $21.840.000 |
| 7–9 | 4 | $11.200.000 | $55.440.000 |
| 10–12 | 6 | $16.800.000 | $106.440.000 |

**Ingreso año 1 (conservador): ~$106M COP (~$26.500 USD)**

### Escenario moderado — 12 meses

| Mes | Tenants activos | Ingreso mensual (COP) | Ingreso acumulado |
|-----|----------------|----------------------|-------------------|
| 1–3 | 1–2 | $3.360.000 | $10.080.000 |
| 4–6 | 4 | $11.200.000 | $43.680.000 |
| 7–9 | 8 | $22.400.000 | $111.000.000 |
| 10–12 | 12 | $33.600.000 | $212.000.000 |

**Ingreso año 1 (moderado): ~$212M COP (~$53.000 USD)**

### Supuestos de los escenarios

- Tier promedio: Growth ($4.500.000 COP/mes)
- Costo de infraestructura AWS: ~$300.000 COP/mes por tenant
- Costo de API IA (Claude + Voyage): ~$100.000–160.000 COP/mes por tenant (40 vendedores, 3.000 clientes)
- Costo WhatsApp: variable según uso — pass-through al cliente

**Margen bruto estimado por tenant (Tier Growth):**
```
Ingreso:           $4.500.000 COP/mes
AWS:               - $300.000
IA APIs:           - $150.000
WhatsApp:          - pass-through
─────────────────────────────────────
Margen bruto:      ~$4.050.000 COP/mes (~90%)
```

---

## 7. Próximos Pasos para Activar la Monetización

En orden de prioridad:

1. **Cerrar el piloto con Distribuciones La Garantía** — es el caso de estudio que valida todo lo demás. Sin un caso real, el resto es teoría.

2. **Medir y documentar los 5 KPIs del caso de estudio** desde el primer día de operación (ver `bateria_indicadores_kpi.md` — sección "Indicadores para el Caso de Estudio del Piloto").

3. **Definir el precio del piloto para los primeros 3 clientes** — se recomienda precio simbólico o gratuito para los primeros 2–3 tenants a cambio de autorización para usar sus resultados como caso de estudio.

4. **Construir las alianzas con distribuidores de software** — agencias que implementan Siesa, World Office o SAP para distribuidoras son el canal de distribución más eficiente. Ellos ya tienen la confianza del cliente.

5. **Publicar el caso de estudio** en LinkedIn y en eventos del sector (FENALCO, ACOLDIST, ferias de distribución) para generar demanda entrante.

---

*Documento mantenido en `docs/go_to_market/`*
*Próxima actualización: al definir precio del primer piloto pagado*
