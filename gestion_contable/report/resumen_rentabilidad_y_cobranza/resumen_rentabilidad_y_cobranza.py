import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "encargo", "label": _("Encargo"), "fieldtype": "Link", "options": "Encargo Contable", "width": 200},
        {"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente Contable", "width": 200},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 100},
        {"fieldname": "moneda", "label": _("Moneda"), "fieldtype": "Link", "options": "Currency", "hidden": 1},
        {"fieldname": "ingreso_facturado", "label": _("Ingreso Facturado"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "costo_interno_total", "label": _("Costo Interno"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "margen_ejecutado", "label": _("Margen Ejecutado"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "cobrado_total", "label": _("Cobrado Total"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "saldo_por_cobrar", "label": _("Saldo por Cobrar"), "fieldtype": "Currency", "options": "moneda", "width": 120},
        {"fieldname": "cartera_vencida", "label": _("Cartera Vencida"), "fieldtype": "Currency", "options": "moneda", "width": 120},
    ]

def get_data(filters):
    conditions = ""
    values = {}
    if filters and filters.get("company"):
        conditions += " AND company = %(company)s"
        values["company"] = filters.get("company")
    if filters and filters.get("cliente"):
        conditions += " AND cliente = %(cliente)s"
        values["cliente"] = filters.get("cliente")
    if filters and filters.get("estado"):
        conditions += " AND estado = %(estado)s"
        values["estado"] = filters.get("estado")

    return frappe.db.sql(f"""
        SELECT 
            name as encargo, cliente, estado, moneda,
            ingreso_facturado, costo_interno_total, margen_ejecutado,
            cobrado_total, saldo_por_cobrar, cartera_vencida
        FROM `tabEncargo Contable`
        WHERE docstatus < 2 {conditions}
        ORDER BY modified DESC
    """, values, as_dict=True)
