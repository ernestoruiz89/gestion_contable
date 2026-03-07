frappe.ui.form.on("Hallazgo Auditoria", {
    refresh(frm) {
        frm.set_query("riesgo_control_auditoria", () => ({
            filters: frm.doc.expediente_auditoria ? { expediente_auditoria: frm.doc.expediente_auditoria } : {},
        }));

        frm.set_query("papel_trabajo_auditoria", () => ({
            filters: frm.doc.expediente_auditoria ? { expediente_auditoria: frm.doc.expediente_auditoria } : {},
        }));
    },
});
