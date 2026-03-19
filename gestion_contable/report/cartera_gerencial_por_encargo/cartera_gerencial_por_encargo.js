frappe.query_reports["Cartera Gerencial por Encargo"] = {
    filters: [
        { fieldname: "company", label: __("Compania"), fieldtype: "Link", options: "Company" },
        { fieldname: "cliente", label: __("Cliente"), fieldtype: "Link", options: "Cliente Contable" },
        { fieldname: "responsable", label: __("Responsable"), fieldtype: "Link", options: "User" },
        {
            fieldname: "estado",
            label: __("Estado"),
            fieldtype: "Select",
            options: "\nPlanificado\nEn Ejecucion\nEn Revision\nCerrado\nCancelado",
        },
        { fieldname: "solo_con_saldo", label: __("Solo con saldo"), fieldtype: "Check", default: 1 },
        { fieldname: "solo_vencidos", label: __("Solo vencidos"), fieldtype: "Check", default: 0 },
    ],
};
