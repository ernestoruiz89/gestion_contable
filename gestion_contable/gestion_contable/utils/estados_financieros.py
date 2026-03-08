import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO

ESTADOS_FINANCIEROS_BASE_REQUERIDOS = (
    "Estado de Situacion Financiera",
    "Estado de Resultados",
    "Estado de Cambios en el Patrimonio",
    "Estado de Flujos de Efectivo",
)
MATH_TOLERANCE = 0.01


def get_required_statement_types(_package=None):
    return list(ESTADOS_FINANCIEROS_BASE_REQUERIDOS)


def normalize_note_number(note_number):
    return cstr(note_number or "").strip()


def empty_package_summary():
    return {
        "total_estados": 0,
        "estados_aprobados": 0,
        "total_notas": 0,
        "notas_aprobadas": 0,
        "notas_requeridas_pendientes": 0,
        "total_ajustes": 0,
        "ajustes_registrados": 0,
        "ajustes_no_registrados": 0,
        "ajustes_materiales_no_registrados": 0,
        "monto_ajustes": 0,
    }


def calculate_package_summary(package_name=None):
    if not package_name or not frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        return empty_package_summary()

    summary = empty_package_summary()

    if frappe.db.exists("DocType", "Estado Financiero Cliente"):
        summary["total_estados"] = frappe.db.count(
            "Estado Financiero Cliente",
            {"paquete_estados_financieros_cliente": package_name},
        )
        summary["estados_aprobados"] = frappe.db.count(
            "Estado Financiero Cliente",
            {
                "paquete_estados_financieros_cliente": package_name,
                "estado_aprobacion": ESTADO_APROBACION_APROBADO,
            },
        )

    required_note_numbers, missing_reference_rows = get_required_note_numbers(package_name)

    if frappe.db.exists("DocType", "Nota Estado Financiero"):
        notas = frappe.get_all(
            "Nota Estado Financiero",
            filters={"paquete_estados_financieros_cliente": package_name},
            fields=["numero_nota", "estado_aprobacion"],
            limit_page_length=500,
        )
        summary["total_notas"] = len(notas)
        notes_by_number = {}
        for nota in notas:
            note_number = normalize_note_number(nota.numero_nota)
            if not note_number:
                continue
            notes_by_number[note_number] = nota.estado_aprobacion
            if nota.estado_aprobacion == ESTADO_APROBACION_APROBADO:
                summary["notas_aprobadas"] += 1

        summary["notas_requeridas_pendientes"] = len(missing_reference_rows)
        for note_number in required_note_numbers:
            if notes_by_number.get(note_number) != ESTADO_APROBACION_APROBADO:
                summary["notas_requeridas_pendientes"] += 1

    if frappe.db.exists("DocType", "Ajuste Estados Financieros Cliente"):
        ajustes = frappe.get_all(
            "Ajuste Estados Financieros Cliente",
            filters={"paquete_estados_financieros_cliente": package_name},
            fields=["estado_ajuste", "registrado_en_version_final", "material", "monto_total"],
            limit_page_length=500,
        )

        summary["total_ajustes"] = len(ajustes)
        for ajuste in ajustes:
            registrado = ajuste.registrado_en_version_final or ajuste.estado_ajuste == "Registrado"
            if registrado:
                summary["ajustes_registrados"] += 1
            else:
                summary["ajustes_no_registrados"] += 1
                if ajuste.material:
                    summary["ajustes_materiales_no_registrados"] += 1
            summary["monto_ajustes"] += flt(ajuste.monto_total)

    return summary


def sync_package_summary(package_name):
    summary = calculate_package_summary(package_name)
    if package_name and frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        frappe.db.set_value("Paquete Estados Financieros Cliente", package_name, summary, update_modified=False)
    return summary


