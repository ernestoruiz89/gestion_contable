frappe.ui.form.on("Contrato Comercial", {
    refresh(frm) {
        frm.set_query("oportunidad", () => ({
            filters: frm.doc.customer ? { opportunity_from: "Customer", party_name: frm.doc.customer } : {},
        }));
        frm.set_query("cotizacion", () => ({
            filters: frm.doc.customer ? { quotation_to: "Customer", party_name: frm.doc.customer } : {},
        }));
        frm.set_query("contrato_erpnext", () => ({
            filters: frm.doc.customer ? { party_type: "Customer", party_name: frm.doc.customer } : {},
        }));

        if (frm.is_new()) {
            return;
        }

        if (frm.doc.formato_impresion_sugerido) {
            frm.add_custom_button(__("Imprimir Formato Sugerido"), () => {
                const url = frappe.urllib.get_full_url(
                    `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(frm.doc.formato_impresion_sugerido)}&trigger_print=1`
                );
                window.open(url, "_blank");
            }, __("Impresion"));
        }

        const canManage =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Supervisor del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        if (!canManage || frm.doc.estado_aprobacion !== "Aprobado") {
            return;
        }

        frm.add_custom_button(__("Sincronizar Tarifas Vigentes"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.contrato_comercial.contrato_comercial.sincronizar_tarifas_contrato",
                args: { contrato_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Sincronizando tarifas..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Comercial"));

        frm.add_custom_button(__("Nuevo Cambio de Alcance"), () => {
            frappe.new_doc("Cambio Alcance Comercial", {
                contrato_comercial: frm.doc.name,
            });
        }, __("Comercial"));
    },
});
