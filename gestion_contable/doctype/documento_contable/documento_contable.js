frappe.ui.form.on("Documento Contable", {
    refresh(frm) {
        frm.set_query("periodo", () => ({
            filters: build_periodo_filters(frm),
        }));

        frm.set_query("task", () => {
            const filters = {};
            if (frm.doc.encargo_contable) filters.encargo_contable = frm.doc.encargo_contable;
            else if (frm.doc.cliente) filters.cliente = frm.doc.cliente;
            return { filters };
        });

        frm.set_query("entregable_cliente", () => {
            const filters = {};
            if (frm.doc.cliente) filters.cliente = frm.doc.cliente;
            return { filters };
        });
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
        sync_from_linked_doc(frm, "Encargo Contable", frm.doc.encargo_contable, ["cliente", "company", "periodo_referencia"], {
            periodo_referencia: "periodo",
        });
    },

    task(frm) {
        sync_from_linked_doc(frm, "Task", frm.doc.task, ["encargo_contable", "cliente", "company", "periodo"]);
    },

    entregable_cliente(frm) {
        sync_from_linked_doc(frm, "Entregable Cliente", frm.doc.entregable_cliente, ["encargo_contable", "cliente", "company", "periodo"]);
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

function sync_from_linked_doc(frm, doctype, name, fields, fieldMap = {}) {
    if (!name) return;
    frappe.db.get_value(doctype, name, fields).then((r) => {
        const data = r.message || {};
        Object.keys(data).forEach((fieldname) => {
            const target = fieldMap[fieldname] || fieldname;
            if (data[fieldname]) {
                frm.set_value(target, data[fieldname]);
            }
        });
    });
}
