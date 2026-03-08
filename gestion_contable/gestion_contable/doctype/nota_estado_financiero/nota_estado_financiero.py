import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt

from gestion_contable.gestion_contable.utils.estados_financieros import (
    get_note_line_references,
    get_required_note_numbers,
    normalize_note_number,
    sync_note_cross_references,
    sync_package_summary,
)
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_de_la_nota",
    "paquete_estados_financieros_cliente",
    "numero_nota",
    "titulo",
    "categoria_nota",
    "orden_presentacion",
    "es_requerida",
    "politica_contable",
    "contenido_narrativo",
    "cifras_nota",
    "secciones_estructuradas",
    "columnas_tabulares",
    "filas_tabulares",
    "celdas_tabulares",
    "observaciones_preparacion",
)
CATEGORIAS_NOTA = (
    "Base de Preparacion",
    "Politicas Contables",
    "Efectivo",
    "Cuentas por Cobrar",
    "Inventarios",
    "Propiedad Planta y Equipo",
    "Pasivos",
    "Patrimonio",
    "Ingresos",
    "Gastos",
    "Impuestos",
    "Partes Relacionadas",
    "Contingencias",
    "Hechos Posteriores",
    "Otra",
)
TIPOS_SECCION = ("Narrativa", "Tabla", "Texto y Tabla")
TIPOS_FILA = ("Detalle", "Subtotal", "Total", "Comentario")
TIPOS_DATO_COLUMNA = ("Texto", "Numero", "Moneda", "Porcentaje")
ALINEACIONES_COLUMNA = ("Left", "Center", "Right")
FORMATOS_NUMERO = ("Numero", "Moneda", "Porcentaje")
FORMULA_SPLIT_RE = re.compile(r"[\n,;]+")


