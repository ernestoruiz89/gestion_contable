# Manual de Usuario — Gestión Contable

> **Versión del documento:** 1.0 · Marzo 2026
> **Plataforma:** Frappe Framework / ERPNext

---

## 1. Introducción al Sistema

### 1.1 Propósito

**Gestión Contable** es una aplicación construida sobre Frappe Framework y ERPNext que centraliza la operación completa de un despacho contable y firma de auditoría. El sistema permite:

- Gestionar la relación comercial con prospectos y clientes.
- Firmar contratos con alcances de servicio definidos por tipo (Contabilidad, Auditoría, Trabajo Especial, Consultoría).
- Ejecutar encargos: asignar tareas, controlar hitos, registrar horas y presupuesto.
- Solicitar y dar seguimiento a información requerida al cliente.
- Realizar auditorías formales con expediente, matriz de riesgos, papeles de trabajo y hallazgos.
- Preparar y emitir estados financieros con notas, ajustes y versiones.
- Facturar servicios y dar seguimiento a la cobranza.
- Aplicar gobierno corporativo: flujos de aprobación escalonados (Supervisor → Socio) en 16 tipos de documento.

### 1.2 Navegación Básica

Al iniciar sesión, acceda al **Panel de Gestión** desde la barra lateral o escribiendo "Panel de Gestión" en la barra de búsqueda.

[Imagen: Pantalla principal del Workspace "Panel de Gestión" mostrando las tarjetas de Operaciones, Comercial, Estados Financieros, Auditoría y Configuración]

El Panel organiza los accesos en tarjetas:

| Tarjeta | Contenido |
|---|---|
| **Operaciones** | Clientes, Periodos, Tareas, Documentos, Encargos, Servicios, Tarifas, Plantillas, Requerimientos, Entregables, Cobranza |
| **Comercial** | Leads, Opportunities, Quotations, Contracts ERPNext, Contratos Comerciales, Cambios de Alcance |
| **Estados Financieros** | Paquetes EEFF, Estados Financieros, Notas, Ajustes |
| **Auditoría** | Expedientes, Matriz Riesgo-Control, Papeles de Trabajo, Hallazgos, Informes Finales |
| **Panel** | Panel de Tareas, Resumen de Asignados, Seguimiento Auditoría, Rentabilidad y Cobranza, Reportes Gerenciales, Salida a Producción |
| **Configuración** | Configuración del Despacho Contable |

---

## 2. Guía por Roles

El sistema utiliza cinco roles personalizados. Cada usuario puede tener uno o varios roles según sus responsabilidades.

| Rol | ¿Quién lo usa? | Responsabilidades principales |
|---|---|---|
| **Socio del Despacho** | Socios o directores de la firma | Aprobación final de documentos, contratos y encargos. Acceso a reportes de rentabilidad y margen. Permite aprobar en el último nivel del workflow. |
| **Supervisor del Despacho** | Gerentes / supervisores | Revisión intermedia de documentos. Puede aprobar o devolver al nivel de Supervisor. Revisión de papeles de trabajo de auditoría. Control de encargos. |
| **Contador del Despacho** | Contadores / auditores operativos | Creación y gestión de clientes, encargos, contratos, periodos, estados financieros. Puede iniciar flujos de aprobación. |
| **Auxiliar Contable del Despacho** | Asistentes / capturistas | Captura de datos, carga de documentos, creación de papeles de trabajo y entregables. Sus ediciones están restringidas a campos operativos cuando el documento está en revisión. |
| **System Manager** | Administrador del sistema | Control total sobre la configuración, plantillas de correo y herramientas de desarrollo. |

[Imagen: Sección de administración de usuarios en Frappe mostrando la asignación de los roles del despacho]

---

## 3. Procesos Paso a Paso

---

### 3.1 Gestión Comercial

**Objetivo:** Registrar prospectos, oportunidades, cotizaciones y formalizar contratos de servicios profesionales con los clientes.

**Roles responsables:** Contador del Despacho, Supervisor del Despacho, Socio del Despacho.

#### 3.1.1 Registrar un Prospecto (Lead)

1. Desde el Panel de Gestión, en la tarjeta **Comercial**, haz clic en **Leads**.
2. Haz clic en **+ Nuevo**.
3. Llena los campos: Nombre del Lead, Compañía, Fuente, Correo y Teléfono.
4. Haz clic en **Guardar**.

[Imagen: Formulario de creación de un nuevo Lead en ERPNext mostrando los campos obligatorios]

#### 3.1.2 Crear una Oportunidad

1. Desde el Lead, haz clic en el botón **Crear > Oportunidad** o ve a **Comercial > Opportunities > + Nuevo**.
2. Selecciona el Lead asociado, tipo de oportunidad y los servicios de interés.
3. Haz clic en **Guardar**.

#### 3.1.3 Generar una Cotización

