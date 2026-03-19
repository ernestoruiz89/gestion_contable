import frappe

from gestion_contable.gestion_contable.services.encargos.analytics import rebuild_all_snapshots


def execute():
    if not frappe.db.exists("DocType", "Encargo Contable"):
        return
    rebuild_all_snapshots(update_modified=False)
