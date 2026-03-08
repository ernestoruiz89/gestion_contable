const statePrintFormats = {
    "Estado de Situacion Financiera": "Estado Financiero Cliente - Situacion Financiera",
    "Estado de Resultados": "Estado Financiero Cliente - Resultados",
    "Estado de Cambios en el Patrimonio": "Estado Financiero Cliente - Cambios en el Patrimonio",
    "Estado de Flujos de Efectivo": "Estado Financiero Cliente - Flujos de Efectivo",
};

frappe.ui.form.on("Estado Financiero Cliente", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        const formatName = statePrintFormats[frm.doc.tipo_estado];
        if (!formatName) {
            return;
        }

        frm.add_custom_button(__("Imprimir Formato Sugerido"), () => {
            const url = frappe.urllib.get_full_url(
                `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(formatName)}&trigger_print=1`
            );
            window.open(url, "_blank");
        }, __("Impresion"));
    },
});