class NotaEstadoFinanciero(Document):
    def autoname(self):
        if self.nombre_de_la_nota:
            self.name = self.nombre_de_la_nota
            return
        numero = normalize_note_number(self.numero_nota) or "SN"
        base_name = f"Nota {numero} - {self.paquete_estados_financieros_cliente or frappe.generate_hash(length=6)}"
        self.nombre_de_la_nota = self._build_unique_name(base_name)
        self.name = self.nombre_de_la_nota

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar notas a los estados financieros del cliente."))
        previous_doc = self.get_doc_before_save() if not self.is_new() else None
        self.sincronizar_desde_paquete()
        self.validar_categoria()
        self.normalizar_cifras()
        self.normalizar_secciones_estructuradas()
        self.normalizar_columnas_tabulares()
        self.normalizar_filas_tabulares()
        self.normalizar_celdas_tabulares()
        self.validar_contenido()
        self.validar_unicidad_numero()
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            label=_("la nota a los estados financieros del cliente"),
        )
        self.sincronizar_referencias_por_cambio_de_numero(previous_doc)
        self.sincronizar_referencias_cruzadas()

    def on_update(self):
        sync_package_summary(self.paquete_estados_financieros_cliente)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar notas a los estados financieros del cliente."))
        sync_package_summary(self.paquete_estados_financieros_cliente)

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Nota Estado Financiero", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Nota Estado Financiero", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_desde_paquete(self):
        if not self.paquete_estados_financieros_cliente:
            frappe.throw(_("Debes seleccionar un paquete de estados financieros del cliente."), title=_("Paquete Requerido"))
        if not frappe.db.exists("Paquete Estados Financieros Cliente", self.paquete_estados_financieros_cliente):
            frappe.throw(_("El paquete de estados financieros indicado no existe."), title=_("Paquete Invalido"))

        package = frappe.db.get_value(
            "Paquete Estados Financieros Cliente",
            self.paquete_estados_financieros_cliente,
            ["cliente", "periodo_contable"],
            as_dict=True,
        )
        self.cliente = package.cliente
        self.periodo_contable = package.periodo_contable
        self.numero_nota = normalize_note_number(self.numero_nota)
        if not self.numero_nota:
            frappe.throw(_("Debes indicar el numero de nota."), title=_("Numero Requerido"))
        self.nombre_de_la_nota = _build_note_display_name(self.paquete_estados_financieros_cliente, self.numero_nota)
        if not cstr(self.titulo or "").strip():
            self.titulo = f"Nota {self.numero_nota}"
        self.orden_presentacion = cint(self.orden_presentacion or 0)
        if not self.orden_presentacion and self.numero_nota.isdigit():
            self.orden_presentacion = cint(self.numero_nota)
        required_numbers, _missing = get_required_note_numbers(self.paquete_estados_financieros_cliente)
        self.es_requerida = int(self.numero_nota in required_numbers)

    def sincronizar_referencias_cruzadas(self):
        references = get_note_line_references(self.paquete_estados_financieros_cliente, self.numero_nota)
        current = [
            {
                "estado_financiero_cliente": row.estado_financiero_cliente,
                "tipo_estado": row.tipo_estado,
                "numero_linea": cint(row.numero_linea or 0),
                "codigo_rubro": row.codigo_rubro,
                "descripcion_linea_estado": row.descripcion_linea_estado,
                "linea_estado_name": row.linea_estado_name,
                "tipo_referencia": row.tipo_referencia,
                "obligatoria": cint(row.obligatoria or 0),
            }
            for row in self.referencias_cruzadas or []
        ]
        changed = current != references
        if changed:
            self.set("referencias_cruzadas", [])
            for reference in references:
                self.append("referencias_cruzadas", reference)
        self.total_referencias = len(references)
        return changed

    def validar_categoria(self):
        if self.categoria_nota and self.categoria_nota not in CATEGORIAS_NOTA:
            frappe.throw(_("La categoria de nota seleccionada no es valida."), title=_("Categoria Invalida"))
        self.categoria_nota = self.categoria_nota or "Otra"

    def normalizar_cifras(self):
        for idx, row in enumerate(self.cifras_nota or [], start=1):
            row.orden = cint(row.orden or idx)
            if not cstr(row.concepto or "").strip():
                frappe.throw(_("Cada cifra de nota debe indicar el concepto."), title=_("Concepto Requerido"))
        self.total_cifras = len(self.cifras_nota or [])

    def normalizar_secciones_estructuradas(self):
        seen = set()
        for idx, row in enumerate(self.secciones_estructuradas or [], start=1):
            row.orden = cint(row.orden or idx)
            row.tipo_seccion = row.tipo_seccion or "Narrativa"
            if row.tipo_seccion not in TIPOS_SECCION:
                frappe.throw(_("El tipo de seccion <b>{0}</b> no es valido.").format(row.tipo_seccion), title=_("Seccion Invalida"))
            if not cstr(row.titulo_seccion or "").strip():
                frappe.throw(_("Cada seccion estructurada debe indicar un titulo."), title=_("Titulo Requerido"))
            row.seccion_id = cstr(row.seccion_id or f"SEC-{idx:02d}").strip().upper()
            if row.seccion_id in seen:
                frappe.throw(_("La seccion <b>{0}</b> esta duplicada dentro de la nota.").format(row.seccion_id), title=_("Seccion Duplicada"))
            seen.add(row.seccion_id)

    def normalizar_columnas_tabulares(self):
        section_ids = {row.seccion_id for row in self.secciones_estructuradas or []}
        seen = set()
        for idx, row in enumerate(self.columnas_tabulares or [], start=1):
            row.orden = cint(row.orden or idx)
            row.seccion_id = cstr(row.seccion_id or "").strip().upper()
            row.codigo_columna = cstr(row.codigo_columna or "").strip().upper()
            row.tipo_dato = row.tipo_dato or "Texto"
            row.alineacion = row.alineacion or "Left"
            row.calculo_automatico = cint(row.calculo_automatico or 0)
            row.formula_columnas = cstr(row.formula_columnas or "").strip().upper()
            if row.seccion_id not in section_ids:
                frappe.throw(_("La columna <b>{0}</b> referencia una seccion inexistente.").format(row.codigo_columna or idx), title=_("Seccion Invalida"))
            if not row.codigo_columna or not cstr(row.etiqueta or "").strip():
                frappe.throw(_("Cada columna tabular debe indicar codigo y etiqueta."), title=_("Columna Invalida"))
            if row.tipo_dato not in TIPOS_DATO_COLUMNA:
                frappe.throw(_("El tipo de dato de la columna <b>{0}</b> no es valido.").format(row.codigo_columna), title=_("Columna Invalida"))
            if row.alineacion not in ALINEACIONES_COLUMNA:
                frappe.throw(_("La alineacion de la columna <b>{0}</b> no es valida.").format(row.codigo_columna), title=_("Columna Invalida"))
            if row.formula_columnas and not row.calculo_automatico:
                row.calculo_automatico = 1
            if row.calculo_automatico and not row.formula_columnas:
                frappe.throw(_("La columna <b>{0}</b> esta marcada como calculo automatico pero no tiene formula.").format(row.codigo_columna), title=_("Formula Requerida"))
            key = (row.seccion_id, row.codigo_columna)
            if key in seen:
                frappe.throw(_("La columna <b>{0}</b> esta duplicada en la seccion <b>{1}</b>.").format(row.codigo_columna, row.seccion_id), title=_("Columna Duplicada"))
            seen.add(key)

    def normalizar_filas_tabulares(self):
        section_ids = {row.seccion_id for row in self.secciones_estructuradas or []}
        seen = set()
        for idx, row in enumerate(self.filas_tabulares or [], start=1):
            row.orden = cint(row.orden or idx)
            row.nivel = cint(row.nivel or 1)
            row.seccion_id = cstr(row.seccion_id or "").strip().upper()
            row.codigo_fila = cstr(row.codigo_fila or "").strip().upper()
            row.tipo_fila = row.tipo_fila or "Detalle"
            row.calculo_automatico = cint(row.calculo_automatico or 0)
            row.formula_filas = cstr(row.formula_filas or "").strip().upper()
            if row.seccion_id not in section_ids:
                frappe.throw(_("La fila <b>{0}</b> referencia una seccion inexistente.").format(row.codigo_fila or idx), title=_("Seccion Invalida"))
            if not row.codigo_fila or not cstr(row.descripcion or "").strip():
                frappe.throw(_("Cada fila tabular debe indicar codigo y descripcion."), title=_("Fila Invalida"))
            if row.tipo_fila not in TIPOS_FILA:
                frappe.throw(_("El tipo de fila <b>{0}</b> no es valido.").format(row.codigo_fila), title=_("Fila Invalida"))
            if row.formula_filas and not row.calculo_automatico:
                row.calculo_automatico = 1
            if row.calculo_automatico and not row.formula_filas:
                frappe.throw(_("La fila <b>{0}</b> esta marcada como calculo automatico pero no tiene formula.").format(row.codigo_fila), title=_("Formula Requerida"))
            key = (row.seccion_id, row.codigo_fila)
            if key in seen:
                frappe.throw(_("La fila <b>{0}</b> esta duplicada en la seccion <b>{1}</b>.").format(row.codigo_fila, row.seccion_id), title=_("Fila Duplicada"))
            seen.add(key)

    def normalizar_celdas_tabulares(self):
        section_ids = {row.seccion_id for row in self.secciones_estructuradas or []}
        row_keys = {(row.seccion_id, row.codigo_fila) for row in self.filas_tabulares or []}
        col_keys = {(row.seccion_id, row.codigo_columna) for row in self.columnas_tabulares or []}
        seen = set()
        for row in self.celdas_tabulares or []:
            row.seccion_id = cstr(row.seccion_id or "").strip().upper()
            row.codigo_fila = cstr(row.codigo_fila or "").strip().upper()
            row.codigo_columna = cstr(row.codigo_columna or "").strip().upper()
            row.formato_numero = row.formato_numero or "Numero"
            if row.seccion_id not in section_ids:
                frappe.throw(_("Una celda tabular referencia una seccion inexistente."), title=_("Seccion Invalida"))
            if (row.seccion_id, row.codigo_fila) not in row_keys:
                frappe.throw(_("La celda de la fila <b>{0}</b> referencia una fila inexistente.").format(row.codigo_fila), title=_("Fila Invalida"))
            if (row.seccion_id, row.codigo_columna) not in col_keys:
                frappe.throw(_("La celda de la columna <b>{0}</b> referencia una columna inexistente.").format(row.codigo_columna), title=_("Columna Invalida"))
            if row.formato_numero not in FORMATOS_NUMERO:
                frappe.throw(_("El formato numerico de una celda no es valido."), title=_("Celda Invalida"))
            key = (row.seccion_id, row.codigo_fila, row.codigo_columna)
            if key in seen:
                frappe.throw(_("La celda para fila <b>{0}</b> y columna <b>{1}</b> esta duplicada.").format(row.codigo_fila, row.codigo_columna), title=_("Celda Duplicada"))
            seen.add(key)
            if row.valor_texto in (None, "") and row.valor_numero in (None, ""):
                frappe.throw(_("Cada celda tabular debe tener valor texto o valor numero."), title=_("Celda Vacia"))

        for section in self.secciones_estructuradas or []:
            if section.tipo_seccion in ("Tabla", "Texto y Tabla"):
                has_columns = any(col.seccion_id == section.seccion_id for col in self.columnas_tabulares or [])
                has_rows = any(fila.seccion_id == section.seccion_id for fila in self.filas_tabulares or [])
                has_cells = any(celda.seccion_id == section.seccion_id for celda in self.celdas_tabulares or [])
                if not (has_columns and has_rows and has_cells):
                    frappe.throw(_("La seccion <b>{0}</b> requiere columnas, filas y celdas para su tabla estructurada.").format(section.titulo_seccion), title=_("Tabla Incompleta"))

        self.validar_formulas_tabulares()

    def validar_contenido(self):
        has_narrative = bool(cstr(self.contenido_narrativo or "").strip())
        has_policy = bool(cstr(self.politica_contable or "").strip())
        has_figures = bool(self.cifras_nota)
        has_structured = bool(self.secciones_estructuradas)
        if not any((has_narrative, has_policy, has_figures, has_structured)):
            frappe.throw(
                _("La nota debe incluir contenido narrativo, politica contable, cifras simples o al menos una seccion estructurada."),
                title=_("Contenido Requerido"),
            )

    def sincronizar_referencias_por_cambio_de_numero(self, previous_doc=None):
        previous_doc = previous_doc or (self.get_doc_before_save() if not self.is_new() else None)
        if not previous_doc:
            return False

        previous_number = normalize_note_number(previous_doc.numero_nota)
        current_number = normalize_note_number(self.numero_nota)
        if not previous_number or not current_number or previous_number == current_number:
            return False

        if cstr(previous_doc.titulo or "").strip() == f"Nota {previous_number}":
            self.titulo = f"Nota {current_number}"

        _remap_note_number_references(
            self.paquete_estados_financieros_cliente,
            {previous_number: current_number},
        )
        return True

    def validar_unicidad_numero(self):
        existing = frappe.get_all(
            "Nota Estado Financiero",
            filters={
                "name": ["!=", self.name or ""],
                "paquete_estados_financieros_cliente": self.paquete_estados_financieros_cliente,
                "numero_nota": self.numero_nota,
            },
            fields=["name"],
            limit_page_length=1,
        )
        if existing:
            frappe.throw(
                _("Ya existe una nota numero <b>{0}</b> dentro de este paquete.").format(self.numero_nota),
                title=_("Nota Duplicada"),
            )

    def validar_formulas_tabulares(self):
        row_codes_by_section = {}
        col_codes_by_section = {}

        for row in self.filas_tabulares or []:
            row_codes_by_section.setdefault(row.seccion_id, set()).add(row.codigo_fila)
        for row in self.columnas_tabulares or []:
            col_codes_by_section.setdefault(row.seccion_id, set()).add(row.codigo_columna)

        row_graph = {}
        col_graph = {}

        for row in self.filas_tabulares or []:
            refs = self._parse_formula_references(row.formula_filas, _("la fila {0}").format(row.codigo_fila))
            if row.codigo_fila in {code for _sign, code in refs}:
                frappe.throw(_("La fila <b>{0}</b> no puede referenciarse a si misma en la formula.").format(row.codigo_fila), title=_("Formula Invalida"))
            for _sign, code in refs:
                if code not in row_codes_by_section.get(row.seccion_id, set()):
                    frappe.throw(_("La fila <b>{0}</b> referencia la fila inexistente <b>{1}</b>.").format(row.codigo_fila, code), title=_("Formula Invalida"))
            row_graph[(row.seccion_id, row.codigo_fila)] = [(row.seccion_id, code) for _sign, code in refs]

        for row in self.columnas_tabulares or []:
            refs = self._parse_formula_references(row.formula_columnas, _("la columna {0}").format(row.codigo_columna))
            if row.codigo_columna in {code for _sign, code in refs}:
                frappe.throw(_("La columna <b>{0}</b> no puede referenciarse a si misma en la formula.").format(row.codigo_columna), title=_("Formula Invalida"))
            for _sign, code in refs:
                if code not in col_codes_by_section.get(row.seccion_id, set()):
                    frappe.throw(_("La columna <b>{0}</b> referencia la columna inexistente <b>{1}</b>.").format(row.codigo_columna, code), title=_("Formula Invalida"))
            col_graph[(row.seccion_id, row.codigo_columna)] = [(row.seccion_id, code) for _sign, code in refs]

        self._validate_dependency_cycles(row_graph, _("las formulas de filas"))
        self._validate_dependency_cycles(col_graph, _("las formulas de columnas"))

    def _validate_dependency_cycles(self, graph, label):
        visited = set()
        visiting = set()

        def visit(node):
            if node in visiting:
                frappe.throw(_("Se detecto una referencia circular en {0}.").format(label), title=_("Formula Invalida"))
            if node in visited:
                return
            visiting.add(node)
            for child in graph.get(node, []):
                visit(child)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)

    def _parse_formula_references(self, expression, label):
        expression = cstr(expression or "").strip().upper()
        if not expression:
            return []

        references = []
        for token in FORMULA_SPLIT_RE.split(expression):
            token = cstr(token or "").strip().upper()
            if not token:
                continue
            sign = 1
            if token[0] in "+-":
                sign = -1 if token[0] == "-" else 1
                token = token[1:].strip()
            if not token:
                frappe.throw(_("La formula de {0} contiene un operador sin codigo.").format(label), title=_("Formula Invalida"))
            references.append((sign, token))

        if not references:
            frappe.throw(_("La formula de {0} no contiene codigos validos.").format(label), title=_("Formula Invalida"))
        return references

    def get_structured_sections(self):
        sections = sorted(self.secciones_estructuradas or [], key=lambda row: (cint(row.orden or 0), row.idx or 0))
        columns = sorted(self.columnas_tabulares or [], key=lambda row: (row.seccion_id, cint(row.orden or 0), row.idx or 0))
        rows = sorted(self.filas_tabulares or [], key=lambda row: (row.seccion_id, cint(row.orden or 0), row.idx or 0))
        cells = list(self.celdas_tabulares or [])
        row_lookup = {(row.seccion_id, row.codigo_fila): row for row in rows}
        column_lookup = {(row.seccion_id, row.codigo_columna): row for row in columns}
        cell_map = {
            (cell.seccion_id, cell.codigo_fila, cell.codigo_columna): {
                "valor_texto": cstr(cell.valor_texto or "").strip(),
                "valor_numero": None if cell.valor_numero in (None, "") else flt(cell.valor_numero),
                "formato_numero": cell.formato_numero or "Numero",
                "comentario": cell.comentario,
            }
            for cell in cells
        }
        numeric_cache = {}

        def get_numeric_value(section_id, row_code, column_code, stack=None):
            key = (section_id, row_code, column_code)
            if key in numeric_cache:
                return numeric_cache[key]

            stack = stack or set()
            if key in stack:
                frappe.throw(_("Se detecto una referencia circular al calcular la tabla estructurada de la nota."), title=_("Formula Invalida"))

            explicit = cell_map.get(key)
            if explicit and explicit["valor_numero"] is not None:
                numeric_cache[key] = flt(explicit["valor_numero"])
                return numeric_cache[key]

            row_obj = row_lookup.get((section_id, row_code))
            col_obj = column_lookup.get((section_id, column_code))
            value = None
            next_stack = set(stack)
            next_stack.add(key)

            if row_obj and cint(row_obj.calculo_automatico or 0) and cstr(row_obj.formula_filas or "").strip():
                value = 0.0
                for sign, ref_code in self._parse_formula_references(row_obj.formula_filas, _("la fila {0}").format(row_code)):
                    value += sign * flt(get_numeric_value(section_id, ref_code, column_code, next_stack) or 0)
            elif col_obj and cint(col_obj.calculo_automatico or 0) and cstr(col_obj.formula_columnas or "").strip():
                value = 0.0
                for sign, ref_code in self._parse_formula_references(col_obj.formula_columnas, _("la columna {0}").format(column_code)):
                    value += sign * flt(get_numeric_value(section_id, row_code, ref_code, next_stack) or 0)

            numeric_cache[key] = value
            return value

        output = []
        for section in sections:
            section_columns = [col for col in columns if col.seccion_id == section.seccion_id]
            column_groups, has_column_groups = self._build_column_groups(section_columns)
            section_rows = []
            for row in rows:
                if row.seccion_id != section.seccion_id:
                    continue
                rendered_cells = []
                for col in section_columns:
                    explicit = cell_map.get((section.seccion_id, row.codigo_fila, col.codigo_columna), {})
                    rendered_cells.append({
                        "valor_texto": explicit.get("valor_texto", ""),
                        "valor_numero": get_numeric_value(section.seccion_id, row.codigo_fila, col.codigo_columna),
                        "formato_numero": explicit.get("formato_numero") or (col.tipo_dato if col.tipo_dato in FORMATOS_NUMERO else "Numero"),
                        "comentario": explicit.get("comentario"),
                    })
                section_rows.append({
                    "codigo_fila": row.codigo_fila,
                    "descripcion": row.descripcion,
                    "nivel": cint(row.nivel or 1),
                    "tipo_fila": row.tipo_fila,
                    "calculo_automatico": cint(row.calculo_automatico or 0),
                    "formula_filas": row.formula_filas,
                    "negrita": cint(row.negrita or 0),
                    "subrayado": cint(row.subrayado or 0),
                    "celdas": rendered_cells,
                })
            output.append({
                "seccion_id": section.seccion_id,
                "titulo_seccion": section.titulo_seccion,
                "tipo_seccion": section.tipo_seccion,
                "contenido_narrativo": section.contenido_narrativo,
                "columnas": section_columns,
                "grupos_columnas": column_groups,
                "tiene_grupos_columnas": has_column_groups,
                "filas": section_rows,
            })
        return output

    def _build_column_groups(self, columns):
        has_groups = any(cstr(col.grupo_columna or "").strip() for col in columns)
        if not columns:
            return [], False
        if not has_groups:
            return [], False

        groups = []
        current_group = None
        for column in columns:
            group_label = cstr(column.grupo_columna or "").strip()
            if not group_label:
                groups.append(
                    {
                        "label": "",
                        "span": 1,
                        "standalone": True,
                        "columns": [column],
                    }
                )
                current_group = None
                continue

            if current_group and not current_group["standalone"] and current_group["label"] == group_label:
                current_group["columns"].append(column)
                current_group["span"] += 1
                continue

            current_group = {
                "label": group_label,
                "span": 1,
                "standalone": False,
                "columns": [column],
            }
            groups.append(current_group)

        return groups, True


