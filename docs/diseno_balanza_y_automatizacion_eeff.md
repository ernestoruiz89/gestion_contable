# Diseno Tecnico: Balanza de Comprobacion, Sumarias, EEFF y Notas

## 1. Objetivo

Disenar un flujo completo para:

- importar una balanza de comprobacion del cliente
- registrar ajustes y reclasificaciones
- publicar una balanza final normalizada como fuente unica de cifras
- generar o actualizar cedulas sumarias de auditoria
- actualizar estados financieros del cliente
- actualizar notas a los estados financieros, incluyendo `cifras_nota` y `celdas_tabulares`

El diseno esta aterrizado a la arquitectura actual de `gestion_contable`, que ya incluye:

- `Documento Contable` como repositorio de evidencia y archivo fuente
- `Paquete Estados Financieros Cliente` como contenedor del juego de EEFF
- `Estado Financiero Cliente` y `Linea Estado Financiero Cliente`
- `Nota Estado Financiero`, `Cifra Nota Estado Financiero` y tablas complejas
- `Papel Trabajo Auditoria` como contenedor de cedulas y papeles de trabajo

## 2. Principios de diseno

### 2.1 Fuente unica

Ningun estado, nota o sumaria debe leer directamente del archivo importado. Todo debe leer de una version publicada de balanza normalizada.

### 2.2 Separacion de capas

El proceso se divide en cuatro capas:

1. evidencia documental
2. datos contables normalizados
3. reglas de mapeo
4. artefactos de salida

### 2.3 Trazabilidad completa

Cada cifra automatica debe poder responder:

- de que version de balanza provino
- con que regla se calculo
- cuando se recalculo
- quien ejecuto el proceso

### 2.4 Convivencia con contenido manual

No todo sale de la balanza. El modelo debe soportar:

- datos automaticos desde balanza
- datos desde auxiliares en una fase posterior
- sobreescritura manual controlada

### 2.5 Reutilizacion del motor

La misma capa de mapeo debe servir para:

- cedulas sumarias
- lineas de estados financieros
- cifras simples de notas
- celdas de tablas complejas

## 3. Alcance funcional

### 3.1 Incluido

- importacion inicial de balanza en CSV
- soporte a balanza original, ajustada, reclasificada y final
- publicacion de una version final vigente
- mapeo automatico a sumarias, EEFF y notas
- soporte a actual y comparativo
- logs de ejecucion y diferencias

### 3.2 No incluido en la primera entrega

- lectura nativa de Excel con formatos arbitrarios
- auxiliares de cartera, inventarios, activos fijos o impuestos
- consolidacion multi-company
- conversion multi-moneda

## 4. Arquitectura general

```text
Archivo cliente / ERP
    -> Documento Contable
    -> Version Balanza Cliente (importada)
    -> Ajustes y Reclasificaciones
    -> Version Balanza Cliente (publicada)
    -> Motor de Mapeo Contable
       -> Cedulas Sumarias
       -> Estados Financieros
       -> Notas y Tablas Complejas
    -> Log de Ejecucion
```

## 5. Modelo de datos propuesto

## 5.1 Nuevos doctypes

### A. `Version Balanza Cliente`

Cabecera versionada de la balanza.

Campos propuestos:

- `nombre_version`
- `cliente`
- `company`
- `periodo_contable`
- `encargo_contable`
- `expediente_auditoria`
- `paquete_estados_financieros_cliente`
- `fecha_corte`
- `tipo_version`
  - `Original`
  - `Ajustada`
  - `Reclasificada`
  - `Final Publicada`
- `version`
- `es_version_vigente`
- `estado_version`
  - `Borrador`
  - `Importada`
  - `Validada`
  - `Publicada`
  - `Reemplazada`
- `rol_periodo`
  - `Actual`
  - `Comparativo`
  - `Otro`
- `documento_contable_fuente`
- `archivo_fuente_file`
- `hash_fuente_sha256`
- `moneda_presentacion`
- `total_debitos`
- `total_creditos`
- `saldo_neto`
- `cuadra`
- `total_lineas`
- `total_cuentas_sin_mapear`
- `ultima_publicacion`
- `publicado_por`
- `observaciones`

Notas de diseno:

- Debe ser un doctype de cabecera.
- No debe cargar miles de lineas como child table dentro del form.
- Debe tener botones custom para importar, validar, publicar y recalcular salidas.

### B. `Linea Balanza Cliente`

Detalle normalizado de una `Version Balanza Cliente`.

