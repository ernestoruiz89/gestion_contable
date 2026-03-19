frappe.ui.form.on("Papel Trabajo Auditoria", {
    refresh(frm) {
        frm.set_query("riesgo_control_auditoria", () => ({
            filters: frm.doc.expediente_auditoria ? { expediente_auditoria: frm.doc.expediente_auditoria } : {},
        }));

        frm.set_query("documento_contable", () => ({
            filters: frm.doc.encargo_contable ? { encargo_contable: frm.doc.encargo_contable } : {},
        }));

        frm.set_query("task", () => ({
            filters: frm.doc.encargo_contable ? { encargo_contable: frm.doc.encargo_contable } : {},
        }));

        frm.set_query("evidencia_documental_file", () => ({
            filters: {
                name: ["in", frm.__evidence_files || []],
            },
        }));

        this.load_document_evidence_options(frm);
    },

    documento_contable(frm) {
        frm.set_value("evidencia_documental_file", null);
        frm.set_value("codigo_evidencia_documental", null);
        frm.set_value("version_evidencia_documental", null);
        frm.set_value("hash_evidencia_sha256", null);
        this.load_document_evidence_options(frm);
    },

    evidencia_documental_file(frm) {
        const selected = (frm.__document_evidences || []).find((row) => row.file === frm.doc.evidencia_documental_file);
        frm.set_value("codigo_evidencia_documental", selected ? selected.codigo_documental || null : null);
        frm.set_value("version_evidencia_documental", selected ? selected.numero_version || null : null);
        frm.set_value("hash_evidencia_sha256", selected ? selected.hash_sha256 || null : null);
    },

    load_document_evidence_options(frm) {
        frm.__evidence_files = [];
        frm.__document_evidences = [];

        if (!frm.doc.documento_contable) {
            frm.refresh_field("evidencia_documental_file");
            return;
        }

        frappe.call({
            method: "gestion_contable.gestion_contable.doctype.papel_trabajo_auditoria.papel_trabajo_auditoria.get_documento_evidencias",
            args: { documento_contable: frm.doc.documento_contable },
            callback: (r) => {
                const evidences = r.message || [];
                frm.__document_evidences = evidences;
                frm.__evidence_files = evidences.map((row) => row.file);
                frm.refresh_field("evidencia_documental_file");
                if (frm.doc.evidencia_documental_file) {
                    this.evidencia_documental_file(frm);
                }
            },
        });
    },
});