1. Desde la Oportunidad, haz clic en **Crear > Cotización** o ve a **Comercial > Quotations > + Nuevo**.
2. Selecciona el cliente o lead, agrega los ítems de servicio y define los montos estimados.
3. Haz clic en **Guardar** y luego **Enviar** para formalizar la cotización.

[Imagen: Formulario de Cotización con los ítems de servicios contables cotizados]

#### 3.1.4 Crear un Contrato Comercial

Este es el documento central que formaliza la relación con el cliente. Un contrato agrupa uno o varios **alcances por tipo de servicio** (Contabilidad, Auditoría, Trabajo Especial, Consultoría).

1. Ve a **Comercial > Contratos Comerciales > + Nuevo**.
2. Llena los campos obligatorios:
   - **Cliente** (vínculo a Cliente Contable — obligatorio).
   - **Fecha Inicio** (obligatorio).
   - **Fecha Fin** (opcional, para contratos con vigencia definida).
3. Opcionalmente vincula: **Lead**, **Opportunity**, **Quotation** y **Contract ERPNext** para mantener la trazabilidad del ciclo comercial.
4. Define la **Compañía**, **Moneda**, **Ejecutivo Comercial** y **Responsable Operativo**.
5. En la sección **SLA y Valores**, configura:
   - SLA de Respuesta (horas) y SLA de Entrega (días).
   - Marca **Renovación Automática** si el contrato se renueva al vencer.
6. En la tabla **Alcance por Servicio** (obligatoria), agrega al menos una línea definiendo el tipo de servicio, modalidad de honorario y tarifa correspondiente.

[Imagen: Formulario de Contrato Comercial mostrando las secciones de datos generales, SLA y la tabla de Alcances por Servicio]

7. Haz clic en **Guardar**. El contrato inicia en estado **Borrador**.
8. El sistema calculará automáticamente el **Valor Mensual Estimado** y **Valor Anual Estimado** a partir de los alcances.
9. También se asignará el **Formato de Impresión Sugerido** cuando todos los alcances activos son de un mismo tipo de servicio (ej. "Contrato Comercial Auditoría").

**Flujo de Aprobación del Contrato:**

> Borrador → **Enviar a Revisión** → Revisión Supervisor → **Enviar a Socio** → Revisión Socio → **Aprobar** → Aprobado

10. Para iniciar el flujo, haz clic en el botón de acción **Enviar a Revisión**.
11. El Supervisor revisará y hará clic en **Enviar a Socio** (o **Devolver** con comentarios).
12. El Socio revisará y hará clic en **Aprobar** (o **Devolver** con comentarios).
13. Una vez aprobado, cambia el Estado Comercial a **Vigente** para activar el contrato.

[Imagen: Barra de estado de aprobación del Contrato Comercial mostrando los botones "Enviar a Socio" y "Devolver"]

#### 3.1.5 Registrar un Cambio de Alcance

Cuando el contrato necesita modificaciones post-firma:

1. Desde el Contrato Comercial, haz clic en el vínculo lateral **Cambios de Alcance > + Nuevo**.
2. Selecciona el Contrato Comercial de origen.
3. En la tabla **Detalle de Cambios**, indica los servicios que se agregan, modifican o eliminan, junto con el impacto en honorarios.
4. Guarda y envía a revisión siguiendo el mismo flujo de aprobación.

[Imagen: Formulario de Cambio de Alcance Comercial con la tabla de detalle de cambios]

---

### 3.2 Gestión Operativa

**Objetivo:** Dar de alta clientes contables, abrir encargos o proyectos, asignar tareas y subir documentos de soporte.

**Roles responsables:** Contador del Despacho (creación), Auxiliar Contable (captura), Supervisor (supervisión), Socio (aprobación).

#### 3.2.1 Dar de Alta un Cliente Contable

1. Ve a **Operaciones > Clientes > + Nuevo**.
2. Llena los campos obligatorios:
   - **Cliente ERPNext**: Selecciona el Customer de ERPNext existente (la Identificación Fiscal se trae automáticamente).
3. Configura los datos del cliente:
   - **Estado**: Activo / Inactivo.
   - **Frecuencia de Cierre**: Mensual, Bimestral, Trimestral, Semestral o Anual.
   - **Régimen Fiscal**, **Clasificación de Riesgo**, **Moneda Preferida**.
4. En la sección **Responsables y SLA**, asigna:
   - Ejecutivo Comercial Default, Responsable Operativo Default y Responsable de Cobranza.
   - SLA Respuesta (horas) y SLA Entrega (días).
   - Canal de Envío Preferido (Correo, Portal, WhatsApp, etc.).
5. En la sección **Contacto General y Cobranza**, registra los datos de contacto, incluyendo contactos de facturación y cobranza.
6. En **Contactos Funcionales**, agrega una tabla con los contactos clave del cliente (Gerente, Contador, etc.).
7. En **Cobranza y Cumplimiento**, define los términos de pago, días de gracia, política de retención y confidencialidad.
8. En **Portal Cliente**, habilita si este cliente tendrá acceso al portal web de autoservicio.
9. Haz clic en **Guardar**.