def _build_note_display_name(package_name, note_number):
    normalized = normalize_note_number(note_number) or "SN"
    return f"Nota {normalized} - {package_name or frappe.generate_hash(length=6)}"


def _resolve_note_package(note_name=None, package_name=None):
    if note_name:
        package_name = frappe.db.get_value("Nota Estado Financiero", note_name, "paquete_estados_financieros_cliente")
    if not package_name:
        frappe.throw(_("Debes indicar el paquete de estados financieros del cliente."), title=_("Paquete Requerido"))
    return package_name


def _get_numeric_notes(package_name, exclude_note_name=None, min_number=None):
    rows = frappe.get_all(
        "Nota Estado Financiero",
        filters={"paquete_estados_financieros_cliente": package_name},
        fields=["name", "numero_nota", "titulo", "nombre_de_la_nota", "orden_presentacion"],
        order_by="creation asc",
    )
    output = []
    for row in rows:
        if exclude_note_name and row.name == exclude_note_name:
            continue
        normalized = normalize_note_number(row.numero_nota)
        if not normalized.isdigit():
            continue
        row.numero_nota = normalized
        row.numero_entero = cint(normalized)
        if min_number is not None and row.numero_entero < cint(min_number):
            continue
        output.append(row)
    output.sort(key=lambda row: (row.numero_entero, row.name))
    return output