Recomendacion:

- usar doctype regular enlazado por link, no `istable`
- motivo: la balanza puede tener un volumen muy superior al de una tabla hija comun

Campos propuestos:

- `version_balanza_cliente`
- `row_no`
- `codigo_cuenta`
- `descripcion_cuenta`
- `periodo_linea`
- `centro_costo`
- `debe_mes_actual`
- `haber_mes_actual`
- `debe_saldo`
- `haber_saldo`
- `saldo_final`
- `cuenta_padre`
- `nivel_cuenta`
- `tipo_cuenta`
- `naturaleza`
  - `Activo`
  - `Pasivo`
  - `Patrimonio`
  - `Ingreso`
  - `Gasto`
  - `Otro`
- `segmento`
- `tercero`
- `saldo_neto`
- `origen_linea`
  - `Importada`
  - `Ajuste`
  - `Reclasificacion`
  - `Calculada`
- `linea_fuente_externa`
- `cuenta_normalizada`
- `comentario`

Notas de diseno:

- `debe_mes_actual` y `haber_mes_actual` representan el movimiento del mes.
- `debe_saldo` y `haber_saldo` representan el saldo acumulado segregado por naturaleza.
- `saldo_final` es un valor derivado internamente por el sistema.
- `saldo_neto` es el campo canonico interno para calculo y mapeo.
- `saldo_final` y `saldo_neto` se derivan a partir de `debe_saldo` y `haber_saldo`
- la regla de derivacion debe quedar parametrizable por cliente si el despacho maneja una convencion especial de signos

### C. `Movimiento Balanza Cliente`

Documento de movimientos manuales sobre la balanza.

Campos propuestos:

- `tipo_movimiento`
  - `Ajuste`
  - `Reclasificacion`
- `cliente`
- `company`
- `periodo_contable`
- `version_balanza_base`
- `version_balanza_resultante`
- `fecha_movimiento`
- `descripcion`
- `documento_contable_soporte`
- `estado_movimiento`
  - `Borrador`
  - `Aplicado`
  - `Anulado`
- `aprobado_por`
- `observaciones`

### D. `Linea Movimiento Balanza Cliente`

Tabla hija del movimiento.

Campos propuestos:

- `codigo_cuenta_origen`
- `codigo_cuenta_destino`
- `descripcion`
- `debito`
- `credito`
- `saldo_neto`
- `naturaleza`
- `centro_costo`
- `tercero`
- `comentario`

Reglas:

- `Ajuste` debe cuadrar debitos y creditos.
- `Reclasificacion` debe mover saldo sin alterar el total neto del conjunto.

### E. `Esquema Mapeo Contable`

Cabecera de configuracion reusable.

Campos propuestos:

- `nombre_esquema`
- `cliente`
- `company`
- `marco_contable`
- `tipo_paquete`
- `activo`
- `version`
- `es_vigente`
- `aplica_auditoria`
- `aplica_contabilidad`
- `descripcion`

Debe existir una sola version vigente por combinacion:

- `cliente`
- `company`
- `marco_contable`
- `tipo_paquete`

### F. `Regla Mapeo Contable`

Regla atomica de transformacion desde balanza hacia un destino.

Campos propuestos:

- `esquema_mapeo_contable`
- `activo`
- `orden_ejecucion`
- `destino_tipo`
  - `Cedula Sumaria`
  - `Linea Estado`
  - `Cifra Nota`
  - `Celda Nota`
- `origen_version`
  - `Actual`
  - `Comparativo`
- `selector_tipo`
  - `Cuenta Exacta`
  - `Prefijo`
  - `Rango`
  - `Lista`
  - `Regex`
  - `Todas`
- `selector_valor`
- `filtro_naturaleza`
- `filtro_centro_costo`
- `filtro_tercero`
- `filtro_segmento`
- `operacion_agregacion`
  - `Saldo Neto`
  - `Saldo Deudor`
  - `Saldo Acreedor`
  - `Debito`
  - `Credito`
- `signo_presentacion`
  - `Normal`
  - `Inverso`
- `redondear_entero`
- `destino_codigo_sumaria`
- `destino_tipo_estado`
- `destino_codigo_linea_estado`
- `destino_numero_nota`
- `destino_codigo_cifra`
- `destino_seccion_id`
- `destino_codigo_fila`
- `destino_codigo_columna`
- `sobrescribir_manual`
- `obligatoria`
- `comentario`

Regla de unicidad recomendada:

