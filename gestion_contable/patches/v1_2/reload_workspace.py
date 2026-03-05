import frappe

def execute():
	"""Recarga el workspace Panel de Gestion para incluir Resumen de Asignados"""
	from frappe.modules.import_file import import_file_by_path
	import os
	
	app_path = frappe.get_app_path("gestion_contable")
	json_path = os.path.join(app_path, "gestion_contable", "workspace", "panel_de_gestion", "panel_de_gestion.json")
	
	if os.path.exists(json_path):
		import_file_by_path(json_path, force=True, data_import=True)
