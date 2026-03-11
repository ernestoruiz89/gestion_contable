import json
import re

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, now_datetime

from gestion_contable.gestion_contable.utils.estados_financieros import normalize_note_number
from gestion_contable.gestion_contable.utils.security import ensure_supervisor

FORMULA_SPLIT_RE = re.compile(r"[\n,;]+")
STATE_AMOUNT_FIELDS = {"Actual": "monto_actual", "Comparativo": "monto_comparativo"}
NOTE_AMOUNT_FIELDS = {"Actual": "monto_actual", "Comparativo": "monto_comparativo"}
OPERACION_FIELD_MAP = {
    "Saldo Neto": "saldo_neto",
    "Debe Mes Actual": "debe_mes_actual",
    "Haber Mes Actual": "haber_mes_actual",
    "Debe Saldo": "debe_saldo",
    "Haber Saldo": "haber_saldo",
}


def _normalize_code(value):
    return cstr(value or "").strip().upper()


def _split_tokens(value):
    return [_normalize_code(token) for token in FORMULA_SPLIT_RE.split(cstr(value or "")) if _normalize_code(token)]


def _parse_formula(expression, label):
    expression = _normalize_code(expression)
    if not expression:
        return []

    tokens = []
    for raw_token in FORMULA_SPLIT_RE.split(expression):
        token = _normalize_code(raw_token)
        if not token:
            continue
        sign = 1
        if token[0] in "+-":
            sign = -1 if token[0] == "-" else 1
            token = _normalize_code(token[1:])
        if not token:
            frappe.throw(_("La formula de {0} contiene un operador sin codigo.").format(label), title=_("Formula Invalida"))
        tokens.append((sign, token))
    if not tokens:
        frappe.throw(_("La formula de {0} no contiene codigos validos.").format(label), title=_("Formula Invalida"))
    return tokens


def _select_rule_lines(lines, rule):
    selector_type = cstr(rule.selector_tipo or "Lista").strip()
    tokens = _split_tokens(rule.selector_valor)
    ranges = []
    if selector_type == "Rango":
        for token in tokens:
            if "-" not in token:
                frappe.throw(_("La regla {0} contiene un rango invalido: {1}.").format(rule.idx, token), title=_("Regla Invalida"))
            start, end = token.split("-", 1)
            if not _normalize_code(start) or not _normalize_code(end):
                frappe.throw(_("La regla {0} contiene un rango incompleto: {1}.").format(rule.idx, token), title=_("Regla Invalida"))
            ranges.append((_normalize_code(start), _normalize_code(end)))

    regex = None
    if selector_type == "Regex" and cstr(rule.selector_valor or "").strip():
        try:
            regex = re.compile(cstr(rule.selector_valor).strip(), re.IGNORECASE)
        except re.error as exc:
            frappe.throw(_("La regla {0} contiene un patron regex invalido: {1}.").format(rule.idx, cstr(exc)), title=_("Regla Invalida"))

    centro_tokens = _split_tokens(getattr(rule, "filtro_centro_costo", ""))
    selected = []
    for line in lines:
        cuenta = _normalize_code(line.codigo_cuenta)
        centro_costo = _normalize_code(line.centro_costo)

        matches = False
        if selector_type == "Todas":
            matches = True
        elif selector_type in ("Cuenta Exacta", "Lista"):
            matches = cuenta in tokens
        elif selector_type == "Prefijo":
            matches = any(cuenta.startswith(token) for token in tokens)
        elif selector_type == "Rango":
            matches = any(start <= cuenta <= end for start, end in ranges)
        elif selector_type == "Regex" and regex:
            matches = bool(regex.search(cuenta))

        if not matches:
            continue
        if centro_tokens and centro_costo not in centro_tokens:
            continue
        selected.append(line)
    return selected


def _aggregate_lines(lines, rule):
    fieldname = OPERACION_FIELD_MAP.get(cstr(rule.operacion_agregacion or "Saldo Neto").strip(), "saldo_neto")
    amount = sum(flt(getattr(line, fieldname, 0)) for line in lines)
    if cstr(rule.signo_presentacion or "Normal").strip() == "Inverso":
        amount *= -1
    return flt(amount)