[Imagen: Formulario de Cliente Contable mostrando las secciones de datos generales, responsables, contacto y portal]

#### 3.2.2 Crear un Periodo Contable

1. Ve a **Operaciones > Periodos > + Nuevo**.
2. Define el **Nombre del Periodo** (ej. "Enero 2026"), **Fecha de Inicio**, **Fecha de Fin**, **Cliente** y **Compañía**.
3. El estado inicial es **Abierto**. Cámbialo a **Cerrado** cuando finalice el periodo.
4. Haz clic en **Guardar**.

> **Validación:** La fecha de fin debe ser posterior a la fecha de inicio.

[Imagen: Formulario de Periodo Contable con los campos de nombre, fechas y estado]

#### 3.2.3 Abrir un Encargo Contable

El Encargo es el centro de la operación: agrupa tareas, horas, facturación y rentabilidad de un servicio para un cliente específico.

1. Ve a **Operaciones > Encargos > + Nuevo**.
2. Llena los campos:
   - **Cliente** (obligatorio) — vínculo a Cliente Contable.
   - **Contrato Comercial** — vínculo al contrato vigente.
   - **Plantilla de Encargo** — si aplica, selecciona una plantilla que preconfigura hitos.
   - **Servicio Contable** — el servicio específico (ej. "Contabilidad Mensual").
   - **Tipo de Servicio** — se calcula automáticamente: Contabilidad, Auditoría, Trabajo Especial o Consultoría.
   - **Proyecto ERPNext** — opcionalmente vincúlalo a un Project estándar para concentrar Timesheets.
3. En **Fechas y Responsable**:
   - Define Fecha de Inicio, Fecha Fin Estimada, Periodo de Referencia y Responsable.
4. En **Planeación y Presupuesto**:
   - Define Presupuesto de Horas y Presupuesto de Monto.
   - Los indicadores de avance (Hitos %, Consumo Horas %, Consumo Monto %) se calculan automáticamente.
5. En **Hitos del Encargo**:
   - Agrega las actividades clave con nombre, fecha estimada y estado.
6. En **Horas, Honorarios y Facturación**:
   - Define la Modalidad de Honorario: **Por Hora**, **Fijo** o **Mixto**.
   - Asigna Tarifa Hora, Honorario Fijo y Costo Interno Hora.
   - Los campos de horas registradas, monto pendiente y factura se actualizan automáticamente cuando se sincroniza con ERPNext.
7. Haz clic en **Guardar**.

[Imagen: Formulario de Encargo Contable mostrando las secciones de planeación, hitos y honorarios]

> **Nota:** Las secciones de **Rentabilidad y WIP**, **Margen** y **Cartera y Cobranza** se actualizan automáticamente cuando se registran Facturas de Venta, Pagos y Timesheets en ERPNext.

**Flujo de Aprobación del Encargo:**

> Borrador → Enviar a Revisión → Revisión Supervisor → Enviar a Socio → Revisión Socio → Aprobar → Aprobado

#### 3.2.4 Asignar y Gestionar Tareas

Las tareas se gestionan usando el DocType estándar **Task** de ERPNext, enriquecido con campos personalizados:

1. Desde un Encargo Contable, haz clic en el vínculo lateral **Operación > Task > + Nuevo**, o ve a **Operaciones > Tareas > + Nuevo**.
2. Define el Asunto, Descripción, Proyecto, y los campos personalizados:
   - **Encargo Contable**, **Cliente Contable**, **Servicio Contable**, **Tipo de Tarea** y **Periodo**.
3. Asigna la tarea a un usuario usando el campo estándar de Assigned To.
4. Haz clic en **Guardar**.

**Flujo de Aprobación de Tareas:**

Cada tarea tiene un campo **Estado de Aprobación** que pasa por el workflow:

> Borrador → Enviar a Revisión → Revisión Supervisor → Enviar a Socio → Revisión Socio → Aprobar → Aprobado

Esto permite al Supervisor y Socio revisar el trabajo hecho antes de darlo por cerrado.

[Imagen: Panel de Tareas (Kanban) mostrando las tarjetas de tareas organizadas por estado con filtros por cliente y encargo]

#### 3.2.5 Subir Documentos Contables

1. Ve a **Operaciones > Documentos > + Nuevo**.
2. Llena:
   - **Título del Documento** (obligatorio).
   - **Cliente** (obligatorio).
   - **Periodo** (obligatorio).
   - **Encargo**, **Tarea** y **Entregable Cliente** (opcionales, para trazabilidad).
   - **Tipo**: Factura, Estado de Cuenta, Declaración, Recibo, Contrato, Cédula de Auditoría, Correspondencia u Otro.
   - **Archivo Principal**: Adjunta el archivo digitalizado.
   - **Preparado por**: Selecciona el usuario que preparó el documento.
