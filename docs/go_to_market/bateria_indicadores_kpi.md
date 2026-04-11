# Batería de Indicadores KPI — Sales Agent SaaS

> **Propósito:** Batería de indicadores para demostrar el valor del sistema a clientes potenciales,
> construir el caso de estudio del piloto y fundamentar la estrategia de monetización.
>
> **Fuente de datos:** Modelo de datos del proyecto (tablas referenciadas en cada indicador).
> **Audiencia:** Gerentes y propietarios de distribuidoras — lenguaje de negocio, no técnico.

---

## Control de Versiones

| Versión | Fecha      | Descripción |
|---------|------------|-------------|
| 1.0.0   | 2026-04-11 | Versión inicial — batería completa cruzada con modelo de datos |

---

## Estructura de la Batería

Los indicadores se organizan en tres dimensiones según lo que le importa al gerente:

| Dimensión | Qué mide | Por qué vende |
|-----------|----------|---------------|
| **D1 — Impacto en ventas** | Incremento directo en ingresos | Es el argumento de ROI principal |
| **D2 — Eficiencia operacional** | Productividad del equipo y reducción de costos | Justifica el precio mensual |
| **D3 — Inteligencia exclusiva del agente** | Lo que solo existe con el sistema activo | Es el diferenciador competitivo |

---

## D1 — Indicadores de Impacto en Ventas

Estos son los indicadores que el gerente pregunta primero. Deben ser los protagonistas del piloto.

---

### KPI-01 — Incremento en Frecuencia de Compra Activa

**Definición:** Promedio de días entre pedidos por cliente, antes y después de activar el agente.

**Fórmula:**
```
Frecuencia_antes = AVG(avg_purchase_frequency_days) antes del piloto
Frecuencia_después = AVG(avg_purchase_frequency_days) después del piloto
Incremento = ((Frecuencia_antes - Frecuencia_después) / Frecuencia_antes) × 100
```

**Tabla de origen:** `clients.avg_purchase_frequency_days`, `client_product_affinities.avg_days_between_orders`

**Frecuencia de cálculo:** Mensual

**Por qué le importa al gerente:** Si un cliente que compraba cada 10 días ahora compra cada 7, eso es un 30% más de pedidos por cliente sin contratar un vendedor adicional. Multiplicado por 300 clientes, el impacto en ventas es inmediato.

**Benchmark de referencia:** Sistemas similares en distribución LATAM reportan incrementos de 15–35% en frecuencia de compra en los primeros 90 días.

---

### KPI-02 — Pedidos Generados por Canal WhatsApp (sin visita)

**Definición:** Número y valor de pedidos tomados directamente por el agente IA en días en que el vendedor no visitó al cliente.

**Fórmula:**
```
Pedidos_canal_WA = COUNT(orders) WHERE order_source = 'AGENT_WA'
Valor_canal_WA = SUM(orders.net_total) WHERE order_source = 'AGENT_WA'
% sobre total = (Valor_canal_WA / SUM(orders.net_total)) × 100
```

**Tabla de origen:** `orders.order_source`, `orders.net_total`, `daily_sales_snapshots`

**Frecuencia de cálculo:** Semanal

**Por qué le importa al gerente:** Cada pedido tomado por el agente en una visita no realizada es venta que antes se perdía completamente. Es el indicador más poderoso del piloto porque representa ingreso incremental puro — no redistribución del mismo volumen.

**Argumento de venta:** "En el piloto, el agente generó X pedidos que de otra forma hubieran sido cero."

---

### KPI-03 — Conversión de Clientes Venta 0

**Definición:** Porcentaje de clientes registrados que nunca habían comprado y que generaron su primer pedido durante el período con el agente activo.

**Fórmula:**
```
Venta_0_convertidos = COUNT(daily_sales_snapshots.venta_zero_converted) en el período
Total_Venta_0_inicial = COUNT(clients) WHERE nunca tuvieron un order
Tasa_conversión = (Venta_0_convertidos / Total_Venta_0_inicial) × 100
```

**Tabla de origen:** `daily_sales_snapshots.venta_zero_converted`, `clients`

**Frecuencia de cálculo:** Mensual

