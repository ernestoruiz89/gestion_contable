const AUDIT_PACKAGE_TYPES = ["Para Auditoria", "Auditado"];

function isAuditFlow(frm) {
    return AUDIT_PACKAGE_TYPES.includes(frm.doc.tipo_paquete)
        || Boolean(frm.doc.expediente_auditoria)
        || Boolean(frm.doc.informe_final_auditoria)
        || Boolean(frm.doc.dictamen_de_auditoria);
}

function updateAuditFields(frm) {
    const auditFlow = isAuditFlow(frm);
    const auditFields = ["expediente_auditoria", "informe_final_auditoria", "dictamen_de_auditoria"];

    auditFields.forEach((fieldname) => frm.toggle_display(fieldname, auditFlow));
    frm.set_df_property(
        "section_integracion",
        "label",
        auditFlow ? __("Integracion de Auditoria y Resumen") : __("Resumen del Paquete y Flujo Contable")
    );
    frm.set_df_property(
        "dictamen_de_auditoria",
        "description",
        auditFlow
            ? __("Requerido para emitir un paquete auditado.")
            : __("No aplica para paquetes preparados por contabilidad.")
    );
    frm.set_df_property(
        "informe_final_auditoria",
        "description",
        auditFlow
            ? __("Informe general del encargo de auditoria asociado al paquete.")
            : __("Este campo solo se usa cuando el paquete pertenece a un encargo de auditoria.")
    );
    frm.set_df_property(
        "expediente_auditoria",
        "description",
        auditFlow
            ? __("Expediente de auditoria vinculado al paquete.")
            : __("Este campo solo se usa cuando los estados financieros forman parte de una auditoria.")
    );

    frm.dashboard.clear_headline();
    frm.dashboard.set_headline_alert(
        auditFlow
            ? __("Flujo auditado: el paquete puede vincular expediente, informe final y dictamen. El dictamen sera obligatorio al emitir si el tipo de paquete es Auditado.")
            : __("Flujo contable: este paquete puede prepararse y exportarse sin expediente, informe final ni dictamen de auditoria."),
        auditFlow ? "blue" : "green"
    );
}

function openPrint(frm, formatName) {
    const url = frappe.urllib.get_full_url(
        `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(formatName)}&trigger_print=1`
    );
    window.open(url, "_blank");
}

function callWordExport({ method, packageName, freezeMessage, successMessage, errorTitle, errorMessage, reloadOnSuccess = false }) {
    frappe.call({
        method,
        args: { package_name: packageName },
        freeze: true,
        freeze_message: freezeMessage,
        callback: (r) => {
            if (!r.message || !r.message.file_url) {
                return;
            }
            frappe.show_alert({ message: successMessage(r.message), indicator: "green" });
            window.open(r.message.file_url, "_blank");
            if (reloadOnSuccess) {
                cur_frm.reload_doc();
            }
        },
        error: () => {
            frappe.msgprint({
                title: errorTitle,
                indicator: "orange",
                message: errorMessage,
            });
        },
    });
}