3. En la tabla **Evidencias Documentales**, agrega evidencias adicionales si aplica.
4. Haz clic en **Guardar**.

[Imagen: Formulario de Documento Contable con archivo adjunto y tabla de evidencias documentales]

---

### 3.3 Gestión de Auditoría

**Objetivo:** Planear y ejecutar auditorías formales: desde la creación del expediente hasta la emisión del informe final.

**Roles responsables:** Contador del Despacho (ejecución), Auxiliar (papeles de trabajo), Supervisor (revisión), Socio (aprobación y firma de dictamen).

#### 3.3.1 Crear un Expediente de Auditoría

1. Ve a **Auditoría > Expedientes Auditoría > + Nuevo**.
2. Selecciona el **Encargo Contable** de tipo Auditoría (obligatorio). El Cliente, Periodo, Compañía y Proyecto se llenan automáticamente.
3. Define el **Equipo de Auditoría**: Socio a Cargo y Supervisor a Cargo.
4. Define las **Fechas**: Inicio Planeada y Fin Planeada.
5. Llena la sección **Planeación**:
   - **Objetivo de la Auditoría**: Qué se busca verificar.
   - **Alcance**: Periodos, áreas y procesos cubiertos.
   - **Materialidad Monetaria**: Monto de materialidad definido.
   - **Enfoque**: Controles, Sustantivo o Mixto.
   - **Base Normativa**: Marco de referencia (ej. NIIF, NIA, normativa local).
   - **Estrategia de Muestreo**: Descripción del método.
6. En **Memorando de Planeación**, redacta el memo formal de planeación.
7. El **Estado del Expediente** inicia en **Planeación** y avanza: Ejecución → Revisión Técnica → Cerrada → Archivada.
8. Haz clic en **Guardar**.

[Imagen: Formulario de Expediente de Auditoría mostrando las secciones de planeación, equipo y memorando]

#### 3.3.2 Construir la Matriz de Riesgos y Controles

1. Desde el Expediente, haz clic en el vínculo lateral **Auditoría > Riesgo Control Auditoría > + Nuevo**.
2. Llena:
   - **Afirmación de los EEFF** que se está evaluando.
   - **Descripción del Riesgo** identificado.
   - **Probabilidad** e **Impacto** (Bajo, Medio, Alto, Crítico).
   - **Control(es) Identificado(s)**: Descripción de las medidas que mitigan el riesgo.
   - **Evaluación del Control**: Efectivo, Parcial, Deficiente.
   - **Respuesta Planificada**: Pruebas a ejecutar.
3. Haz clic en **Guardar** y envía a revisión.

[Imagen: Formulario de Riesgo Control de Auditoría con los campos de riesgo, probabilidad, impacto y controles]

#### 3.3.3 Documentar Papeles de Trabajo

1. Desde el Expediente, haz clic en **Auditoría > Papeles de Trabajo > + Nuevo**.
2. Llena los campos:
   - **Tipo de Papel**: Cédula Sumaria, Cédula Analítica, Prueba de Control, Prueba Sustantiva, Confirmación, Observación u Otro.
   - **Referencia**: Código de referencia interno (ej. "A-1", "B-2.1").
   - **Título**: Descripción breve.
   - **Riesgo/Control vinculado** (opcional).
   - **Documento Contable** y/o **Archivo de Evidencia**: Adjunta la evidencia soporte.
   - **Tarea** (opcional): Vincula a la tarea de ERPNext donde se registran horas.
3. Completa la sección técnica:
   - **Objetivo de la Prueba**, **Procedimiento Ejecutado**, **Resultado** y **Conclusión**.
4. En **Preparación y Revisión**: se registra quién preparó y quién revisa.
5. El **Estado del Papel** avanza: Borrador → Preparado → En Revisión → Aprobado (o Requiere Ajuste) → Cerrado.
6. Haz clic en **Guardar** y envía a revisión.

> **Integridad documental:** El sistema calcula automáticamente un **Hash SHA256** de la evidencia adjunta para garantizar la integridad del archivo.

[Imagen: Formulario de Papel de Trabajo mostrando tipo, referencia, procedimiento y conclusión]

#### 3.3.4 Registrar Hallazgos

1. Desde el Expediente, haz clic en **Auditoría > Hallazgos Auditoría > + Nuevo**.
2. Llena los campos obligatorios:
   - **Título del Hallazgo** y **Severidad** (Baja, Media, Alta, Crítica).
   - **Condición** (obligatorio): Descripción de lo encontrado.
3. Completa la estructura del hallazgo:
   - **Criterio**: La norma o estándar que debería cumplirse.
   - **Causa**: Razón de la desviación.
   - **Efecto**: Impacto en los estados financieros o la operación.
   - **Recomendación**: Mejora sugerida.