**Por qué le importa al gerente:** Los clientes Venta 0 son base de datos que no genera dinero. Convertirlos es activar activos dormidos. Cada distribuidora típicamente tiene entre 15–30% de su base en Venta 0.

---

### KPI-04 — Ticket Promedio por Canal

**Definición:** Valor promedio por pedido según el canal de origen — vendedor presencial vs. agente WhatsApp.

**Fórmula:**
```
Ticket_presencial = AVG(orders.net_total) WHERE order_source = 'SALESPERSON'
Ticket_agente = AVG(orders.net_total) WHERE order_source = 'AGENT_WA'
Delta = Ticket_presencial - Ticket_agente
```

**Tabla de origen:** `orders.net_total`, `orders.order_source`

**Frecuencia de cálculo:** Semanal

**Por qué le importa al gerente:** Permite comparar si el canal WhatsApp complementa o canibaliza la venta presencial. Si el ticket del agente es menor, la estrategia es usarlo para frecuencia. Si es comparable, puede reemplazar visitas de bajo rendimiento.

---

### KPI-05 — Venta Neta Total (Incremental del Período)

**Definición:** Diferencia en venta neta mensual antes y después de activar el agente, controlando por estacionalidad.

**Fórmula:**
```
Venta_neta = SUM(daily_sales_snapshots.net_total) en el período
Incremental = Venta_neta_con_agente - Venta_neta_período_equivalente_sin_agente
```

**Tabla de origen:** `daily_sales_snapshots.net_total`, `daily_sales_snapshots.returns_total`

**Frecuencia de cálculo:** Mensual

**Por qué le importa al gerente:** Es el número final que resume todo. Si la venta neta subió X%, el agente justifica su costo.

---

## D2 — Indicadores de Eficiencia Operacional

Estos indicadores justifican el precio mensual del sistema en términos de productividad y reducción de costo operativo.

---

### KPI-06 — Efectividad del Equipo Comercial

**Definición:** Porcentaje de visitas planificadas que resultaron en al menos un pedido.

**Fórmula:**
```
Efectividad = (clients_impacted / clients_planned) × 100
```

**Tabla de origen:** `daily_sales_snapshots.effectiveness_pct`, `daily_sales_snapshots.clients_impacted`, `daily_sales_snapshots.clients_planned`

**Frecuencia de cálculo:** Diaria por vendedor, semanal consolidada

**Por qué le importa al gerente:** Una efectividad del 60% significa que 4 de cada 10 visitas no generan pedido. El agente impacta este indicador de dos formas: el briefing matutino prepara mejor al vendedor, y el seguimiento nocturno recupera los clientes no visitados.

**Benchmark del sector:** Efectividad típica sin herramientas: 55–65%. Con el agente activo: objetivo 75–85%.

---

### KPI-07 — Tasa de Cobertura de Ruta

**Definición:** Porcentaje de clientes programados que recibieron contacto (presencial o WhatsApp) en el día.

**Fórmula:**
```
Cobertura = (clients_visited / clients_planned) × 100
Cobertura_ampliada = ((clients_visited + clientes_contactados_WA) / clients_planned) × 100
```

**Tabla de origen:** `daily_sales_snapshots.clients_visited`, `daily_sales_snapshots.clients_planned`, `route_visits`

**Frecuencia de cálculo:** Diaria

**Por qué le importa al gerente:** Sin el agente, un cliente no visitado es un cliente ignorado. Con el agente, el follow-up automático a las 19:00 convierte visitas perdidas en oportunidades de venta por WhatsApp. La cobertura ampliada puede llegar al 100% aunque el vendedor no complete la ruta.

---

### KPI-08 — Tiempo de Respuesta al Cliente

**Definición:** Tiempo promedio entre el primer mensaje del cliente y la primera respuesta del agente.

**Fórmula:**
```
Tiempo_respuesta = AVG(primera_respuesta_at - primer_mensaje_at) por conversación
```

**Tabla de origen:** `wa_conversations`, `message_logs`

**Frecuencia de cálculo:** Semanal

**Por qué le importa al gerente:** Un vendedor humano no puede responder a las 9 PM. El agente sí. Tiempo de respuesta < 1 minuto 24/7 vs. tiempo de respuesta del vendedor: horas o días.

