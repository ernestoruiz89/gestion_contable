frappe.ui.form.on("Seguimiento Cobranza", {
    refresh(frm) {
        frm.set_query("sales_invoice", () => ({
            filters: {
                docstatus: 1,
            },
        }));

        frm.set_query("payment_entry", () => ({
            filters: frm.doc.customer
                ? { party: frm.doc.customer, docstatus: ["<", 2] }
                : { docstatus: ["<", 2] },
        }));

        render_email_mode_indicator(frm);

        if (frm.is_new()) {
            return;
        }

        const canManage =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Supervisor del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        if (!canManage || (frm.doc.canal || "") !== "Correo") {
            return;
        }

        frm.add_custom_button(__("Enviar Correo Cobranza"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.seguimiento_cobranza.seguimiento_cobranza.enviar_correo_seguimiento_cobranza_manual",
                args: { seguimiento_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Enviando correo de cobranza..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Correo"));
    },

    canal(frm) {
        render_email_mode_indicator(frm);
    },
});

function render_email_mode_indicator(frm) {
    const field = frm.fields_dict.indicador_modo_envio_correo;
    if (!field) return;

    if ((frm.doc.canal || "") !== "Correo") {
        field.$wrapper.empty();
        frm.toggle_display("indicador_modo_envio_correo", false);
        return;
    }

    frm.toggle_display("indicador_modo_envio_correo", true);
    field.$wrapper.html(`<div class="text-muted small">${__("Consultando configuracion de correo...")}</div>`);

    frappe.call({
        method: "gestion_contable.gestion_contable.utils.emailing.get_despacho_email_automation_status",
        callback(r) {
            const status = r.message || {};
            const modo = status.auto_enviar_correo_cobranza ? __("Automatico") : __("Manual");
            const tone = status.auto_enviar_correo_cobranza ? "alert-info" : "alert-warning";

            field.$wrapper.html(`
                <div class="alert ${tone}" style="margin-bottom: 0;">
                    <strong>${__("Modo de envio por correo")}</strong><br>
                    ${__("Correo de cobranza")}: <strong>${modo}</strong><br>
                    <span class="small">${__("Si el modo es manual, usa el boton Enviar Correo Cobranza del grupo Correo.")}</span>
                </div>
            `);
        },
        error() {
            field.$wrapper.html(`
                <div class="alert alert-warning" style="margin-bottom: 0;">
                    ${__("No fue posible consultar la configuracion de automatizacion de correo.")}
                </div>
            `);
        },
    });
}