4. Vincula al **Riesgo/Control** y **Papel de Trabajo** relacionados.
5. Registra la **Respuesta de la Administración**, **Responsable del Plan de Acción** y **Fecha de Compromiso**.
6. El estado avanza: Borrador → Abierto → En Seguimiento → Resuelto → Cerrado (o Descartado).
7. Haz clic en **Guardar** y envía a revisión.

[Imagen: Formulario de Hallazgo de Auditoría con las secciones de criterio, condición, causa, efecto y recomendación]

#### 3.3.5 Revisión Técnica y Cierre del Expediente

1. Cuando todos los papeles de trabajo estén aprobados y los hallazgos estén cerrados o en seguimiento, el Supervisor cambia el Estado del Expediente a **Revisión Técnica**.
2. Asigna al **Revisado Técnicamente por** y registra el **Resultado**: Pendiente, Observado o Aprobado.
3. Una vez que la revisión técnica esté Aprobada, complete el **Informe Final de Auditoría** (ver sección siguiente).
4. Vincule el Informe Final al Expediente y registre el **Memo de Cierre**.
5. Cambie el estado del Expediente a **Cerrada** — el sistema registrará la fecha de cierre y el usuario que cerró.

#### 3.3.6 Emitir Informe Final de Auditoría

1. Ve a **Auditoría > Informes Finales Auditoría > + Nuevo**.
2. Vincúlalo al Expediente de Auditoría.
3. Selecciona el tipo de informe y completa el dictamen.
4. Envía a revisión siguiendo el flujo Supervisor → Socio → Aprobado.
5. Una vez aprobado, puede generar el formato de impresión para firma y emisión.

Los formatos de impresión disponibles incluyen: **Dictamen de Auditoría**, **Carta a la Gerencia**, **Informe de Control Interno**, **Informe de Hallazgos**, **Procedimientos Acordados**, entre otros.

[Imagen: Formato de impresión del Dictamen de Auditoría listo para firma]

---

### 3.4 Requerimientos al Cliente

**Objetivo:** Solicitar información o documentación al cliente, dar seguimiento al estado de cada entregable y validar lo recibido.

**Roles responsables:** Contador / Auxiliar (creación y seguimiento), Supervisor / Socio (aprobación).

#### 3.4.1 Crear un Requerimiento

1. Ve a **Operaciones > Requerimientos Cliente > + Nuevo**.
2. Llena los campos:
   - **Cliente** (obligatorio).
   - **Encargo Contable** y **Periodo** (para contextualizar).
   - **Prioridad**: Baja, Media, Alta o Crítica.
   - **Canal de Envío**: Correo, Portal, WhatsApp, Teléfono, Reunión u Otro.
   - **Responsable Interno**: Quién da seguimiento.
   - **Fecha de Solicitud** (default: hoy) y **Fecha de Vencimiento**.
   - **Contacto Cliente**: A quién se dirige la solicitud.
3. En la sección **Detalle**, redacta la **Descripción** del requerimiento y las **Instrucciones al Cliente** (texto rico).
4. Haz clic en **Guardar**. El requerimiento inicia en **Estado Requerimiento: Borrador**.

[Imagen: Formulario de Requerimiento Cliente mostrando campos de cliente, prioridad, canal y descripción]

#### 3.4.2 Enviar el Requerimiento

1. Cambia el Estado del Requerimiento a **Enviado**. El sistema registra la **Fecha de Envío** automáticamente.
2. Si la Configuración del Despacho tiene habilitado **Auto Enviar Requerimiento al Marcar Enviado**, el sistema enviará un correo automático al contacto del cliente usando la plantilla configurada.

#### 3.4.3 Agregar Entregables

1. Desde el Requerimiento, haz clic en **Operación > Entregable Cliente > + Nuevo**.
2. Define:
   - **Tipo de Entregable** (obligatorio): Ej. "Balance de Comprobación", "Conciliación Bancaria".
   - **Obligatorio**: Marca si es indispensable para cerrar el requerimiento.
   - **Fecha de Solicitud** y **Fecha de Compromiso**.
   - **Responsable Cliente**: Quién debe entregar la información.
3. El **Estado del Entregable** avanza: Pendiente → Solicitado → Recibido → Validado (o Rechazado, Vencido, No Aplica).
4. Al recibir el documento, cambia el estado a **Recibido** y vincula el **Documento Contable** correspondiente.
5. Un Contador o Supervisor puede **Validar** el entregable. El sistema registra quién validó y la fecha.

[Imagen: Lista de entregables dentro de un requerimiento mostrando estados varíados: Pendiente, Recibido, Validado]

#### 3.4.4 Seguimiento Automático por Correo

El sistema ejecuta diariamente un proceso automatizado que:

- **Envía recordatorios** a los clientes con requerimientos cuya fecha de vencimiento se acerca (si la opción está habilitada en la Configuración del Despacho).
- **Envía avisos de vencido** cuando la fecha de vencimiento ya pasó.
- Registra la fecha del último recordatorio y último aviso para evitar envíos duplicados.