- una regla activa por destino final y `origen_version`
- si se permiten varias reglas al mismo destino, el sistema las suma

### G. `Ejecucion Actualizacion EEFF`

Bitacora de cada corrida.

Campos propuestos:

- `cliente`
- `company`
- `paquete_estados_financieros_cliente`
- `version_balanza_actual`
- `version_balanza_comparativa`
- `esquema_mapeo_contable`
- `fecha_ejecucion`
- `ejecutado_por`
- `estado_ejecucion`
  - `En Proceso`
  - `Completada`
  - `Completada con Alertas`
  - `Fallida`
- `sumarias_actualizadas`
- `estados_actualizados`
- `notas_actualizadas`
- `reglas_ejecutadas`
- `cuentas_sin_mapear`
- `destinos_sin_regla`
- `destinos_bloqueados_manual`
- `errores`
- `detalle_json`

### H. `Resultado Actualizacion EEFF`

Detalle hijo o doctype asociado al log.

Campos propuestos:

- `ejecucion_actualizacion_eeff`
- `tipo_resultado`
  - `Warning`
  - `Error`
  - `Info`
- `objeto_tipo`
  - `Cuenta`
  - `Sumaria`
  - `Estado`
  - `Nota`
  - `Celda`
- `objeto_referencia`
- `mensaje`

## 5.2 Cambios a doctypes existentes

### A. `Paquete Estados Financieros Cliente`

Agregar:

- `version_balanza_actual`
- `version_balanza_comparativa`
- `esquema_mapeo_contable`
- `fecha_ultima_actualizacion_automatica`
- `ultima_ejecucion_actualizacion_eeff`
- `alertas_actualizacion_automatica`

Botones custom:

- `Actualizar desde Balanza`
- `Ver Log de Actualizacion`
- `Ver Cuentas sin Mapear`

### B. `Linea Estado Financiero Cliente`

Agregar:

- `codigo_linea_estado`
- `es_manual`
- `origen_dato`
  - `Manual`
  - `Balanza`
  - `Formula`
- `calculo_automatico`
- `formula_lineas`
- `ultima_regla_mapeo`
- `ultima_actualizacion_automatica`

Motivo:

- hoy las lineas tienen montos, pero no una clave estable ni formulas internas
- para automatizar bien, los detalles deben mapearse por codigo y los totales deben calcularse por formula

### C. `Estado Financiero Cliente`

Agregar:

- `version_balanza_actual`
- `version_balanza_comparativa`
- `fecha_ultima_actualizacion_automatica`
- `ultima_ejecucion_actualizacion_eeff`

### D. `Cifra Nota Estado Financiero`

Agregar:

- `codigo_cifra`
- `es_manual`
- `origen_dato`
  - `Manual`
  - `Balanza`
  - `Formula`
- `calculo_automatico`
- `formula_cifras`
- `ultima_regla_mapeo`
- `ultima_actualizacion_automatica`

Motivo:

- mapear por `concepto` no es robusto
- la cifra necesita identificador estable y capacidad de formula

### E. `Nota Estado Financiero`

Agregar:

- `version_balanza_actual`
- `version_balanza_comparativa`
- `fecha_ultima_actualizacion_automatica`
- `ultima_ejecucion_actualizacion_eeff`
- `total_cifras_automaticas`
- `total_celdas_automaticas`

### F. `Celda Tabla Nota Estado Financiero`

Agregar:

- `origen_dato`
  - `Manual`
  - `Balanza`
  - `Formula Fila`
  - `Formula Columna`
- `ultima_regla_mapeo`
- `ultima_actualizacion_automatica`

Notas:

- la llave natural ya existe: `seccion_id + codigo_fila + codigo_columna`
- `es_manual` ya permite bloquear sobreescritura automatica

### G. `Papel Trabajo Auditoria`

Agregar soporte especifico para `Cedula Sumaria`.

Campos propuestos:

- `version_balanza_cliente`
- `codigo_sumaria`
- `linea_estado_origen`
- `nota_origen`
- `actualizado_desde_balanza`
- `fecha_ultima_actualizacion_automatica`
- `ultima_ejecucion_actualizacion_eeff`
- `lineas_cedula_sumaria`

### H. `Linea Cedula Sumaria Auditoria`

Nueva child table de `Papel Trabajo Auditoria`.

Campos propuestos:

- `codigo_linea`
- `descripcion`
- `nivel`
- `tipo_linea`
  - `Detalle`
  - `Subtotal`
  - `Total`
