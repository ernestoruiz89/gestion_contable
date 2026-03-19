import frappe


def execute():
    frappe.reload_doc("gestion_contable", "doctype", "nota_estado_financiero")