#### 3.4.5 Resumen del Requerimiento

La sección **Resumen de Entregables** en el requerimiento muestra indicadores calculados automáticamente:

- Total de Entregables, Recibidos, Validados, Vencidos, Obligatorios Pendientes y **Porcentaje de Cumplimiento**.

Cuando todos los entregables obligatorios estén recibidos/validados, puede cerrar el requerimiento cambiando su estado a **Cerrado**.

#### 3.4.6 Portal de Autoservicio para Clientes

Si el Cliente Contable tiene habilitado el **Portal**, el contacto del cliente puede acceder vía web a:

- `/portal-cliente` — Dashboard general.
- `/requerimientos-cliente` — Ver sus requerimientos pendientes.
- `/entregables-cliente` — Consultar y descargar entregables.

[Imagen: Vista del Portal de Cliente mostrando la lista de requerimientos pendientes]

---

### 3.5 Tiempos y Facturación

**Objetivo:** Registrar horas invertidas en cada encargo, emitir facturas de venta y dar seguimiento a la cobranza.

**Roles responsables:** Auxiliar/Contador (registro de horas), Contador (facturación), Contador/Supervisor (cobranza).

#### 3.5.1 Registrar Horas (Timesheets)

1. En ERPNext, ve a **Proyectos > Timesheet > + Nuevo**.
2. Selecciona el **Employee** (tu usuario) y agrega líneas de tiempo:
   - **Project**: Selecciona el proyecto vinculado al Encargo Contable.
   - **Activity Type**: Tipo de actividad realizada.
   - **Hours**: Horas invertidas.
   - **From/To**: Fecha y hora de inicio y fin.
3. Haz clic en **Guardar** y luego **Enviar**.

> **Sincronización automática:** Al guardar o enviar un Timesheet, el sistema actualiza automáticamente el Encargo Contable vinculado: Horas Registradas, Horas Facturables, Costo Interno Total y el WIP (Work in Progress).

[Imagen: Formulario de Timesheet con líneas de tiempo vinculadas a un proyecto del encargo]

#### 3.5.2 Emitir una Factura de Venta

1. En ERPNext, ve a **Cuentas > Sales Invoice > + Nuevo**.
2. Selecciona el **Customer** vinculado al Cliente Contable.
3. En los campos personalizados, selecciona el **Encargo Contable**, **Contrato Comercial** y **Servicio Contable**.
4. Agrega los ítems de facturación con los montos correspondientes.
5. Haz clic en **Guardar** y luego **Enviar**.

> **Sincronización automática:** Al enviar la factura, el sistema actualiza el Encargo Contable: Ingreso Facturado, Facturas Emitidas, Saldo por Cobrar, y los márgenes (Ejecutado, Facturado).

[Imagen: Sales Invoice con los campos personalizados de Encargo Contable y Servicio visibles]

#### 3.5.3 Registrar Cobros (Payment Entry)

1. Desde la Sales Invoice, haz clic en **Crear > Payment Entry**, o ve a **Cuentas > Payment Entry > + Nuevo**.
2. Complete la información de pago.
3. Haz clic en **Guardar** y luego **Enviar**.

> **Sincronización automática:** Al registrar el pago, el Encargo Contable se actualiza: Cobrado Total, Saldo por Cobrar, Cartera Vencida, Aging (Corriente, 0-30, 31-60, 61-90, 91+ días).

#### 3.5.4 Seguimiento de Cobranza

1. Ve a **Operaciones > Seguimientos Cobranza > + Nuevo**.
2. Selecciona la **Sales Invoice** pendiente de cobro (obligatorio). Los campos de Encargo, Cliente, Servicio, Compañía. Moneda, Monto y Saldo se llenan automáticamente.
3. Registra la gestión:
   - **Estado**: Pendiente, Contactado, Compromiso de Pago, Escalado, Pagado o Cerrado.
   - **Fecha de Gestión**, **Responsable** y **Canal** (Correo, Llamada, WhatsApp, Reunión, etc.).
   - **Próxima Gestión**: Fecha del siguiente contacto.
4. Si hay un compromiso de pago, registra el **Monto** y **Fecha de Compromiso**.
5. Vincula el **Payment Entry** cuando el pago se concrete.
6. En **Comentarios**, documenta el resultado de la gestión.
7. Haz clic en **Guardar**.

> **Sincronización automática:** Al guardar el Seguimiento de Cobranza, el Encargo Contable se actualiza con la Última Gestión de Cobranza y la Próxima Gestión.

[Imagen: Formulario de Seguimiento de Cobranza mostrando la factura vinculada, estado de gestión y compromiso de pago]

---

### 3.6 Gobierno y Control

**Objetivo:** Asegurar que todos los documentos clave pasen por un proceso de aprobación escalonado antes de ser emitidos o considerados definitivos.

**Roles responsables:** Todos los roles participan según su nivel.

