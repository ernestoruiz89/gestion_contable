frappe.ui.form.on("Entregable Cliente", {
    refresh(frm) {
        frm.set_query("documento_contable", () => ({
            filters: frm.doc.encargo_contable ? { encargo_contable: frm.doc.encargo_contable } : {},
        }));
    },
});
