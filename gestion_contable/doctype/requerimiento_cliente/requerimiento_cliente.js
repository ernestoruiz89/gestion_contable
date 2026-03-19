frappe.ui.form.on("Requerimiento Cliente", {
    refresh(frm) {
        frm.set_query("encargo_contable", () => ({
            filters: frm.doc.cliente ? { cliente: frm.doc.cliente } : {},
        }));

        frm.set_query("periodo", () => ({
            filters: build_periodo_filters(frm),
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

        if (!canManage) {
            return;
        }

        frm.add_custom_button(__("Actualizar Seguimiento"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente.refrescar_resumen_requerimiento",
                args: { requerimiento_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Recalculando entregables..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Requerimiento"));

        if (!frm.doc.fecha_envio && frm.doc.estado_requerimiento === "Borrador") {
            frm.add_custom_button(__("Marcar Enviado"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente.marcar_requerimiento_enviado",
                    args: { requerimiento_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Marcando requerimiento como enviado..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Requerimiento"));
        }

        if ((frm.doc.canal_envio || "") === "Correo") {
            frm.add_custom_button(__("Enviar Correo"), () => {
                frappe.prompt(
                    [
                        {
                            fieldname: "tipo",
                            fieldtype: "Select",
                            label: __("Tipo de Correo"),
                            reqd: 1,
                            default: frm.doc.fecha_envio ? "recordatorio" : "envio",
                            options: "envio\nrecordatorio\nvencido",
                        },
                    ],
                    (values) => {
                        frappe.call({
                            method: "gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente.enviar_correo_requerimiento_manual",
                            args: { requerimiento_name: frm.doc.name, tipo: values.tipo },
                            freeze: true,
                            freeze_message: __("Enviando correo de requerimiento..."),
                            callback: () => frm.reload_doc(),
                        });
                    },
                    __("Enviar Correo"),
                    __("Enviar")
                );
            }, __("Correo"));
        }

        if (frm.doc.estado_requerimiento === "Recibido") {
            frm.add_custom_button(__("Cerrar Requerimiento"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente.cerrar_requerimiento_cliente",
                    args: { requerimiento_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Cerrando requerimiento..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Requerimiento"));
        }
    },

    cliente(frm) {
        if (!frm.doc.encargo_contable) {
            sync_company_from_cliente(frm);
        }
        frm.set_value("periodo", null);
    },

    company(frm) {
        frm.set_value("periodo", null);
    },

    canal_envio(frm) {
        render_email_mode_indicator(frm);
    },

    encargo_contable(frm) {
        if (!frm.doc.encargo_contable) {
            return;
        }
        frappe.db.get_value("Encargo Contable", frm.doc.encargo_contable, ["cliente", "company", "periodo_referencia"]).then((r) => {
            const data = r.message || {};
            if (data.cliente) frm.set_value("cliente", data.cliente);
            if (data.company) frm.set_value("company", data.company);
            if (data.periodo_referencia) frm.set_value("periodo", data.periodo_referencia);
        });
    },
});

function build_periodo_filters(frm) {
    const filters = {};
    if (frm.doc.cliente) filters.cliente = frm.doc.cliente;
    if (frm.doc.company) filters.company = frm.doc.company;
    return filters;
}

function sync_company_from_cliente(frm) {
    if (!frm.doc.cliente) return;
    frappe.db.get_value("Cliente Contable", frm.doc.cliente, "company_default").then((r) => {
        const company = r.message && r.message.company_default;
        if (company && !frm.doc.company) {
            frm.set_value("company", company);
        }
    });
}

function render_email_mode_indicator(frm) {
    const field = frm.fields_dict.indicador_modo_envio_correo;
    if (!field) return;

    if ((frm.doc.canal_envio || "") !== "Correo") {
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
            const envio = formatMode(status.auto_enviar_correo_requerimiento_envio);
            const recordatorio = formatMode(status.auto_enviar_recordatorio_requerimiento);
            const vencido = formatMode(status.auto_enviar_aviso_vencido_requerimiento);
            const tone = status.auto_enviar_correo_requerimiento_envio || status.auto_enviar_recordatorio_requerimiento || status.auto_enviar_aviso_vencido_requerimiento
                ? "alert-info"
                : "alert-warning";

            field.$wrapper.html(`
                <div class="alert ${tone}" style="margin-bottom: 0;">
                    <strong>${__("Modo de envio por correo")}</strong><br>
                    ${__("Envio inicial")}: <strong>${envio}</strong><br>
                    ${__("Recordatorio")}: <strong>${recordatorio}</strong><br>
                    ${__("Aviso vencido")}: <strong>${vencido}</strong><br>
                    <span class="small">${__("Si el modo es manual, usa el boton Enviar Correo del grupo Correo.")}</span>
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

function formatMode(enabled) {
    return enabled ? __("Automatico") : __("Manual");
}