#### 3.6.1 Flujo de Aprobación Estándar

El sistema aplica un **flujo de aprobación idéntico** a 16 tipos de documento:

```
 ┌──────────┐    Enviar a     ┌──────────────────┐    Enviar a    ┌────────────────┐    Aprobar    ┌───────────┐
 │ Borrador │───Revisión────▶│Revisión Supervisor│────Socio─────▶│ Revisión Socio │────────────▶│ Aprobado  │
 └──────────┘                └──────────────────┘                └────────────────┘              └───────────┘
       ▲                           │ Devolver                         │ Devolver
       │                           ▼                                  ▼
       └─────────────────── Devuelto ◄────────────────────────────────┘
                             (con comentarios)
```

**Documentos que pasan por este flujo:**

| Área | Documentos |
|---|---|
| Operaciones | Task, Documento Contable, Requerimiento Cliente, Entregable Cliente, Encargo Contable |
| Comercial | Contrato Comercial, Cambio Alcance Comercial |
| Auditoría | Expediente Auditoría, Riesgo Control, Papel de Trabajo, Hallazgo, Informe Final |
| Estados Financieros | Paquete EEFF, Estado Financiero, Nota EEFF, Ajuste EEFF |

#### 3.6.2 Cómo Enviar a Revisión

1. Abre el documento que deseas someter a aprobación.
2. Haz clic en el botón de acción **Enviar a Revisión** (visible en la parte superior del formulario).
3. El estado cambiará de **Borrador** a **Revisión Supervisor**.
4. El sistema registra automáticamente la **Fecha de Envío a Revisión**.

> **Importante:** Una vez que el documento está en Revisión, **no se puede modificar su contenido**. Si el Supervisor o Socio necesitan correcciones, deben usar la opción "Devolver".

[Imagen: Botones de acción del Workflow: "Enviar a Revisión", "Enviar a Socio", "Devolver", "Aprobar"]

#### 3.6.3 Cómo Revisar como Supervisor

1. Abre el documento en estado **Revisión Supervisor**.
2. Revisa el contenido y, en la sección **Comentarios de Revisión**, agrega tus observaciones en el campo **Comentarios Supervisor**.
3. Decide:
   - **Enviar a Socio**: Si el documento está conforme.
   - **Devolver**: Si requiere correcciones (los comentarios son obligatorios al devolver).

#### 3.6.4 Cómo Aprobar como Socio

1. Abre el documento en estado **Revisión Socio**.
2. Revisa el contenido y agrega observaciones en **Comentarios Socio** si lo consideras necesario.
3. Decide:
   - **Aprobar**: El documento queda en estado definitivo.
   - **Devolver**: Regresa a Borrador/Devuelto (con comentarios obligatorios).

El sistema registra automáticamente:
- **Revisado por Supervisor** y **Fecha de Revisión del Supervisor**.
- **Aprobado por Socio** y **Fecha de Aprobación del Socio**.

Estos campos son de solo lectura y sirven como bitácora de auditoría.

#### 3.6.5 Bitácora de Cambios

Todos los documentos del sistema tienen habilitado **Track Changes**. Esto significa que cada modificación queda registrada en el historial del documento, incluyendo: quién hizo el cambio, cuándo y qué campo se modificó.

Para ver el historial, desplázate al final de cualquier formulario y haz clic en **Actividad**.

[Imagen: Sección de Actividad de un documento mostrando el historial de cambios con fechas y usuarios]

---

## 4. Reportes y Dashboards

### 4.1 Páginas Personalizadas (SPAs)

| Página | Ubicación | Descripción |
|---|---|---|
| **Panel de Tareas** | Panel > Panel de Tareas | Vista Kanban interactiva con filtros por empresa, cliente, periodo y asignado. Permite arrastrar tareas entre columnas de estado. |
| **Rentabilidad y Cobranza** | Panel > Rentabilidad y Cobranza | Dashboard financiero que muestra la rentabilidad por encargo, cartera vencida y aging. |
| **Resumen de Asignados** | Panel > Resumen de Asignados | Vista de la carga de trabajo por colaborador: tareas asignadas, vencidas y completadas. |
| **Seguimiento de Auditoría** | Panel > Seguimiento Auditoría | Estado consolidado de todos los expedientes de auditoría y sus papeles de trabajo. |
| **Salida a Producción** | Panel > Salida a Producción | Control de puesta en marcha de nuevos clientes o servicios. |

[Imagen: Dashboard de Rentabilidad y Cobranza mostrando gráficos de margen ejecutado, facturado y cobrado por encargo]

### 4.2 Reportes Gerenciales (Script Reports)

