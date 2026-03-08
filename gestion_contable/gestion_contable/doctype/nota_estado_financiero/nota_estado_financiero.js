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

        frm.add_custom_button(__("Nueva Seccion"), () => open_section_dialog(frm), __("Tabla Compleja"));
        frm.add_custom_button(__("Nueva Columna"), () => open_column_dialog(frm), __("Tabla Compleja"));
        frm.add_custom_button(__("Nueva Fila"), () => open_row_dialog(frm), __("Tabla Compleja"));
        frm.add_custom_button(__("Nueva Celda"), () => open_cell_dialog(frm), __("Tabla Compleja"));
        frm.add_custom_button(__("Asistente de Tabla"), () => open_table_wizard(frm), __("Tabla Compleja"));
    },
});

function get_sections(frm) {
    return (frm.doc.secciones_estructuradas || []).map((row) => ({
        value: row.seccion_id,
        label: `${row.seccion_id} - ${row.titulo_seccion}`,
        row,
    }));
}

function get_section_options(frm) {
    return get_sections(frm).map((item) => item.value);
}

function get_rows_for_section(frm, sectionId) {
    return (frm.doc.filas_tabulares || []).filter((row) => row.seccion_id === sectionId);
}

function get_columns_for_section(frm, sectionId) {
    return (frm.doc.columnas_tabulares || []).filter((row) => row.seccion_id === sectionId);
}

function nextOrder(rows, fieldname = "orden") {
    return (rows || []).reduce((max, row) => Math.max(max, parseInt(row[fieldname] || 0, 10)), 0) + 1;
}

function nextSectionId(frm) {
    const seq = (frm.doc.secciones_estructuradas || []).length + 1;
    return `SEC-${String(seq).padStart(2, "0")}`;
}

function refreshTableFields(frm) {
    ["secciones_estructuradas", "columnas_tabulares", "filas_tabulares", "celdas_tabulares"].forEach((fieldname) => frm.refresh_field(fieldname));
}

function openSectionDialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Nueva Seccion Estructurada"),
        fields: [
            { fieldname: "seccion_id", fieldtype: "Data", label: __("ID Seccion"), default: nextSectionId(frm), reqd: 1 },
            { fieldname: "titulo_seccion", fieldtype: "Data", label: __("Titulo Seccion"), reqd: 1 },
            { fieldname: "tipo_seccion", fieldtype: "Select", label: __("Tipo Seccion"), options: ["Narrativa", "Tabla", "Texto y Tabla"], default: "Tabla", reqd: 1 },
            { fieldname: "orden", fieldtype: "Int", label: __("Orden"), default: nextOrder(frm.doc.secciones_estructuradas) },
            { fieldname: "contenido_narrativo", fieldtype: "Small Text", label: __("Contenido Narrativo") },
        ],
        primary_action_label: __("Agregar"),
        primary_action(values) {
            frm.add_child("secciones_estructuradas", values);
            refreshTableFields(frm);
            frm.dirty();
            dialog.hide();
        },
    });
    dialog.show();
}

function openColumnDialog(frm) {
    const sectionOptions = get_section_options(frm);
    if (!sectionOptions.length) {
        frappe.msgprint(__("Primero crea una seccion estructurada."));
        return;
    }
    const dialog = new frappe.ui.Dialog({
        title: __("Nueva Columna Tabular"),
        fields: [
            { fieldname: "seccion_id", fieldtype: "Select", label: __("Seccion"), options: sectionOptions.join("\n"), reqd: 1, default: sectionOptions[0] },
            { fieldname: "codigo_columna", fieldtype: "Data", label: __("Codigo Columna"), reqd: 1 },
            { fieldname: "etiqueta", fieldtype: "Data", label: __("Etiqueta"), reqd: 1 },
            { fieldname: "tipo_dato", fieldtype: "Select", label: __("Tipo Dato"), options: ["Texto", "Numero", "Moneda", "Porcentaje"], default: "Moneda", reqd: 1 },
            { fieldname: "alineacion", fieldtype: "Select", label: __("Alineacion"), options: ["Left", "Center", "Right"], default: "Right", reqd: 1 },
            { fieldname: "grupo_columna", fieldtype: "Data", label: __("Grupo Columna") },
            { fieldname: "orden", fieldtype: "Int", label: __("Orden") },
            { fieldname: "es_total", fieldtype: "Check", label: __("Es Total") },
        ],
        primary_action_label: __("Agregar"),
        primary_action(values) {
            values.orden = values.orden || nextOrder(get_columns_for_section(frm, values.seccion_id));
            frm.add_child("columnas_tabulares", values);
            refreshTableFields(frm);
            frm.dirty();
            dialog.hide();
        },
    });
    dialog.show();
}

