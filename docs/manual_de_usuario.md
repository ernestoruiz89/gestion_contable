# Manual de Usuario

## 1. Proposito

`gestion_contable` es una app para Frappe Framework y ERPNext orientada a despachos contables y firmas de auditoria.

El sistema cubre:
- gestion comercial y contractual
- operacion contable por cliente
- requerimientos al cliente y portal web
- auditoria formal
- estados financieros del cliente
- facturacion, rentabilidad y cobranza

Este manual describe el uso funcional de la app desde Desk.

## 2. Modulos principales

La app se apoya en doctypes estandar de ERPNext como `Customer`, `Task`, `Project`, `Timesheet`, `Sales Invoice`, `Payment Entry`, `Lead`, `Opportunity`, `Quotation`, `Contract`, `Communication`, `File` y `Workflow`.

Sobre esa base agrega estos modulos propios:
- `Cliente Contable`
- `Periodo Contable`
- `Servicio Contable`
- `Tarifa Cliente Servicio`
- `Contrato Comercial`
- `Cambio Alcance Comercial`
- `Encargo Contable`
- `Documento Contable`
- `Requerimiento Cliente`
- `Entregable Cliente`
- `Expediente Auditoria`
- `Riesgo Control Auditoria`
- `Papel Trabajo Auditoria`
- `Hallazgo Auditoria`
- `Informe Final Auditoria`
- `Paquete Estados Financieros Cliente`
- `Estado Financiero Cliente`
- `Nota Estado Financiero`
- `Ajuste Estados Financieros Cliente`
- `Version Documento EEFF`

## 3. Acceso y navegacion

El workspace principal es `Panel de Gestion`.

Desde ahi se accede a:
- operaciones contables
- comercial y contratos
- auditoria
- estados financieros del cliente
- reportes y paneles
- configuracion

Pages principales:
- `panel-de-tareas`
- `resumen-de-asignados`
- `seguimiento-de-auditoria`
- `rentabilidad-y-cobranza`
- `salida-a-produccion`
- `creador-de-notas-eeff`

## 4. Roles y gobierno

La app usa permisos por rol, validaciones de servidor y workflows nativos.

Roles internos relevantes:
- `Auxiliar Contable del Despacho`
- `Contador del Despacho`
- `Supervisor del Despacho`
- `Socio del Despacho`
- `System Manager`

Reglas generales:
- los borradores pueden ser preparados por roles operativos segun el documento
- la revision y aprobacion pasan por workflow
- la devolucion exige comentario de revision
- varios documentos bloquean edicion de contenido al entrar en revision o aprobacion

## 5. Flujo comercial y contractual

### 5.1 Pipeline comercial

El proceso comercial puede iniciar en:
- `Lead`
- `Opportunity`
- `Quotation`
- `Contract`

### 5.2 Contrato comercial

`Contrato Comercial` formaliza:
- cliente
- alcance por servicio
- SLA
- vigencia
- company y moneda
- responsables
- honorario fijo o tarifa por hora

Cada linea de alcance alimenta `Tarifa Cliente Servicio` para el uso posterior en encargos.

### 5.3 Cambio de alcance

`Cambio Alcance Comercial` sirve para:
- ampliar o reducir servicios
- cambiar tarifas
- ajustar horas
- mantener trazabilidad contractual

## 6. Operacion por cliente y encargo

### 6.1 Cliente y periodo

`Cliente Contable` es el maestro operativo del cliente.

`Periodo Contable` controla el periodo por:
- cliente
- company
- mes y anio

### 6.2 Encargo contable

`Encargo Contable` es el eje de la operacion. Desde ahi se conecta:
- servicio
- cliente
- contrato
- project
- hitos
- task
- timesheets
- facturacion
- cobranza

### 6.3 Tareas

La app usa `Task` como modelo canonico de tareas.

Desde `panel-de-tareas` puedes:
- ver tareas por estado
- crear tareas
- asignar responsables
- mover tareas entre columnas segun permisos

### 6.4 Documentos y evidencias

`Documento Contable` guarda evidencia y trazabilidad operativa.

Incluye:
- vinculo a `Task`
- vinculo a `Encargo Contable`
- evidencias documentales
- hash
- retencion
- integracion con entregables del cliente

## 7. Requerimientos al cliente y portal

### 7.1 Requerimientos y entregables

`Requerimiento Cliente` y `Entregable Cliente` controlan:
- solicitudes de informacion
- estado de cumplimiento
- validacion de recepcion
- vencimientos
- recordatorios y seguimiento