def _load_balance_lines(version_name):
    if not version_name:
        return []
    return frappe.get_all(
        "Linea Balanza Cliente",
        filters={"version_balanza_cliente": version_name},
        fields=[
            "name",
            "codigo_cuenta",
            "descripcion_cuenta",
            "centro_costo",
            "periodo_linea",
            "debe_mes_actual",
            "haber_mes_actual",
            "debe_saldo",
            "haber_saldo",
            "saldo_final",
            "saldo_neto",
        ],
        order_by="idx_importacion asc, creation asc",
        limit_page_length=20000,
    )


def _find_state_line(doc, code):
    target = _normalize_code(code)
    for row in doc.lineas or []:
        if _normalize_code(getattr(row, "codigo_linea_estado", "")) == target or _normalize_code(getattr(row, "codigo_rubro", "")) == target:
            return row
    return None


def _find_note_figure(doc, code):
    target = _normalize_code(code)
    for row in doc.cifras_nota or []:
        if _normalize_code(getattr(row, "codigo_cifra", "")) == target:
            return row
    return None


def _find_table_cell(doc, section_id, row_code, column_code):
    section_id = _normalize_code(section_id)
    row_code = _normalize_code(row_code)
    column_code = _normalize_code(column_code)
    for cell in doc.celdas_tabulares or []:
        if _normalize_code(cell.seccion_id) == section_id and _normalize_code(cell.codigo_fila) == row_code and _normalize_code(cell.codigo_columna) == column_code:
            return cell
    return None


def _ensure_note_table_coordinates(doc, section_id, row_code, column_code):
    section_id = _normalize_code(section_id)
    row_code = _normalize_code(row_code)
    column_code = _normalize_code(column_code)
    section_exists = any(_normalize_code(row.seccion_id) == section_id for row in doc.secciones_estructuradas or [])
    row_exists = any(_normalize_code(row.seccion_id) == section_id and _normalize_code(row.codigo_fila) == row_code for row in doc.filas_tabulares or [])
    column_exists = any(_normalize_code(row.seccion_id) == section_id and _normalize_code(row.codigo_columna) == column_code for row in doc.columnas_tabulares or [])
    return section_exists and row_exists and column_exists


def _get_column_format(doc, section_id, column_code):
    section_id = _normalize_code(section_id)
    column_code = _normalize_code(column_code)
    for row in doc.columnas_tabulares or []:
        if _normalize_code(row.seccion_id) != section_id or _normalize_code(row.codigo_columna) != column_code:
            continue
        tipo = cstr(row.tipo_dato or "").strip()
        return tipo if tipo in ("Numero", "Moneda", "Porcentaje") else "Numero"
    return "Numero"


def _get_rule_cell_coordinates(rule, origin_version):
    section_id = _normalize_code(rule.destino_seccion_id)
    row_code = _normalize_code(rule.destino_codigo_fila)
    column_code = _normalize_code(rule.destino_codigo_columna)

    if cstr(rule.origen_version or "Actual").strip() == "Ambas" and cstr(origin_version or "Actual").strip() == "Comparativo":
        section_id = _normalize_code(getattr(rule, "destino_seccion_id_comparativa", "") or section_id)
        row_code = _normalize_code(getattr(rule, "destino_codigo_fila_comparativa", "") or row_code)
        column_code = _normalize_code(getattr(rule, "destino_codigo_columna_comparativa", "") or column_code)

    return section_id, row_code, column_code