---

### KPI-09 — Cumplimiento de Metas por Vendedor

**Definición:** Porcentaje de cumplimiento de la meta mensual por vendedor, con proyección al cierre.

**Fórmula:**
```
Cumplimiento = (goal_progress.current_value / sales_goals.target_value) × 100
Proyección = (current_value / días_transcurridos) × días_totales_período
```

**Tabla de origen:** `goal_progress`, `sales_goals`, `daily_sales_snapshots`

**Frecuencia de cálculo:** Diaria

**Por qué le importa al gerente:** El agente no solo mide — actúa. Cuando un vendedor está por debajo de su proyección, el briefing del día siguiente se ajusta automáticamente con más clientes prioritarios y más urgencia en la comunicación. El sistema convierte el indicador en acción.

---

### KPI-10 — Fill Rate (Tasa de Surtido)

**Definición:** Porcentaje de unidades facturadas sobre unidades pedidas. Mide la capacidad de la bodega de cumplir los pedidos del agente.

**Fórmula:**
```
Fill_rate = (SUM(order_items.invoiced_qty) / SUM(order_items.ordered_qty)) × 100
Delta_pedido_factura = SUM(ordered_total) - SUM(invoice_total) en orders
```

**Tabla de origen:** `order_items`, `orders.ordered_total`, `orders.invoice_total`

**Frecuencia de cálculo:** Semanal

**Por qué le importa al gerente:** Un fill rate bajo indica que la bodega no puede cumplir lo que el agente vende. Es un indicador de alerta temprana para planeación de inventario. El agente lo hace visible en tiempo real — antes se enteraban en el reporte del viernes.

---

## D3 — Indicadores de Inteligencia Exclusiva del Agente

Estos indicadores no existen sin el sistema. Son el diferenciador que ninguna distribuidora puede calcular con herramientas tradicionales.

---

### KPI-11 — Efectividad del Agente IA como Vendedor

**Definición:** Comparación directa del rendimiento del agente IA vs. vendedores humanos en la misma zona — pedidos generados, ticket promedio y tasa de respuesta del cliente.

**Fórmula:**
```
Pedidos_agente = COUNT(orders) WHERE assigned_user.role = 'AGENT'
Pedidos_vendedor = COUNT(orders) WHERE assigned_user.role = 'SALESPERSON'
Ratio = Pedidos_agente / Pedidos_vendedor (por zona equivalente)
```

**Tabla de origen:** `orders`, `users.role`, `routes.route_type`

**Frecuencia de cálculo:** Mensual

**Por qué le importa al gerente:** Este es el indicador más disruptivo de la propuesta. Permite responder: "¿Vale la pena reemplazar una visita presencial de bajo rendimiento con el agente?" Con datos reales de su propia operación.

**Argumento de venta:** "Al final del piloto sabrá exactamente cuánto vendió el agente vs. su vendedor en la misma zona."

---

### KPI-12 — Tasa de Aceptación de Recomendaciones RAG

**Definición:** Porcentaje de productos recomendados por el agente que el cliente efectivamente pidió.

**Fórmula:**
```
Productos_recomendados = COUNT(productos en briefing/pre-visita por cliente)
Productos_pedidos = COUNT(order_items que coinciden con recomendaciones)
Tasa_aceptación = (Productos_pedidos / Productos_recomendados) × 100
```

**Tabla de origen:** `client_product_affinities`, `order_items`, `message_logs`

**Frecuencia de cálculo:** Semanal

**Por qué le importa al gerente:** Mide qué tan buenas son las recomendaciones del sistema. Una tasa de aceptación alta significa que el agente conoce bien a cada cliente. Es la prueba de que la IA aprende con el tiempo.

---

### KPI-13 — Efectividad de Siembra (Seed Conversion)

**Definición:** Porcentaje de productos introducidos vía promoción (siembra) que generaron recompra sostenida después de 30 y 60 días.

**Fórmula:**
```
Productos_sembrados = COUNT(client_product_affinities) WHERE was_seeded_by_promo = TRUE
Recompras_30d = COUNT de los anteriores con pedido en los siguientes 30 días
Tasa_siembra = (Recompras_30d / Productos_sembrados) × 100
```

