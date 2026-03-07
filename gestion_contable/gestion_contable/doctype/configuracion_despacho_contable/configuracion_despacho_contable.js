// Copyright (c) 2024, ernestoruiz89 and contributors
// For license information, please see license.txt

const DUMMY_TOOLS_METHOD_PREFIX = "gestion_contable.gestion_contable.doctype.configuracion_despacho_contable.configuracion_despacho_contable";
const SUGGESTED_EMAIL_TEMPLATES = [
    "GC - Requerimiento Envio",
    "GC - Requerimiento Recordatorio",
    "GC - Requerimiento Vencido",
    "GC - Cobranza Recordatorio",
    "GC - Cobranza Compromiso Pago",
];

frappe.ui.form.on("Configuracion Despacho Contable", {
    refresh(frm) {
        render_email_template_status(frm);
        update_dummy_tools_ui(frm);
    },

    generar_datos_dummy(frm) {
        if (frappe.session.user !== "Administrator") {
            frappe.msgprint(__("Solo el usuario Administrator puede ejecutar estas utilidades."));
            return;
        }

        frappe.confirm(
            __("Estas a punto de generar datos demo de desarrollo. Continuar?"),
            () => {
                frappe.call({
                    method: `${DUMMY_TOOLS_METHOD_PREFIX}.generar_datos_dummy`,
                    freeze: true,
                    freeze_message: __("Generando datos dummy de desarrollo..."),
                    callback(r) {
                        if (!r.exc) {
                            frappe.msgprint(__("Datos dummy generados exitosamente."));
                        }
                    },
                });
            }
        );
    },

    limpiar_datos_dummy(frm) {
        if (frappe.session.user !== "Administrator") {
            frappe.msgprint(__("Solo el usuario Administrator puede ejecutar estas utilidades."));
            return;
        }

        frappe.confirm(
            __("Vas a eliminar datos demo generados por la herramienta de desarrollo. Esta accion no se puede deshacer. Continuar?"),
            () => {
                frappe.call({
                    method: `${DUMMY_TOOLS_METHOD_PREFIX}.limpiar_datos_dummy`,
                    freeze: true,
                    freeze_message: __("Limpiando datos dummy de desarrollo..."),
                    callback(r) {
                        if (!r.exc) {
                            frappe.msgprint(__("Datos dummy eliminados exitosamente."));
                        }
                    },
                });
            }
        );
    },
});

function render_email_template_status(frm) {
    const wrapper = frm.fields_dict.plantillas_correo_estado.$wrapper;
    const configured = [
        frm.doc.template_email_requerimiento_envio,
        frm.doc.template_email_requerimiento_recordatorio,
        frm.doc.template_email_requerimiento_vencido,
        frm.doc.template_email_cobranza_recordatorio,
        frm.doc.template_email_cobranza_compromiso,
    ].filter(Boolean);

    const automation = [
        [__("Envio inicial requerimiento"), !!frm.doc.auto_enviar_correo_requerimiento_envio],
        [__("Recordatorio requerimiento"), !!frm.doc.auto_enviar_recordatorio_requerimiento],
        [__("Aviso vencido requerimiento"), !!frm.doc.auto_enviar_aviso_vencido_requerimiento],
        [__("Correo cobranza"), !!frm.doc.auto_enviar_correo_cobranza],
    ];

    const list = SUGGESTED_EMAIL_TEMPLATES.map((name) => `<li><code>${frappe.utils.escape_html(name)}</code></li>`).join("");
    const configuredText = configured.length
        ? `<p style="margin-top: 10px; margin-bottom: 0;"><strong>Configuradas actualmente:</strong> ${configured.map((name) => `<code>${frappe.utils.escape_html(name)}</code>`).join(", ")}</p>`
        : `<p style="margin-top: 10px; margin-bottom: 0;">Si dejas estos campos vacios, la app intentara usar los templates sugeridos.</p>`;
    const automationHtml = automation
        .map(([label, enabled]) => `<li>${frappe.utils.escape_html(label)}: <strong>${enabled ? __("Automatico") : __("Manual")}</strong></li>`)
        .join("");

    wrapper.html(`
        <div class="alert alert-info" style="margin-bottom: 0;">
            <strong>Templates sugeridos sincronizados por migrate/install:</strong>
            <ul style="margin-top: 8px; margin-bottom: 0; padding-left: 20px;">
                ${list}
            </ul>
            ${configuredText}
            <p style="margin-top: 10px; margin-bottom: 6px;"><strong>Modo actual de envio:</strong></p>
            <ul style="margin-top: 0; margin-bottom: 0; padding-left: 20px;">
                ${automationHtml}
            </ul>
        </div>
    `);
}

function update_dummy_tools_ui(frm) {
    toggle_dummy_buttons(frm, false);

    frappe.call({
        method: `${DUMMY_TOOLS_METHOD_PREFIX}.get_dummy_tools_status`,
        callback(r) {
            const status = r.message || {};
            render_dummy_tools_status(frm, status);
            toggle_dummy_buttons(frm, Boolean(status.enabled));
        },
        error() {
            render_dummy_tools_status(frm, {
                enabled: false,
                site_config_key: "gestion_contable_enable_destructive_dummy_tools",
                message: __("No fue posible verificar el estado de las herramientas dummy."),
            });
        },
    });
}

function toggle_dummy_buttons(frm, enabled) {
    ["generar_datos_dummy", "limpiar_datos_dummy"].forEach((fieldname) => {
        frm.toggle_display(fieldname, enabled);
    });
}

function render_dummy_tools_status(frm, status) {
    const wrapper = frm.fields_dict.herramientas_desarrollo_estado.$wrapper;
    const key = frappe.utils.escape_html(status.site_config_key || "gestion_contable_enable_destructive_dummy_tools");
    const message = frappe.utils.escape_html(status.message || "");

    if (status.enabled) {
        wrapper.html(`
            <div class="alert alert-warning" style="margin-bottom: 0;">
                <strong>Modo desarrollo habilitado.</strong><br>
                ${message}<br>
                Estas acciones siguen restringidas a <code>Administrator</code> y deben usarse solo temporalmente.
            </div>
        `);
        return;
    }

    wrapper.html(`
        <div class="alert alert-info" style="margin-bottom: 0;">
            <strong>Herramientas dummy deshabilitadas.</strong><br>
            ${message}<br>
            Para habilitarlas temporalmente, define <code>${key}: 1</code> en <code>site_config.json</code> y recarga el sitio.
        </div>
    `);
}
