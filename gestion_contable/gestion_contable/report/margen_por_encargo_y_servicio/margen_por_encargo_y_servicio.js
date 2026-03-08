frappe.query_reports["Margen por Encargo y Servicio"] = {
    filters: [
        { fieldname: "company", label: __("Compania"), fieldtype: "Link", options: "Company" },
        { fieldname: "cliente", label: __("Cliente"), fieldtype: "Link", options: "Cliente Contable" },
        { fieldname: "servicio_contable", label: __("Servicio"), fieldtype: "Link", options: "Servicio Contable" },
        {
            fieldname: "tipo_de_servicio",
            label: __("Tipo Servicio"),
            fieldtype: "Select",
            options: "\nContabilidad\nAuditoria\nTrabajo Especial\nConsultoria",
        },
        { fieldname: "responsable", label: __("Responsable"), fieldtype: "Link", options: "User" },
        {
            fieldname: "estado",
            label: __("Estado"),
            fieldtype: "Select",
            options: "\nPlanificado\nEn Ejecucion\nEn Revision\nCerrado\nCancelado",
        },
        {
            fieldname: "modalidad_honorario",
            label: __("Modalidad"),
            fieldtype: "Select",
            options: "\nPor Hora\nFijo\nMixto",
        },
        { fieldname: "solo_margen_negativo", label: __("Solo margen negativo"), fieldtype: "Check", default: 0 },
    ],
};