def get_customer_identity(cliente_name):
    if not cliente_name or not frappe.db.exists("Cliente Contable", cliente_name):
        return {"razon_social": cliente_name, "identificacion_fiscal": None, "moneda": None}

    cliente = frappe.get_cached_doc("Cliente Contable", cliente_name)
    razon_social = cliente.name
    if cliente.customer and frappe.db.exists("Customer", cliente.customer):
        razon_social = frappe.db.get_value("Customer", cliente.customer, "customer_name") or razon_social

    return {
        "razon_social": razon_social,
        "identificacion_fiscal": cliente.identificacion_fiscal,
        "moneda": cliente.moneda_preferida,
    }


def get_required_note_numbers(package_name):
    required_numbers = set()
    missing_reference_rows = []
    if not package_name or not frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        return required_numbers, missing_reference_rows
    if not frappe.db.exists("DocType", "Estado Financiero Cliente"):
        return required_numbers, missing_reference_rows

    state_names = frappe.get_all(
        "Estado Financiero Cliente",
        filters={"paquete_estados_financieros_cliente": package_name},
        pluck="name",
        limit_page_length=200,
    )
    for state_name in state_names:
        state_doc = frappe.get_doc("Estado Financiero Cliente", state_name)
        for row in state_doc.lineas or []:
            if not cint(row.requiere_nota):
                continue
            note_number = normalize_note_number(row.numero_nota_referencial)
            if note_number:
                required_numbers.add(note_number)
                continue
            line_label = cstr(row.descripcion or row.codigo_rubro or _("Fila {0}").format(row.idx)).strip()
            missing_reference_rows.append(f"{state_doc.tipo_estado}: {line_label}")
    return required_numbers, missing_reference_rows


def get_note_line_references(package_name, note_number=None):
    note_number = normalize_note_number(note_number)
    references = []
    if not note_number:
        return references

    state_names = frappe.get_all(
        "Estado Financiero Cliente",
        filters={"paquete_estados_financieros_cliente": package_name},
        pluck="name",
        limit_page_length=200,
    )
    for state_name in state_names:
        state_doc = frappe.get_doc("Estado Financiero Cliente", state_name)
        for row in state_doc.lineas or []:
            if normalize_note_number(row.numero_nota_referencial) != note_number:
                continue
            references.append(
                {
                    "estado_financiero_cliente": state_doc.name,
                    "tipo_estado": state_doc.tipo_estado,
                    "numero_linea": cint(row.idx or 0),
                    "codigo_rubro": row.codigo_rubro,
                    "descripcion_linea_estado": cstr(row.descripcion or row.codigo_rubro or _("Fila {0}").format(row.idx)).strip(),
                    "linea_estado_name": row.name,
                    "tipo_referencia": "Principal",
                    "obligatoria": 1,
                }
            )
    return references


def sync_note_cross_references(package_name, note_number=None):
    if not package_name or not frappe.db.exists("DocType", "Nota Estado Financiero"):
        return

    filters = {"paquete_estados_financieros_cliente": package_name}
    if note_number:
        filters["numero_nota"] = normalize_note_number(note_number)

    for note_name in frappe.get_all("Nota Estado Financiero", filters=filters, pluck="name", limit_page_length=500):
        note = frappe.get_doc("Nota Estado Financiero", note_name)
        changed = note.sincronizar_referencias_cruzadas()
        if changed:
            note.save(ignore_permissions=True)


def _signed_amount(row, fieldname):
    amount = flt(getattr(row, fieldname, 0))
    if cstr(getattr(row, "signo_presentacion", "")).strip() == "Inverso":
        amount *= -1
    return amount


def _get_top_level_total_row(state_doc, naturaleza):
    rows = [row for row in state_doc.lineas or [] if cint(row.es_total) and cstr(row.naturaleza or "").strip() == naturaleza]
    if not rows:
        return None
    min_level = min(cint(row.nivel or 1) for row in rows)
    top_rows = [row for row in rows if cint(row.nivel or 1) == min_level]
    if len(top_rows) > 1:
        frappe.throw(
            _("El estado <b>{0}</b> tiene multiples filas de total de nivel principal para la naturaleza <b>{1}</b>. Deja una sola fila de total principal para validar cuadratura.").format(state_doc.tipo_estado, naturaleza),
            title=_("Totales Ambiguos"),
        )
    return top_rows[0]


