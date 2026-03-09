frappe.ui.form.on("Paquete Estados Financieros Cliente", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(__("Imprimir Paquete Completo"), () => {
            const url = frappe.urllib.get_full_url(
                `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent("Paquete Estados Financieros Cliente - Completo")}&trigger_print=1`
            );
            window.open(url, "_blank");
        }, __("Impresion"));

        frm.add_custom_button(__("Imprimir Notas Consolidadas"), () => {
            const url = frappe.urllib.get_full_url(
                `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent("Paquete Estados Financieros Cliente - Notas Consolidadas")}&trigger_print=1`
            );
            window.open(url, "_blank");
        }, __("Impresion"));

        if (frm.doc.dictamen_de_auditoria) {
            frm.add_custom_button(__("Imprimir Informe Completo Auditado"), () => {
                const url = frappe.urllib.get_full_url(
                    `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent("Informe Completo de EEFF Auditados")}&trigger_print=1`
                );
                window.open(url, "_blank");
            }, __("Impresion"));

            frm.add_custom_button(__("Exportar Carta de Remision"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.exportar_carta_remision_word",
                    args: { package_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Generando carta de remision en Word..."),
                    callback: (r) => {
                        if (!r.message || !r.message.file_url) {
                            return;
                        }
                        frappe.show_alert({ message: __("Carta de remision generada"), indicator: "green" });
                        window.open(r.message.file_url, "_blank");
                    },
                    error: () => {
                        frappe.msgprint({
                            title: __("Exportacion Word no disponible"),
                            indicator: "orange",
                            message: __(
                                "No se pudo generar la carta de remision en Word. Si falta la dependencia opcional, instale <b>python-docx</b> con <b>bench pip install python-docx</b>."
                            ),
                        });
                    },
                });
            }, __("Impresion"));

            frm.add_custom_button(__("Exportar Word Revision"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.exportar_informe_completo_eeff_auditados_word",
                    args: { package_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Generando documento Word para revision..."),
                    callback: (r) => {
                        if (!r.message || !r.message.file_url) {
                            return;
                        }
                        const versionText = r.message.version_documento
                            ? __("Documento Word generado. Version {0}", [r.message.version_documento])
                            : __("Documento Word generado");
                        frappe.show_alert({ message: versionText, indicator: "green" });
                        window.open(r.message.file_url, "_blank");
                        frm.reload_doc();
                    },
                    error: () => {
                        frappe.msgprint({
                            title: __("Exportacion Word no disponible"),
                            indicator: "orange",
                            message: __(
                                "No se pudo generar el documento Word. Si falta la dependencia opcional, instale <b>python-docx</b> con <b>bench pip install python-docx</b>. El resto de la app sigue operando normalmente."
                            ),
                        });
                    },
                });
            }, __("Impresion"));
        }

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
                        options: "Preliminar
Para Auditoria
Auditado
Reexpresado
Comparativo",
                        default: frm.doc.tipo_paquete,
                    },
                    {
                        fieldtype: "Select",
                        fieldname: "marco_contable",
                        label: __("Marco Contable"),
                        options: "NIIF
NIIF para PYMES
Base Fiscal
Gerencial
Otra",
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

        frm.add_custom_button(__("Refrescar Resumen"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.refrescar_resumen_paquete_estados_financieros",
                args: { package_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Actualizando resumen del paquete..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Estados Financieros"));

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