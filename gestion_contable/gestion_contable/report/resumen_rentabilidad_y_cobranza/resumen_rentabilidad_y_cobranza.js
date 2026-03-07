frappe.query_reports["Resumen Rentabilidad y Cobranza"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Compañía"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "cliente",
            "label": __("Cliente"),
            "fieldtype": "Link",
            "options": "Cliente Contable"
        },
        {
            "fieldname": "estado",
            "label": __("Estado"),
            "fieldtype": "Select",
            "options": "\nPlanificado\nEn Ejecucion\nEn Revision\nCerrado\nCancelado",
            "default": "En Ejecucion"
        }
    ]
};
