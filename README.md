# Gestión Contable

Aplicación de [Frappe Framework](https://frappeframework.com) / [ERPNext](https://erpnext.com) para la gestión integral de clientes, periodos y tareas contables de un despacho contable.

## Descripción

**Gestión Contable** permite a despachos contables administrar de forma centralizada:

- **Clientes** vinculados al DocType `Customer` de ERPNext, con campos contables adicionales.
- **Periodos contables** con fechas de inicio/fin y control de apertura/cierre.
- **Tareas contables** asignadas por cliente y periodo, con seguimiento de estado, responsable y fechas de vencimiento.
- **Documentos contables** vinculados a clientes y periodos, con soporte para archivos adjuntos.

La app incluye un **Panel de Gestión** (workspace) con métricas clave, gráficos de estado de tareas y accesos rápidos.

## Módulos y DocTypes

| DocType | Descripción | Campos Clave |
|---------|-------------|--------------|
| **Cliente Contable** | Extensión del Customer de ERPNext | Customer (Link), Identificación Fiscal (auto-fetch), Estado, Frecuencia de Cierre, Teléfono, Correo, Cuenta de Correo |
| **Periodo Contable** | Periodos fiscales o contables | Nombre del Periodo, Fecha de Inicio, Fecha de Fin, Estado (Abierto/Cerrado) |
| **Tarea Contable** | Tareas y obligaciones contables | Título, Cliente, Periodo, Tipo de Tarea, Estado, Fecha de Vencimiento, Asignado a, Notas |
| **Documento Contable** | Documentos digitalizados | Título, Cliente, Periodo, Tipo, Archivo adjunto |

### Tipos de Tarea

- Impuestos
- Nómina
- Cierre Contable
- Auditoría
- Otro

### Tipos de Documento

- Factura
- Estado de Cuenta
- Declaración
- Recibo
- Otro

## Validaciones

La app incluye validaciones server-side automáticas:

- **Periodo Contable**: La fecha de fin debe ser posterior a la fecha de inicio.
- **Tarea Contable**: No se permiten tareas para clientes inactivos ni en periodos cerrados.
- **Documento Contable**: No se permiten documentos para clientes inactivos ni en periodos cerrados.

## Roles

| Rol | Permisos |
|-----|----------|
| **System Manager** | CRUD completo + delete + export |
| **Contador del Despacho** | CRUD completo + delete + export |
| **Auxiliar Contable del Despacho** | Crear, leer, escribir, email, imprimir, reportes, compartir |

## Workspace y Páginas

La app incluye un **Panel de Gestión** (workspace) y una página personalizada:

- 📋 **Panel de Tareas** (Página): Visualización estilo Kanban de todas las tareas por estado, con filtros por Empresa, Cliente, Periodo, Tipo y Asignado.
- 📊 **Gráfico**: Estado de Tareas por Cierre.
- 🔢 **Tarjetas numéricas**: Tareas Pendientes, Documentos Recibidos Hoy.
- ⚡ **Accesos rápidos**: Clientes Activos, Nueva Tarea, Periodo Actual.

## Requisitos Previos

- [ERPNext](https://erpnext.com) instalado (proporciona el DocType `Customer`)
- [Frappe Bench](https://frappeframework.com/docs/user/en/installation) configurado
- Python >= 3.10
- MariaDB o PostgreSQL
- Redis
- Node.js

## Instalación

```bash
# Desde el directorio de tu bench
bench get-app https://[url-del-repositorio]/gestion_contable.git

# Instalar en un sitio
bench --site [nombre-del-sitio] install-app gestion_contable

# Ejecutar migraciones
bench --site [nombre-del-sitio] migrate
```

## Tests

```bash
# Ejecutar todos los tests de la app
bench --site [nombre-del-sitio] run-tests --app gestion_contable

# Test de un módulo específico
bench --site [nombre-del-sitio] run-tests --module gestion_contable.gestion_contable.doctype.periodo_contable.test_periodo_contable
```

## Desarrollo

```bash
# Iniciar el entorno de desarrollo
bench start

# Acceder al sitio
# http://localhost:8000
```

## Estructura del Proyecto

```
gestion_contable/
├── gestion_contable/
│   ├── gestion_contable/
│   │   ├── doctype/
│   │   │   ├── cliente_contable/       # Gestión de clientes (→ Customer ERPNext)
│   │   │   ├── documento_contable/     # Documentos adjuntos
│   │   │   ├── periodo_contable/       # Periodos fiscales
│   │   │   └── tarea_contable/         # Tareas y obligaciones
│   │   └── workspace/
│   │       └── panel_de_gestion/       # Dashboard principal
│   └── hooks.py                        # Configuración y fixtures
├── pyproject.toml
├── setup.py
└── README.md
```

## Licencia

MIT