- `calculo_automatico`
- `formula_lineas`
- `monto_actual`
- `monto_comparativo`
- `comentario`
- `origen_dato`
- `ultima_regla_mapeo`

## 6. Flujo operativo objetivo

## 6.1 Carga

1. Se registra el archivo fuente como `Documento Contable`.
2. Desde ese documento o desde la `Version Balanza Cliente`, el usuario ejecuta `Importar balanza`.
3. El sistema parsea el CSV y crea una version `Original`.
4. El sistema valida columnas obligatorias y cuadratura.

Layout canonico de importacion propuesto:

- `cuenta`
- `descripcion`
- `debe_mes_actual`
- `haber_mes_actual`
- `debe_saldo`
- `haber_saldo`
- `centro_costo`
- `periodo`

Normalizacion interna sugerida:

- `cuenta` -> `codigo_cuenta`
- `descripcion` -> `descripcion_cuenta`
- `periodo` -> `periodo_linea`

Reglas:

- `periodo` puede venir por linea para compatibilidad con archivos externos, pero la referencia oficial sigue siendo `periodo_contable` de la cabecera
- `debe_mes_actual` y `haber_mes_actual` se usan para conciliacion de movimiento mensual
- `debe_saldo` y `haber_saldo` se usan para validar la posicion acumulada de la cuenta
- `saldo_final` se deriva internamente desde `debe_saldo` y `haber_saldo`
- `saldo_neto` se calcula desde `saldo_final`, segun la convencion de signos definida para el cliente

Columnas opcionales de segunda fase:

- `tercero`
- `segmento`
- `cuenta_padre`
- `nivel_cuenta`

## 6.2 Ajustes y reclasificaciones

1. El usuario registra `Movimiento Balanza Cliente` tipo `Ajuste` o `Reclasificacion`.
2. El sistema recalcula la version resultante.
3. Se conserva la cadena de trazabilidad:
   - version base
   - movimiento
   - version resultante

## 6.3 Publicacion

1. El usuario publica una version `Final Publicada`.
2. El paquete de EEFF vincula:
   - balanza actual publicada
   - balanza comparativa publicada
   - esquema de mapeo contable

## 6.4 Actualizacion automatica

1. El usuario entra a `Paquete Estados Financieros Cliente`.
2. Ejecuta `Actualizar desde Balanza`.
3. El motor:
   - carga balanza actual y comparativa
   - carga el esquema de mapeo
   - actualiza sumarias
   - actualiza lineas de estados
   - actualiza cifras simples de notas
   - actualiza celdas base de tablas complejas
   - recalcula formulas
   - registra log y alertas

## 7. Motor de calculo y materializacion

## 7.1 Fuente de datos

El motor nunca lee del archivo CSV directo. Lee siempre de:

- `Version Balanza Cliente` actual
- `Version Balanza Cliente` comparativa

## 7.2 Orden de ejecucion

Orden recomendado:

1. validar balanzas publicadas
2. materializar sumarias
3. materializar lineas base de EEFF
4. recalcular formulas de EEFF
5. materializar cifras base de notas
6. materializar celdas base de notas
7. recalcular formulas de notas
8. persistir metadatos de actualizacion
9. generar log y alertas

## 7.3 Reglas de prioridad

Prioridad de valor en un destino:

1. si `es_manual = 1` y no se marco `sobrescribir_manual`, no se toca
2. si hay regla de balanza aplicable, se actualiza
3. si el destino es automatico por formula, se recalcula
4. si no hay regla, se mantiene el valor previo y se registra alerta

## 7.4 Destinos base y destinos derivados

Se deben mapear solo destinos base.

Destinos base:

- detalles de sumarias
- lineas detalle de estados
- cifras simples sin formula
- celdas detalle de tablas complejas

Destinos derivados:

- subtotales
- totales
- filas por formula
- columnas por formula

Los destinos derivados no deben leer directamente de la balanza.

## 7.5 Calculo de EEFF

Se recomienda extender `Linea Estado Financiero Cliente` para que soporte formulas similares a las notas.

Ejemplo:

- `EFE` detalle se mapea por balanza
- `ACT_CORR` subtotal se calcula por formula `+EFE,+CXC,+INV`
- `TOTAL_ACTIVO` se calcula por formula `+ACT_CORR,+ACT_NO_CORR`

## 7.6 Calculo de notas

### `cifras_nota`

Cada fila debe tener `codigo_cifra`.

