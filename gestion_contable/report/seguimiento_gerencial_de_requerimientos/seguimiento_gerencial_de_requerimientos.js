frappe.query_reports["Seguimiento Gerencial de Requerimientos"] = {
    filters: [
        { fieldname: "company", label: __("Compania"), fieldtype: "Link", options: "Company" },
        { fieldname: "cliente", label: __("Cliente"), fieldtype: "Link", options: "Cliente Contable" },
        { fieldname: "responsable_interno", label: __("Responsable"), fieldtype: "Link", options: "User" },
        {
            fieldname: "estado_requerimiento",
            label: __("Estado"),
            fieldtype: "Select",
            options: "\nBorrador\nEnviado\nParcial\nRecibido\nCerrado\nVencido\nCancelado",
        },
        {
            fieldname: "prioridad",
            label: __("Prioridad"),
            fieldtype: "Select",
            options: "\nBaja\nMedia\nAlta\nCritica",
        },
        {
            fieldname: "canal_envio",
            label: __("Canal"),
            fieldtype: "Select",
            options: "\nCorreo\nPortal\nWhatsApp\nTelefono\nReunion\nOtro",
        },
        { fieldname: "solo_pendientes", label: __("Solo pendientes"), fieldtype: "Check", default: 1 },
        { fieldname: "solo_vencidos", label: __("Solo vencidos"), fieldtype: "Check", default: 0 },
    ],
};
