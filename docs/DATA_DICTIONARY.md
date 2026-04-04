# Sales Agent SaaS - Diccionario de Datos

## Control de Versiones

| Version | Fecha      | Descripcion                                                                         | Autor               |
|---------|------------|-------------------------------------------------------------------------------------|---------------------|
| 1.8.0   | 2026-04-04 | RAG con pgvector: `products` agrega `semantic_tags` JSONB (sinonimos, terminos de canal, contexto de uso, estrategia, atributos) y `embedding` VECTOR(1024) para busqueda semantica de productos via Voyage AI voyage-3. Los embeddings se generan de forma asincrona via Celery (campo NULL hasta que el worker procese la tarea) | Diseño colaborativo |
| 1.0.0   | 2026-03-31 | Version inicial — modelo completo de dominio                                        | Diseño colaborativo |
| 1.1.0   | 2026-03-31 | Agrega `delivery_days` y `delivery_cutoff_time` en `routes`; nueva tabla `goal_benefits` | Diseño colaborativo |
| 1.2.0   | 2026-04-01 | Reemplaza `start_time`, `end_time`, `delivery_cutoff_time` en `routes` por `daily_schedule` JSONB para soportar horarios distintos por dia de la semana | Diseño colaborativo |
| 1.3.0   | 2026-04-01 | Unicidad cruzada de `phone` entre `users` y `clients`; validacion de formato E.164 por pais en ambas tablas | Diseño colaborativo |
| 1.7.0   | 2026-04-04 | Nueva entidad `zones` (zonas geograficas formales); `routes` agrega `zone_id` FK y `route_type` ENUM (`presential`/`agent_wa`); `clients` agrega `zone_id` FK reemplazando campo texto `zone`; `route_visits` agrega `visit_type`, `escalated_to_salesperson_id` y `escalated_at`; nuevo `UserRole.AGENT` para el vendedor virtual IA; soporte para modelo de atencion de alta frecuencia (multiples rutas por zona con distintos vendedores o agente IA) | Diseño colaborativo |
| 1.6.0   | 2026-04-02 | Patron de integracion ERP estandarizado: `external_id` + `external_source` en `users`, `clients`, `products` y `orders`; unicidad `(tenant_id, external_id)` en cada tabla; alcance del agente acotado a gestion de pedidos (pre-documento); facturacion electronica queda en el ERP del tenant | Diseño colaborativo |
| 1.5.0   | 2026-04-01 | Nueva entidad `business_owners` (propietarios); `clients` vincula a owner via FK; datos legales migran a `business_owners`; reglas de unicidad de telefono actualizadas; principio de transparencia de normalizacion en herramientas admin | Diseño colaborativo |
| 1.4.0   | 2026-04-01 | Jerarquia geografica DANE (4 niveles): nuevas tablas `geo_countries`, `geo_departments`, `geo_municipalities`, `geo_populated_centers`; nueva tabla `geo_neighborhoods` (barrios tenant-managed); nueva tabla `client_typologies` reemplaza ENUM fijo en `clients`; campo `address` pasa a opcional cuando existen coordenadas GPS; agrega `address_normalized` y `address_validated` en `clients` | Diseño colaborativo |

---

## Convenciones

| Convencion        | Descripcion                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| `PK`              | Llave primaria                                                              |
| `FK`              | Llave foranea                                                               |
| `UK`              | Restriccion de unicidad                                                     |
| `NN`              | Not Null — campo obligatorio                                                |
| `IDX`             | Campo indexado para busquedas frecuentes                                    |
| `tenant_id`       | Presente en todas las tablas. Garantiza aislamiento de datos entre clientes del SaaS |
| `JSONB`           | Columna PostgreSQL de tipo JSON binario — permite consultas sobre su contenido |
| `ENUM`            | Conjunto cerrado de valores validos                                         |
| `v1.0.0`          | Version del modelo en que se introdujo el campo                             |

Todos los identificadores son `UUID` salvo indicacion contraria.
Todos los registros incluyen `created_at TIMESTAMPTZ` y, donde aplica, `updated_at TIMESTAMPTZ`.

---

## Indice de Tablas

| # | Tabla                        | Dominio             | Descripcion breve                                      |
|---|------------------------------|---------------------|--------------------------------------------------------|
| 1  | `tenants`                   | Configuracion       | Clientes del SaaS (distribuidoras)                    |
| 2  | `users`                     | Configuracion       | Vendedores, gerentes, admins y agente IA              |
| 3  | `suppliers`                 | Catalogo            | Proveedores que suministran los articulos             |
| 4  | `brands`                    | Catalogo            | Marcas comerciales vinculadas a un proveedor          |
| 5  | `categories`                | Catalogo            | Primer nivel de clasificacion de productos            |
| 6  | `subcategories`             | Catalogo            | Segundo nivel de clasificacion de productos           |
| 7  | `products`                  | Catalogo            | Articulos comercializados                             |
| 8  | `product_packaging`         | Catalogo            | Unidades de venta y embalajes por producto            |
| 9  | `client_classifications`    | Clientes            | Categorias de clasificacion configurables (Oro, Plata…)|
| 10 | `classification_rules`      | Clientes            | Reglas numericas para asignar clasificacion           |
| 11 | `clients`                   | Clientes            | Tiendas y establecimientos que compran al distribuidor|
| 12 | `zones`                     | Rutas               | Zonas geograficas. Agrupan clientes; pueden tener multiples rutas (presencial + agente IA) |
| 13 | `routes`                    | Rutas               | Rutas comerciales: presencial (vendedor) o agent_wa (agente IA) |
| 14 | `route_assignments`         | Rutas               | Historial de vendedores asignados a cada ruta         |
| 15 | `route_clients`             | Rutas               | Relacion N:N entre rutas y clientes                   |
| 16 | `visit_reasons`             | Visitas             | Catalogo de motivos de visita y no-visita             |
| 17 | `route_visits`              | Visitas             | Registro de cada contacto (presencial o WA) con un cliente |
| 17 | `promotions`                | Promociones         | Cabecera de ofertas y promociones comerciales         |
| 18 | `promotion_items`           | Promociones         | Productos que componen cada promocion                 |
| 19 | `orders`                    | Pedidos             | Cabecera del pedido tomado al cliente                 |
| 20 | `order_items`               | Pedidos             | Lineas de producto dentro de un pedido                |
| 21 | `order_returns`             | Pedidos             | Cabecera de devolucion asociada a un pedido           |
| 22 | `order_return_items`        | Pedidos             | Lineas de producto devueltas                          |
| 23 | `erp_imports`               | Integracion ERP     | Log de integraciones entrantes (facturas/devoluciones)|
| 24 | `sales_goals`               | Metas               | Metas de venta asignadas a vendedores o a la empresa  |
| 25 | `goal_progress`             | Metas               | Snapshots de avance periodico de cada meta            |
| 26 | `client_product_affinities` | Analitica           | Historial de afinidad cliente-producto para el agente |
| 27 | `daily_sales_snapshots`     | Analitica           | Pre-agregados diarios para reportes rapidos           |
| 28 | `wa_conversations`          | WhatsApp            | Estado de cada conversacion activa en WhatsApp        |
| 29 | `message_logs`              | WhatsApp            | Historial de mensajes enviados y recibidos            |
| 30 | `notification_schedules`    | Notificaciones      | Programacion de notificaciones automaticas            |
| 31 | `goal_benefits`             | Metas               | Beneficios asociados al cumplimiento de una meta (bonos, comisiones, premios) |
| 32 | `geo_countries`             | Geografía           | Paises soportados. Datos de referencia pre-cargados                           |
| 33 | `geo_departments`           | Geografía           | Departamentos de Colombia segun DANE. Pre-cargados                            |
| 34 | `geo_municipalities`        | Geografía           | Municipios de Colombia segun DANE (1.123 registros). Pre-cargados             |
| 35 | `geo_populated_centers`     | Geografía           | Centros poblados segun DANE (9.235 registros). Pre-cargados                   |
| 36 | `geo_neighborhoods`         | Geografía           | Barrios/sectores por centro poblado. Gestionados por el tenant                |
| 37 | `client_typologies`         | Clientes            | Tipologias de establecimiento configurables por tenant (reemplaza ENUM fijo)  |
| 38 | `business_owners`           | Clientes            | Propietarios de establecimientos. Un propietario puede tener N negocios       |

---

## 1. `tenants`

Representa a cada empresa distribuidora que contrata el SaaS. Es la raiz del aislamiento multi-tenant.

| Campo                        | Tipo           | Restricciones | v     | Descripcion                                                                 |
|------------------------------|----------------|---------------|-------|-----------------------------------------------------------------------------|
| `id`                         | UUID           | PK, NN        | 1.0.0 | Identificador unico del tenant                                              |
| `company_name`               | VARCHAR(200)   | NN            | 1.0.0 | Razon social de la distribuidora                                            |
| `slug`                       | VARCHAR(100)   | UK, NN        | 1.0.0 | Identificador URL-friendly unico (ej. `dist-norte`). Usado en rutas de API  |
| `whatsapp_phone_number_id`   | VARCHAR(50)    | UK, IDX       | 1.0.0 | ID del numero de telefono en Meta Business. Identifica el tenant al recibir un webhook |
| `whatsapp_business_account_id` | VARCHAR(50)  |               | 1.0.0 | ID de la cuenta de WhatsApp Business en Meta                                |
| `whatsapp_access_token`      | TEXT           |               | 1.0.0 | Token de acceso a la API de WhatsApp Business (cifrado en reposo)           |
| `sendgrid_api_key`           | TEXT           |               | 1.0.0 | API Key de SendGrid especifica del tenant para envio de correos (cifrado)   |
| `email_from`                 | VARCHAR(200)   |               | 1.0.0 | Direccion de correo remitente para notificaciones del tenant                |
| `email_from_name`            | VARCHAR(200)   |               | 1.0.0 | Nombre del remitente que aparece en los correos enviados                    |
| `erp_webhook_secret`         | TEXT           |               | 1.0.0 | Secret para validar la firma HMAC de los webhooks entrantes del ERP         |
| `timezone`                   | VARCHAR(50)    | NN            | 1.0.0 | Zona horaria del tenant (ej. `America/Bogota`). Afecta scheduler y reportes |
| `country_code`               | CHAR(2)        | NN            | 1.0.0 | Codigo ISO 3166-1 del pais (ej. `CO`). Determina formato de facturacion     |
| `currency_code`              | CHAR(3)        | NN            | 1.0.0 | Codigo ISO 4217 de moneda (ej. `COP`). Usado en todos los valores monetarios|
| `is_active`                  | BOOLEAN        | NN            | 1.0.0 | Indica si el tenant esta habilitado. Tenants inactivos no procesan mensajes  |
| `created_at`                 | TIMESTAMPTZ    | NN            | 1.0.0 | Fecha y hora de creacion del registro                                       |
| `updated_at`                 | TIMESTAMPTZ    | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                      |

---

## 2. `users`

Personas que interactuan con el sistema: vendedores, gerentes de zona y administradores del tenant.

