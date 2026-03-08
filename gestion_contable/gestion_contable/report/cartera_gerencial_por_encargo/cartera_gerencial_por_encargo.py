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
        {"fieldname": "responsable", "label": _("Responsable"), "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 110},
        {"fieldname": "moneda", "label": _("Moneda"), "fieldtype": "Link", "options": "Currency", "hidden": 1},
        {"fieldname": "facturas_emitidas", "label": _("Facturas Emitidas"), "fieldtype": "Int", "width": 110},
        {"fieldname": "facturas_abiertas", "label": _("Facturas Abiertas"), "fieldtype": "Int", "width": 110},
        {"fieldname": "facturas_vencidas", "label": _("Facturas Vencidas"), "fieldtype": "Int", "width": 110},
        {"fieldname": "cobrado_total", "label": _("Cobrado Total"), "fieldtype": "Currency", "options": "moneda", "width": 125},
        {"fieldname": "saldo_por_cobrar", "label": _("Saldo por Cobrar"), "fieldtype": "Currency", "options": "moneda", "width": 130},
        {"fieldname": "cartera_vencida", "label": _("Cartera Vencida"), "fieldtype": "Currency", "options": "moneda", "width": 130},
        {"fieldname": "aging_current", "label": _("Aging Corriente"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "aging_0_30", "label": _("Aging 0-30"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "aging_31_60", "label": _("Aging 31-60"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "aging_61_90", "label": _("Aging 61-90"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "aging_91_plus", "label": _("Aging 91+"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "ultima_gestion_cobranza", "label": _("Ultima Gestion Cobranza"), "fieldtype": "Datetime", "width": 150},
        {"fieldname": "proxima_gestion_cobranza", "label": _("Proxima Gestion Cobranza"), "fieldtype": "Date", "width": 140},
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
    if filters.get("responsable"):
        conditions.append("responsable = %(responsable)s")
        values["responsable"] = filters.get("responsable")
    if filters.get("estado"):
        conditions.append("estado = %(estado)s")
        values["estado"] = filters.get("estado")
    if cint(filters.get("solo_con_saldo")):
        conditions.append("ifnull(saldo_por_cobrar, 0) > 0")
    if cint(filters.get("solo_vencidos")):
        conditions.append("ifnull(cartera_vencida, 0) > 0")

    return frappe.db.sql(
        f"""
        SELECT
            name AS encargo_contable,
            cliente,
            servicio_contable,
            responsable,
            estado,
            moneda,
            facturas_emitidas,
            facturas_abiertas,
            facturas_vencidas,
            cobrado_total,
            saldo_por_cobrar,
            cartera_vencida,
            aging_current,
            aging_0_30,
            aging_31_60,
            aging_61_90,
            aging_91_plus,
            ultima_gestion_cobranza,
            proxima_gestion_cobranza
        FROM `tabEncargo Contable`
        WHERE {' AND '.join(conditions)}
        ORDER BY cartera_vencida DESC, saldo_por_cobrar DESC, modified DESC
        """,
        values,
        as_dict=True,
    )
