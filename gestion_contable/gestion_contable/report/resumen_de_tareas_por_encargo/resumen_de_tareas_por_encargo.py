import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "tarea", "label": _("Tarea"), "fieldtype": "Link", "options": "Task", "width": 250},
        {"fieldname": "encargo_contable", "label": _("Encargo"), "fieldtype": "Link", "options": "Encargo Contable", "width": 200},
        {"fieldname": "cliente", "label": _("Cliente"), "fieldtype": "Link", "options": "Cliente Contable", "width": 150},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 100},
        {"fieldname": "asignado_a", "label": _("Asignado a"), "fieldtype": "Data", "width": 150},
        {"fieldname": "fecha_de_vencimiento", "label": _("Vencimiento"), "fieldtype": "Date", "width": 120},
    ]

def get_data(filters):
    conditions = ""
    values = {}
    if filters and filters.get("encargo_contable"):
        conditions += " AND encargo_contable = %(encargo_contable)s"
        values["encargo_contable"] = filters.get("encargo_contable")
    if filters and filters.get("asignado_a"):
        conditions += " AND _assign LIKE %(asignado_a)s"
        values["asignado_a"] = f'%{filters.get("asignado_a")}%'
    if filters and filters.get("estado"):
        conditions += " AND status = %(estado)s"
        values["estado"] = filters.get("estado")

    return frappe.db.sql(f"""
        SELECT 
            name as tarea, encargo_contable, cliente, status as estado, _assign as asignado_a, exp_end_date as fecha_de_vencimiento
        FROM `tabTask`
        WHERE docstatus < 2 {conditions}
        ORDER BY exp_end_date ASC
    """, values, as_dict=True)