| Campo            | Tipo         | Restricciones | v     | Descripcion                                                                        |
|------------------|--------------|---------------|-------|------------------------------------------------------------------------------------|
| `id`             | UUID         | PK, NN        | 1.0.0 | Identificador unico del usuario                                                    |
| `tenant_id`      | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece el usuario                                                 |
| `full_name`      | VARCHAR(200) | NN            | 1.0.0 | Nombre completo del usuario                                                        |
| `email`          | VARCHAR(200) | UK, NN        | 1.0.0 | Correo electronico. Usado para login y para envio de reportes de gerencia          |
| `phone`          | VARCHAR(20)  | IDX           | 1.0.0 | Numero de telefono en formato E.164 (ej. `+573001234567`). Es el identificador del vendedor en WhatsApp. **Unicidad cruzada (v1.3.0):** el sistema valida que este numero no exista en `clients.phone` del mismo tenant antes de permitir la creacion o edicion. Validacion de longitud minima segun `tenants.country_code` (Colombia: minimo 13 caracteres en formato E.164) |
| `hashed_password`| TEXT         | NN            | 1.0.0 | Contrasena cifrada con bcrypt                                                      |
| `role`           | ENUM         | NN            | 1.0.0 | Rol del usuario: `admin` (acceso total al tenant), `manager` (gerencia, recibe reportes), `supervisor` (jefe de zona), `salesperson` (vendedor de campo), `agent` (vendedor virtual IA — se asigna a rutas `agent_wa`; no tiene telefono propio ni password) |
| `is_active`      | BOOLEAN      | NN            | 1.0.0 | Indica si el usuario puede operar. Usuarios inactivos no pueden iniciar sesion     |
| `external_id`    | VARCHAR(100) | IDX           | 1.6.0 | ID del usuario en el ERP o sistema de nomina del tenant. Permite sincronizar el equipo de ventas desde el sistema de origen. **Unicidad:** `(tenant_id, external_id)`. NULL en usuarios creados directamente en el panel |
| `external_source`| VARCHAR(50)  |               | 1.6.0 | Sistema externo de origen: `siesa`, `world_office`, `sap`, `helisa`, `contapyme`, etc. NULL si el registro se creo en el panel del SaaS |
| `created_at`     | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                              |
| `updated_at`     | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                             |

---

## 3. `suppliers`

Empresas proveedoras que suministran los articulos que la distribuidora comercializa.

| Campo          | Tipo         | Restricciones | v     | Descripcion                                                                  |
|----------------|--------------|---------------|-------|------------------------------------------------------------------------------|
| `id`           | UUID         | PK, NN        | 1.0.0 | Identificador unico del proveedor                                            |
| `tenant_id`    | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece el proveedor                                         |
| `name`         | VARCHAR(200) | NN            | 1.0.0 | Nombre o razon social del proveedor                                          |
| `nit`          | VARCHAR(20)  |               | 1.0.0 | Numero de identificacion tributaria del proveedor. Requerido para facturacion electronica |
| `contact_name` | VARCHAR(200) |               | 1.0.0 | Nombre del contacto comercial en el proveedor                                |
| `contact_email`| VARCHAR(200) |               | 1.0.0 | Correo del contacto comercial                                                |
| `contact_phone`| VARCHAR(20)  |               | 1.0.0 | Telefono del contacto comercial                                              |
| `is_active`    | BOOLEAN      | NN            | 1.0.0 | Indica si el proveedor esta vigente                                          |
| `created_at`   | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                        |
| `updated_at`   | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                       |

---

## 4. `brands`

Marcas comerciales de los productos. Una marca pertenece a un unico proveedor.

| Campo         | Tipo         | Restricciones | v     | Descripcion                                                                   |
|---------------|--------------|---------------|-------|-------------------------------------------------------------------------------|
| `id`          | UUID         | PK, NN        | 1.0.0 | Identificador unico de la marca                                               |
| `tenant_id`   | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece la marca                                              |
| `supplier_id` | UUID         | FK, NN, IDX   | 1.0.0 | Proveedor dueno de la marca                                                   |
| `name`        | VARCHAR(200) | NN            | 1.0.0 | Nombre de la marca (ej. `Coca-Cola`, `Postobón`)                              |
| `logo_url`    | TEXT         |               | 1.0.0 | URL del logotipo de la marca. Puede apuntar al sitio del fabricante           |
| `is_active`   | BOOLEAN      | NN            | 1.0.0 | Indica si la marca esta vigente                                               |
| `created_at`  | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                         |
| `updated_at`  | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                        |

---

## 5. `categories`

Primer nivel de clasificacion del catalogo de productos (ej. Gaseosas, Lacteos, Aseo).

| Campo        | Tipo         | Restricciones | v     | Descripcion                                                                    |
|--------------|--------------|---------------|-------|--------------------------------------------------------------------------------|
| `id`         | UUID         | PK, NN        | 1.0.0 | Identificador unico de la categoria                                            |
| `tenant_id`  | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece la categoria                                           |
| `name`       | VARCHAR(200) | NN            | 1.0.0 | Nombre de la categoria                                                         |
| `description`| TEXT         |               | 1.0.0 | Descripcion opcional de la categoria                                           |
| `is_active`  | BOOLEAN      | NN            | 1.0.0 | Indica si la categoria esta vigente                                            |
| `created_at` | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                          |
| `updated_at` | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                         |

---

## 6. `subcategories`

Segundo nivel de clasificacion del catalogo (ej. dentro de Gaseosas: Personal, Familiar, Jumbo).

| Campo         | Tipo         | Restricciones | v     | Descripcion                                                                   |
|---------------|--------------|---------------|-------|-------------------------------------------------------------------------------|
| `id`          | UUID         | PK, NN        | 1.0.0 | Identificador unico de la subcategoria                                        |
| `tenant_id`   | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece la subcategoria                                       |
| `category_id` | UUID         | FK, NN, IDX   | 1.0.0 | Categoria padre a la que pertenece                                            |
| `name`        | VARCHAR(200) | NN            | 1.0.0 | Nombre de la subcategoria                                                     |
| `description` | TEXT         |               | 1.0.0 | Descripcion opcional de la subcategoria                                       |
| `is_active`   | BOOLEAN      | NN            | 1.0.0 | Indica si la subcategoria esta vigente                                        |
| `created_at`  | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                         |
| `updated_at`  | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                        |

---

## 7. `products`

Articulo basico del catalogo. La jerarquia completa es: Proveedor → Marca → Categoria → Subcategoria → Producto.

| Campo            | Tipo         | Restricciones | v     | Descripcion                                                                         |
|------------------|--------------|---------------|-------|-------------------------------------------------------------------------------------|
| `id`             | UUID         | PK, NN        | 1.0.0 | Identificador unico del producto                                                    |
| `tenant_id`      | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece el producto                                                 |
| `brand_id`       | UUID         | FK, NN, IDX   | 1.0.0 | Marca a la que pertenece el producto                                                |
| `subcategory_id` | UUID         | FK, NN, IDX   | 1.0.0 | Subcategoria a la que pertenece el producto                                         |
| `name`           | VARCHAR(200) | NN            | 1.0.0 | Nombre comercial del producto                                                       |
| `description`    | TEXT         |               | 1.0.0 | Descripcion detallada del producto                                                  |
| `ean`            | VARCHAR(20)  | IDX           | 1.0.0 | Codigo de barras EAN de la unidad minima (unidad base). Es el identificador universal del producto |
| `external_sku`   | VARCHAR(100) | IDX           | 1.0.0 | Codigo del articulo en el ERP del tenant. Es el `external_id` del producto: el identificador con el que el ERP conoce este articulo. **Unicidad (v1.6.0):** `(tenant_id, external_sku)`. Permite mapear pedidos contra facturas. NULL en productos creados directamente en el panel |
| `external_source`| VARCHAR(50)  |               | 1.6.0 | Sistema externo de origen del catalogo: `siesa`, `world_office`, `sap`, `helisa`, `contapyme`, etc. NULL si el producto se creo en el panel del SaaS |
| `is_mandatory`   | BOOLEAN      | NN            | 1.0.0 | Indica si el producto es "infaltable" o "imperdonable". Los productos marcados asi generan metas y alertas especiales. Este flag puede actualizarse por periodo segun estrategia comercial |
| `tax_type`       | ENUM         |               | 1.0.0 | Tipo de impuesto aplicable: `iva`, `ipoconsumo`, `exempt`. Requerido para facturacion electronica |
| `tax_rate`       | NUMERIC(5,2) |               | 1.0.0 | Tasa del impuesto en porcentaje (ej. `19.00` para IVA del 19%)                     |
| `image_url`      | TEXT         |               | 1.0.0 | URL externa de la imagen del producto (ej. sitio del fabricante). Si se provee, tiene precedencia sobre `image_file_path` para mantener la imagen siempre actualizada |
| `image_file_path`| TEXT         |               | 1.0.0 | Ruta en almacenamiento propio (S3/local) de la imagen cargada manualmente          |
| `is_active`      | BOOLEAN      | NN            | 1.0.0 | Indica si el producto esta vigente en el catalogo                                   |
| `semantic_tags`  | JSONB        |               | 1.8.0 | Etiquetas semanticas enriquecidas para mejorar precision del embedding. Estructura: `{"synonyms": [], "channel_terms": [], "use_context": [], "strategy": [], "attributes": []}`. Editables en panel admin o generables automaticamente via IA |
| `embedding`      | VECTOR(1024) | IDX           | 1.8.0 | Vector de 1024 dimensiones generado por Voyage AI voyage-3 a partir del texto semantico compuesto del producto. NULL hasta que el worker Celery ejecute `index_product_task`. Los productos con NULL quedan excluidos de busqueda semantica. Indice IVFFlat (coseno) en PostgreSQL |
| `created_at`     | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                               |
| `updated_at`     | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                              |

**Texto semantico compuesto** (insumo para el embedding): se construye concatenando `name`, `brand`, `category`, `subcategory`, `description`, `unit`, `price` y cada lista dentro de `semantic_tags`. El campo `embedding` se regenera automaticamente cuando cambia cualquiera de esos campos via `PATCH /admin/productos/{id}`.

**Busqueda semantica** (`search_products`): convierte la consulta en lenguaje natural del vendedor a embedding y ejecuta `ORDER BY embedding <=> query_vector::vector` con filtro `tenant_id + is_active + embedding IS NOT NULL` usando el indice IVFFlat.

---

## 8. `product_packaging`

Unidades de venta o embalajes de un producto. Cada producto tiene al menos una unidad base y puede tener embalajes superiores (sixpack, caja, display, master). Cada embalaje tiene su propio EAN y precio.

| Campo               | Tipo          | Restricciones | v     | Descripcion                                                                     |
|---------------------|---------------|---------------|-------|---------------------------------------------------------------------------------|
| `id`                | UUID          | PK, NN        | 1.0.0 | Identificador unico del embalaje                                                |
| `tenant_id`         | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                         |
| `product_id`        | UUID          | FK, NN, IDX   | 1.0.0 | Producto al que pertenece este embalaje                                         |
| `name`              | VARCHAR(100)  | NN            | 1.0.0 | Nombre del embalaje (ej. `Unidad`, `Sixpack`, `Caja x12`, `Display`, `Master`)  |
| `ean`               | VARCHAR(20)   | IDX           | 1.0.0 | Codigo de barras EAN propio de este embalaje. Diferente al EAN del producto base|
| `units_per_package` | INTEGER       | NN            | 1.0.0 | Cantidad de unidades base que contiene este embalaje. La unidad base tiene valor `1` |
| `is_base_unit`      | BOOLEAN       | NN            | 1.0.0 | TRUE unicamente en el embalaje de menor nivel (unidad minima de venta). Solo puede haber un embalaje base por producto |
| `sale_price`        | NUMERIC(14,2) | NN            | 1.0.0 | Precio de lista de venta de este embalaje. Es el precio base antes de cualquier descuento o promocion |
| `cost_price`        | NUMERIC(14,2) |               | 1.0.0 | Costo del embalaje (opcional). Permite calcular margen cuando se dispone del dato |
| `image_url`         | TEXT          |               | 1.0.0 | URL externa de la imagen de este embalaje especifico                            |
| `image_file_path`   | TEXT          |               | 1.0.0 | Ruta en almacenamiento propio de la imagen cargada para este embalaje           |
| `is_active`         | BOOLEAN       | NN            | 1.0.0 | Indica si este embalaje esta disponible para la venta                           |
| `sort_order`        | INTEGER       | NN            | 1.0.0 | Orden de presentacion del embalaje (de menor a mayor: 1=unidad, 2=sixpack…)    |
| `created_at`        | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                           |
| `updated_at`        | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                          |

---

## 9. `client_classifications`

Categorias de clasificacion de clientes configurables por tenant (ej. Oro, Plata, Bronce o cualquier esquema propio).

