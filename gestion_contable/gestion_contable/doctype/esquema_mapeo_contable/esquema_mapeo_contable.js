frappe.ui.form.on("Esquema Mapeo Contable", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(__("Ir al Creador"), () => {
            frappe.route_options = {
                esquema_name: frm.doc.name,
                cliente: frm.doc.cliente,
            };
            frappe.set_route("creador-de-mapeo-contable");
        });
    },
});