def _compute_formula_rows(rows, amount_fields, code_getter, formula_getter, auto_getter, manual_getter, origin_setter, label_builder):
    row_map = {}
    for row in rows:
        for code in code_getter(row):
            norm_code = _normalize_code(code)
            if norm_code:
                row_map[norm_code] = row

    cache = {}

    def get_value(code, fieldname, stack=None):
        code = _normalize_code(code)
        key = (code, fieldname)
        if key in cache:
            return cache[key]

        row = row_map.get(code)
        if not row:
            return 0.0

        stack = stack or set()
        if key in stack:
            frappe.throw(_("Se detecto una referencia circular en {0}.").format(label_builder(code)), title=_("Formula Invalida"))

        if cint(manual_getter(row)):
            value = flt(getattr(row, fieldname, 0))
        elif cint(auto_getter(row)) and cstr(formula_getter(row) or "").strip():
            value = 0.0
            next_stack = set(stack)
            next_stack.add(key)
            for sign, ref_code in _parse_formula(formula_getter(row), label_builder(code)):
                value += sign * flt(get_value(ref_code, fieldname, next_stack) or 0)
            setattr(row, fieldname, value)
            origin_setter(row, "Formula")
        else:
            value = flt(getattr(row, fieldname, 0))

        cache[key] = value
        for other_code in code_getter(row):
            other_norm = _normalize_code(other_code)
            if other_norm:
                cache[(other_norm, fieldname)] = value

        return value

    for row in rows:
        if not cint(auto_getter(row)) or not cstr(formula_getter(row) or "").strip():
            continue
        codes = code_getter(row)
        primary = next((_normalize_code(c) for c in codes if _normalize_code(c)), None)
        if primary:
            for fieldname in amount_fields:
                get_value(primary, fieldname, set())


def _compute_state_formulas(state_doc):
    _compute_formula_rows(
        state_doc.lineas or [],
        ("monto_actual", "monto_comparativo"),
        lambda row: [getattr(row, "codigo_linea_estado", ""), getattr(row, "codigo_rubro", "")],
        lambda row: getattr(row, "formula_lineas", ""),
        lambda row: getattr(row, "calculo_automatico", 0),
        lambda row: getattr(row, "es_manual", 0),
        lambda row, value: setattr(row, "origen_dato", value),
        lambda code: _("la linea de estado {0}").format(code),
    )


def _compute_note_figure_formulas(note_doc):
    _compute_formula_rows(
        note_doc.cifras_nota or [],
        ("monto_actual", "monto_comparativo"),
        lambda row: [getattr(row, "codigo_cifra", "")],
        lambda row: getattr(row, "formula_cifras", ""),
        lambda row: getattr(row, "calculo_automatico", 0),
        lambda row: getattr(row, "es_manual", 0),
        lambda row, value: setattr(row, "origen_dato", value),
        lambda code: _("la cifra {0}").format(code),
    )


def _load_state_docs(package_name):
    docs = {"by_code": {}, "by_type": {}, "all": []}
    for name in frappe.get_all(
        "Estado Financiero Cliente", filters={"paquete_estados_financieros_cliente": package_name}, pluck="name", limit_page_length=200
    ):
        doc = frappe.get_doc("Estado Financiero Cliente", name)
        docs["all"].append(doc)
        state_code = _normalize_code(getattr(doc, "codigo_estado", ""))
        if state_code:
            docs["by_code"][state_code] = doc
        docs["by_type"].setdefault(doc.tipo_estado, []).append(doc)
    return docs


def _load_note_docs(package_name):
    docs = {}
    for name in frappe.get_all("Nota Estado Financiero", filters={"paquete_estados_financieros_cliente": package_name}, pluck="name", limit_page_length=500):
        doc = frappe.get_doc("Nota Estado Financiero", name)
        docs[normalize_note_number(doc.numero_nota)] = doc
    return docs


def _load_sumaria_docs(expediente_name):
    docs = {}
    if not expediente_name:
        return docs
    for name in frappe.get_all(
        "Papel Trabajo Auditoria",
        filters={"expediente_auditoria": expediente_name, "tipo_papel": "Cedula Sumaria"},
        pluck="name",
        limit_page_length=500,
    ):
        doc = frappe.get_doc("Papel Trabajo Auditoria", name)
        docs[_normalize_code(getattr(doc, "codigo_sumaria", "") or getattr(doc, "referencia", ""))] = doc
    return docs