def _get_unique_marker_row(state_doc, marker_field, marker_label):
    rows = [row for row in state_doc.lineas or [] if cint(getattr(row, marker_field, 0))]
    if not rows:
        return None
    if len(rows) > 1:
        frappe.throw(
            _("El estado <b>{0}</b> tiene multiples filas marcadas como <b>{1}</b>. Deja una sola fila para esa funcion de control.").format(state_doc.tipo_estado, marker_label),
            title=_("Marcador Duplicado"),
        )
    return rows[0]


def _validate_balance_sheet_math(state_doc):
    totals = {}
    missing = []
    for naturaleza in ("Activo", "Pasivo", "Patrimonio"):
        total_row = _get_top_level_total_row(state_doc, naturaleza)
        if not total_row:
            missing.append(naturaleza)
            continue
        totals[naturaleza] = total_row

    if missing:
        frappe.throw(
            _("Para validar la cuadratura del Estado de Situacion Financiera debes definir una sola fila de total principal para: <b>{0}</b>.").format(", ".join(missing)),
            title=_("Totales Requeridos"),
        )

    activo_actual = _signed_amount(totals["Activo"], "monto_actual")
    pasivo_actual = _signed_amount(totals["Pasivo"], "monto_actual")
    patrimonio_actual = _signed_amount(totals["Patrimonio"], "monto_actual")
    if abs(activo_actual - (pasivo_actual + patrimonio_actual)) > MATH_TOLERANCE:
        frappe.throw(
            _("El Estado de Situacion Financiera no cuadra en monto actual: Activo ({0}) != Pasivo + Patrimonio ({1}).").format(
                flt(activo_actual, 2),
                flt(pasivo_actual + patrimonio_actual, 2),
            ),
            title=_("Cuadratura Invalida"),
        )

    activo_comp = _signed_amount(totals["Activo"], "monto_comparativo")
    pasivo_comp = _signed_amount(totals["Pasivo"], "monto_comparativo")
    patrimonio_comp = _signed_amount(totals["Patrimonio"], "monto_comparativo")
    if any(abs(value) > MATH_TOLERANCE for value in (activo_comp, pasivo_comp, patrimonio_comp)):
        if abs(activo_comp - (pasivo_comp + patrimonio_comp)) > MATH_TOLERANCE:
            frappe.throw(
                _("El Estado de Situacion Financiera no cuadra en monto comparativo: Activo ({0}) != Pasivo + Patrimonio ({1}).").format(
                    flt(activo_comp, 2),
                    flt(pasivo_comp + patrimonio_comp, 2),
                ),
                title=_("Cuadratura Comparativa Invalida"),
            )


