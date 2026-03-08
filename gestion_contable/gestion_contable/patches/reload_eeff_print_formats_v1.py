import frappe


def execute():
    frappe.reload_doc("gestion_contable", "print_format", "nota_estado_financiero_individual", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "paquete_estados_financieros_cliente_notas_consolidadas", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "paquete_estados_financieros_cliente_completo", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "estado_financiero_cliente_situacion_financiera", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "estado_financiero_cliente_resultados", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "estado_financiero_cliente_cambios_patrimonio", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "estado_financiero_cliente_flujos_efectivo", force=True)
    frappe.reload_doc("gestion_contable", "print_format", "informe_completo_de_eeff_auditados", force=True)