def _update_note_sequence_fields(note_row, package_name, new_number):
    current_number = normalize_note_number(note_row.numero_nota)
    updates = {
        "numero_nota": new_number,
        "orden_presentacion": cint(new_number),
        "nombre_de_la_nota": _build_note_display_name(package_name, new_number),
    }
    if cstr(note_row.titulo or "").strip() == f"Nota {current_number}":
        updates["titulo"] = f"Nota {new_number}"
    frappe.db.set_value("Nota Estado Financiero", note_row.name, updates, update_modified=False)


def _remap_note_number_references(package_name, mapping):
    normalized_mapping = {
        normalize_note_number(source): normalize_note_number(target)
        for source, target in (mapping or {}).items()
        if normalize_note_number(source) and normalize_note_number(target)
    }
    if not normalized_mapping:
        return

    state_names = frappe.get_all(
        "Estado Financiero Cliente",
        filters={"paquete_estados_financieros_cliente": package_name},
        pluck="name",
    )
    if state_names:
        state_rows = frappe.get_all(
            "Linea Estado Financiero Cliente",
            filters={"parent": ["in", state_names]},
            fields=["name", "numero_nota_referencial"],
            limit_page_length=0,
        )
        for row in state_rows:
            current = normalize_note_number(row.numero_nota_referencial)
            if current in normalized_mapping:
                frappe.db.set_value(
                    "Linea Estado Financiero Cliente",
                    row.name,
                    "numero_nota_referencial",
                    normalized_mapping[current],
                    update_modified=False,
                )

    adjustment_names = frappe.get_all(
        "Ajuste Estados Financieros Cliente",
        filters={"paquete_estados_financieros_cliente": package_name},
        pluck="name",
    )
    if adjustment_names:
        adjustment_rows = frappe.get_all(
            "Linea Ajuste Estado Financiero Cliente",
            filters={"parent": ["in", adjustment_names]},
            fields=["name", "numero_nota_referencial"],
            limit_page_length=0,
        )
        for row in adjustment_rows:
            current = normalize_note_number(row.numero_nota_referencial)
            if current in normalized_mapping:
                frappe.db.set_value(
                    "Linea Ajuste Estado Financiero Cliente",
                    row.name,
                    "numero_nota_referencial",
                    normalized_mapping[current],
                    update_modified=False,
                )