| Reporte | Descripción |
|---|---|
| **Resumen de Tareas por Encargo** | Desglose de tareas por encargo y su estado, incluyendo porcentaje de completitud. |
| **Resumen Rentabilidad y Cobranza** | Ingresos, costos, margen y saldo por cobrar por encargo. |
| **Cartera Gerencial por Encargo** | Aging de cartera vencida desglosada por encargo y cliente. |
| **Estado Gerencial de Auditoría** | Estado de expedientes, papeles de trabajo y hallazgos por cliente. |
| **Seguimiento Gerencial de Requerimientos** | Estado de requerimientos enviados, vencidos y porcentaje de cumplimiento. |
| **Margen por Encargo y Servicio** | Margen ejecutado, facturado y cobrado agrupado por tipo de servicio. |

Para acceder a los reportes, ve a **Panel > Reportes** y selecciona el que necesites. Todos permiten filtrar por Compañía, Cliente y periodo.

[Imagen: Reporte "Cartera Gerencial por Encargo" con columnas de aging (Corriente, 0-30, 31-60, 61-90, 91+)]

### 4.3 Formatos de Impresión

La aplicación incluye **19 formatos de impresión** especializados para generar documentos profesionales:

- **Contratos**: Por tipo de servicio (Contabilidad, Auditoría, Consultoría, Trabajo Especial).
- **Estados Financieros**: Situación Financiera, Resultados, Flujos de Efectivo, Cambios en Patrimonio, Paquete completo, Notas individuales y consolidadas.
- **Auditoría**: Dictamen, Carta a la Gerencia, Informe de Control Interno, Informe de Hallazgos, Informe Final (General y de Emisión), Procedimientos Acordados, Informe Completo de EEFF Auditados.

Para generar un formato, abra el documento correspondiente, haga clic en **Imprimir** (icono de impresora) y seleccione el formato deseado.

[Imagen: Menú de selección de formato de impresión mostrando los diferentes formatos disponibles para un Contrato Comercial]

---

## 5. Preguntas Frecuentes y Solución de Problemas

### P1: "No puedo modificar un documento, dice que está en Revisión"

**Causa:** Cuando un documento está en estado "Revisión Supervisor" o "Revisión Socio", el sistema bloquea toda edición de contenido por diseño.

**Solución:** Solicite al Supervisor o Socio que haga clic en **Devolver** (con comentarios explicando qué debe corregirse). El documento regresará a estado "Devuelto" y podrá editarse nuevamente.

[Imagen: Mensaje de error "No puedes modificar el contenido mientras esta en Revisión Supervisor"]

### P2: "Intento devolver un documento pero me pide comentarios"

**Causa:** El sistema requiere que quien devuelve un documento registre comentarios obligatorios para justificar la devolución.

**Solución:** En la sección "Comentarios de Revisión", escriba sus observaciones en el campo "Comentarios Supervisor" (o "Comentarios Socio" según su rol) y luego haga clic en **Devolver**.

### P3: "No tengo permisos para crear un registro"

**Causa:** Su rol no tiene permiso de creación para ese tipo de documento. Por ejemplo, un Auxiliar no puede crear Clientes Contables ni Seguimientos de Cobranza.

**Solución:** Contacte al Contador o Supervisor para que cree el registro, o solicite al Administrador que le asigne un rol con los permisos necesarios.

### P4: "La información financiera del encargo no se actualiza"

**Causa:** Los campos de horas, facturación, cobros, aging y márgenes en el Encargo Contable se sincronizan automáticamente cuando se guardan o envían Timesheets, Sales Invoices y Payment Entries en ERPNext.

**Solución:** Verifique que el campo **Encargo Contable** esté correctamente vinculado en el Timesheet/Sales Invoice/Payment Entry. Si el campo está vacío, la sincronización no ocurrirá.

### P5: "El cliente no recibió el correo del requerimiento"

**Causa:** Puede deberse a:
- La opción de auto-envío está deshabilitada en la Configuración del Despacho.
- No se ha configurado el Email Template correspondiente.
- El contacto del cliente no tiene correo registrado.

**Solución:**
1. Vaya a **Configuración > Configuración Despacho Contable**.
2. Verifique que los Templates de Correo estén asignados (Requerimiento Envío, Recordatorio, Vencido).
3. Verifique que los checkbox de auto-envío estén habilitados.
4. Confirme que el Cliente Contable tenga un correo electrónico registrado.

[Imagen: Pantalla de Configuración del Despacho Contable mostrando las secciones de Plantillas de Correo y Automatización]

### P6: "¿Cómo puedo exportar un reporte a Excel?"

**Solución:** En cualquier reporte, haga clic en el botón **⬇ Descargar** (disponible en la barra superior del reporte) y seleccione el formato deseado (Excel o CSV).

### P7: "¿Cómo sé quién aprobó un documento?"

**Solución:** Abra el documento y revise la sección **Gobierno y Aprobación**. Los campos "Revisado por Supervisor", "Fecha Revisión Supervisor", "Aprobado por Socio" y "Fecha Aprobación Socio" muestran la trazabilidad completa del flujo de aprobación.

---

> **Soporte:** Para preguntas adicionales o reportar incidencias, contacte al Administrador del Sistema.