function addPrintButtons(frm) {
    const auditFlow = isAuditFlow(frm);

    frm.add_custom_button(__("Imprimir Paquete Completo"), () => {
        openPrint(frm, "Paquete Estados Financieros Cliente - Completo");
    }, __("Impresion"));

    frm.add_custom_button(__("Imprimir Notas Consolidadas"), () => {
        openPrint(frm, "Paquete Estados Financieros Cliente - Notas Consolidadas");
    }, __("Impresion"));

    frm.add_custom_button(__("Exportar Word EEFF"), () => {
        callWordExport({
            method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.exportar_paquete_eeff_word",
            packageName: frm.doc.name,
            freezeMessage: __("Generando paquete de estados financieros en Word..."),
            successMessage: (message) => message.version_documento
                ? __("Documento Word EEFF generado. Version {0}", [message.version_documento])
                : __("Documento Word EEFF generado"),
            errorTitle: __("Exportacion Word no disponible"),
            errorMessage: __(
                "No se pudo generar el documento Word EEFF. Si falta la dependencia opcional, instale <b>python-docx</b> con <b>bench pip install python-docx</b>."
            ),
            reloadOnSuccess: true,
        });
    }, __("Impresion"));

    if (frm.doc.dictamen_de_auditoria) {
        frm.add_custom_button(__("Imprimir Informe Completo Auditado"), () => {
            openPrint(frm, "Informe Completo de EEFF Auditados");
        }, __("Impresion"));

        frm.add_custom_button(__("Exportar Carta de Remision"), () => {
            callWordExport({
                method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.exportar_carta_remision_word",
                packageName: frm.doc.name,
                freezeMessage: __("Generando carta de remision en Word..."),
                successMessage: () => __("Carta de remision generada"),
                errorTitle: __("Exportacion Word no disponible"),
                errorMessage: __(
                    "No se pudo generar la carta de remision en Word. Si falta la dependencia opcional, instale <b>python-docx</b> con <b>bench pip install python-docx</b>."
                ),
            });
        }, __("Impresion"));

        frm.add_custom_button(__("Exportar Word Revision Auditada"), () => {
            callWordExport({
                method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.exportar_informe_completo_eeff_auditados_word",
                packageName: frm.doc.name,
                freezeMessage: __("Generando documento auditado en Word..."),
                successMessage: (message) => message.version_documento
                    ? __("Documento Word auditado generado. Version {0}", [message.version_documento])
                    : __("Documento Word auditado generado"),
                errorTitle: __("Exportacion Word no disponible"),
                errorMessage: __(
                    "No se pudo generar el documento Word auditado. Si falta la dependencia opcional, instale <b>python-docx</b> con <b>bench pip install python-docx</b>."
                ),
                reloadOnSuccess: true,
            });
        }, __("Impresion"));
    } else if (auditFlow) {
        frm.add_custom_button(__("Informacion Flujo Auditado"), () => {
            frappe.msgprint({
                title: __("Dictamen pendiente"),
                indicator: "blue",
                message: __("El paquete ya esta en flujo de auditoria. Podras imprimir y exportar la version auditada cuando vincules un Dictamen de Auditoria valido."),
            });
        }, __("Impresion"));
    }
}

function addDuplicateButton(frm) {
    frm.add_custom_button(__("Duplicar Paquete"), () => {
        const dialog = new frappe.ui.Dialog({
            title: __("Duplicar Paquete de Estados Financieros"),
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "cliente_info",
                    options: `<div><strong>${__("Cliente")}:<\/strong> ${frappe.utils.escape_html(frm.doc.cliente || "")}</div><div><strong>${__("Paquete origen")}:<\/strong> ${frappe.utils.escape_html(frm.doc.name || "")}</div>`,
                },
                {
                    fieldtype: "Link",
                    fieldname: "periodo_contable",
                    label: __("Periodo Contable"),
                    options: "Periodo Contable",
                    reqd: 1,
                    get_query: () => ({ filters: { cliente: frm.doc.cliente } }),
                },
                {
                    fieldtype: "Date",
                    fieldname: "fecha_corte",
                    label: __("Fecha Corte"),
                    reqd: 1,
                    default: frm.doc.fecha_corte,
                },
                {
                    fieldtype: "Select",
                    fieldname: "tipo_paquete",
                    label: __("Tipo Paquete"),
                    options: ["Preliminar", "Para Auditoria", "Auditado", "Reexpresado", "Comparativo", "Interno"].join("\n"),
                    default: frm.doc.tipo_paquete,
                },
                {
                    fieldtype: "Select",
                    fieldname: "marco_contable",
                    label: __("Marco Contable"),
                    options: ["NIIF", "NIIF para PYMES", "Base Fiscal", "Gerencial", "PCGA", "CONAMI", "Otra"].join("\n"),
                    default: frm.doc.marco_contable,
                },
                {
                    fieldtype: "Int",
                    fieldname: "version",
                    label: __("Version"),
                    reqd: 1,
                    default: 1,
                },
                {
                    fieldtype: "Check",
                    fieldname: "es_version_vigente",
                    label: __("Marcar como Version Vigente"),
                    default: 0,
                },
                {
                    fieldtype: "Link",
                    fieldname: "encargo_contable",
                    label: __("Encargo Contable"),
                    options: "Encargo Contable",
                    default: frm.doc.encargo_contable,
                },
                {
                    fieldtype: "Link",
                    fieldname: "expediente_auditoria",
                    label: __("Expediente Auditoria"),
                    options: "Expediente Auditoria",
                },
                {
                    fieldtype: "Small Text",
                    fieldname: "observaciones_generales",
                    label: __("Observaciones Generales"),
                    default: frm.doc.observaciones_generales,
                },
            ],
            primary_action_label: __("Duplicar"),
            primary_action(values) {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.duplicar_paquete_estados_financieros",
                    args: {
                        package_name: frm.doc.name,
                        ...values,
                    },
                    freeze: true,
                    freeze_message: __("Duplicando paquete de estados financieros..."),
                    callback: (r) => {
                        if (!r.message || !r.message.name) {
                            return;
                        }
                        frappe.show_alert({
                            message: __("Paquete duplicado. Estados: {0}, Notas: {1}", [r.message.copied_states || 0, r.message.copied_notes || 0]),
                            indicator: "green",
                        });
                        dialog.hide();
                        frappe.set_route("Form", "Paquete Estados Financieros Cliente", r.message.name);
                    },
                });
            },
        });
        dialog.show();
    }, __("Estados Financieros"));
}