def _validate_income_statement_math(state_doc):
    ingresos = _get_top_level_total_row(state_doc, "Ingreso")
    gastos = _get_top_level_total_row(state_doc, "Gasto")
    resultado = _get_unique_marker_row(state_doc, "es_resultado_final", _("resultado final"))

    missing = []
    if not ingresos:
        missing.append(_("total principal de Ingresos"))
    if not gastos:
        missing.append(_("total principal de Gastos"))
    if not resultado:
        missing.append(_("fila marcada como resultado final"))
    if missing:
        frappe.throw(
            _("Para validar el Estado de Resultados debes definir: <b>{0}</b>.").format(", ".join(missing)),
            title=_("Control de Resultado Incompleto"),
        )

    resultado_actual = _signed_amount(resultado, "monto_actual")
    esperado_actual = _signed_amount(ingresos, "monto_actual") - _signed_amount(gastos, "monto_actual")
    if abs(resultado_actual - esperado_actual) > MATH_TOLERANCE:
        frappe.throw(
            _("El Estado de Resultados no cuadra en monto actual: Resultado Final ({0}) != Ingresos - Gastos ({1}).").format(
                flt(resultado_actual, 2),
                flt(esperado_actual, 2),
            ),
            title=_("Resultado Invalido"),
        )

    if any(abs(_signed_amount(row, "monto_comparativo")) > MATH_TOLERANCE for row in (ingresos, gastos, resultado)):
        resultado_comp = _signed_amount(resultado, "monto_comparativo")
        esperado_comp = _signed_amount(ingresos, "monto_comparativo") - _signed_amount(gastos, "monto_comparativo")
        if abs(resultado_comp - esperado_comp) > MATH_TOLERANCE:
            frappe.throw(
                _("El Estado de Resultados no cuadra en monto comparativo: Resultado Final ({0}) != Ingresos - Gastos ({1}).").format(
                    flt(resultado_comp, 2),
                    flt(esperado_comp, 2),
                ),
                title=_("Resultado Comparativo Invalido"),
            )


def _validate_cash_flow_math(state_doc):
    efectivo_inicial = _get_unique_marker_row(state_doc, "es_efectivo_inicial", _("efectivo inicial"))
    variacion_neta = _get_unique_marker_row(state_doc, "es_variacion_neta_efectivo", _("variacion neta de efectivo"))
    efectivo_final = _get_unique_marker_row(state_doc, "es_efectivo_final", _("efectivo final"))

    missing = []
    if not efectivo_inicial:
        missing.append(_("fila marcada como efectivo inicial"))
    if not variacion_neta:
        missing.append(_("fila marcada como variacion neta de efectivo"))
    if not efectivo_final:
        missing.append(_("fila marcada como efectivo final"))
    if missing:
        frappe.throw(
            _("Para validar el Estado de Flujos de Efectivo debes definir: <b>{0}</b>.").format(", ".join(missing)),
            title=_("Control de Flujo Incompleto"),
        )

    inicial_actual = _signed_amount(efectivo_inicial, "monto_actual")
    variacion_actual = _signed_amount(variacion_neta, "monto_actual")
    final_actual = _signed_amount(efectivo_final, "monto_actual")
    if abs(final_actual - (inicial_actual + variacion_actual)) > MATH_TOLERANCE:
        frappe.throw(
            _("El Estado de Flujos de Efectivo no cuadra en monto actual: Efectivo Final ({0}) != Efectivo Inicial + Variacion Neta ({1}).").format(
                flt(final_actual, 2),
                flt(inicial_actual + variacion_actual, 2),
            ),
            title=_("Flujo de Efectivo Invalido"),
        )

    if any(abs(_signed_amount(row, "monto_comparativo")) > MATH_TOLERANCE for row in (efectivo_inicial, variacion_neta, efectivo_final)):
        inicial_comp = _signed_amount(efectivo_inicial, "monto_comparativo")
        variacion_comp = _signed_amount(variacion_neta, "monto_comparativo")
        final_comp = _signed_amount(efectivo_final, "monto_comparativo")
        if abs(final_comp - (inicial_comp + variacion_comp)) > MATH_TOLERANCE:
            frappe.throw(
                _("El Estado de Flujos de Efectivo no cuadra en monto comparativo: Efectivo Final ({0}) != Efectivo Inicial + Variacion Neta ({1}).").format(
                    flt(final_comp, 2),
                    flt(inicial_comp + variacion_comp, 2),
                ),
                title=_("Flujo Comparativo Invalido"),
            )