function openRowDialog(frm) {
    const sectionOptions = get_section_options(frm);
    if (!sectionOptions.length) {
        frappe.msgprint(__("Primero crea una seccion estructurada."));
        return;
    }
    const dialog = new frappe.ui.Dialog({
        title: __("Nueva Fila Tabular"),
        fields: [
            { fieldname: "seccion_id", fieldtype: "Select", label: __("Seccion"), options: sectionOptions.join("\n"), reqd: 1, default: sectionOptions[0] },
            { fieldname: "codigo_fila", fieldtype: "Data", label: __("Codigo Fila"), reqd: 1 },
            { fieldname: "descripcion", fieldtype: "Data", label: __("Descripcion"), reqd: 1 },
            { fieldname: "nivel", fieldtype: "Int", label: __("Nivel"), default: 1 },
            { fieldname: "tipo_fila", fieldtype: "Select", label: __("Tipo Fila"), options: ["Detalle", "Subtotal", "Total", "Comentario"], default: "Detalle", reqd: 1 },
            { fieldname: "orden", fieldtype: "Int", label: __("Orden") },
            { fieldname: "negrita", fieldtype: "Check", label: __("Negrita") },
            { fieldname: "subrayado", fieldtype: "Check", label: __("Subrayado") },
        ],
        primary_action_label: __("Agregar"),
        primary_action(values) {
            values.orden = values.orden || nextOrder(get_rows_for_section(frm, values.seccion_id));
            frm.add_child("filas_tabulares", values);
            refreshTableFields(frm);
            frm.dirty();
            dialog.hide();
        },
    });
    dialog.show();
}

function openCellDialog(frm) {
    const sectionOptions = get_section_options(frm);
    if (!sectionOptions.length) {
        frappe.msgprint(__("Primero crea una seccion estructurada."));
        return;
    }
    const dialog = new frappe.ui.Dialog({
        title: __("Nueva Celda Tabular"),
        fields: [
            { fieldname: "seccion_id", fieldtype: "Select", label: __("Seccion"), options: sectionOptions.join("\n"), reqd: 1, default: sectionOptions[0], onchange: () => updateCellDialogOptions(frm, dialog) },
            { fieldname: "codigo_fila", fieldtype: "Select", label: __("Fila"), options: "", reqd: 1 },
            { fieldname: "codigo_columna", fieldtype: "Select", label: __("Columna"), options: "", reqd: 1 },
            { fieldname: "valor_texto", fieldtype: "Data", label: __("Valor Texto") },
            { fieldname: "valor_numero", fieldtype: "Float", label: __("Valor Numero") },
            { fieldname: "formato_numero", fieldtype: "Select", label: __("Formato Numero"), options: ["Numero", "Moneda", "Porcentaje"], default: "Moneda" },
            { fieldname: "comentario", fieldtype: "Small Text", label: __("Comentario") },
        ],
        primary_action_label: __("Agregar"),
        primary_action(values) {
            frm.add_child("celdas_tabulares", values);
            refreshTableFields(frm);
            frm.dirty();
            dialog.hide();
        },
    });
    dialog.show();
    updateCellDialogOptions(frm, dialog);
}

function updateCellDialogOptions(frm, dialog) {
    const sectionId = dialog.get_value("seccion_id");
    const rows = get_rows_for_section(frm, sectionId).map((row) => row.codigo_fila);
    const columns = get_columns_for_section(frm, sectionId).map((row) => row.codigo_columna);
    dialog.set_df_property("codigo_fila", "options", rows.join("\n"));
    dialog.set_df_property("codigo_columna", "options", columns.join("\n"));
    if (rows.length && !dialog.get_value("codigo_fila")) {
        dialog.set_value("codigo_fila", rows[0]);
    }
    if (columns.length && !dialog.get_value("codigo_columna")) {
        dialog.set_value("codigo_columna", columns[0]);
    }
}