def _get_rule_versions(rule):
    if cstr(rule.origen_version or "Actual").strip() == "Ambas":
        return ("Actual", "Comparativo")
    return (cstr(rule.origen_version or "Actual").strip(),)


def _get_rule_source_version(package_doc, origin_version):
    return package_doc.version_balanza_comparativa if cstr(origin_version or "Actual").strip() == "Comparativo" else package_doc.version_balanza_actual


def _apply_state_rule(state_docs, rule, amount, summary, origin_version):
    state_doc = None
    state_code = _normalize_code(getattr(rule, "destino_codigo_estado", ""))
    if state_code:
        state_doc = state_docs["by_code"].get(state_code)
        if not state_doc:
            summary["alertas"].append(_("No existe el estado con codigo {0} para aplicar la regla {1}.").format(state_code, rule.idx))
            return None
    else:
        matching_states = state_docs["by_type"].get(rule.destino_tipo_estado, [])
        if len(matching_states) > 1:
            summary["alertas"].append(
                _("El destino {0} es ambiguo para la regla {1}; debes indicar un codigo de estado destino.").format(rule.destino_tipo_estado, rule.idx)
            )
            return None
        state_doc = matching_states[0] if matching_states else None

    if not state_doc:
        summary["alertas"].append(_("No existe el estado {0} para aplicar la regla {1}.").format(rule.destino_tipo_estado, rule.idx))
        return None

    row = _find_state_line(state_doc, rule.destino_codigo_linea_estado)
    if not row:
        summary["alertas"].append(_("No existe la linea {0} en el estado {1}.").format(rule.destino_codigo_linea_estado, rule.destino_tipo_estado))
        return None

    if cint(getattr(row, "es_manual", 0)) and not cint(rule.sobrescribir_manual or 0):
        summary["destinos_bloqueados_manual"] += 1
        return None

    amount_field = STATE_AMOUNT_FIELDS.get(cstr(origin_version or "Actual"), "monto_actual")
    current_val = flt(getattr(row, amount_field, 0))
    setattr(row, amount_field, current_val + amount)
    row.origen_dato = "Balanza"
    row.ultima_regla_mapeo = f"R{cint(rule.idx or 0):03d}"
    return state_doc


def _apply_figure_rule(note_docs, rule, amount, summary, origin_version):
    note_doc = note_docs.get(normalize_note_number(rule.destino_numero_nota))
    if not note_doc:
        summary["alertas"].append(_("No existe la nota {0} para aplicar una regla de cifra.").format(rule.destino_numero_nota))
        return None

    row = _find_note_figure(note_doc, rule.destino_codigo_cifra)
    if not row:
        summary["alertas"].append(_("No existe la cifra {0} en la nota {1}.").format(rule.destino_codigo_cifra, rule.destino_numero_nota))
        return None

    if cint(getattr(row, "es_manual", 0)) and not cint(rule.sobrescribir_manual or 0):
        summary["destinos_bloqueados_manual"] += 1
        return None

    amount_field = NOTE_AMOUNT_FIELDS.get(cstr(origin_version or "Actual"), "monto_actual")
    current_val = flt(getattr(row, amount_field, 0))
    setattr(row, amount_field, current_val + amount)
    row.origen_dato = "Balanza"
    row.ultima_regla_mapeo = f"R{cint(rule.idx or 0):03d}"
    return note_doc