| Campo        | Tipo         | Restricciones | v     | Descripcion                                                                    |
|--------------|--------------|---------------|-------|--------------------------------------------------------------------------------|
| `id`         | UUID         | PK, NN        | 1.0.0 | Identificador unico de la clasificacion                                        |
| `tenant_id`  | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                        |
| `name`       | VARCHAR(100) | NN            | 1.0.0 | Nombre de la clasificacion (ej. `Oro`, `Plata`, `Bronce`, `Diamante`)         |
| `color`      | CHAR(7)      |               | 1.0.0 | Color hexadecimal para visualizacion en dashboards (ej. `#FFD700`)             |
| `icon`       | VARCHAR(50)  |               | 1.0.0 | Nombre del icono o emoji de referencia para la clasificacion                   |
| `sort_order` | INTEGER      | NN            | 1.0.0 | Posicion en el ranking (1 = clasificacion mas alta)                            |
| `is_active`  | BOOLEAN      | NN            | 1.0.0 | Indica si la clasificacion esta vigente                                        |
| `created_at` | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                          |
| `updated_at` | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                         |

---

## 10. `classification_rules`

Reglas numericas que determinan automaticamente la clasificacion de un cliente. Se evaluan contra los datos de venta neta del periodo.

| Campo                  | Tipo          | Restricciones | v     | Descripcion                                                                |
|------------------------|---------------|---------------|-------|----------------------------------------------------------------------------|
| `id`                   | UUID          | PK, NN        | 1.0.0 | Identificador unico de la regla                                            |
| `classification_id`    | UUID          | FK, NN, IDX   | 1.0.0 | Clasificacion a la que pertenece esta regla                                |
| `metric`               | ENUM          | NN            | 1.0.0 | Metrica evaluada: `monthly_volume` ($ ventas netas), `order_frequency` (pedidos/mes), `effectiveness_pct` (% visitas efectivas), `net_sales_pct`, `new_clients_pct`, `mandatory_sales` |
| `operator`             | ENUM          | NN            | 1.0.0 | Operador de comparacion: `gte` (mayor o igual), `lte` (menor o igual), `eq` (igual) |
| `value`                | NUMERIC(14,2) | NN            | 1.0.0 | Valor umbral de la regla (ej. `500000` para ventas >= $500.000)            |
| `period_days`          | INTEGER       | NN            | 1.0.0 | Ventana de dias hacia atras para calcular la metrica (ej. `30` para el ultimo mes) |
| `created_at`           | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                      |

---

## 11. `clients`

Establecimientos comerciales (tiendas, superetes, panaderias, etc.) que son clientes de la distribuidora. Incluye datos legales para facturacion electronica valida en Colombia y region.

| Campo                  | Tipo          | Restricciones | v     | Descripcion                                                                              |
|------------------------|---------------|---------------|-------|------------------------------------------------------------------------------------------|
| `id`                   | UUID          | PK, NN        | 1.0.0 | Identificador unico del cliente                                                          |
| `tenant_id`            | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece el cliente                                                       |
| `zone_id`              | UUID          | FK, IDX       | 1.7.0 | Zona geografica a la que pertenece el cliente (FK a `zones`). Reemplaza el campo texto `zone`. Un cliente en una zona aparece automaticamente en todas las rutas activas de esa zona (presenciales y agent_wa), sin necesidad de asignarlo ruta por ruta |
| `owner_id`             | UUID          | FK, NN, IDX   | 1.5.0 | Propietario del establecimiento (FK a `business_owners`). Un mismo propietario puede estar vinculado a multiples establecimientos. **Transparencia para el operador:** al registrar un cliente el sistema detecta automaticamente si ya existe un propietario con la misma CC y lo vincula, presentando solo una confirmacion simple al operador |
| `business_name`        | VARCHAR(200)  | NN            | 1.0.0 | Nombre comercial del establecimiento (ej. `Tienda La Esquina`). Nombre con el que se conoce en la calle |
| `phone`                | VARCHAR(20)   | IDX           | 1.0.0 | Numero de telefono principal en formato E.164. Es el numero de WhatsApp del tendero para interaccion con el agente. **Unicidad cruzada (v1.3.0):** el sistema valida que este numero no exista en `users.phone` del mismo tenant antes de permitir la creacion o edicion, evitando referencias circulares que impedirian identificar correctamente al interlocutor en WhatsApp. Validacion de longitud minima segun `tenants.country_code` (Colombia: minimo 13 caracteres en formato E.164) |
| `email`                | VARCHAR(200)  |               | 1.0.0 | Correo electronico del cliente. Usado para envio de confirmaciones de pedido             |
| `country_id`                | UUID          | FK, NN, IDX   | 1.4.0 | Pais del establecimiento (FK a `geo_countries`). Reemplaza el campo `country` de texto libre |
| `department_id`             | UUID          | FK, NN, IDX   | 1.4.0 | Departamento segun DANE (FK a `geo_departments`). Reemplaza el campo `department` de texto libre |
| `municipality_id`           | UUID          | FK, NN, IDX   | 1.4.0 | Municipio segun DANE (FK a `geo_municipalities`). Reemplaza el campo `city` de texto libre |
| `populated_center_id`       | UUID          | FK, IDX       | 1.4.0 | Centro poblado segun DANE (FK a `geo_populated_centers`). Nivel mas granular del catalogo geografico oficial. Requerido cuando el municipio tiene multiples centros poblados |
| `neighborhood_id`           | UUID          | FK, IDX       | 1.4.0 | Barrio o sector (FK a `geo_neighborhoods`). Gestionado por el tenant, vinculado al centro poblado para evitar homonimos entre ciudades |
| `address`                   | TEXT          |               | 1.4.0 | Direccion fisica del establecimiento en nomenclatura local (ej. `Calle 13 # 24-66`). **Opcional desde v1.4.0** cuando existen `latitude` y `longitude` validos, para soportar negocios en zonas de invasion o sin nomenclatura convencional |
| `address_normalized`        | TEXT          |               | 1.4.0 | Version corregida/normalizada de la direccion sugerida por el sistema antes de geocodificar (ej. corrige `Carerra` → `Carrera`). El operador debe aprobar la correccion antes de que se dispare la geocodificacion automatica |
| `address_validated`         | BOOLEAN       | NN            | 1.4.0 | TRUE cuando el operador ha confirmado que la direccion (o `address_normalized`) es correcta y lista para geocodificar. FALSE mientras esta pendiente de revision |
| `latitude`                  | NUMERIC(10,7) | IDX           | 1.0.0 | Latitud GPS del establecimiento. Puede provenir de geocodificacion automatica o de captura manual en campo. Junto con `longitude` permite validar el check-in del vendedor y calcular el area de cobertura de la ruta |
| `longitude`                 | NUMERIC(10,7) | IDX           | 1.0.0 | Longitud GPS del establecimiento                                                         |
| `typology_id`               | UUID          | FK, NN, IDX   | 1.4.0 | Tipologia del establecimiento (FK a `client_typologies`). Reemplaza el ENUM fijo `typology` de v1.0.0. Configurable por tenant; el sistema sugiere la tipologia basandose en palabras clave del nombre del negocio pero el operador decide |
| `classification_id`    | UUID          | FK, IDX       | 1.0.0 | Clasificacion actual del cliente (Oro/Plata/Bronce). Se recalcula automaticamente segun reglas |
| `external_id`          | VARCHAR(100)  | IDX           | 1.0.0 | ID del cliente en el ERP del tenant. **Unicidad (v1.6.0):** `(tenant_id, external_id)`. NULL en clientes capturados directamente por el vendedor en campo sin pasar por el ERP |
| `external_source`      | VARCHAR(50)   |               | 1.6.0 | Sistema externo de origen: `siesa`, `world_office`, `sap`, `helisa`, `contapyme`, etc. NULL si el registro se creo en el panel del SaaS |
| `first_purchase_date`  | DATE          |               | 1.0.0 | Fecha del primer pedido facturado y entregado. NULL indica que el cliente es **Venta 0** (nunca ha comprado) |
| `whatsapp_opt_in`      | BOOLEAN       | NN            | 1.0.0 | Indica si el cliente ha dado consentimiento explicito para recibir mensajes por WhatsApp. Requerido por politicas de Meta |
| `credit_limit`         | NUMERIC(14,2) |               | 1.0.0 | Cupo de credito maximo otorgado al cliente (gancho para modulo de cartera futuro)        |
| `payment_terms_days`   | INTEGER       |               | 1.0.0 | Plazo de pago en dias (ej. `30`, `60`). NULL indica pago de contado                     |
| `credit_balance`       | NUMERIC(14,2) |               | 1.0.0 | Saldo actual de cartera (deuda vigente del cliente). Se actualiza con cada factura y pago |
| `credit_status`        | ENUM          |               | 1.0.0 | Estado crediticio: `active` (puede comprar), `blocked` (supero cupo o mora), `suspended` (decision manual gerencia). La logica de bloqueo de pedidos se activa en fase posterior |
| `is_active`            | BOOLEAN       | NN            | 1.0.0 | Indica si el cliente esta vigente. Clientes inactivos no se programan en rutas          |
| `created_at`           | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                    |
| `updated_at`           | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                                   |

---

## 12. `zones`

Agrupacion geografica de clientes. Una zona puede tener multiples rutas activas simultaneas con distintos vendedores y/o el agente IA, lo que habilita el modelo de atencion de alta frecuencia (ej. visita presencial lunes + contacto WA del agente miercoles).

| Campo         | Tipo         | Restricciones | v     | Descripcion                                                                             |
|---------------|--------------|---------------|-------|-----------------------------------------------------------------------------------------|
| `id`          | UUID         | PK, NN        | 1.7.0 | Identificador unico de la zona                                                          |
| `tenant_id`   | UUID         | FK, NN, IDX   | 1.7.0 | Tenant al que pertenece la zona                                                         |
| `name`        | VARCHAR(200) | NN            | 1.7.0 | Nombre descriptivo de la zona (ej. `Zona Norte Magangue`, `Centro Historico`)           |
| `description` | TEXT         |               | 1.7.0 | Descripcion de la cobertura geografica de la zona                                       |
| `is_active`   | BOOLEAN      | NN            | 1.7.0 | Indica si la zona esta operativa                                                         |
| `created_at`  | TIMESTAMPTZ  | NN            | 1.7.0 | Fecha y hora de creacion del registro                                                   |
| `updated_at`  | TIMESTAMPTZ  | NN            | 1.7.0 | Fecha y hora de la ultima modificacion                                                  |

---

## 13. `routes`

Ruta comercial: define quien visita que zona, en que dias, con que horario y de que forma. Una misma zona puede tener N rutas activas: una presencial (vendedor humano) y una agent_wa (agente IA), habilitando el modelo de alta frecuencia de visita.

| Campo            | Tipo         | Restricciones | v     | Descripcion                                                                        |
|------------------|--------------|---------------|-------|------------------------------------------------------------------------------------|
| `id`             | UUID         | PK, NN        | 1.0.0 | Identificador unico de la ruta                                                     |
| `tenant_id`      | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece la ruta                                                    |
| `zone_id`        | UUID         | FK, IDX       | 1.7.0 | Zona geografica que cubre esta ruta (FK a `zones`). Permite agrupar rutas presenciales y agent_wa bajo la misma zona para analytics comparativos |
| `salesperson_id` | UUID         | FK, NN, IDX   | 1.0.0 | Usuario asignado a la ruta. Puede ser un vendedor (`role=salesperson`) o el agente IA (`role=agent`). Para rutas `agent_wa`, apunta al registro de usuario especial del agente |
| `name`           | VARCHAR(200) |               | 1.0.0 | Nombre descriptivo (ej. `Ruta Zona Norte - Lunes`, `Ruta Zona Norte - Mie IA`)     |
| `route_type`     | ENUM         | NN            | 1.7.0 | Tipo de ruta: `presential` (visita fisica del vendedor) o `agent_wa` (el agente IA contacta a cada cliente por WhatsApp en el dia asignado, tomando pedidos y manejando objeciones) |
| `operating_days` | JSONB        |               | 1.0.0 | Dias de visita/contacto como array ISO (1=Lun…6=Sab). Ej: `[1]` para ruta solo lunes |
| `delivery_days`  | JSONB        |               | 1.1.0 | Dias de entrega/despacho como array ISO. Puede diferir de `operating_days`. Ej: visita lunes `[1]`, entrega martes `[2]` |
| `daily_schedule` | JSONB        |               | 1.2.0 | Horario de atencion y corte por dia de la semana. Formato: `{"1": {"start": "07:30", "end": "16:00", "cutoff": "15:30"}}`. El agente consulta la entrada del dia actual |
| `is_active`      | BOOLEAN      | NN            | 1.0.0 | Indica si la ruta esta operativa                                                    |
| `created_at`     | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                               |
| `updated_at`     | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                              |

