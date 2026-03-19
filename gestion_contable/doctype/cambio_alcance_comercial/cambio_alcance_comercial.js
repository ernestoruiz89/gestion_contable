frappe.ui.form.on("Cambio Alcance Comercial", {
    refresh(frm) {
        frm.set_query("cotizacion", () => ({
            filters: frm.doc.customer ? { quotation_to: "Customer", party_name: frm.doc.customer } : {},
        }));

        if (frm.is_new()) {
            return;
        }

        const canApply =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        if (!canApply || frm.doc.estado_cambio === "Aplicado" || frm.doc.estado_aprobacion !== "Aprobado") {
            return;
        }

        frm.add_custom_button(__("Aplicar Cambio"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.cambio_alcance_comercial.cambio_alcance_comercial.aplicar_cambio_alcance",
                args: { cambio_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Aplicando cambio de alcance..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Comercial"));
    },
});