def validate_state_math(state_doc):
    total_rows = [row for row in state_doc.lineas or [] if cint(row.es_total) or cint(row.es_subtotal)]
    for row in total_rows:
        if abs(flt(row.monto_actual)) <= MATH_TOLERANCE and abs(flt(row.monto_comparativo)) <= MATH_TOLERANCE:
            frappe.throw(
                _("La fila <b>{0}</b> marcada como subtotal/total debe tener al menos un monto informado.").format(cstr(row.descripcion or row.codigo_rubro or row.idx)),
                title=_("Fila de Total Incompleta"),
            )

    if state_doc.tipo_estado == "Estado de Situacion Financiera":
        _validate_balance_sheet_math(state_doc)
        return

    if state_doc.tipo_estado == "Estado de Resultados":
        _validate_income_statement_math(state_doc)
        return

    if state_doc.tipo_estado == "Estado de Flujos de Efectivo":
        _validate_cash_flow_math(state_doc)
        return


def validate_package_math(package_doc):
    if not frappe.db.exists("DocType", "Estado Financiero Cliente"):
        return
    for state_name in frappe.get_all(
        "Estado Financiero Cliente",
        filters={"paquete_estados_financieros_cliente": package_doc.name},
        pluck="name",
        limit_page_length=200,
    ):
        validate_state_math(frappe.get_doc("Estado Financiero Cliente", state_name))


def validate_required_statement_types(package_doc):
    required_types = set(get_required_statement_types(package_doc))
    existing_rows = frappe.get_all(
        "Estado Financiero Cliente",
        filters={"paquete_estados_financieros_cliente": package_doc.name},
        fields=["tipo_estado", "estado_aprobacion"],
        limit_page_length=200,
    )
    existing_types = {row.tipo_estado for row in existing_rows}
    missing = [state_type for state_type in required_types if state_type not in existing_types]
    if missing:
        frappe.throw(
            _("No puedes emitir el paquete mientras falten los siguientes estados: <b>{0}</b>.").format(", ".join(missing)),
            title=_("Estados Financieros Incompletos"),
        )

    pending = [row.tipo_estado for row in existing_rows if row.tipo_estado in required_types and row.estado_aprobacion != ESTADO_APROBACION_APROBADO]
    if pending:
        frappe.throw(
            _("Todos los estados base deben estar aprobados antes de emitir el paquete. Pendientes: <b>{0}</b>.").format(", ".join(pending)),
            title=_("Estados Pendientes de Aprobacion"),
        )


def validate_required_notes(package_doc):
    required_note_numbers, missing_reference_rows = get_required_note_numbers(package_doc.name)
    if missing_reference_rows:
        frappe.throw(
            _("Hay lineas marcadas con nota requerida pero sin numero referencial: <b>{0}</b>.").format(", ".join(missing_reference_rows)),
            title=_("Referencias de Nota Incompletas"),
        )
    if not required_note_numbers:
        return
    if not frappe.db.exists("DocType", "Nota Estado Financiero"):
        frappe.throw(
            _("El modulo de notas a los estados financieros no esta disponible para validar la emision del paquete."),
            title=_("Modulo Incompleto"),
        )

    notes = frappe.get_all(
        "Nota Estado Financiero",
        filters={"paquete_estados_financieros_cliente": package_doc.name},
        fields=["name", "numero_nota", "estado_aprobacion"],
        limit_page_length=500,
    )
    notes_by_number = {normalize_note_number(note.numero_nota): note for note in notes}

    missing = [note_number for note_number in sorted(required_note_numbers) if note_number not in notes_by_number]
    if missing:
        frappe.throw(
            _("No puedes emitir el paquete mientras falten las siguientes notas requeridas: <b>{0}</b>.").format(", ".join(missing)),
            title=_("Notas Requeridas Incompletas"),
        )

    pending = [
        note_number
        for note_number in sorted(required_note_numbers)
        if notes_by_number[note_number].estado_aprobacion != ESTADO_APROBACION_APROBADO
    ]
    if pending:
        frappe.throw(
            _("Todas las notas requeridas deben estar aprobadas antes de emitir el paquete. Pendientes: <b>{0}</b>.").format(", ".join(pending)),
            title=_("Notas Pendientes de Aprobacion"),
        )
