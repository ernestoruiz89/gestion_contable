frappe.ui.form.on("Nota Estado Financiero", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(__("Imprimir Nota"), () => {
            window.open(
                `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent("Nota Estado Financiero - Individual")}&trigger_print=1`
            );
        }, __("Impresion"));
    },
});