def _apply_cell_rule(note_docs, rule, amount, summary, origin_version):
    note_doc = note_docs.get(normalize_note_number(rule.destino_numero_nota))
    if not note_doc:
        summary["alertas"].append(_("No existe la nota {0} para aplicar una regla de celda.").format(rule.destino_numero_nota))
        return None

    section_id, row_code, column_code = _get_rule_cell_coordinates(rule, origin_version)

    if not _ensure_note_table_coordinates(note_doc, section_id, row_code, column_code):
        summary["alertas"].append(
            _("La celda {0}/{1}/{2} no existe como coordenada valida en la nota {3}.").format(
                section_id,
                row_code,
                column_code,
                rule.destino_numero_nota,
            )
        )
        return None

    cell = _find_table_cell(note_doc, section_id, row_code, column_code)
    if cell and cint(getattr(cell, "es_manual", 0)) and not cint(rule.sobrescribir_manual or 0):
        summary["destinos_bloqueados_manual"] += 1
        return None

    if not cell:
        cell = note_doc.append(
            "celdas_tabulares",
            {
                "seccion_id": section_id,
                "codigo_fila": row_code,
                "codigo_columna": column_code,
                "es_manual": 0,
            },
        )

    cell.valor_texto = None
    cell.valor_numero = flt(getattr(cell, "valor_numero", 0)) + amount
    cell.formato_numero = _get_column_format(note_doc, section_id, column_code)
    cell.origen_dato = "Balanza"
    cell.ultima_regla_mapeo = f"R{cint(rule.idx or 0):03d}-{cstr(origin_version or 'Actual')[0]}"
    return note_doc


def _apply_sumaria_rule(package_doc, sumaria_docs, rule, amount, summary, origin_version):
    if not package_doc.expediente_auditoria:
        summary["alertas"].append(_("El paquete no tiene expediente de auditoria y no puede materializar cedulas sumarias."))
        return None

    sumaria_code = _normalize_code(rule.destino_codigo_sumaria)
    if not sumaria_code:
        summary["alertas"].append(_("La regla {0} no define codigo de sumaria.").format(rule.idx))
        return None

    paper = sumaria_docs.get(sumaria_code)
    if not paper:
        source_version_name = _get_rule_source_version(package_doc, origin_version)
        paper = frappe.get_doc(
            {
                "doctype": "Papel Trabajo Auditoria",
                "expediente_auditoria": package_doc.expediente_auditoria,
                "tipo_papel": "Cedula Sumaria",
                "referencia": sumaria_code,
                "codigo_sumaria": sumaria_code,
                "titulo": _("Cedula Sumaria {0}").format(sumaria_code),
                "version_balanza_cliente": source_version_name,
            }
        )
        paper.insert(ignore_permissions=True)
        sumaria_docs[sumaria_code] = paper

    line_code = _normalize_code(rule.destino_codigo_linea_sumaria or rule.destino_codigo_linea_estado or rule.destino_codigo_cifra or rule.destino_codigo_columna or rule.selector_valor)
    row = None
    for candidate in paper.lineas_cedula_sumaria or []:
        if _normalize_code(candidate.codigo_linea) == line_code:
            row = candidate
            break
    if not row:
        row = paper.append(
            "lineas_cedula_sumaria",
            {
                "codigo_linea": line_code or f"LIN-{len(paper.lineas_cedula_sumaria or []) + 1:03d}",
                "descripcion": cstr(rule.destino_descripcion or rule.destino_codigo_linea_sumaria or line_code or _("Linea de Sumaria")).strip(),
                "orden": len(paper.lineas_cedula_sumaria or []) + 1,
            },
        )

    fieldname = "monto_comparativo" if cstr(origin_version or "Actual") == "Comparativo" else "monto_actual"
    current_val = flt(getattr(row, fieldname, 0))
    setattr(row, fieldname, current_val + amount)
    row.origen_dato = "Balanza"
    row.ultima_regla_mapeo = f"R{cint(rule.idx or 0):03d}"

    source_version_name = cstr(_get_rule_source_version(package_doc, origin_version) or "").strip()
    source_versions = getattr(paper, "_source_version_names", None)
    if source_versions is None:
        source_versions = set()
        if cstr(paper.version_balanza_cliente or "").strip():
            source_versions.add(cstr(paper.version_balanza_cliente).strip())
    if source_version_name:
        source_versions.add(source_version_name)
    paper._source_version_names = source_versions

    if len(source_versions) == 1:
        paper.version_balanza_cliente = next(iter(source_versions))
    elif len(source_versions) > 1:
        paper.version_balanza_cliente = None
        sumarias_mixtas = summary.setdefault("sumarias_fuente_mixta", [])
        if sumaria_code not in sumarias_mixtas:
            sumarias_mixtas.append(sumaria_code)
            summary["alertas"].append(
                _("La cedula sumaria {0} usa balanza actual y comparativa; se limpio la version asociada para evitar trazabilidad incorrecta.").format(sumaria_code)
            )
    return paper


