import frappe
from frappe import _
from frappe.utils import cint



def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data



def get_columns():
    return [
        {"fieldname": "encargo_contable", "label": _("Encargo"), "fieldtype": "Link", "options": "Encargo Contable", "width": 220},
        {"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente Contable", "width": 180},
        {"fieldname": "servicio_contable", "label": _("Servicio"), "fieldtype": "Link", "options": "Servicio Contable", "width": 170},
        {"fieldname": "tipo_de_servicio", "label": _("Tipo Servicio"), "fieldtype": "Data", "width": 120},
        {"fieldname": "responsable", "label": _("Responsable"), "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 110},
        {"fieldname": "modalidad_honorario", "label": _("Modalidad"), "fieldtype": "Data", "width": 100},
        {"fieldname": "moneda", "label": _("Moneda"), "fieldtype": "Link", "options": "Currency", "hidden": 1},
        {"fieldname": "presupuesto_horas", "label": _("Presupuesto Horas"), "fieldtype": "Float", "width": 120},
        {"fieldname": "horas_registradas", "label": _("Horas Registradas"), "fieldtype": "Float", "width": 120},
        {"fieldname": "ingreso_facturado", "label": _("Ingreso Facturado"), "fieldtype": "Currency", "options": "moneda", "width": 125},
        {"fieldname": "cobrado_total", "label": _("Cobrado Total"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "costo_interno_total", "label": _("Costo Interno"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "wip_monto", "label": _("WIP"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "margen_ejecutado", "label": _("Margen Ejecutado"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "margen_ejecutado_pct", "label": _("Margen Ejecutado %"), "fieldtype": "Percent", "width": 120},
        {"fieldname": "margen_facturado", "label": _("Margen Facturado"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "margen_facturado_pct", "label": _("Margen Facturado %"), "fieldtype": "Percent", "width": 120},
        {"fieldname": "margen_cobrado", "label": _("Margen Cobrado"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "margen_cobrado_pct", "label": _("Margen Cobrado %"), "fieldtype": "Percent", "width": 120},
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
    if filters.get("servicio_contable"):
        conditions.append("servicio_contable = %(servicio_contable)s")
        values["servicio_contable"] = filters.get("servicio_contable")
    if filters.get("tipo_de_servicio"):
        conditions.append("tipo_de_servicio = %(tipo_de_servicio)s")
        values["tipo_de_servicio"] = filters.get("tipo_de_servicio")
    if filters.get("responsable"):
        conditions.append("responsable = %(responsable)s")
        values["responsable"] = filters.get("responsable")
    if filters.get("estado"):
        conditions.append("estado = %(estado)s")
        values["estado"] = filters.get("estado")
    if filters.get("modalidad_honorario"):
        conditions.append("modalidad_honorario = %(modalidad_honorario)s")
        values["modalidad_honorario"] = filters.get("modalidad_honorario")
    if cint(filters.get("solo_margen_negativo")):
        conditions.append("(ifnull(margen_ejecutado, 0) < 0 OR ifnull(margen_facturado, 0) < 0 OR ifnull(margen_cobrado, 0) < 0)")

    return frappe.db.sql(
        f"""
        SELECT
            name AS encargo_contable,
            cliente,
            servicio_contable,
            tipo_de_servicio,
            responsable,
            estado,
            modalidad_honorario,
            moneda,
            presupuesto_horas,
            horas_registradas,
            ingreso_facturado,
            cobrado_total,
            costo_interno_total,
            wip_monto,
            margen_ejecutado,
            margen_ejecutado_pct,
            margen_facturado,
            margen_facturado_pct,
            margen_cobrado,
            margen_cobrado_pct
        FROM `tabEncargo Contable`
        WHERE {' AND '.join(conditions)}
        ORDER BY margen_facturado_pct ASC, modified DESC
        """,
        values,
        as_dict=True,
    )
