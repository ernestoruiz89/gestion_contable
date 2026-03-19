import frappe


def execute():
    """Force reload of Panel de Gestion workspace from JSON during migrate (v2)."""
    frappe.reload_doc("gestion_contable", "workspace", "panel_de_gestion", force=True)