Ejemplo:

- `EFE_CAJA`
- `EFE_BANCOS`
- `EFE_TOTAL`

Las dos primeras pueden venir de balanza. La tercera puede venir por formula.

### `celdas_tabulares`

Cada celda base se identifica con:

- `seccion_id`
- `codigo_fila`
- `codigo_columna`

Ejemplo:

- `SEC-01 / NAL / VIG_2025`
- `SEC-01 / EXT / VIG_2025`
- `SEC-01 / TOT / VIG_2025`

Las celdas detalle se actualizan por balanza. Las columnas o filas de total usan formulas ya soportadas por la nota.

## 7.7 Comparativo

El motor debe soportar dos fuentes:

- actual
- comparativa

Mapeo por tipo de destino:

- `Linea Estado`: `monto_actual` o `monto_comparativo`
- `Cifra Nota`: `monto_actual` o `monto_comparativo`
- `Celda Nota`: una regla por celda y periodo, o reglas separadas con `origen_version`
- `Cedula Sumaria`: `monto_actual` o `monto_comparativo`

## 8. Ejemplos de reglas

## 8.1 Efectivo en estado de situacion financiera

Regla:

- `destino_tipo = Linea Estado`
- `destino_tipo_estado = Estado de Situacion Financiera`
- `destino_codigo_linea_estado = EFE`
- `selector_tipo = Prefijo`
- `selector_valor = 1101,1102`
- `operacion_agregacion = Saldo Neto`
- `signo_presentacion = Normal`
- `origen_version = Actual`

## 8.2 Nota de efectivo, cifra simple

Regla:

- `destino_tipo = Cifra Nota`
- `destino_numero_nota = 4`
- `destino_codigo_cifra = BANCOS_MN`
- `selector_tipo = Lista`
- `selector_valor = 1102-01,1102-02`

## 8.3 Nota con tabla compleja

Celda:

- `destino_tipo = Celda Nota`
- `destino_numero_nota = 6`
- `destino_seccion_id = SEC-01`
- `destino_codigo_fila = NAL`
- `destino_codigo_columna = VIG_2025`
- `selector_tipo = Prefijo`
- `selector_valor = 1201`

Luego:

- fila `TOT` se calcula por formula `+NAL,+EXT`
- columna `TOT_2025` se calcula por formula `+VIG_2025,+VENC_2025`

## 9. UI y experiencia de usuario

## 9.1 Formulario `Version Balanza Cliente`

Botones:

- `Importar CSV`
- `Validar`
- `Aplicar Movimientos`
- `Publicar`
- `Vista Previa de Cuentas sin Mapear`
- `Actualizar Paquete EEFF`

Tableros:

- resumen de cuadratura
- resumen de cuentas mapeadas / no mapeadas
- artefactos impactados

## 9.2 Formulario `Paquete Estados Financieros Cliente`

Nuevos campos visibles:

- `version_balanza_actual`
- `version_balanza_comparativa`
- `esquema_mapeo_contable`
- `ultima_ejecucion_actualizacion_eeff`

Botones:

- `Actualizar desde Balanza`
- `Ver diferencias`
- `Ver bitacora`

## 9.3 Estado Financiero y Nota

Se recomienda mostrar insignias visuales:

- `Manual`
- `Balanza`
- `Formula`
- `Actualizado automaticamente`

## 9.4 Pagina futura opcional

Pagina dedicada `constructor-de-mapeo-contable` para:

- buscar cuenta
- probar reglas
- ver vista previa de destino
- validar huecos de mapeo

No es obligatoria en la primera fase.

## 10. Servicios y organizacion de codigo

Crear un nuevo namespace:

`gestion_contable/gestion_contable/services/balanza/`

Archivos sugeridos:

- `importing.py`
- `normalization.py`
- `movements.py`
- `mapping.py`
- `materialize_sumarias.py`
- `materialize_states.py`
- `materialize_notes.py`
- `validators.py`
- `queries.py`
- `diffs.py`

Y utilidades comunes:

`gestion_contable/gestion_contable/utils/balanza.py`

Funciones publicas sugeridas:

- `importar_balanza_cliente(documento_contable, version_name=None, replace=0)`
- `validar_version_balanza(version_name)`
- `publicar_version_balanza(version_name)`
- `aplicar_movimientos_balanza(version_name)`
- `actualizar_paquete_desde_balanza(package_name, force_manual=0)`
- `generar_sumarias_desde_balanza(expediente_name=None, package_name=None)`
- `obtener_diferencias_balanza_vs_eeff(package_name)`