function parseDefinitionLines(raw, minParts) {
    return (raw || "")
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => line.split("|").map((part) => part.trim()))
        .filter((parts) => parts.length >= minParts);
}

function openTableWizard(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Asistente de Tabla Compleja"),
        size: "extra-large",
        fields: [
            { fieldname: "help_html", fieldtype: "HTML", options: `<div style="padding-bottom:8px;color:#475569;">${__("Usa una linea por columna y fila. Formato columnas: CODIGO|Etiqueta|TipoDato|Alineacion. Formato filas: CODIGO|Descripcion|Nivel|TipoFila.")}</div>` },
            { fieldname: "seccion_id", fieldtype: "Data", label: __("ID Seccion"), default: nextSectionId(frm), reqd: 1 },
            { fieldname: "titulo_seccion", fieldtype: "Data", label: __("Titulo Seccion"), reqd: 1 },
            { fieldname: "tipo_seccion", fieldtype: "Select", label: __("Tipo Seccion"), options: ["Tabla", "Texto y Tabla"], default: "Tabla", reqd: 1 },
            { fieldname: "orden", fieldtype: "Int", label: __("Orden"), default: nextOrder(frm.doc.secciones_estructuradas) },
            { fieldname: "contenido_narrativo", fieldtype: "Small Text", label: __("Introduccion / Narrativa") },
            { fieldname: "section_cols", fieldtype: "Section Break", label: __("Columnas") },
            { fieldname: "columnas_def", fieldtype: "Long Text", label: __("Definicion de Columnas"), reqd: 1, default: "VIG|Vigentes|Moneda|Right\nTOT|Total|Moneda|Right" },
            { fieldname: "section_rows", fieldtype: "Section Break", label: __("Filas") },
            { fieldname: "filas_def", fieldtype: "Long Text", label: __("Definicion de Filas"), reqd: 1, default: "DET|Detalle principal|1|Detalle\nSUB|Subtotal|1|Subtotal" },
        ],
        primary_action_label: __("Construir Tabla"),
        primary_action(values) {
            const sectionId = (values.seccion_id || "").trim().toUpperCase();
            if (!sectionId) {
                frappe.throw(__("Debes indicar el ID de seccion."));
            }
            frm.add_child("secciones_estructuradas", {
                seccion_id: sectionId,
                titulo_seccion: values.titulo_seccion,
                tipo_seccion: values.tipo_seccion,
                orden: values.orden,
                contenido_narrativo: values.contenido_narrativo,
            });

            const columnas = parseDefinitionLines(values.columnas_def, 4);
            const filas = parseDefinitionLines(values.filas_def, 4);
            if (!columnas.length || !filas.length) {
                frappe.throw(__("Debes definir al menos una columna y una fila validas."));
            }

            columnas.forEach((parts, index) => {
                frm.add_child("columnas_tabulares", {
                    seccion_id: sectionId,
                    codigo_columna: parts[0].toUpperCase(),
                    etiqueta: parts[1],
                    tipo_dato: parts[2] || "Moneda",
                    alineacion: parts[3] || "Right",
                    orden: index + 1,
                });
            });

            filas.forEach((parts, index) => {
                frm.add_child("filas_tabulares", {
                    seccion_id: sectionId,
                    codigo_fila: parts[0].toUpperCase(),
                    descripcion: parts[1],
                    nivel: parseInt(parts[2] || 1, 10),
                    tipo_fila: parts[3] || "Detalle",
                    orden: index + 1,
                    negrita: ["Subtotal", "Total"].includes(parts[3]) ? 1 : 0,
                });
            });

            refreshTableFields(frm);
            frm.dirty();
            dialog.hide();
            frappe.show_alert({ message: __("Seccion, columnas y filas creadas. Ahora agrega las celdas desde 'Nueva Celda'."), indicator: "green" });
        },
    });
    dialog.show();
}

function open_section_dialog(frm) {
    return openSectionDialog(frm);
}

function open_column_dialog(frm) {
    return openColumnDialog(frm);
}

function open_row_dialog(frm) {
    return openRowDialog(frm);
}

function open_cell_dialog(frm) {
    return openCellDialog(frm);
}

function open_table_wizard(frm) {
    return openTableWizard(frm);
}
