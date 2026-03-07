frappe.query_reports["Resumen de Tareas por Encargo"] = {
    "filters": [
        {
            "fieldname": "encargo_contable",
            "label": __("Encargo Contable"),
            "fieldtype": "Link",
            "options": "Encargo Contable"
        },
        {
            "fieldname": "asignado_a",
            "label": __("Asignado a"),
            "fieldtype": "Link",
            "options": "User",
            "default": frappe.session.user
        },
        {
            "fieldname": "estado",
            "label": __("Estado"),
            "fieldtype": "Select",
            "options": "\nOpen\nWorking\nPending Review\nOverdue\nTemplate\nCompleted\nCancelled",
            "default": ""
        }
    ]
};
