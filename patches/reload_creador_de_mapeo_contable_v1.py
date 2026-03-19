import frappe


def execute():
    frappe.reload_doc("gestion_contable", "doctype", "esquema_mapeo_contable")
    frappe.reload_doc("gestion_contable", "doctype", "regla_mapeo_contable")
    frappe.reload_doc("gestion_contable", "page", "creador_de_mapeo_contable", force=True)
    frappe.reload_doc("gestion_contable", "page", "creador_de_notas_eeff", force=True)
