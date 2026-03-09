# Gestion Contable

Aplicacion para Frappe Framework y ERPNext orientada a despachos contables y firmas de auditoria.

Centraliza el ciclo comercial, la operacion por cliente, la auditoria formal, la preparacion de estados financieros del cliente, la facturacion, la cobranza y la interaccion con clientes por portal web.

## Alcance

La app cubre estos frentes:

- Comercial y contractual: `Lead`, `Opportunity`, `Quotation`, `Contract`, `Contrato Comercial`, `Cambio Alcance Comercial`.
- Operacion del despacho: `Cliente Contable`, `Periodo Contable`, `Encargo Contable`, `Task`, `Documento Contable`, `Servicio Contable`, `Tarifa Cliente Servicio`, `Plantilla Encargo Contable`.
- Requerimientos al cliente: `Requerimiento Cliente`, `Entregable Cliente`, portal de cliente, correos y seguimiento.
- Auditoria formal: `Expediente Auditoria`, `Riesgo Control Auditoria`, `Papel Trabajo Auditoria`, `Hallazgo Auditoria`, `Informe Final Auditoria`.
- Estados financieros del cliente: `Paquete Estados Financieros Cliente`, `Estado Financiero Cliente`, `Nota Estado Financiero`, `Ajuste Estados Financieros Cliente`, `Version Documento EEFF`.
- Facturacion y cobranza: integracion con `Sales Invoice`, `Payment Entry`, `Timesheet`, dashboards y reportes gerenciales.

## Integracion con ERPNext

La app se apoya en doctypes estandar, no los reemplaza:

- `Customer`
- `Task`
- `Project`
- `Timesheet`
- `Sales Invoice`
- `Payment Entry`
- `Lead`
- `Opportunity`
- `Quotation`
- `Contract`
- `Communication`
- `File`
- `Workflow`

## Modulos principales

### Comercial

- `Contrato Comercial` con alcances por servicio, SLA, vigencia y control de cambios.
- `Cambio Alcance Comercial` para adendas y modificaciones controladas.

### Operacion y encargos

- `Encargo Contable` como eje de horas, presupuesto, hitos, facturacion, rentabilidad y cobranza.
- Integracion con `Project`, `Task` y `Timesheet`.
- `Documento Contable` con evidencias documentales, hash, retencion y trazabilidad.

### Requerimientos y portal

- `Requerimiento Cliente` y `Entregable Cliente` para solicitudes de informacion.
- Portal web para clientes:
  - `/portal-cliente`
  - `/requerimientos-cliente`
  - `/entregables-cliente`
- Carga de archivos desde portal y registro de comunicaciones.

### Auditoria

- Expediente formal de auditoria.
- Matriz riesgo-control.
- Papeles de trabajo vinculados a evidencia especifica.
- Hallazgos y seguimiento.
- Informe final y dictamen de auditoria.

### Estados financieros del cliente

- Paquetes de EEFF auditados y no auditados.
- Estados individuales, notas, ajustes y versionado.
- Creador visual de notas complejas: `creador-de-notas-eeff`.
- Exportacion Word de:
  - paquete de EEFF no auditado
  - informe completo auditado
  - carta de remision

## Flujos de EEFF

### Flujo contable

Permite preparar y emitir estados financieros para clientes a los que la firma lleva contabilidad, sin requerir auditoria.

- `Paquete Estados Financieros Cliente`
- `Estado Financiero Cliente`
- `Nota Estado Financiero`
- `Ajuste Estados Financieros Cliente`
- `Exportar Word EEFF`

### Flujo auditado

Extiende el paquete de EEFF con expediente e informe de auditoria.

- `Expediente Auditoria`
- `Informe Final Auditoria`
- `Dictamen de Auditoria`
- `Informe Completo de EEFF Auditados`
- `Exportar Word Revision Auditada`
- `Exportar Carta de Remision`

## Workspace y pages

La app expone un workspace principal: `Panel de Gestion`.

Pages principales:

- `panel-de-tareas`
- `resumen-de-asignados`
- `seguimiento-de-auditoria`
- `rentabilidad-y-cobranza`
- `salida-a-produccion`
- `creador-de-notas-eeff`

## Reportes

Reportes gerenciales incluidos:

- `Resumen de Tareas por Encargo`
- `Resumen Rentabilidad y Cobranza`
- `Cartera Gerencial por Encargo`
- `Estado Gerencial de Auditoria`
- `Seguimiento Gerencial de Requerimientos`
- `Margen por Encargo y Servicio`

## Instalacion

```bash
bench get-app https://github.com/ernestoruiz89/gestion_contable
bench --site [sitio] install-app gestion_contable
bench build --app gestion_contable
bench --site [sitio] migrate
```

## Requisitos

- Python `>= 3.10`
- Frappe / ERPNext compatibles con la version de tu bench
- Node.js para construir assets

Dependencia opcional para exportacion Word:

```bash
bench pip install python-docx
```

Si `python-docx` no esta instalado, la app sigue funcionando y solo fallan las acciones de exportacion Word con un mensaje explicito.

## Bootstrap automatico

En `after_install` y `after_migrate` la app sincroniza elementos base como:

- workflows
- roles
- templates de correo
- recargas de metadata necesarias

## Data demo

La app incluye utilidades de dataset demo, pero estan deshabilitadas por defecto.

Para habilitarlas temporalmente en un sitio de desarrollo, agrega en `site_config.json`:

```json
{
  "gestion_contable_enable_dummy_tools": 1
}
```

Luego:

```bash
bench --site [sitio] clear-cache
```

Con eso podras usar `Configuracion Despacho Contable` para:

- generar data demo
- limpiar data demo

El dataset demo actual cubre:

- multiples clientes
- operacion de los ultimos meses
- contabilidad recurrente
- auditorias completas y en proceso
- facturas y pagos
- portal de cliente
- paquetes de estados financieros

## Estructura del proyecto

```text
gestion_contable/
|-- gestion_contable/
|   |-- hooks.py
|   |-- patches.txt
|   `-- gestion_contable/
|       |-- doctype/
|       |-- overrides/
|       |-- page/
|       |-- patches/
|       |-- portal/
|       |-- print_format/
|       |-- report/
|       |-- services/
|       |-- setup/
|       |-- templates/
|       |-- tests/
|       |-- utils/
|       `-- workspace/
|-- docs/
|-- pyproject.toml
`-- README.md
```

## Documentacion adicional

- Manual de usuario: [docs/manual_de_usuario.md](docs/manual_de_usuario.md)

## Licencia

MIT