**Tabla de origen:** `client_product_affinities.was_seeded_by_promo`, `client_product_affinities.seed_promo_id`

**Frecuencia de cálculo:** Mensual (rolling 30/60 días)

**Por qué le importa al gerente:** El ROI de una promoción de siembra no se mide en el momento — se mide en la recompra posterior. El agente es el primero en hacer este cálculo automáticamente. Ningún sistema tradicional lo hace.

---

### KPI-14 — Índice de Clientes en Riesgo de Churn

**Definición:** Número de clientes cuyo intervalo entre pedidos supera significativamente su promedio histórico, indicando riesgo de abandono.

**Fórmula:**
```
Días_sin_compra = TODAY - MAX(last_order_date) por cliente
Riesgo_churn = clients WHERE días_sin_compra > (avg_days_between_orders × 1.5)
```

**Tabla de origen:** `client_product_affinities.avg_days_between_orders`, `client_product_affinities.last_order_date`

**Frecuencia de cálculo:** Diaria (alimenta el briefing matutino)

**Por qué le importa al gerente:** Un cliente en riesgo de churn aparece en el briefing del vendedor como prioritario. El gerente ve cuántos clientes están en riesgo antes de perderlos — no después.

---

### KPI-15 — Tasa de Respuesta al Canal WhatsApp

**Definición:** Porcentaje de clientes que respondieron al menos un mensaje del agente en el período.

**Fórmula:**
```
Clientes_contactados = COUNT(wa_conversations iniciadas por el agente)
Clientes_respondieron = COUNT(wa_conversations con al menos 1 mensaje entrante)
Tasa_respuesta = (Clientes_respondieron / Clientes_contactados) × 100
```

**Tabla de origen:** `wa_conversations`, `message_logs`

**Frecuencia de cálculo:** Semanal

**Por qué le importa al gerente:** Una tasa de respuesta alta valida que el canal WhatsApp funciona para su base de clientes. Es el primer indicador que se mide en el piloto — antes de hablar de ventas, hay que saber si los clientes responden.

**Benchmark:** Tasa de apertura WhatsApp promedio en LATAM: 85–95%. Tasa de respuesta esperada en primeras semanas del piloto: 30–50%.

---

## Dashboard Propuesto para el Gerente

Resumen de los indicadores prioritarios para el reporte diario (el que el agente ya envía por email):

```
REPORTE DIARIO — [Fecha]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VENTAS DEL DÍA
  Venta neta:          $X.XXX.XXX    [▲ +X% vs. mismo día semana anterior]
  Pedidos tomados:     XX            [X por vendedor, X por agente WA]
  Ticket promedio:     $XX.XXX

EQUIPO COMERCIAL
  Efectividad:         XX%           [semáforo: verde >75%, amarillo 60-75%, rojo <60%]
  Cobertura de ruta:   XX%
  Clientes no visitados con seguimiento WA: XX

ALERTAS
  Clientes en riesgo churn: XX
  Venta 0 pendientes:       XX
  Vendedores bajo proyección: XX

PROYECCIÓN AL CIERRE DEL MES
  Avance actual:       XX%
  Proyectado:          XX%
  Gap para la meta:    $X.XXX.XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Indicadores para el Caso de Estudio del Piloto

Al finalizar los 90 días del piloto con el primer tenant, estos son los 5 indicadores que deben aparecer en el caso de estudio para convertirlo en material de ventas:

| # | Indicador | Formato de presentación |
|---|-----------|------------------------|
| 1 | KPI-02 — Pedidos generados sin visita | "X pedidos por $XX millones que antes se perdían" |
| 2 | KPI-01 — Incremento frecuencia de compra | "Los clientes compraron X% más seguido" |
| 3 | KPI-03 — Conversión Venta 0 | "X clientes inactivos generaron su primer pedido" |
| 4 | KPI-11 — Agente vs. vendedor | "El agente generó el X% de la venta de la zona" |
| 5 | KPI-06 — Efectividad del equipo | "La efectividad subió de X% a Y%" |

---

*Documento mantenido en `docs/go_to_market/`*
*Próxima actualización: al cierre del piloto con Distribuciones La Garantía*