---

## 14. `route_assignments`

Historial de asignacion de vendedores a rutas. Permite saber quien atendio cada ruta en cada periodo y transferir inteligencia historica al nuevo vendedor.

| Campo        | Tipo        | Restricciones | v     | Descripcion                                                                        |
|--------------|-------------|---------------|-------|------------------------------------------------------------------------------------|
| `id`         | UUID        | PK, NN        | 1.0.0 | Identificador unico de la asignacion                                               |
| `route_id`   | UUID        | FK, NN, IDX   | 1.0.0 | Ruta asignada                                                                      |
| `salesperson_id`  | UUID        | FK, NN, IDX   | 1.0.0 | Vendedor asignado (referencia a `users`)                                           |
| `valid_from` | DATE        | NN            | 1.0.0 | Fecha de inicio de la asignacion                                                   |
| `valid_to`   | DATE        |               | 1.0.0 | Fecha de fin de la asignacion. NULL indica que es la asignacion vigente actualmente|
| `is_active`  | BOOLEAN     | NN            | 1.0.0 | TRUE en la asignacion actual. Facilita consultas sin filtrar por fechas            |
| `created_at` | TIMESTAMPTZ | NN            | 1.0.0 | Fecha y hora de creacion del registro                                              |

---

## 14. `route_clients`

Relacion muchos-a-muchos entre rutas y clientes. Un cliente puede pertenecer a varias rutas (atendido por distintos vendedores para diferentes lineas de producto).

| Campo             | Tipo        | Restricciones | v     | Descripcion                                                                          |
|-------------------|-------------|---------------|-------|--------------------------------------------------------------------------------------|
| `id`              | UUID        | PK, NN        | 1.0.0 | Identificador unico del vinculo ruta-cliente                                         |
| `route_id`        | UUID        | FK, NN, IDX   | 1.0.0 | Ruta a la que pertenece esta entrada                                                 |
| `client_id`       | UUID        | FK, NN, IDX   | 1.0.0 | Cliente incluido en la ruta                                                          |
| `category_filter` | JSONB       |               | 1.0.0 | Array opcional de IDs de categorias o marcas que atiende este vendedor en este cliente por esta ruta. NULL indica que atiende todo el catalogo |
| `sort_order`      | INTEGER     |               | 1.0.0 | Orden de visita sugerido del cliente dentro de la ruta                               |
| `valid_from`      | DATE        | NN            | 1.0.0 | Fecha desde la que el cliente esta en la ruta                                        |
| `valid_to`        | DATE        |               | 1.0.0 | Fecha de retiro del cliente de la ruta. NULL indica que sigue activo                 |
| `is_active`       | BOOLEAN     | NN            | 1.0.0 | Indica si la relacion esta vigente                                                   |
| `created_at`      | TIMESTAMPTZ | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                |

---

## 15. `visit_reasons`

Catalogo parametrizable de motivos de visita y no-visita. Define ademas si el motivo exige o permite evidencia fotografica.

| Campo          | Tipo         | Restricciones | v     | Descripcion                                                                     |
|----------------|--------------|---------------|-------|---------------------------------------------------------------------------------|
| `id`           | UUID         | PK, NN        | 1.0.0 | Identificador unico del motivo                                                  |
| `tenant_id`    | UUID         | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece el motivo                                               |
| `code`         | VARCHAR(50)  | NN            | 1.0.0 | Codigo corto del motivo (ej. `TIENDA_CERRADA`, `SIN_DINERO`, `PEDIDO_TOMADO`)  |
| `description`  | VARCHAR(200) | NN            | 1.0.0 | Descripcion legible del motivo para el vendedor y los reportes                  |
| `applies_to`   | ENUM         | NN            | 1.0.0 | Contexto en que aplica el motivo: `visited_with_sale` (visita con venta), `visited_no_sale` (visita sin venta), `not_visited` (no se realizo la visita) |
| `requires_photo`| BOOLEAN     | NN            | 1.0.0 | TRUE si el motivo obliga a adjuntar una fotografia como evidencia (ej. tienda cerrada) |
| `allows_photo` | BOOLEAN      | NN            | 1.0.0 | TRUE si el motivo permite adjuntar foto de forma opcional                       |
| `is_active`    | BOOLEAN      | NN            | 1.0.0 | Indica si el motivo esta vigente y disponible para seleccion                    |
| `created_at`   | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de creacion del registro                                           |
| `updated_at`   | TIMESTAMPTZ  | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                          |

---

## 17. `route_visits`

Registro de cada contacto (presencial o WA) con un cliente dentro de una ruta. Es la fuente de verdad para calcular efectividad, comparar rendimiento vendedor vs agente IA, y gestionar escalaciones.

| Campo              | Tipo          | Restricciones | v     | Descripcion                                                                          |
|--------------------|---------------|---------------|-------|--------------------------------------------------------------------------------------|
| `id`               | UUID          | PK, NN        | 1.0.0 | Identificador unico de la visita                                                     |
| `tenant_id`        | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                              |
| `route_id`         | UUID          | FK, NN, IDX   | 1.0.0 | Ruta en la que se enmarca la visita                                                  |
| `route_client_id`  | UUID          | FK, NN, IDX   | 1.0.0 | Vinculo ruta-cliente especifico que origino la visita                                |
| `salesperson_id`        | UUID          | FK, NN, IDX   | 1.0.0 | Vendedor que realizo o intento la visita                                             |
| `visit_date`       | DATE          | NN, IDX       | 1.0.0 | Fecha en que estaba programada la visita                                             |
| `status`           | ENUM          | NN            | 1.0.0 | Estado de la visita: `planned` (programada), `checked_in` (vendedor en el punto), `completed` (visita finalizada), `rescheduled` (reagendada para otro dia), `postponed` (pospuesta para mas tarde hoy), `skipped` (omitida sin registro) |
| `result`           | ENUM          |               | 1.0.0 | Resultado final: `effective_with_sale` (hubo pedido), `effective_no_sale` (visita sin pedido), `not_visited` (no se llego al cliente) |
| `reason_id`        | UUID          | FK, IDX       | 1.0.0 | Motivo del resultado (FK a `visit_reasons`)                                         |
| `checkin_lat`      | NUMERIC(10,7) |               | 1.0.0 | Latitud GPS registrada en el momento del check-in del vendedor                       |
| `checkin_lng`      | NUMERIC(10,7) |               | 1.0.0 | Longitud GPS registrada en el momento del check-in                                   |
| `checkin_at`       | TIMESTAMPTZ   |               | 1.0.0 | Fecha y hora exacta del check-in                                                     |
| `checkout_at`      | TIMESTAMPTZ   |               | 1.0.0 | Fecha y hora exacta del checkout (fin de la visita)                                  |
| `is_gps_verified`  | BOOLEAN       |               | 1.0.0 | TRUE si las coordenadas de check-in estaban dentro del radio valido del cliente. Calculado automaticamente al registrar el check-in |
| `photo_evidence_url`| TEXT         |               | 1.0.0 | URL de la fotografia de evidencia subida al almacenamiento. Obligatoria cuando `visit_reasons.requires_photo = TRUE` |
| `rescheduled_to`   | TIMESTAMPTZ   |               | 1.0.0 | Nueva fecha y hora propuesta cuando la visita se pospone o reagenda                  |
| `order_id`         | UUID          | FK            |  1.0.0 | Pedido generado durante esta visita. NULL si no hubo venta                          |
| `visit_type`                  | ENUM          | NN            | 1.7.0 | Tipo de contacto: `presential` (visita fisica del vendedor) o `agent_wa` (mensaje WA iniciado por el agente IA). Permite segregar efectividad y ventas por canal en analytics |
| `escalated_to_salesperson_id` | UUID          | FK, IDX       | 1.7.0 | Cuando el agente IA no obtiene respuesta del cliente (ruta `agent_wa`), registra aqui el vendedor presencial al que se escala para seguimiento. NULL si no hay escalacion |
| `escalated_at`                | TIMESTAMPTZ   |               | 1.7.0 | Fecha y hora en que se ejecuto la escalacion al vendedor humano                      |
| `notes`            | TEXT          |               | 1.0.0 | Notas libres del vendedor o del agente sobre el contacto                             |
| `created_at`       | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                |
| `updated_at`       | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                               |

---

## 18. `promotions`

Cabecera de una oferta o promocion comercial. Soporta seis tipos de mecanismo de descuento o bonificacion.

| Campo               | Tipo          | Restricciones | v     | Descripcion                                                                                 |
|---------------------|---------------|---------------|-------|---------------------------------------------------------------------------------------------|
| `id`                | UUID          | PK, NN        | 1.0.0 | Identificador unico de la promocion                                                         |
| `tenant_id`         | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                                     |
| `name`              | VARCHAR(200)  | NN            | 1.0.0 | Nombre comercial de la promocion (ej. `12+2 Mega Roll`)                                     |
| `description`       | TEXT          |               | 1.0.0 | Descripcion detallada de la mecanica de la oferta                                           |
| `promo_type`        | ENUM          | NN            | 1.0.0 | Tipo de mecanica: `pay_n_take_m` (paga N lleva M del mismo producto), `buy_n_get_free` (compra N lleva A gratis), `combo` (combinacion a precio especial), `quantity_discount` (descuento por volumen), `tiered_price` (precio cambia a partir de X unidades), `spend_based_discount` (descuento por gasto en marca/categoria) |
| `scope_level`       | ENUM          |               | 1.0.0 | Nivel de catalogo al que aplica el trigger para `spend_based_discount`: `brand`, `category`, `subcategory`, `product`. NULL para los demas tipos |
| `scope_id`          | UUID          |               | 1.0.0 | ID de la entidad en `scope_level` (marca, categoria, etc.) sobre la que se mide el gasto   |
| `trigger_qty`       | INTEGER       |               | 1.0.0 | Cantidad minima de unidades que activa la promocion (N en "paga N lleva M" o "compra X cantidad") |
| `trigger_spend`     | NUMERIC(14,2) |               | 1.0.0 | Monto minimo en pesos que activa la promocion (para `spend_based_discount`)                 |
| `reward_qty`        | INTEGER       |               | 1.0.0 | Cantidad de unidades del beneficio (M en "lleva M gratis", unidades del regalo)             |
| `reward_discount_pct`| NUMERIC(5,2) |               | 1.0.0 | Porcentaje de descuento otorgado como recompensa (ej. `15.00` para 15% de descuento)       |
| `reward_price_override`| NUMERIC(14,2)|            | 1.0.0 | Precio especial por embalaje que reemplaza al precio de lista (para `tiered_price`)         |
| `valid_from`        | DATE          | NN            | 1.0.0 | Fecha de inicio de vigencia de la promocion                                                 |
| `valid_to`          | DATE          |               | 1.0.0 | Fecha de fin de vigencia. NULL indica vigencia indefinida                                   |
| `image_url`         | TEXT          |               | 1.0.0 | URL externa de la imagen promocional (ej. arte del proveedor)                               |
| `image_file_path`   | TEXT          |               | 1.0.0 | Ruta en almacenamiento propio de la imagen cargada para la promocion                        |
| `is_active`         | BOOLEAN       | NN            | 1.0.0 | Indica si la promocion esta activa y disponible para aplicarse en pedidos                   |
| `created_at`        | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                       |
| `updated_at`        | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                                      |