@frappe.whitelist()
def preview_note_number_change(numero_nota, note_name=None, package_name=None):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden renumerar notas a los estados financieros del cliente."))
    package_name = _resolve_note_package(note_name=note_name, package_name=package_name)
    target_number = normalize_note_number(numero_nota)
    if not target_number:
        frappe.throw(_("Debes indicar el numero de nota."), title=_("Numero Requerido"))

    duplicate = frappe.get_all(
        "Nota Estado Financiero",
        filters={
            "paquete_estados_financieros_cliente": package_name,
            "numero_nota": target_number,
            "name": ["!=", note_name or ""],
        },
        fields=["name", "numero_nota", "titulo"],
        limit_page_length=1,
    )

    response = {
        "package_name": package_name,
        "note_name": note_name,
        "numero_nota": target_number,
        "suggested_note_name": _build_note_display_name(package_name, target_number),
        "conflict": bool(duplicate),
        "can_cascade": bool(duplicate) and target_number.isdigit(),
        "affected_notes": [],
    }

    if response["conflict"] and response["can_cascade"]:
        affected = _get_numeric_notes(package_name, exclude_note_name=note_name, min_number=cint(target_number))
        response["affected_notes"] = [
            {
                "name": row.name,
                "titulo": row.titulo,
                "numero_actual": row.numero_nota,
                "numero_nuevo": cstr(row.numero_entero + 1),
            }
            for row in affected
        ]

    return response


