frappe.ui.form.on("Version Balanza Cliente", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(__("Importar CSV"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.version_balanza_cliente.version_balanza_cliente.importar_version_balanza_desde_archivo",
                args: { version_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Importando balanza..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Balanza"));

        frm.add_custom_button(__("Publicar Version"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.version_balanza_cliente.version_balanza_cliente.publicar_version_balanza",
                args: { version_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Publicando balanza..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Balanza"));
    },
});
