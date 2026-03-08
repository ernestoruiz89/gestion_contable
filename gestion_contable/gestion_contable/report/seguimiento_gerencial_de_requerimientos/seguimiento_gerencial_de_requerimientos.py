import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate


ESTADOS_CIERRE = {"Cerrado", "Cancelado"}



def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data



def get_columns():
    return [
        {"fieldname": "requerimiento", "label": _("Requerimiento"), "fieldtype": "Link", "options": "Requerimiento Cliente", "width": 220},
        {"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente Contable", "width": 180},
        {"fieldname": "company", "label": _("Compania"), "fieldtype": "Link", "options": "Company", "width": 140},
        {"fieldname": "encargo_contable", "label": _("Encargo"), "fieldtype": "Link", "options": "Encargo Contable", "width": 180},
        {"fieldname": "periodo", "label": _("Periodo"), "fieldtype": "Link", "options": "Periodo Contable", "width": 130},
        {"fieldname": "prioridad", "label": _("Prioridad"), "fieldtype": "Data", "width": 90},
        {"fieldname": "canal_envio", "label": _("Canal"), "fieldtype": "Data", "width": 95},
        {"fieldname": "responsable_interno", "label": _("Responsable"), "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "estado_requerimiento", "label": _("Estado"), "fieldtype": "Data", "width": 110},
        {"fieldname": "alerta_gerencial", "label": _("Alerta Gerencial"), "fieldtype": "Data", "width": 140},
        {"fieldname": "fecha_envio", "label": _("Fecha Envio"), "fieldtype": "Datetime", "width": 145},
        {"fieldname": "fecha_vencimiento", "label": _("Fecha Vencimiento"), "fieldtype": "Date", "width": 125},
        {"fieldname": "dias_para_vencer", "label": _("Dias para Vencer"), "fieldtype": "Int", "width": 105},
        {"fieldname": "total_entregables", "label": _("Total Entregables"), "fieldtype": "Int", "width": 115},
        {"fieldname": "entregables_validados", "label": _("Validados"), "fieldtype": "Int", "width": 85},
        {"fieldname": "entregables_obligatorios_pendientes", "label": _("Oblig. Pendientes"), "fieldtype": "Int", "width": 120},
        {"fieldname": "entregables_vencidos", "label": _("Entregables Vencidos"), "fieldtype": "Int", "width": 125},
        {"fieldname": "porcentaje_cumplimiento", "label": _("Cumplimiento %"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "contacto_cliente", "label": _("Contacto Cliente"), "fieldtype": "Data", "width": 180},
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
    if filters.get("responsable_interno"):
        conditions.append("responsable_interno = %(responsable_interno)s")
        values["responsable_interno"] = filters.get("responsable_interno")
    if filters.get("estado_requerimiento"):
        conditions.append("estado_requerimiento = %(estado_requerimiento)s")
        values["estado_requerimiento"] = filters.get("estado_requerimiento")
    if filters.get("prioridad"):
        conditions.append("prioridad = %(prioridad)s")
        values["prioridad"] = filters.get("prioridad")
    if filters.get("canal_envio"):
        conditions.append("canal_envio = %(canal_envio)s")
        values["canal_envio"] = filters.get("canal_envio")
    if cint(filters.get("solo_vencidos")):
        conditions.append("estado_requerimiento = 'Vencido'")
    elif cint(filters.get("solo_pendientes")):
        conditions.append("estado_requerimiento NOT IN ('Cerrado', 'Cancelado', 'Recibido')")

    rows = frappe.db.sql(
        f"""
        SELECT
            name AS requerimiento,
            cliente,
            company,
            encargo_contable,
            periodo,
            prioridad,
            canal_envio,
            responsable_interno,
            estado_requerimiento,
            fecha_envio,
            fecha_vencimiento,
            total_entregables,
            entregables_validados,
            entregables_obligatorios_pendientes,
            entregables_vencidos,
            porcentaje_cumplimiento,
            contacto_cliente
        FROM `tabRequerimiento Cliente`
        WHERE {' AND '.join(conditions)}
        ORDER BY fecha_vencimiento ASC, modified DESC
        """,
        values,
        as_dict=True,
    )

    today = getdate(nowdate())
    for row in rows:
        row.dias_para_vencer = None
        if row.fecha_vencimiento:
            row.dias_para_vencer = (getdate(row.fecha_vencimiento) - today).days
        if row.estado_requerimiento in ESTADOS_CIERRE:
            row.alerta_gerencial = _("Cerrado")
        elif row.estado_requerimiento == "Vencido" or (row.dias_para_vencer is not None and row.dias_para_vencer < 0):
            row.alerta_gerencial = _("Vencido")
        elif row.dias_para_vencer is not None and row.dias_para_vencer <= 2:
            row.alerta_gerencial = _("Por Vencer")
        elif row.entregables_obligatorios_pendientes:
            row.alerta_gerencial = _("Pendiente Cliente")
        else:
            row.alerta_gerencial = _("Controlado")
    return rows