---

## 18. `promotion_items`

Productos que componen una promocion, con el rol que cada uno cumple en la mecanica.

| Campo                  | Tipo    | Restricciones | v     | Descripcion                                                                         |
|------------------------|---------|---------------|-------|-------------------------------------------------------------------------------------|
| `id`                   | UUID    | PK, NN        | 1.0.0 | Identificador unico del item de la promocion                                        |
| `promotion_id`         | UUID    | FK, NN, IDX   | 1.0.0 | Promocion a la que pertenece                                                        |
| `product_packaging_id` | UUID    | FK, NN, IDX   | 1.0.0 | Embalaje especifico del producto involucrado                                        |
| `role`                 | ENUM    | NN            | 1.0.0 | Rol del producto en la promocion: `trigger` (el que se compra para activarla), `gift` (el que se entrega gratis o a precio especial — frecuentemente un producto que se quiere "sembrar" en el cliente), `combo_item` (parte de un combo a precio conjunto) |
| `quantity`             | INTEGER | NN            | 1.0.0 | Cantidad de este producto/embalaje en la mecanica (ej. para "12+2", el trigger tiene quantity=12 y el gift tiene quantity=2) |
| `sort_order`           | INTEGER |               | 1.0.0 | Orden de presentacion del item dentro de la promocion                               |
| `created_at`           | TIMESTAMPTZ | NN        | 1.0.0 | Fecha y hora de creacion del registro                                               |

---

## 19. `orders`

Cabecera del pedido. Registra las tres capas de valor: lo pedido, lo facturado y lo entregado neto.

| Campo                    | Tipo          | Restricciones | v     | Descripcion                                                                                 |
|--------------------------|---------------|---------------|-------|---------------------------------------------------------------------------------------------|
| `id`                     | UUID          | PK, NN        | 1.0.0 | Identificador unico del pedido                                                              |
| `tenant_id`              | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                                     |
| `reference_code`         | VARCHAR(50)   | UK, NN        | 1.0.0 | Codigo de referencia unico del pedido. Se envia al ERP externo junto con el pedido y debe regresar con la factura para permitir la reconciliacion automatica |
| `client_id`              | UUID          | FK, NN, IDX   | 1.0.0 | Cliente al que se le tomo el pedido                                                         |
| `salesperson_id`              | UUID          | FK, NN, IDX   | 1.0.0 | Vendedor que tomo el pedido                                                                 |
| `route_visit_id`         | UUID          | FK, IDX       | 1.0.0 | Visita en la que se origino el pedido. NULL si el pedido llega por un canal externo         |
| `status`                 | ENUM          | NN, IDX       | 1.0.0 | Estado del pedido: `draft` (en construccion por el agente), `pending` (enviado, esperando logistica), `confirmed` (aprobado por logistica), `dispatched` (en camino), `invoiced` (facturado totalmente), `partially_invoiced` (facturado parcialmente), `cancelled` (anulado) |
| `source`                 | ENUM          | NN            | 1.0.0 | Origen del pedido: `agent_wa` (tomado por el agente via WhatsApp), `admin_panel` (ingresado desde el panel), `erp_api` (recibido via API del ERP), `erp_csv` (importado via CSV), `erp_xml` (importado via XML). Refleja que el agente es una capa de inteligencia, no el unico canal |
| `order_date`             | DATE          | NN, IDX       | 1.0.0 | Fecha en que se tomo el pedido                                                              |
| `ordered_subtotal`       | NUMERIC(14,2) |               | 1.0.0 | Suma de los totales de linea del pedido original antes de impuestos                         |
| `ordered_discount_total` | NUMERIC(14,2) |               | 1.0.0 | Suma de todos los descuentos aplicados en el pedido original                                |
| `ordered_tax_total`      | NUMERIC(14,2) |               | 1.0.0 | Suma de impuestos calculados sobre el pedido original                                       |
| `ordered_total`          | NUMERIC(14,2) |               | 1.0.0 | Total del pedido original (subtotal - descuentos + impuestos)                               |
| `invoice_subtotal`       | NUMERIC(14,2) |               | 1.0.0 | Subtotal segun la factura recibida del ERP. Puede diferir del pedido por ajustes de stock o precio |
| `invoice_discount_total` | NUMERIC(14,2) |               | 1.0.0 | Total de descuentos segun la factura del ERP                                                |
| `invoice_tax_total`      | NUMERIC(14,2) |               | 1.0.0 | Total de impuestos segun la factura del ERP                                                 |
| `invoice_total`          | NUMERIC(14,2) |               | 1.0.0 | Total de la factura recibida del ERP                                                        |
| `invoiced_at`            | TIMESTAMPTZ   |               | 1.0.0 | Fecha y hora en que se recibio y proceso la factura del ERP                                 |
| `external_id`            | VARCHAR(100)  | IDX           | 1.6.0 | ID del pedido en el ERP del tenant. Nace NULL cuando el pedido es creado por el agente; el ERP lo asigna al procesar el pedido y lo devuelve via webhook/CSV. **Unicidad:** `(tenant_id, external_id)`. El campo `reference_code` es la referencia que el agente envia al ERP; `external_id` es la respuesta del ERP |
| `external_source`        | VARCHAR(50)   |               | 1.6.0 | Sistema externo que proceso el pedido: `siesa`, `world_office`, `sap`, `helisa`, `contapyme`, etc. NULL mientras el pedido no haya sido procesado por el ERP |
| `external_invoice_id`    | VARCHAR(100)  | IDX           | 1.0.0 | ID interno de la factura en el ERP externo                                                  |
| `external_invoice_number`| VARCHAR(50)   |               | 1.0.0 | Numero de factura legible (ej. `FE-00123456`). El que aparece en el documento fiscal       |
| `returns_total`          | NUMERIC(14,2) |               | 1.0.0 | Suma del valor de todas las devoluciones asociadas a este pedido                            |
| `net_total`              | NUMERIC(14,2) |               | 1.0.0 | Valor neto final = `invoice_total` - `returns_total`. Base para calcular todas las metas y KPIs |
| `payment_link`           | TEXT          |               | 1.0.0 | URL de enlace de pago generado para este pedido. Gancho para integracion futura de pagos electronicos |
| `notes`                  | TEXT          |               | 1.0.0 | Observaciones del pedido ingresadas por el vendedor o el agente                             |
| `created_at`             | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                       |
| `updated_at`             | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                                      |

---

## 20. `order_items`

Lineas de detalle de un pedido. Registra las tres capas (pedido, factura, devolucion) a nivel de cada producto/embalaje.

| Campo                   | Tipo          | Restricciones | v     | Descripcion                                                                              |
|-------------------------|---------------|---------------|-------|------------------------------------------------------------------------------------------|
| `id`                    | UUID          | PK, NN        | 1.0.0 | Identificador unico de la linea                                                          |
| `order_id`              | UUID          | FK, NN, IDX   | 1.0.0 | Pedido al que pertenece la linea                                                         |
| `tenant_id`             | UUID          | FK, NN, IDX   | 1.0.0 | Tenant (desnormalizado para agilizar consultas analiticas por tenant)                    |
| `product_packaging_id`  | UUID          | FK, NN, IDX   | 1.0.0 | Embalaje del producto vendido                                                            |
| `promotion_id`          | UUID          | FK, IDX       | 1.0.0 | Promocion que genero esta linea. NULL si es una venta normal sin oferta                  |
| `item_role`             | ENUM          | NN            | 1.0.0 | Rol del item en la transaccion: `regular` (venta normal), `trigger` (activo la promocion), `gift` (entregado como regalo/bonificacion), `combo_item` (parte de un combo). Permite descomponer analitica de ofertas |
| `is_product_seed`       | BOOLEAN       | NN            | 1.0.0 | TRUE si este es el primer registro de este producto en este cliente (fue "sembrado" via regalo de promocion). Permite medir tasa de recompra posterior al sembrado |
| `ordered_qty`           | NUMERIC(10,3) | NN            | 1.0.0 | Cantidad solicitada en el pedido original en unidades del embalaje                       |
| `ordered_unit_price`    | NUMERIC(14,2) | NN            | 1.0.0 | Precio unitario del embalaje al momento de tomar el pedido (precio de lista vigente)     |
| `ordered_discount`      | NUMERIC(14,2) |               | 1.0.0 | Descuento aplicado a esta linea en el pedido (por promocion u otro)                      |
| `ordered_line_total`    | NUMERIC(14,2) | NN            | 1.0.0 | Total de la linea en el pedido = (`ordered_qty` * `ordered_unit_price`) - `ordered_discount` |
| `invoiced_qty`          | NUMERIC(10,3) |               | 1.0.0 | Cantidad efectivamente facturada por el ERP. Puede ser menor al pedido por quiebre de stock |
| `invoiced_unit_price`   | NUMERIC(14,2) |               | 1.0.0 | Precio unitario segun la factura del ERP. Puede diferir del pedido por ajustes de precio en bodega |
| `invoiced_discount`     | NUMERIC(14,2) |               | 1.0.0 | Descuento aplicado en la factura del ERP                                                 |
| `invoiced_line_total`   | NUMERIC(14,2) |               | 1.0.0 | Total de la linea segun la factura = (`invoiced_qty` * `invoiced_unit_price`) - `invoiced_discount` |
| `returned_qty`          | NUMERIC(10,3) |               | 1.0.0 | Cantidad devuelta de este producto. Suma de todas las devoluciones de este item          |
| `returned_value`        | NUMERIC(14,2) |               | 1.0.0 | Valor monetario total devuelto de este item                                              |
| `net_qty`               | NUMERIC(10,3) |               | 1.0.0 | Cantidad neta entregada = `invoiced_qty` - `returned_qty`. Base para analitica de volumen |
| `net_value`             | NUMERIC(14,2) |               | 1.0.0 | Valor neto de la linea = `invoiced_line_total` - `returned_value`. Base para metas y KPIs|
| `created_at`            | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                    |
| `updated_at`            | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                                   |

---

## 21. `order_returns`

Cabecera de una devolucion. Puede haber multiples devoluciones para un mismo pedido (devoluciones parciales en diferentes momentos).

| Campo              | Tipo          | Restricciones | v     | Descripcion                                                                      |
|--------------------|---------------|---------------|-------|----------------------------------------------------------------------------------|
| `id`               | UUID          | PK, NN        | 1.0.0 | Identificador unico de la devolucion                                             |
| `order_id`         | UUID          | FK, NN, IDX   | 1.0.0 | Pedido original al que esta asociada la devolucion                               |
| `tenant_id`        | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                          |
| `source`           | ENUM          | NN            | 1.0.0 | Canal por el que llego la devolucion: `erp_api`, `erp_csv`, `erp_xml`            |
| `return_date`      | DATE          | NN            | 1.0.0 | Fecha en que se registro la devolucion en el ERP                                 |
| `return_reference` | VARCHAR(100)  |               | 1.0.0 | Numero o referencia de la nota credito en el ERP externo                         |
| `total_value`      | NUMERIC(14,2) | NN            | 1.0.0 | Valor total de la devolucion                                                     |
| `notes`            | TEXT          |               | 1.0.0 | Observaciones sobre la devolucion                                                |
| `created_at`       | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                            |

---

## 22. `order_return_items`

Detalle de productos incluidos en una devolucion.

