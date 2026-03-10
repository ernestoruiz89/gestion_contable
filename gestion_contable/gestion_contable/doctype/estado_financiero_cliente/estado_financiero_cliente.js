const statePrintFormats = {
    "Estado de Situacion Financiera": "Estado Financiero Cliente - Situacion Financiera",
    "Estado de Resultados": "Estado Financiero Cliente - Resultados",
    "Estado de Cambios en el Patrimonio": "Estado Financiero Cliente - Cambios en el Patrimonio",
    "Estado de Flujos de Efectivo": "Estado Financiero Cliente - Flujos de Efectivo",
};

function updateGridAmountLabel(grid, fieldname, label) {
    if (!grid || !fieldname || !label) {
        return;
    }
    if (typeof grid.update_docfield_property === "function") {
        grid.update_docfield_property(fieldname, "label", label);
        return;
    }
    (grid.docfields || []).forEach((df) => {
        if (df.fieldname === fieldname) {
            df.label = label;
        }
    });
}

function refreshStateAmountLabels(frm) {
    const packageName = frm.doc.paquete_estados_financieros_cliente;
    const grid = frm.fields_dict.lineas && frm.fields_dict.lineas.grid;
    if (!packageName || !grid) {
        return;
    }

    frappe.call({
        method: "gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente.obtener_etiquetas_columnas_eeff",
        args: {
            package_name: packageName,
            fecha_actual: frm.doc.fecha_corte || null,
            fecha_comparativa: frm.doc.fecha_comparativa || null,
        },
        callback: (response) => {
            const labels = response.message || {};
            updateGridAmountLabel(grid, "monto_actual", labels.actual || __("Actual"));
            updateGridAmountLabel(grid, "monto_comparativo", labels.comparativo || __("Comparativo"));
            frm.refresh_field("lineas");
        },
    });
}

frappe.ui.form.on("Estado Financiero Cliente", {
    paquete_estados_financieros_cliente(frm) {
        if (frm.doc.paquete_estados_financieros_cliente) {
            frappe.db.get_value("Paquete Estados Financieros Cliente", frm.doc.paquete_estados_financieros_cliente, ["fecha_corte", "fecha_corte_comparativa"], (r) => {
                if (r && r.fecha_corte) {
                    frm.set_value("fecha_corte", r.fecha_corte);
                }
                if (r && r.fecha_corte_comparativa) {
                    frm.set_value("fecha_comparativa", r.fecha_corte_comparativa);
                }
                refreshStateAmountLabels(frm);
            });
        } else {
            refreshStateAmountLabels(frm);
        }
    },

    refresh(frm) {
        refreshStateAmountLabels(frm);

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
