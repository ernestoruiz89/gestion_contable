import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate


ESTADOS_CIERRE = {"Cerrada", "Archivada", "Cancelada"}



def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data



def get_columns():
    return [
        {"fieldname": "expediente_auditoria", "label": _("Expediente"), "fieldtype": "Link", "options": "Expediente Auditoria", "width": 220},
        {"fieldname": "encargo_contable", "label": _("Encargo"), "fieldtype": "Link", "options": "Encargo Contable", "width": 180},
        {"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente Contable", "width": 180},
        {"fieldname": "company", "label": _("Compania"), "fieldtype": "Link", "options": "Company", "width": 140},
        {"fieldname": "periodo", "label": _("Periodo"), "fieldtype": "Link", "options": "Periodo Contable", "width": 130},
        {"fieldname": "estado_expediente", "label": _("Estado Expediente"), "fieldtype": "Data", "width": 140},
        {"fieldname": "estado_aprobacion", "label": _("Aprobacion"), "fieldtype": "Data", "width": 130},
        {"fieldname": "alerta_gerencial", "label": _("Alerta Gerencial"), "fieldtype": "Data", "width": 140},
        {"fieldname": "dias_retraso", "label": _("Dias Retraso"), "fieldtype": "Int", "width": 100},
        {"fieldname": "socio_a_cargo", "label": _("Socio"), "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "supervisor_a_cargo", "label": _("Supervisor"), "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "fecha_inicio_planeada", "label": _("Inicio Planeado"), "fieldtype": "Date", "width": 120},
        {"fieldname": "fecha_fin_planeada", "label": _("Fin Planeado"), "fieldtype": "Date", "width": 120},
        {"fieldname": "resultado_revision_tecnica", "label": _("Revision Tecnica"), "fieldtype": "Data", "width": 140},
        {"fieldname": "total_riesgos", "label": _("Riesgos"), "fieldtype": "Int", "width": 80},
        {"fieldname": "riesgos_altos", "label": _("Riesgos Altos"), "fieldtype": "Int", "width": 95},
        {"fieldname": "total_papeles", "label": _("Papeles"), "fieldtype": "Int", "width": 80},
        {"fieldname": "papeles_pendientes_revision", "label": _("Papeles Pend. Rev."), "fieldtype": "Int", "width": 120},
        {"fieldname": "papeles_aprobados", "label": _("Papeles Aprobados"), "fieldtype": "Int", "width": 115},
        {"fieldname": "total_hallazgos", "label": _("Hallazgos"), "fieldtype": "Int", "width": 85},
        {"fieldname": "hallazgos_abiertos", "label": _("Hallazgos Abiertos"), "fieldtype": "Int", "width": 120},
        {"fieldname": "hallazgos_cerrados", "label": _("Hallazgos Cerrados"), "fieldtype": "Int", "width": 120},
        {"fieldname": "fecha_cierre", "label": _("Fecha Cierre"), "fieldtype": "Datetime", "width": 145},
    ]



def get_data(filters):
    conditions = ["docstatus < 2"]
    values = {}

    if filters.get("company"):
        conditions.append("company = %(company)s")
        values["company"] = filters.get("company")
    if filters.get("cliente"):
        conditions.append("cliente = %(cliente)s")
        values["cliente"] = filters.get("cliente")
    if filters.get("estado_expediente"):
        conditions.append("estado_expediente = %(estado_expediente)s")
        values["estado_expediente"] = filters.get("estado_expediente")
    if filters.get("estado_aprobacion"):
        conditions.append("estado_aprobacion = %(estado_aprobacion)s")
        values["estado_aprobacion"] = filters.get("estado_aprobacion")
    if filters.get("socio_a_cargo"):
        conditions.append("socio_a_cargo = %(socio_a_cargo)s")
        values["socio_a_cargo"] = filters.get("socio_a_cargo")
    if filters.get("supervisor_a_cargo"):
        conditions.append("supervisor_a_cargo = %(supervisor_a_cargo)s")
        values["supervisor_a_cargo"] = filters.get("supervisor_a_cargo")

    rows = frappe.db.sql(
        f"""
        SELECT
            name AS expediente_auditoria,
            encargo_contable,
            cliente,
            company,
            periodo,
            estado_expediente,
            estado_aprobacion,
            socio_a_cargo,
            supervisor_a_cargo,
            fecha_inicio_planeada,
            fecha_fin_planeada,
            resultado_revision_tecnica,
            total_riesgos,
            riesgos_altos,
            total_papeles,
            papeles_pendientes_revision,
            papeles_aprobados,
            total_hallazgos,
            hallazgos_abiertos,
            hallazgos_cerrados,
            fecha_cierre
        FROM `tabExpediente Auditoria`
        WHERE {' AND '.join(conditions)}
        ORDER BY modified DESC
        """,
        values,
        as_dict=True,
    )

    today = getdate(nowdate())
    filtered = []
    only_overdue = cint(filters.get("solo_atrasados"))
    for row in rows:
        row.dias_retraso = 0
        if row.fecha_fin_planeada and row.estado_expediente not in ESTADOS_CIERRE:
            delta = (today - getdate(row.fecha_fin_planeada)).days
            row.dias_retraso = delta if delta > 0 else 0
        if row.estado_expediente in ESTADOS_CIERRE:
            row.alerta_gerencial = _("Cerrado")
        elif row.dias_retraso > 0:
            row.alerta_gerencial = _("Atrasado")
        elif row.hallazgos_abiertos:
            row.alerta_gerencial = _("Hallazgos Abiertos")
        elif row.papeles_pendientes_revision:
            row.alerta_gerencial = _("Pendiente Revision")
        else:
            row.alerta_gerencial = _("En Curso")

        if only_overdue and row.dias_retraso <= 0:
            continue
        filtered.append(row)

    return filtered