@frappe.whitelist()
def apply_note_number_change(numero_nota, note_name=None, package_name=None, cascade=0):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden renumerar notas a los estados financieros del cliente."))
    package_name = _resolve_note_package(note_name=note_name, package_name=package_name)
    target_number = normalize_note_number(numero_nota)
    if not target_number:
        frappe.throw(_("Debes indicar el numero de nota."), title=_("Numero Requerido"))

    duplicate = frappe.get_all(
        "Nota Estado Financiero",
        filters={
            "paquete_estados_financieros_cliente": package_name,
            "numero_nota": target_number,
            "name": ["!=", note_name or ""],
        },
        fields=["name"],
        limit_page_length=1,
    )
    if duplicate and not cint(cascade):
        frappe.throw(_("Ya existe una nota numero <b>{0}</b> dentro de este paquete.").format(target_number), title=_("Nota Duplicada"))
    if duplicate and not target_number.isdigit():
        frappe.throw(_("Solo se puede renumerar en cascada cuando el numero de nota es numerico."), title=_("Renumeracion No Soportada"))

    shifted = []
    mapping = {}
    if duplicate:
        affected = _get_numeric_notes(package_name, exclude_note_name=note_name, min_number=cint(target_number))
        for row in sorted(affected, key=lambda item: item.numero_entero, reverse=True):
            new_number = cstr(row.numero_entero + 1)
            _update_note_sequence_fields(row, package_name, new_number)
            mapping[row.numero_nota] = new_number
            shifted.append({
                "name": row.name,
                "numero_actual": row.numero_nota,
                "numero_nuevo": new_number,
            })
        _remap_note_number_references(package_name, mapping)

    updated_note = None
    if note_name:
        note = frappe.get_doc("Nota Estado Financiero", note_name)
        note.numero_nota = target_number
        note.save(ignore_permissions=True)
        updated_note = note.name

    sync_note_cross_references(package_name)
    sync_package_summary(package_name)

    return {
        "package_name": package_name,
        "note_name": updated_note or note_name,
        "numero_nota": target_number,
        "shifted_notes": shifted,
    }