### 7.2 Portal cliente

Rutas web disponibles:
- `/portal-cliente`
- `/requerimientos-cliente`
- `/entregables-cliente`

El portal permite:
- consultar requerimientos
- consultar entregables
- cargar archivos en entregables permitidos
- dejar trazabilidad de comunicaciones

## 8. Auditoria formal

### 8.1 Expediente

`Expediente Auditoria` concentra la auditoria formal y se vincula al encargo.

### 8.2 Matriz riesgo-control

`Riesgo Control Auditoria` registra:
- objetivo
- riesgo
- control
- procedimiento planificado
- severidad y evaluacion

### 8.3 Papeles de trabajo

`Papel Trabajo Auditoria` permite documentar:
- objetivo de prueba
- procedimiento ejecutado
- resultado
- conclusion
- evidencia especifica

### 8.4 Hallazgos

`Hallazgo Auditoria` controla:
- criterio
- condicion
- causa
- efecto
- recomendacion
- respuesta de administracion
- plan de accion

### 8.5 Informe final y dictamen

`Informe Final Auditoria` soporta varios tipos de informe, incluyendo:
- informe final general
- carta a la gerencia
- informe de hallazgos
- informe de control interno
- procedimientos acordados
- dictamen de auditoria

Para dictamen se soporta estructura operativa basada en:
- `NIA 700`
- `NIA 705`
- `NIA 706`

## 9. Estados financieros del cliente

El modulo de EEFF sirve tanto para clientes de contabilidad como para clientes auditados.

### 9.1 Paquete Estados Financieros Cliente

`Paquete Estados Financieros Cliente` es el maestro del juego de estados financieros.

Puede representar:
- flujo contable no auditado
- flujo auditado

Campos de auditoria del paquete:
- `expediente_auditoria`
- `informe_final_auditoria`
- `dictamen_de_auditoria`

Estos campos se usan solo cuando el paquete forma parte de un flujo auditado.

### 9.2 Estados financieros

`Estado Financiero Cliente` permite registrar estados como:
- estado de situacion financiera
- estado de resultados
- estado de cambios en el patrimonio
- estado de flujos de efectivo

Incluye validaciones matematicas para:
- balance
- resultados
- flujo de efectivo

### 9.3 Notas a los estados financieros

`Nota Estado Financiero` soporta:
- contenido narrativo
- cifras simples
- tablas complejas por seccion
- comentarios de preparacion
- renumeracion controlada

Tipos de seccion estructurada:
- `Narrativa`
- `Tabla`
- `Texto y Tabla`

### 9.4 Ajustes y versiones

`Ajuste Estados Financieros Cliente` documenta ajustes propuestos o registrados.

`Version Documento EEFF` lleva control de versiones documentales, especialmente para archivos Word de revision.

### 9.5 Duplicar paquete

En `Paquete Estados Financieros Cliente` existe el boton `Duplicar Paquete`.

El dialogo solicita datos del nuevo paquete, por ejemplo:
- `Periodo Contable`
- `Fecha Corte`
- `Tipo Paquete`
- `Marco Contable`
- `Version`
- `Encargo Contable`
- `Expediente Auditoria`

La duplicacion copia:
- el paquete base
- estados financieros
- notas

Y reinicia gobierno y datos de emision para el nuevo registro.

## 10. Creador de Notas EEFF

La page `creador-de-notas-eeff` es la interfaz recomendada para notas complejas.

Permite filtrar por:
- cliente
- `Paquete Estados Financieros Cliente`
- nota

Funciones principales:
- crear nota desde la page
- editar contenido general de la nota
- administrar secciones estructuradas
- editar columnas, filas y celdas en matriz visual
- importar CSV por seccion
- exportar CSV por seccion cuando la seccion ya tiene datos

### 10.1 CSV simple

Ejemplo:

```csv
Concepto,Vigentes,Prorrogados,Reestructurados
Creditos comerciales,72755643,0,624486
Subtotal,73380129,0,624486
Total,73380129,0,624486
```

### 10.2 CSV con grupos de columna

Ejemplo:

```csv
Concepto,2023,2023,2022,2022
,Valor en libros,Valor razonable,Valor en libros,Valor razonable
Efectivo,225406542,225406542,375132970,375132970
Total activos,2202882363,2254181521,2043458799,2303072057
```

### 10.3 Codigos generados

La page genera codigos secuenciales:
- filas: `FIL-1`, `FIL-2`, `FIL-3`
- columnas: `COL-1`, `COL-2`, `COL-3`