def actualizar_paquete_desde_balanza(package_name):
    if not frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        frappe.throw(_("El paquete indicado no existe."), title=_("Paquete Invalido"))

    package_doc = frappe.get_doc("Paquete Estados Financieros Cliente", package_name)
    if not package_doc.version_balanza_actual:
        frappe.throw(_("Debes vincular una version de balanza actual para actualizar el paquete."), title=_("Balanza Requerida"))
    if not package_doc.esquema_mapeo_contable:
        frappe.throw(_("Debes vincular un esquema de mapeo contable para actualizar el paquete."), title=_("Esquema Requerido"))
    scheme_doc = frappe.get_doc("Esquema Mapeo Contable", package_doc.esquema_mapeo_contable)
    active_rules = [row for row in (scheme_doc.reglas or []) if cint(row.activo or 0)]
    requires_comparative = any(cstr(rule.origen_version or "Actual").strip() in ("Comparativo", "Ambas") for rule in active_rules)
    if requires_comparative and not package_doc.version_balanza_comparativa:
        frappe.throw(
            _("El esquema de mapeo incluye reglas comparativas o para ambas versiones; debes vincular una version de balanza comparativa."),
            title=_("Balanza Comparativa Requerida"),
        )
    for fieldname in ("version_balanza_actual", "version_balanza_comparativa"):
        version_name = package_doc.get(fieldname)
        if not version_name:
            continue
        version_status = frappe.db.get_value("Version Balanza Cliente", version_name, ["estado_version", "es_version_vigente"], as_dict=True)
        if not version_status or version_status.estado_version != "Publicada":
            frappe.throw(_("La version de balanza vinculada en {0} debe estar publicada antes de actualizar el paquete.").format(fieldname), title=_("Balanza No Publicada"))
        if not cint(version_status.es_version_vigente):
            frappe.throw(_("La version de balanza vinculada en {0} fue reemplazada y ya no es la version vigente.").format(fieldname), title=_("Balanza Reemplazada"))

    actual_lines = _load_balance_lines(package_doc.version_balanza_actual)
    comparative_lines = _load_balance_lines(package_doc.version_balanza_comparativa)
    state_docs = _load_state_docs(package_name)
    note_docs = _load_note_docs(package_name)
    sumaria_docs = _load_sumaria_docs(package_doc.expediente_auditoria)

    summary = {
        "sumarias_actualizadas": 0,
        "estados_actualizados": 0,
        "notas_actualizadas": 0,
        "reglas_ejecutadas": 0,
        "destinos_bloqueados_manual": 0,
        "sumarias_fuente_mixta": [],
        "alertas": [],
    }
    touched_states = set()
    touched_notes = set()
    touched_sumarias = set()

    # Limpiar montos previamente mapeados (no manuales) para permitir acumulacion por reglas
    for doc in state_docs.get("all", []):
        for row in doc.lineas or []:
            if not cint(getattr(row, "es_manual", 0)):
                row.monto_actual = 0.0
                row.monto_comparativo = 0.0

    for doc in note_docs.values():
        for row in doc.cifras_nota or []:
            if not cint(getattr(row, "es_manual", 0)):
                row.monto_actual = 0.0
                row.monto_comparativo = 0.0

    for paper in sumaria_docs.values():
        for row in paper.lineas_cedula_sumaria or []:
            if not cint(getattr(row, "es_manual", 0)):
                row.monto_actual = 0.0
                row.monto_comparativo = 0.0

    active_rules.sort(key=lambda row: (cint(row.orden_ejecucion or 0), cint(row.idx or 0)))

    for rule in active_rules:
        summary["reglas_ejecutadas"] += 1
        for origin_version in _get_rule_versions(rule):
            lines = actual_lines if origin_version != "Comparativo" else comparative_lines
            selected = _select_rule_lines(lines, rule)
            amount = _aggregate_lines(selected, rule)

            if not selected and cint(rule.obligatoria or 0):
                summary["alertas"].append(_("La regla {0} no encontro cuentas coincidentes para la version {1}.").format(rule.idx, origin_version))

            destino_tipo = cstr(rule.destino_tipo or "").strip()
            if destino_tipo == "Linea Estado":
                target_doc = _apply_state_rule(state_docs, rule, amount, summary, origin_version)
                if target_doc:
                    touched_states.add(target_doc.name)
            elif destino_tipo == "Cifra Nota":
                target_doc = _apply_figure_rule(note_docs, rule, amount, summary, origin_version)
                if target_doc:
                    touched_notes.add(target_doc.name)
            elif destino_tipo == "Celda Nota":
                target_doc = _apply_cell_rule(note_docs, rule, amount, summary, origin_version)
                if target_doc:
                    touched_notes.add(target_doc.name)
            elif destino_tipo == "Cedula Sumaria":
                target_doc = _apply_sumaria_rule(package_doc, sumaria_docs, rule, amount, summary, origin_version)
                if target_doc:
                    touched_sumarias.add(target_doc.name)

    for doc in state_docs.get("all", []):
        if doc.name not in touched_states and not any(cint(getattr(row, "calculo_automatico", 0)) for row in doc.lineas or []):
            continue
        _compute_state_formulas(doc)
        doc.save(ignore_permissions=True)
        touched_states.add(doc.name)

    for doc in note_docs.values():
        if doc.name not in touched_notes and not any(cint(getattr(row, "calculo_automatico", 0)) for row in doc.cifras_nota or []):
            continue
        _compute_note_figure_formulas(doc)
        doc.save(ignore_permissions=True)
        touched_notes.add(doc.name)

    for paper in sumaria_docs.values():
        if paper.name not in touched_sumarias:
            continue
        paper.save(ignore_permissions=True)

    execution = frappe.get_doc(
        {
            "doctype": "Ejecucion Actualizacion EEFF",
            "cliente": package_doc.cliente,
            "paquete_estados_financieros_cliente": package_doc.name,
            "version_balanza_actual": package_doc.version_balanza_actual,
            "version_balanza_comparativa": package_doc.version_balanza_comparativa,
            "esquema_mapeo_contable": package_doc.esquema_mapeo_contable,
            "fecha_ejecucion": now_datetime(),
            "ejecutado_por": frappe.session.user,
            "estado_ejecucion": "Completada con Alertas" if summary["alertas"] else "Completada",
            "sumarias_actualizadas": len(touched_sumarias),
            "estados_actualizados": len(touched_states),
            "notas_actualizadas": len(touched_notes),
            "reglas_ejecutadas": summary["reglas_ejecutadas"],
            "total_alertas": len(summary["alertas"]),
            "destinos_bloqueados_manual": summary["destinos_bloqueados_manual"],
            "detalle_json": json.dumps(summary, ensure_ascii=True, default=str),
        }
    ).insert(ignore_permissions=True)

    frappe.db.set_value(
        "Paquete Estados Financieros Cliente",
        package_doc.name,
        {
            "fecha_ultima_actualizacion_automatica": now_datetime(),
            "ultima_ejecucion_actualizacion_eeff": execution.name,
            "alertas_actualizacion_automatica": "\n".join(summary["alertas"])[:1400] if summary["alertas"] else None,
        },
        update_modified=False,
    )

    return {
        "ejecucion": execution.name,
        "sumarias_actualizadas": len(touched_sumarias),
        "estados_actualizados": len(touched_states),
        "notas_actualizadas": len(touched_notes),
        "reglas_ejecutadas": summary["reglas_ejecutadas"],
        "alertas": summary["alertas"],
        "destinos_bloqueados_manual": summary["destinos_bloqueados_manual"],
    }


@frappe.whitelist()
def actualizar_paquete_desde_balanza_whitelisted(package_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden actualizar paquetes desde balanza."))
    return actualizar_paquete_desde_balanza(package_name)
