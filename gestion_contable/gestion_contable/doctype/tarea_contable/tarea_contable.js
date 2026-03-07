frappe.ui.form.on("Tarea Contable", {
    refresh(frm) {
        frm.set_query("periodo", () => ({
            filters: build_periodo_filters(frm),
        }));

        frm.set_query("encargo_contable", () => ({
            filters: frm.doc.cliente ? { cliente: frm.doc.cliente } : {},
        }));
    },

    cliente(frm) {
        if (!frm.doc.encargo_contable) {
            sync_company_from_cliente(frm);
        }
        frm.set_value("periodo", null);
    },

    company(frm) {
        frm.set_value("periodo", null);
    },

    encargo_contable(frm) {
        if (!frm.doc.encargo_contable) {
            return;
        }
        frappe.db.get_value("Encargo Contable", frm.doc.encargo_contable, ["cliente", "company", "periodo_referencia"]).then((r) => {
            const data = r.message || {};
            if (data.cliente) frm.set_value("cliente", data.cliente);
            if (data.company) frm.set_value("company", data.company);
            if (data.periodo_referencia) frm.set_value("periodo", data.periodo_referencia);
        });
    },
});

function build_periodo_filters(frm) {
    const filters = {};
    if (frm.doc.cliente) filters.cliente = frm.doc.cliente;
    if (frm.doc.company) filters.company = frm.doc.company;
    return filters;
}

function sync_company_from_cliente(frm) {
    if (!frm.doc.cliente) return;
    frappe.db.get_value("Cliente Contable", frm.doc.cliente, "company_default").then((r) => {
        const company = r.message && r.message.company_default;
        if (company && !frm.doc.company) {
            frm.set_value("company", company);
        }
    });
}
