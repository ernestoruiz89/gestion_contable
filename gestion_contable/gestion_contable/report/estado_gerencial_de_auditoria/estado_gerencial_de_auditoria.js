frappe.query_reports["Estado Gerencial de Auditoria"] = {
    filters: [
        { fieldname: "company", label: __("Compania"), fieldtype: "Link", options: "Company" },
        { fieldname: "cliente", label: __("Cliente"), fieldtype: "Link", options: "Cliente Contable" },
        {
            fieldname: "estado_expediente",
            label: __("Estado Expediente"),
            fieldtype: "Select",
            options: "\nPlaneacion\nEjecucion\nRevision Tecnica\nCerrada\nArchivada\nCancelada",
        },
        {
            fieldname: "estado_aprobacion",
            label: __("Aprobacion"),
            fieldtype: "Select",
            options: "\nBorrador\nRevision Supervisor\nRevision Socio\nAprobado\nDevuelto",
        },
        { fieldname: "socio_a_cargo", label: __("Socio"), fieldtype: "Link", options: "User" },
        { fieldname: "supervisor_a_cargo", label: __("Supervisor"), fieldtype: "Link", options: "User" },
        { fieldname: "solo_atrasados", label: __("Solo atrasados"), fieldtype: "Check", default: 0 },
    ],
};