## 11. Impresion y exportacion

### 11.1 Formatos de impresion

Formatos relevantes:
- `Paquete Estados Financieros Cliente - Completo`
- `Paquete Estados Financieros Cliente - Notas Consolidadas`
- formatos individuales de estados financieros
- `Nota Estado Financiero - Individual`
- `Informe Completo de EEFF Auditados`
- `Ajuste Estados Financieros Cliente - Detalle`
- `Ajustes Estados Financieros Cliente - Consolidado`
- `Riesgo Control Auditoria - Matriz`
- `Papel Trabajo Auditoria - Detalle`
- `Hallazgo Auditoria - Detalle`

### 11.2 Convencion visual de notas y EEFF

Los formatos de EEFF y notas usan estas reglas:
- texto negro
- tipografia `Arial Narrow`
- tamano base 12
- tablas sin grilla general
- subtotales con borde contable simple
- totales con borde contable y doble subrayado cuando aplica
- si una tabla compleja tiene mas de 5 columnas, baja a 10 puntos en impresion

### 11.3 Exportacion Word

Dependencia opcional:

```bash
bench pip install python-docx
```

Exportaciones disponibles desde `Paquete Estados Financieros Cliente`:
- `Exportar Word EEFF` para paquetes no auditados
- `Exportar Word Revision Auditada` para flujo auditado
- `Exportar Carta de Remision` como Word independiente y sin seguimiento documental

Reglas actuales del Word:
- Arial Narrow
- tamano 12
- texto negro
- cada estado financiero en pagina separada
- cada nota en pagina separada
- si una tabla compleja tiene mas de 5 columnas, esa pagina pasa a horizontal

## 12. Facturacion, rentabilidad y cobranza

La app integra la operacion del despacho con:
- `Sales Invoice`
- `Payment Entry`
- `Timesheet`

Desde `Encargo Contable` y `Rentabilidad y Cobranza` se puede revisar:
- ingreso facturado
- cobrado
- saldo por cobrar
- cartera vencida
- aging
- margen
- WIP

`Seguimiento Cobranza` registra las gestiones de cobro y puede usar correo templado.

## 13. Reportes y paneles

Reportes gerenciales incluidos:
- `Resumen de Tareas por Encargo`
- `Resumen Rentabilidad y Cobranza`
- `Cartera Gerencial por Encargo`
- `Estado Gerencial de Auditoria`
- `Seguimiento Gerencial de Requerimientos`
- `Margen por Encargo y Servicio`

## 14. Data demo

Las utilidades demo estan deshabilitadas por defecto.

Para habilitarlas temporalmente en un sitio de desarrollo, agrega en `site_config.json`:

```json
{
  "gestion_contable_enable_dummy_tools": 1
}
```

Luego ejecuta:

```bash
bench --site [sitio] clear-cache
```

Desde `Configuracion Despacho Contable` podras:
- generar data demo
- limpiar data demo

El dataset demo actual incluye:
- multiples clientes
- operacion de meses recientes
- clientes de contabilidad
- auditorias completas y en proceso
- portal cliente
- EEFF del cliente
- facturas, pagos y cobranza

## 15. Operacion recomendada

### 15.1 Clientes de contabilidad

1. Crear o actualizar `Cliente Contable`
2. Crear `Periodo Contable`
3. Formalizar `Contrato Comercial` si aplica
4. Crear `Encargo Contable`
5. Registrar tareas y documentos
6. Preparar `Paquete Estados Financieros Cliente`
7. Preparar estados, notas y ajustes
8. Imprimir o exportar `Word EEFF`
9. Facturar y registrar cobranza

### 15.2 Clientes auditados

1. Crear `Encargo Contable` de auditoria
2. Abrir `Expediente Auditoria`
3. Preparar matriz, papeles y hallazgos
4. Preparar `Paquete Estados Financieros Cliente`
5. Vincular `Informe Final Auditoria` y `Dictamen de Auditoria`
6. Emitir `Informe Completo de EEFF Auditados`
7. Exportar Word de revision y carta de remision cuando aplique

## 16. Soporte operativo

Si no ves cambios recientes en Desk:

```bash
bench --site [sitio] migrate
bench --site [sitio] clear-cache
bench build --app gestion_contable
bench restart
```

Si no funciona la exportacion Word, verifica `python-docx`.

Si un formato de impresion no refleja cambios recientes, ejecuta `migrate` para recargar metadata y print formats.

## 17. Referencias

- README general: [README.md](../README.md)
- App principal: `gestion_contable/gestion_contable`
