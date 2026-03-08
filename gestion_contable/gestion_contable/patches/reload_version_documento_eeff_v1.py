import frappe


def execute():
    frappe.reload_doc("gestion_contable", "doctype", "version_documento_eeff", force=True)
    frappe.reload_doc("gestion_contable", "doctype", "paquete_estados_financieros_cliente", force=True)