| Campo                  | Tipo          | Restricciones | v     | Descripcion                                                         |
|------------------------|---------------|---------------|-------|---------------------------------------------------------------------|
| `id`                   | UUID          | PK, NN        | 1.0.0 | Identificador unico de la linea de devolucion                       |
| `return_id`            | UUID          | FK, NN, IDX   | 1.0.0 | Devolucion a la que pertenece la linea                              |
| `order_item_id`        | UUID          | FK, NN, IDX   | 1.0.0 | Linea del pedido original que se esta devolviendo                   |
| `product_packaging_id` | UUID          | FK, NN, IDX   | 1.0.0 | Embalaje del producto devuelto                                      |
| `qty`                  | NUMERIC(10,3) | NN            | 1.0.0 | Cantidad devuelta en unidades del embalaje                          |
| `unit_price`           | NUMERIC(14,2) | NN            | 1.0.0 | Precio unitario al que se reconoce la devolucion (generalmente igual al precio facturado) |
| `total_value`          | NUMERIC(14,2) | NN            | 1.0.0 | Valor total de esta linea de devolucion = `qty` * `unit_price`      |
| `reason`               | TEXT          |               | 1.0.0 | Motivo de la devolucion de este producto (ej. producto vencido, averia en transporte) |
| `created_at`           | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                               |

---

## 23. `erp_imports`

Registro de auditoria de todas las integraciones entrantes desde el ERP externo (facturas y devoluciones) por cualquier canal.

| Campo           | Tipo        | Restricciones | v     | Descripcion                                                                          |
|-----------------|-------------|---------------|-------|--------------------------------------------------------------------------------------|
| `id`            | UUID        | PK, NN        | 1.0.0 | Identificador unico del evento de importacion                                        |
| `tenant_id`     | UUID        | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece la importacion                                               |
| `import_type`   | ENUM        | NN            | 1.0.0 | Tipo de documento importado: `invoice` (factura), `return` (devolucion/nota credito) |
| `source`        | ENUM        | NN            | 1.0.0 | Canal de recepcion: `api` (webhook POST del ERP), `csv` (archivo CSV subido), `xml` (archivo XML subido) |
| `filename`      | VARCHAR(500)|               | 1.0.0 | Nombre del archivo subido. NULL para importaciones via API                           |
| `raw_data`      | JSONB       |               | 1.0.0 | Contenido original del documento recibido (normalizado a JSON). Permite reprocesar en caso de error |
| `status`        | ENUM        | NN, IDX       | 1.0.0 | Estado del procesamiento: `pending` (recibido, en cola), `processed` (aplicado correctamente), `error` (fallo en procesamiento) |
| `error_details` | TEXT        |               | 1.0.0 | Descripcion del error si el procesamiento fallo                                      |
| `processed_at`  | TIMESTAMPTZ |               | 1.0.0 | Fecha y hora en que se proceso exitosamente la importacion                           |
| `created_at`    | TIMESTAMPTZ | NN            | 1.0.0 | Fecha y hora de recepcion del documento                                              |

---

## 24. `sales_goals`

Metas de venta asignadas a vendedores o a la empresa como conjunto. Las metas se calculan siempre sobre `net_total` (valor entregado neto).

