# Gestión Contable

Aplicación de [Frappe Framework](https://frappeframework.com) / [ERPNext](https://erpnext.com) diseñada para la gestión operativa, administrativa y comercial de despachos contables y firmas de auditoría.

## Descripción

**Gestión Contable** centraliza los procesos de un despacho contable: captación comercial, gestión de contratos, ejecución de encargos, emisión de estados financieros, auditoría, cobranza y comunicación con clientes, incluyendo un portal web de autoservicio.

### Módulos Principales

#### 1. Operaciones y Gestión de Encargos
- **Cliente Contable**: Extensión del Customer de ERPNext con datos contables específicos (frecuencia de cierre, contactos funcionales, etc.).
- **Encargo Contable & Servicios**: Servicios recurrentes o únicos por cliente, basados en plantillas con hitos y tarifas.
- **Requerimientos y Entregables**: Solicitudes de información al cliente y control de entregables emitidos.
- **Periodo Contable**: Control de periodos fiscales (apertura/cierre) por empresa y cliente.
- **Documento Contable**: Repositorio centralizado de documentos con evidencia documental.

#### 2. Gestión Comercial
- **Contrato Comercial**: Honorarios, vigencia, alcance de servicios y facturación.
- **Cambios de Alcance**: Adendas y modificaciones a contratos originales con detalle de cambios.

#### 3. Estados Financieros
- **Paquetes de Estados Financieros**: Generación de juegos completos de EEFF (Situación Financiera, Resultados, Flujos de Efectivo, Cambios en Patrimonio).
- **Notas y Ajustes**: Notas explicativas con cifras y referencias, ajustes de auditoría.
- **Versionado**: Control de versiones de documentos financieros entregados.

#### 4. Auditoría
- **Expediente de Auditoría**: Estructura completa del engagement de auditoría.
- **Matriz de Riesgos y Controles**: Identificación y evaluación de riesgos y controles.
- **Papeles de Trabajo**: Documentación de pruebas sustantivas y de cumplimiento.
- **Hallazgos**: Registro de deficiencias y observaciones.
- **Informes Finales**: Dictamen, Carta a la Gerencia, Informe de Control Interno, Procedimientos Acordados.

#### 5. Cobranza y Comunicación
- **Seguimiento de Cobranza**: Gestiones de cobro, compromisos de pago e historial.
- **Correos Automatizados**: Envío automático de requerimientos, recordatorios y avisos de vencimiento.
- **Configuración del Despacho**: Plantillas de correo y flags de automatización.

## Integraciones con ERPNext

La aplicación se integra directamente con módulos estándar de ERPNext:

| DocType ERPNext | Integración |
|---|---|
| **Customer** | Vínculo base del Cliente Contable |
| **Task** | Custom Fields para tipo de servicio, aprobaciones por supervisor/socio y vínculo a encargos |
| **Sales Invoice** | Sincronización automática de facturación con encargos |
| **Payment Entry** | Sincronización automática de cobros con encargos |
| **Timesheet** | Sincronización de horas registradas por encargo |
| **Lead / Opportunity / Quotation / Contract** | Flujo comercial (CRM estándar de ERPNext) |

## Portal de Cliente

La aplicación incluye un **portal web** para que los clientes del despacho puedan:

- Consultar el estado de sus requerimientos pendientes
- Descargar entregables generados por el despacho
- Acceder a un dashboard general de su relación con el despacho

## Workspace (Panel de Gestión)

Todas las funcionalidades se acceden desde el **Panel de Gestión** integrado:

### Páginas Personalizadas
- 📋 **Panel de Tareas**: Kanban drag-and-drop con filtros avanzados
- 📊 **Rentabilidad y Cobranza**: Dashboard financiero por encargo
- 👥 **Resumen de Asignados**: Carga de trabajo por colaborador
- 🔍 **Seguimiento de Auditoría**: Estado de expedientes y papeles de trabajo
- � **Salida a Producción**: Control de puesta en marcha

### Reportes Gerenciales (Script Reports)
- Resumen de Tareas por Encargo
- Resumen de Rentabilidad y Cobranza
- Cartera Gerencial por Encargo
- Estado Gerencial de Auditoría
- Seguimiento Gerencial de Requerimientos
- Margen por Encargo y Servicio

### Formatos de Impresión
19 formatos especializados, incluyendo: Contratos Comerciales (por tipo de servicio), Estados Financieros individuales, Paquetes de EEFF completos, Dictamen de Auditoría, Carta a la Gerencia, Informe de Hallazgos, Informe de Control Interno, entre otros.

## Roles y Permisos

| Rol | Descripción |
|---|---|
| **System Manager** | Administración completa del sistema |
| **Socio del Despacho** | Aprobación final, reportes gerenciales y de rentabilidad |
| **Supervisor del Despacho** | Revisión de papeles de trabajo, aprobación intermedia, control de encargos |
| **Contador del Despacho** | Gestión operativa de clientes, periodos, estados financieros y auditoría |
| **Auxiliar Contable del Despacho** | Captura de datos, carga de documentos y ejecución de tareas |

## Automatizaciones

- **Scheduler (diario)**: Alertas de retención y correos automáticos de requerimientos (envío, recordatorio, vencimiento).
- **Doc Events**: Sincronización en tiempo real de facturación, pagos y timesheets con encargos contables.
- **Validaciones de Task**: Reglas personalizadas al guardar tareas vinculadas al despacho.
- **Bootstrap**: Configuración automática de workflows, plantillas de correo y roles al instalar o migrar.

## Requisitos Previos

- [Frappe Bench](https://frappeframework.com/docs/user/en/installation)
- [ERPNext](https://erpnext.com) instalado (Customer, Sales Invoice, Payment Entry, Timesheet, Task)
- Python >= 3.10
- Node.js

### Dependencias Opcionales

```bash
# Exportación de documentos a Word (.docx)
pip install python-docx>=1.1.0
```

## Instalación

```bash
# Desde el directorio de tu bench
bench get-app https://github.com/ernestoruiz89/gestion_contable

# Instalar en un sitio
bench --site [nombre-del-sitio] install-app gestion_contable

# Construir los assets
bench build --app gestion_contable

# Ejecutar migraciones
bench --site [nombre-del-sitio] migrate
```

## Estructura del Proyecto

```
gestion_contable/
├── gestion_contable/
│   ├── fixtures/              # Roles y Custom Fields exportados
│   ├── gestion_contable/
│   │   ├── doctype/           # ~35 DocTypes (modelos de datos)
│   │   ├── overrides/         # Overrides de DocTypes estándar (Task)
│   │   ├── page/              # 5 páginas personalizadas (SPAs)
│   │   ├── patches/           # Migraciones de datos
│   │   ├── portal/            # Lógica del portal de cliente
│   │   ├── print_format/      # 19 formatos de impresión
│   │   ├── report/            # 6 reportes gerenciales (Script Reports)
│   │   ├── services/          # Lógica de sincronización con ERPNext
│   │   ├── setup/             # Bootstrap, workflows y email templates
│   │   ├── templates/         # Templates Jinja para print formats
│   │   ├── tests/             # Tests unitarios
│   │   ├── utils/             # Utilidades (emailing, finance, word_export, etc.)
│   │   └── workspace/         # Configuración del Panel de Gestión
│   ├── hooks.py               # Doc events, scheduler, fixtures, portal
│   ├── patches.txt            # Registro de migraciones
│   ├── public/                # Assets (CSS/JS compilados)
│   └── www/                   # Páginas web del portal de cliente
├── pyproject.toml
└── README.md
```

## Licencia

MIT