frappe.ui.form.on("Paquete Estados Financieros Cliente", {
    setup(frm) {
        frm.set_query("encargo_contable", () => {
            return {
                filters: frm.doc.cliente ? { cliente: frm.doc.cliente } : {}
            };
        });

        frm.set_query("periodo_contable", () => {
            return {
                filters: frm.doc.cliente ? { cliente: frm.doc.cliente } : {}
            };
        });

        frm.set_query("expediente_auditoria", () => {
            return {
                filters: frm.doc.cliente ? { cliente: frm.doc.cliente } : {}
            };
        });

        frm.set_query("esquema_mapeo_contable", () => {
            return {
                filters: frm.doc.cliente ? { cliente: frm.doc.cliente } : {}
            };
        });
    },

    tipo_paquete(frm) {
        updateAuditFields(frm);
    },

    refresh(frm) {
        if (frm.is_new()) {
            updateAuditFields(frm);
            return;
        }

        updateAuditFields(frm);
        addPrintButtons(frm);
        addDuplicateButton(frm);

        frm.add_custom_button(__("Refrescar Resumen"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.refrescar_resumen_paquete_estados_financieros",
                args: { package_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Actualizando resumen del paquete..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Estados Financieros"));

        frm.add_custom_button(__("Actualizar desde Balanza"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.actualizar_paquete_desde_balanza_paquete",
                args: { package_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Actualizando estados, notas y sumarias desde balanza..."),
                callback: (r) => {
                    const message = r.message || {};
                    frappe.show_alert({
                        message: __("Actualizacion completada. Estados: {0}, Notas: {1}, Sumarias: {2}", [message.estados_actualizados || 0, message.notas_actualizadas || 0, message.sumarias_actualizadas || 0]),
                        indicator: (message.alertas || []).length ? "orange" : "green",
                    });
                    frm.reload_doc();
                },
            });
        }, __("Estados Financieros"));

        if (frm.doc.esquema_mapeo_contable) {
            frm.add_custom_button(__("Mapeo (Editor)"), () => {
                frappe.route_options = {
                    esquema_name: frm.doc.esquema_mapeo_contable,
                    cliente: frm.doc.cliente
                };
                frappe.set_route("creador-de-mapeo-contable");
            }, __("Estados Financieros"));
        }

        if (frm.doc.estado_aprobacion === "Aprobado" && frm.doc.estado_preparacion !== "Emitido") {
            frm.add_custom_button(__("Emitir Paquete"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.emitir_paquete_estados_financieros",
                    args: { package_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Emitiendo paquete de estados financieros..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Estados Financieros"));
        }
    },
});