| Campo            | Tipo          | Restricciones | v     | Descripcion                                                                              |
|------------------|---------------|---------------|-------|------------------------------------------------------------------------------------------|
| `id`             | UUID          | PK, NN        | 1.0.0 | Identificador unico de la meta                                                           |
| `tenant_id`      | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                                  |
| `name`           | VARCHAR(200)  | NN            | 1.0.0 | Nombre descriptivo de la meta (ej. `Meta Volumen Agosto - Vendedor Norte`)               |
| `description`    | TEXT          |               | 1.0.0 | Descripcion de la meta y su objetivo comercial                                           |
| `assigned_to`    | ENUM          | NN            | 1.0.0 | Nivel de asignacion: `salesperson` (meta individual del vendedor), `company` (meta global que puede irrigar beneficios individuales) |
| `salesperson_id`      | UUID          | FK, IDX       | 1.0.0 | Vendedor al que se le asigna la meta. NULL si `assigned_to = company`                    |
| `parent_goal_id` | UUID          | FK            | 1.0.0 | Meta global de la que se desprende esta meta individual. Permite construir jerarquia empresa → vendedor |
| `goal_type`      | ENUM          | NN            | 1.0.0 | Tipo de indicador: `volume_sales` ($ ventas netas), `order_count` (# pedidos), `effectiveness_pct` (% visitas efectivas), `net_sales_pct` (% venta neta efectiva), `new_clients_pct` (% clientes nuevos), `venta_zero_conversion` (conversion de clientes Venta 0), `mandatory_product_sales` (venta de infaltables), `offer_sales_value` ($ en ofertas), `offer_sales_count` (# ofertas vendidas), `clients_impacted` (# clientes con al menos 1 pedido) |
| `scope_level`    | ENUM          |               | 1.0.0 | Nivel del catalogo al que aplica la meta: `all` (toda la venta), `brand`, `category`, `subcategory`, `product`. Permite crear metas especificas por producto o linea |
| `scope_id`       | UUID          |               | 1.0.0 | ID de la entidad en `scope_level`. NULL cuando `scope_level = all`                       |
| `target_value`   | NUMERIC(14,2) | NN            | 1.0.0 | Valor objetivo de la meta (pesos para monetarias, numero para conteos, porcentaje para ratios) |
| `period_type`    | ENUM          | NN            | 1.0.0 | Tipo de periodo: `monthly` (mes calendario), `weekly` (semana), `custom` (rango definido manualmente) |
| `period_start`   | DATE          | NN            | 1.0.0 | Fecha de inicio del periodo de la meta                                                   |
| `period_end`     | DATE          | NN            | 1.0.0 | Fecha de fin del periodo de la meta                                                      |
| `is_active`      | BOOLEAN       | NN            | 1.0.0 | Indica si la meta esta activa                                                            |
| `created_at`     | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de creacion del registro                                                    |
| `updated_at`     | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima modificacion                                                   |

---

## 25. `goal_progress`

Snapshots periodicos del avance de cada meta. Permite graficar la evolucion del cumplimiento y alimentar los reportes del agente.

| Campo           | Tipo          | Restricciones | v     | Descripcion                                                                |
|-----------------|---------------|---------------|-------|----------------------------------------------------------------------------|
| `id`            | UUID          | PK, NN        | 1.0.0 | Identificador unico del snapshot                                           |
| `goal_id`       | UUID          | FK, NN, IDX   | 1.0.0 | Meta a la que corresponde este snapshot                                    |
| `snapshot_date` | DATE          | NN, IDX       | 1.0.0 | Fecha en que se tomo el snapshot                                           |
| `current_value` | NUMERIC(14,2) | NN            | 1.0.0 | Valor acumulado de la meta hasta la fecha del snapshot                     |
| `target_value`  | NUMERIC(14,2) | NN            | 1.0.0 | Valor objetivo de la meta (copiado del goal para tener trazabilidad historica si el objetivo cambia) |
| `pct_achieved`  | NUMERIC(6,2)  | NN            | 1.0.0 | Porcentaje de cumplimiento = (`current_value` / `target_value`) * 100      |
| `calculated_at` | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora en que se realizo el calculo (puede diferir del snapshot_date)|

---

## 26. `client_product_affinities`

Historial de relacion entre cada cliente y cada producto. Base de conocimiento del agente para recomendaciones, deteccion de quiebres y seguimiento de siembra de productos.

| Campo                   | Tipo          | Restricciones | v     | Descripcion                                                                            |
|-------------------------|---------------|---------------|-------|----------------------------------------------------------------------------------------|
| `id`                    | UUID          | PK, NN        | 1.0.0 | Identificador unico del registro de afinidad                                           |
| `tenant_id`             | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                                |
| `client_id`             | UUID          | FK, NN, IDX   | 1.0.0 | Cliente del registro                                                                   |
| `product_id`            | UUID          | FK, NN, IDX   | 1.0.0 | Producto del registro                                                                  |
| `first_purchased_at`    | DATE          |               | 1.0.0 | Fecha de la primera compra neta de este producto por este cliente                      |
| `last_purchased_at`     | DATE          |               | 1.0.0 | Fecha de la ultima compra neta. Permite detectar quiebres cuando supera el intervalo tipico |
| `total_net_units`       | NUMERIC(12,3) |               | 1.0.0 | Total de unidades base netas compradas historicamente                                  |
| `total_net_value`       | NUMERIC(14,2) |               | 1.0.0 | Valor neto total historico de este producto en este cliente                            |
| `reorder_count`         | INTEGER       |               | 1.0.0 | Numero de pedidos distintos en que aparece este producto. Mide frecuencia de recompra  |
| `avg_days_between_orders`| NUMERIC(6,1) |               | 1.0.0 | Promedio de dias entre pedidos de este producto. Permite al agente predecir cuando el cliente lo va a necesitar de nuevo |
| `was_seeded_by_promo`   | BOOLEAN       | NN            | 1.0.0 | TRUE si el primer registro de este producto en el cliente fue un regalo de promocion. Habilita analisis de efectividad de siembra |
| `seed_promo_id`         | UUID          | FK            | 1.0.0 | Promocion que realizo la siembra inicial del producto en el cliente                     |
| `updated_at`            | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora de la ultima actualizacion de los acumulados                              |

---

## 27. `daily_sales_snapshots`

Pre-agregados diarios por vendedor y ruta para acelerar la generacion de reportes y briefings del agente sin recalcular sobre ordenes.

| Campo                   | Tipo          | Restricciones | v     | Descripcion                                                                   |
|-------------------------|---------------|---------------|-------|-------------------------------------------------------------------------------|
| `id`                    | UUID          | PK, NN        | 1.0.0 | Identificador unico del snapshot                                              |
| `tenant_id`             | UUID          | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                       |
| `snapshot_date`         | DATE          | NN, IDX       | 1.0.0 | Fecha del dia resumido                                                        |
| `salesperson_id`             | UUID          | FK, NN, IDX   | 1.0.0 | Vendedor al que corresponde el resumen                                        |
| `route_id`              | UUID          | FK, IDX       | 1.0.0 | Ruta operada ese dia                                                          |
| `orders_count`          | INTEGER       |               | 1.0.0 | Numero de pedidos tomados en el dia                                           |
| `clients_planned`       | INTEGER       |               | 1.0.0 | Numero de clientes programados para visitar ese dia en la ruta                |
| `clients_visited`       | INTEGER       |               | 1.0.0 | Numero de clientes con visita registrada (efectiva o no)                      |
| `clients_impacted`      | INTEGER       |               | 1.0.0 | Numero de clientes con al menos un pedido tomado                              |
| `effectiveness_pct`     | NUMERIC(5,2)  |               | 1.0.0 | Porcentaje de efectividad del dia = (`clients_impacted` / `clients_planned`) * 100 |
| `ordered_total`         | NUMERIC(14,2) |               | 1.0.0 | Suma de `ordered_total` de todos los pedidos del dia                          |
| `invoiced_total`        | NUMERIC(14,2) |               | 1.0.0 | Suma de `invoice_total` de todas las facturas del dia                         |
| `returns_total`         | NUMERIC(14,2) |               | 1.0.0 | Suma de devoluciones del dia                                                  |
| `net_total`             | NUMERIC(14,2) |               | 1.0.0 | Venta neta del dia = `invoiced_total` - `returns_total`                       |
| `new_clients_count`     | INTEGER       |               | 1.0.0 | Clientes nuevos con primer pedido en el dia                                   |
| `venta_zero_converted`  | INTEGER       |               | 1.0.0 | Clientes que eran Venta 0 y generaron su primer pedido en el dia              |
| `calculated_at`         | TIMESTAMPTZ   | NN            | 1.0.0 | Fecha y hora en que se genero el snapshot                                     |

---

## 28. `wa_conversations`

Estado actual de cada conversacion de WhatsApp. Gestiona la ventana de 24 horas de Meta y el contexto del agente.

| Campo                | Tipo        | Restricciones | v     | Descripcion                                                                         |
|----------------------|-------------|---------------|-------|-------------------------------------------------------------------------------------|
| `id`                 | UUID        | PK, NN        | 1.0.0 | Identificador unico de la conversacion                                              |
| `tenant_id`          | UUID        | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                             |
| `phone_number`       | VARCHAR(20) | NN, IDX       | 1.0.0 | Numero de telefono del interlocutor en formato E.164                                |
| `contact_type`       | ENUM        |               | 1.0.0 | Tipo de contacto identificado: `salesperson` (vendedor en tabla users), `client` (tendero en tabla clients), `unknown` (no identificado) |
| `contact_id`         | UUID        | IDX           | 1.0.0 | ID del vendedor o cliente identificado. NULL si `contact_type = unknown`            |
| `state`              | ENUM        | NN            | 1.0.0 | Estado de la maquina de estados de la conversacion: `idle`, `greeting`, `taking_order`, `confirming_order`, `closed` |
| `context`            | JSONB       |               | 1.0.0 | Contexto serializado de la conversacion actual (orden en construccion, productos mencionados, etc.) |
| `recent_messages`    | JSONB       |               | 1.0.0 | Ultimos 10 mensajes de la conversacion en formato resumido para contexto del agente. Ventana deslizante |
| `last_message_at`    | TIMESTAMPTZ | IDX           | 1.0.0 | Fecha y hora del ultimo mensaje. Determina si la ventana de 24h de Meta sigue abierta |
| `window_expires_at`  | TIMESTAMPTZ |               | 1.0.0 | Fecha y hora de expiracion de la ventana de 24h. Calculada como `last_message_at + 24h` |
| `created_at`         | TIMESTAMPTZ | NN            | 1.0.0 | Fecha y hora de inicio de la conversacion                                           |
| `updated_at`         | TIMESTAMPTZ | NN            | 1.0.0 | Fecha y hora de la ultima actualizacion                                             |

---

## 29. `message_logs`

Registro inmutable de todos los mensajes enviados y recibidos via WhatsApp.

| Campo            | Tipo        | Restricciones | v     | Descripcion                                                                      |
|------------------|-------------|---------------|-------|----------------------------------------------------------------------------------|
| `id`             | UUID        | PK, NN        | 1.0.0 | Identificador unico del mensaje                                                  |
| `tenant_id`      | UUID        | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                          |
| `conversation_id`| UUID        | FK, NN, IDX   | 1.0.0 | Conversacion a la que pertenece el mensaje                                       |
| `direction`      | ENUM        | NN            | 1.0.0 | Direccion del mensaje: `inbound` (recibido del usuario), `outbound` (enviado por el agente) |
| `message_type`   | ENUM        | NN            | 1.0.0 | Tipo de mensaje: `text`, `image`, `audio`, `document`, `template`, `interactive` |
| `content`        | TEXT        |               | 1.0.0 | Contenido textual del mensaje                                                    |
| `media_url`      | TEXT        |               | 1.0.0 | URL del archivo multimedia si el mensaje contiene imagen, audio o documento      |
| `wa_message_id`  | VARCHAR(100)| UK, IDX       | 1.0.0 | ID unico del mensaje en la plataforma de WhatsApp (Meta). Usado para deduplicacion y seguimiento de estado |
| `status`         | ENUM        |               | 1.0.0 | Estado del mensaje saliente: `sent`, `delivered`, `read`, `failed`               |
| `created_at`     | TIMESTAMPTZ | NN, IDX       | 1.0.0 | Fecha y hora de creacion del registro (envio o recepcion)                        |

---

## 30. `notification_schedules`

Programacion de notificaciones automaticas enviadas por el agente segun el flujo diario.

| Campo              | Tipo        | Restricciones | v     | Descripcion                                                                        |
|--------------------|-------------|---------------|-------|------------------------------------------------------------------------------------|
| `id`               | UUID        | PK, NN        | 1.0.0 | Identificador unico de la notificacion programada                                  |
| `tenant_id`        | UUID        | FK, NN, IDX   | 1.0.0 | Tenant al que pertenece                                                            |
| `notification_type`| ENUM        | NN            | 1.0.0 | Tipo de notificacion: `morning_briefing` (briefing 06:30), `pre_visit` (aviso pre-visita al tendero), `daily_summary` (resumen 18:30 al vendedor), `followup_unvisited` (follow-up 19:00 clientes no visitados), `performance_report` (reporte 20:00 al vendedor), `management_daily` (reporte gerencia 07:00), `management_weekly` (reporte semanal gerencia 07:30 lunes) |
| `recipient_id`     | UUID        | NN, IDX       | 1.0.0 | ID del destinatario (vendedor, cliente o gerente segun el tipo)                    |
| `recipient_type`   | ENUM        | NN            | 1.0.0 | Tipo de destinatario: `salesperson`, `client`, `manager`                                |
| `scheduled_at`     | TIMESTAMPTZ | NN, IDX       | 1.0.0 | Fecha y hora programada de envio                                                   |
| `status`           | ENUM        | NN, IDX       | 1.0.0 | Estado: `pending` (en cola), `sent` (enviado exitosamente), `failed` (fallo el envio), `skipped` (omitido por condicion de negocio) |
| `payload`          | JSONB       |               | 1.0.0 | Datos adicionales necesarios para generar el contenido de la notificacion (ej. route_id, visit_id) |
| `error_details`    | TEXT        |               | 1.0.0 | Descripcion del error si el envio fallo                                            |
| `sent_at`          | TIMESTAMPTZ |               | 1.0.0 | Fecha y hora real en que se envio la notificacion                                  |
| `created_at`       | TIMESTAMPTZ | NN            | 1.0.0 | Fecha y hora de creacion del registro                                              |

---

## 31. `goal_benefits`

Beneficios que el vendedor recibe al alcanzar (total o parcialmente) una meta. Puede haber multiples niveles de beneficio por meta (ej. 80% de cumplimiento desbloquea un bono parcial, 100% desbloquea el bono completo y un premio adicional). El agente usa esta tabla para motivar al vendedor mostrando en tiempo real cuanto le falta para desbloquear el siguiente beneficio.

| Campo                       | Tipo          | Restricciones | v     | Descripcion                                                                                      |
|-----------------------------|---------------|---------------|-------|--------------------------------------------------------------------------------------------------|
| `id`                        | UUID          | PK, NN        | 1.1.0 | Identificador unico del beneficio                                                                |
| `tenant_id`                 | UUID          | FK, NN, IDX   | 1.1.0 | Tenant al que pertenece                                                                          |
| `goal_id`                   | UUID          | FK, NN, IDX   | 1.1.0 | Meta a la que esta asociado el beneficio                                                         |
| `name`                      | VARCHAR(200)  | NN            | 1.1.0 | Nombre del beneficio tal como se le muestra al vendedor (ej. `Bono mensual`, `Premio viaje Cartagena`, `Comision extra 2%`) |
| `description`               | TEXT          |               | 1.1.0 | Descripcion detallada del beneficio, condiciones adicionales o instrucciones de redención        |
| `benefit_type`              | ENUM          | NN            | 1.1.0 | Tipo de beneficio: `commission_pct` (comision como % sobre la venta neta del periodo), `commission_fixed` (comision en valor fijo), `bonus_fixed` (bono en efectivo de monto fijo), `prize` (premio no monetario: viaje, electrodomestico, gift card), `recognition` (reconocimiento publico: titulo, insignia, mencion), `other` (otro tipo definido en `description`) |
| `value`                     | NUMERIC(14,2) |               | 1.1.0 | Valor numerico del beneficio. Para `commission_pct`: el porcentaje (ej. `2.50`). Para `commission_fixed` o `bonus_fixed`: el monto en moneda del tenant. NULL para `prize`, `recognition` o `other` |
| `currency_code`             | CHAR(3)       |               | 1.1.0 | Codigo ISO 4217 de la moneda del beneficio monetario. Hereda del tenant si no se especifica      |
| `achievement_threshold_pct` | NUMERIC(5,2)  | NN            | 1.1.0 | Porcentaje de cumplimiento de la meta a partir del cual se desbloquea este beneficio (ej. `80.00` para el 80%). Permite definir beneficios escalonados: varias filas para la misma meta con diferentes umbrales |
| `is_active`                 | BOOLEAN       | NN            | 1.1.0 | Indica si el beneficio esta vigente y debe mostrarse al vendedor                                 |
| `created_at`                | TIMESTAMPTZ   | NN            | 1.1.0 | Fecha y hora de creacion del registro                                                            |
| `updated_at`                | TIMESTAMPTZ   | NN            | 1.1.0 | Fecha y hora de la ultima modificacion                                                           |

**Ejemplo de uso — beneficios escalonados:**

| Meta                    | `achievement_threshold_pct` | `benefit_type`  | `value` | `name`                      |
|-------------------------|-----------------------------|-----------------|---------|-----------------------------|
| Meta Volumen Agosto     | 80.00                       | bonus_fixed     | 150000  | Bono parcial $150.000       |
| Meta Volumen Agosto     | 100.00                      | bonus_fixed     | 300000  | Bono completo $300.000      |
| Meta Volumen Agosto     | 100.00                      | prize           | NULL    | Cena para dos               |
| Meta Infaltables Agosto | 100.00                      | commission_pct  | 1.50    | Comision extra 1.5%         |

---

## 38. `business_owners`

Propietarios de los establecimientos comerciales. Separa los datos personales/legales del dueño de los datos operativos del negocio. Un propietario puede tener uno o varios establecimientos registrados como clientes.

**Principio de transparencia:** el operador nunca gestiona esta tabla directamente. Al registrar o importar un cliente, el sistema verifica si ya existe un propietario con el mismo `document_number` en el tenant y lo vincula automáticamente, presentando solo una confirmación simple. En carga masiva, la descomposición es automática e invisible.

| Campo                | Tipo         | Restricciones      | v     | Descripcion                                                                                |
|----------------------|--------------|--------------------|-------|--------------------------------------------------------------------------------------------|
| `id`                 | UUID         | PK, NN             | 1.5.0 | Identificador unico del propietario                                                        |
| `tenant_id`          | UUID         | FK, NN, IDX        | 1.5.0 | Tenant al que pertenece                                                                    |
| `full_name`          | VARCHAR(200) | NN                 | 1.5.0 | Nombre completo del propietario tal como aparece en su documento de identidad              |
| `document_type`      | ENUM         | NN                 | 1.5.0 | Tipo de documento: `NIT` (empresas/personas juridicas), `CC` (cedula ciudadania), `CE` (cedula extranjeria), `PAS` (pasaporte), `RUT`. Determina el formato valido de `document_number` y `verification_digit` |
| `document_number`    | VARCHAR(20)  | NN, IDX            | 1.5.0 | Numero del documento. Unico por tenant — una misma CC/NIT no puede estar duplicada en el tenant aunque el propietario tenga multiples establecimientos |
| `verification_digit` | CHAR(1)      |                    | 1.5.0 | Digito de verificacion del NIT (aplica unicamente cuando `document_type = NIT` en Colombia) |
| `phone`              | VARCHAR(20)  | IDX                | 1.5.0 | Telefono personal del propietario en formato E.164. Es diferente al telefono del establecimiento (`clients.phone`). No puede coincidir con ningun `users.phone` del tenant (evita confundir propietario con vendedor). Se usa para contacto directo gerencial, no para interaccion con el agente |
| `email`              | VARCHAR(200) |                    | 1.5.0 | Correo electronico personal del propietario. Opcional                                      |
| `is_active`          | BOOLEAN      | NN                 | 1.5.0 | Indica si el propietario esta activo. Inactivar un propietario no inactiva sus establecimientos automaticamente |
| `created_at`         | TIMESTAMPTZ  | NN                 | 1.5.0 | Fecha y hora de creacion del registro                                                      |
| `updated_at`         | TIMESTAMPTZ  | NN                 | 1.5.0 | Fecha y hora de la ultima modificacion                                                     |

**Ejemplo — un propietario, multiples establecimientos:**

| `business_owners` | | `clients` | |
|---|---|---|---|
| Facundo Cabrales CC 75467823 | → | Ferretería La Casa del Carpintero | +573187351158 |
| (mismo registro) | → | Ferretería Libertador | +573173715849 |

---

## 32. `geo_countries`

Paises soportados por el sistema. Datos de referencia pre-cargados. Permite extender la plataforma a otros paises sin cambios de codigo.

| Campo          | Tipo         | Restricciones | v     | Descripcion                                                                       |
|----------------|--------------|---------------|-------|-----------------------------------------------------------------------------------|
| `id`           | UUID         | PK, NN        | 1.4.0 | Identificador unico del pais                                                      |
| `iso_code`     | CHAR(2)      | UK, NN        | 1.4.0 | Codigo ISO 3166-1 alpha-2 del pais (ej. `CO`, `PE`, `EC`, `CL`)                  |
| `name`         | VARCHAR(100) | NN            | 1.4.0 | Nombre del pais                                                                   |
| `phone_min_length` | INTEGER  | NN            | 1.4.0 | Longitud minima del numero de telefono en formato E.164 incluyendo el prefijo pais (ej. Colombia `+57XXXXXXXXXX` = 13 caracteres) |
| `phone_max_length` | INTEGER  | NN            | 1.4.0 | Longitud maxima del numero de telefono en formato E.164                           |
| `currency_code`| CHAR(3)      | NN            | 1.4.0 | Moneda predeterminada del pais (ISO 4217)                                         |
| `is_active`    | BOOLEAN      | NN            | 1.4.0 | Indica si el pais esta habilitado en la plataforma                                |

---

## 33. `geo_departments`

Departamentos de Colombia segun el DANE. Pre-cargados desde el archivo oficial. Equivalente a estado/provincia en otros paises.

| Campo          | Tipo         | Restricciones | v     | Descripcion                                                                       |
|----------------|--------------|---------------|-------|-----------------------------------------------------------------------------------|
| `id`           | UUID         | PK, NN        | 1.4.0 | Identificador unico del departamento                                              |
| `country_id`   | UUID         | FK, NN, IDX   | 1.4.0 | Pais al que pertenece                                                             |
| `dane_code`    | CHAR(2)      | UK, NN        | 1.4.0 | Codigo DANE del departamento (2 digitos, ej. `13` para Bolivar). Fuente: DIVIPOLA |
| `name`         | VARCHAR(100) | NN            | 1.4.0 | Nombre oficial del departamento segun DANE (ej. `BOLÍVAR`)                        |

---

## 34. `geo_municipalities`

Municipios de Colombia segun el DANE (1.123 registros). Pre-cargados. Equivale a `tbl_ciudad` en el SQL del DANE.

| Campo           | Tipo         | Restricciones | v     | Descripcion                                                                      |
|-----------------|--------------|---------------|-------|----------------------------------------------------------------------------------|
| `id`            | UUID         | PK, NN        | 1.4.0 | Identificador unico del municipio                                                |
| `department_id` | UUID         | FK, NN, IDX   | 1.4.0 | Departamento al que pertenece                                                    |
| `dane_code`     | CHAR(5)      | UK, NN        | 1.4.0 | Codigo DANE del municipio (5 digitos: 2 dpto + 3 municipio, ej. `13430` para Magangue). Fuente: DIVIPOLA |
| `name`          | VARCHAR(200) | NN            | 1.4.0 | Nombre oficial del municipio segun DANE (ej. `MAGANGUÉ`)                         |

---

## 35. `geo_populated_centers`

Centros poblados de Colombia segun el DANE (9.235 registros). Nivel mas granular del catalogo geografico oficial. Pre-cargados. Equivale a `tbl_centropoblado` en el SQL del DANE.

| Campo               | Tipo         | Restricciones | v     | Descripcion                                                                    |
|---------------------|--------------|---------------|-------|--------------------------------------------------------------------------------|
| `id`                | UUID         | PK, NN        | 1.4.0 | Identificador unico del centro poblado                                         |
| `municipality_id`   | UUID         | FK, NN, IDX   | 1.4.0 | Municipio al que pertenece                                                     |
| `divipola`          | CHAR(8)      | UK, NN        | 1.4.0 | Codigo DIVIPOLA completo del centro poblado (8 digitos: 2 dpto + 3 mpio + 3 centro poblado, ej. `13430000` para la cabecera de Magangue). Es el identificador unico nacional |
| `name`              | VARCHAR(200) | NN            | 1.4.0 | Nombre oficial del centro poblado segun DANE                                   |
| `type`              | ENUM         | NN            | 1.4.0 | Categoria DANE: `CM` (Cabecera Municipal), `C` (Corregimiento), `CAS` (Caserio), `CP` (Centro Poblado no categorizado), `IPD` (Inspeccion de Policia Departamental), `IPM` (Inspeccion de Policia Municipal), `IP` (Inspeccion de Policia), `TEBF` (Territorio Etnico) |

---

## 36. `geo_neighborhoods`

Barrios y sectores gestionados por el tenant. Se vinculan al centro poblado (no a la ciudad) para evitar homonimos entre municipios. No forman parte del catalogo DANE — los crea el operador.

| Campo                  | Tipo         | Restricciones | v     | Descripcion                                                                   |
|------------------------|--------------|---------------|-------|-------------------------------------------------------------------------------|
| `id`                   | UUID         | PK, NN        | 1.4.0 | Identificador unico del barrio                                                |
| `tenant_id`            | UUID         | FK, NN, IDX   | 1.4.0 | Tenant que creo el barrio                                                     |
| `populated_center_id`  | UUID         | FK, NN, IDX   | 1.4.0 | Centro poblado al que pertenece el barrio. Usar el centro poblado (no solo el municipio) garantiza que dos barrios con el mismo nombre en distintas ciudades no se confundan |
| `name`                 | VARCHAR(200) | NN            | 1.4.0 | Nombre del barrio o sector (ej. `El Progreso`, `La Ensenada`)                 |
| `is_active`            | BOOLEAN      | NN            | 1.4.0 | Indica si el barrio esta vigente                                               |
| `created_at`           | TIMESTAMPTZ  | NN            | 1.4.0 | Fecha y hora de creacion del registro                                         |

---

## 37. `client_typologies`

Tipologias de establecimiento configurables por tenant. Reemplaza el ENUM fijo `typology` de v1.0.0. Permite agregar tipos nuevos (ej. Ferreteria) sin cambios de codigo. El sistema sugiere la tipologia al crear un cliente basandose en palabras clave del nombre del negocio, pero el operador decide si acepta, corrige o ignora la sugerencia.

| Campo          | Tipo         | Restricciones | v     | Descripcion                                                                       |
|----------------|--------------|---------------|-------|-----------------------------------------------------------------------------------|
| `id`           | UUID         | PK, NN        | 1.4.0 | Identificador unico de la tipologia                                               |
| `tenant_id`    | UUID         | FK, NN, IDX   | 1.4.0 | Tenant al que pertenece                                                           |
| `code`         | VARCHAR(50)  | NN            | 1.4.0 | Codigo interno de la tipologia (ej. `tienda_barrio`, `panaderia`, `ferreteria`). Usado por el agente para personalizar su tono e interaccion |
| `name`         | VARCHAR(200) | NN            | 1.4.0 | Nombre legible de la tipologia para mostrar en interfaces (ej. `Tienda de Barrio`, `Panaderia`, `Ferreteria`) |
| `keywords`     | JSONB        |               | 1.4.0 | Array de palabras clave para deteccion automatica en el nombre del negocio (ej. `["panaderia","panderia","pan"]`). El sistema las usa para sugerir la tipologia correcta. El operador decide si acepta la sugerencia |
| `is_active`    | BOOLEAN      | NN            | 1.4.0 | Indica si la tipologia esta disponible para asignar                               |
| `created_at`   | TIMESTAMPTZ  | NN            | 1.4.0 | Fecha y hora de creacion del registro                                             |
| `updated_at`   | TIMESTAMPTZ  | NN            | 1.4.0 | Fecha y hora de la ultima modificacion                                            |

---

## Glosario de Terminos de Negocio

| Termino              | Definicion                                                                                              |
|----------------------|---------------------------------------------------------------------------------------------------------|
| **Venta 0**          | Cliente registrado en la base de datos que nunca ha generado un pedido facturado y entregado. Representa una oportunidad comercial activa |
| **Infaltable / Imperdonable** | Producto cuya venta es obligatoria en cada visita segun la estrategia comercial del periodo. Su no venta afecta indicadores de efectividad |
| **Siembra (Seed)**   | Estrategia de introducir un producto nuevo en un cliente a traves de un regalo en una promocion, con el objetivo de generar recompra sostenida |
| **Fill Rate**        | Porcentaje de unidades facturadas sobre unidades pedidas. Mide la capacidad de surtido de la bodega     |
| **Efectividad**      | Porcentaje de visitas planificadas que resultaron en un pedido. Indicador clave de desempeno del vendedor|
| **Venta Neta**       | Valor facturado menos devoluciones. Base de calculo para todas las metas y KPIs del sistema             |
| **Delta Pedido/Factura** | Diferencia entre lo solicitado en el pedido y lo efectivamente facturado (en cantidad o precio)    |
| **Codificar**        | Lograr que un producto quede como parte del surtido habitual de un establecimiento                      |
| **Canal Tradicional**| Tiendas de barrio, superetes, panaderias y demas establecimientos de comercio minorista independiente   |
| **Tendero**          | Propietario o encargado de una tienda de barrio u otro establecimiento del canal tradicional            |
| **Embalaje**         | Unidad de venta de un producto (unidad, sixpack, caja, display, master). Cada nivel tiene EAN y precio propio |
| **Ruta**             | Conjunto de clientes agrupados geograficamente que un vendedor visita en dias especificos               |
| **Briefing**         | Resumen matutino que el agente envia al vendedor con informacion clave antes de iniciar su jornada      |
| **Beneficio de Meta**| Incentivo (bono, comision, premio, reconocimiento) que el vendedor recibe al alcanzar un umbral de cumplimiento de una meta. El agente lo usa activamente para motivar al vendedor mostrando cuanto le falta para desbloquear el proximo beneficio |
| **Propietario**      | Persona natural o juridica duena de uno o varios establecimientos comerciales. Sus datos legales (CC/NIT, nombre) se almacenan una sola vez en `business_owners` y se vinculan a cada establecimiento. El propietario puede tener telefono personal distinto al de cada local |
| **DANE**             | Departamento Administrativo Nacional de Estadistica de Colombia. Autoridad oficial que define y codifica la division politico-administrativa del pais (DIVIPOLA) |
| **DIVIPOLA**         | Division Politico Administrativa de Colombia. Codigo oficial DANE de 8 digitos que identifica unicamente cada centro poblado del pais (2 dpto + 3 mpio + 3 centro poblado) |
| **Centro Poblado**   | Cuarto nivel de la jerarquia geografica colombiana segun DANE. Puede ser Cabecera Municipal (CM), Corregimiento (C), Caserio (CAS), entre otros. El barrio se ubica dentro de un centro poblado |
| **Zona de Invasion** | Asentamiento informal sin nomenclatura oficial. Los negocios en estas zonas pueden no tener direccion convencional; se identifican unicamente por coordenadas GPS |
| **Geocodificacion**  | Proceso de convertir una direccion de texto en coordenadas GPS (latitud/longitud). En este sistema se dispara automaticamente despues de que el operador valida y aprueba la direccion normalizada |
| **Dia de Entrega**   | Dia(s) de la semana en que el camion de despacho surte a los clientes de la ruta. Puede ser diferente al dia de visita. El agente lo usa para informar al cliente cuando llega su pedido y para gestionar el cierre de pedidos antes del corte |
| **Hora de Corte**    | Hora limite (por dia) antes de la cual debe cerrarse un pedido para ser incluido en el proximo despacho. Configurada dentro de `daily_schedule` en la ruta. Pedidos posteriores al corte quedan para el siguiente ciclo de entrega |

---

*Documento generado para el proyecto Sales Agent SaaS*
*Proxima revision: al aprobarse cambios en el modelo de datos*
