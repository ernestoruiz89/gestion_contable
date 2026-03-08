import frappe


def execute():
    frappe.reload_doc("gestion_contable", "print_format", "ajuste_estados_financieros_cliente_detalle", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "ajustes_estados_financieros_cliente_consolidado", force=True)
