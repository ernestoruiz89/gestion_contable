frappe.ui.form.on("Expediente Auditoria", {
    refresh(frm) {
        frm.set_query("encargo_contable", () => ({
            filters: { tipo_de_servicio: "Auditoria" },
        }));

        if (frm.is_new()) {
            return;
        }

        const canManage =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Supervisor del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        const canClose =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        if (!canManage) {
            return;
        }

        frm.add_custom_button(__("Actualizar Resumen"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.expediente_auditoria.expediente_auditoria.refrescar_resumen_expediente",
                args: { expediente_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Recalculando expediente..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Auditoria"));

        if (frm.doc.estado_expediente === "Planeacion" || frm.doc.estado_expediente === "Ejecucion") {
            frm.add_custom_button(__("Enviar a Revision Tecnica"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.expediente_auditoria.expediente_auditoria.enviar_revision_tecnica",
                    args: { expediente_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Enviando a revision tecnica..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Auditoria"));
        }

        if (canClose && frm.doc.estado_expediente === "Revision Tecnica") {
            frm.add_custom_button(__("Cerrar Expediente"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.expediente_auditoria.expediente_auditoria.cerrar_expediente_auditoria",
                    args: { expediente_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Cerrando expediente..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Auditoria"));
        }
    },
});