## 11. Validaciones clave

## 11.1 Importacion

- el archivo debe tener columnas minimas
- los codigos de cuenta no pueden venir vacios
- los montos deben ser numericos
- `debe_mes_actual` y `haber_mes_actual` deben ser numericos
- `debe_saldo` y `haber_saldo` deben ser numericos
- `saldo_final` debe derivarse sin ambiguedad segun la regla configurada
- la balanza publicada debe soportar la cuadratura general definida para el despacho

## 11.2 Publicacion

- no puede publicarse si la balanza no cuadra
- no puede haber mas de una version vigente por:
  - cliente
  - company
  - periodo
  - rol_periodo
  - tipo_version final

## 11.3 Mapeo

- una regla no puede apuntar a un destino inexistente
- una regla obligatoria sin coincidencias genera alerta critica
- destinos manuales se respetan por defecto
- formulas no pueden ser circulares

## 11.4 Emision de paquete

Se recomienda bloquear `Emitido` si:

- falta balanza actual publicada
- el esquema de mapeo no esta asignado
- hay cuentas sin mapear marcadas como criticas
- hay notas requeridas con destinos sin poblar

## 12. Seguridad y gobierno

Roles sugeridos:

- `Auxiliar Contable del Despacho`
  - puede importar borradores de balanza
  - no puede publicar versiones ni ejecutar actualizacion final
- `Contador del Despacho`
  - puede validar, ajustar, reclasificar y publicar
- `Supervisor del Despacho`
  - puede ejecutar actualizacion y revisar resultados
- `Socio del Despacho`
  - puede aprobar politicas de automatizacion y emitir
- `System Manager`
  - administracion total

Todos los cambios de actualizacion automatica deben dejar:

- usuario
- fecha
- balanza usada
- reglas aplicadas

## 13. Reportes recomendados

- `Cuentas de Balanza sin Mapear`
- `Destinos sin Regla de Mapeo`
- `Diferencias entre Balanza y EEFF`
- `Notas con Celdas Manuales no Actualizadas`
- `Resumen de Ejecuciones de Actualizacion EEFF`

## 14. Migracion desde el modelo actual

## 14.1 Compatibilidad

El sistema debe seguir funcionando sin balanza automatizada.

Por tanto:

- los campos nuevos deben ser opcionales
- si no existe balanza vinculada, los EEFF y notas siguen siendo manuales
- la automatizacion se activa solo cuando el paquete tenga:
  - balanza actual
  - esquema de mapeo

## 14.2 Backfill

Migraciones sugeridas:

1. agregar campos nuevos a doctypes existentes
2. autogenerar `codigo_linea_estado` para lineas existentes
3. autogenerar `codigo_cifra` para cifras de nota existentes
4. marcar filas/celdas con contenido actual como `es_manual = 1` cuando aplique

## 15. Estrategia de implementacion por fases

## Fase 1. Base de balanza

- `Version Balanza Cliente`
- `Linea Balanza Cliente`
- importacion CSV
- validacion y publicacion

## Fase 2. Motor de mapeo y sumarias

- `Esquema Mapeo Contable`
- `Regla Mapeo Contable`
- `Papel Trabajo Auditoria` con lineas de cedula sumaria
- generacion automatica de sumarias

## Fase 3. Estados financieros

- extender `Linea Estado Financiero Cliente`
- soportar codigos y formulas
- actualizar montos actual/comparativo desde balanza

## Fase 4. Notas simples y tablas complejas

- extender `Cifra Nota Estado Financiero`
- extender `Celda Tabla Nota Estado Financiero`
- actualizar `cifras_nota`
- actualizar `celdas_tabulares`
- recalcular formulas de filas y columnas

## Fase 5. Bitacora, diferencias y controles de emision

- `Ejecucion Actualizacion EEFF`
- reportes de diferencias
- bloqueos de emision

## 16. Recomendacion final

La implementacion correcta no es un importador aislado de balanza. Debe construirse como una plataforma contable de cifras normalizadas con tres salidas:

- auditoria: cedulas sumarias
- presentacion: estados financieros
- revelacion: notas y tablas

La decision mas importante es esta:

- mapear solo nodos base
- calcular nodos derivados por formula

Eso reduce mantenimiento, evita duplicidad de reglas y hace que la balanza final pueda alimentar de forma consistente a todo el paquete de EEFF.
