const dictamenModifiedOpinions = ["Con Salvedades", "Adversa", "Abstencion"];

frappe.ui.form.on("Informe Final Auditoria", {
    refresh(frm) {
        frm.set_query("expediente_auditoria", () => ({
            filters: {
                estado_expediente: ["in", ["Cerrada", "Archivada"]],
            },
        }));

        frm.trigger("toggle_type_sections");

        if (frm.is_new()) {
            return;
        }

        const canManage =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Supervisor del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        const canEmit =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        if (!canManage) {
            return;
        }

        if (frm.doc.formato_impresion_sugerido) {
            frm.add_custom_button(__("Imprimir Formato Sugerido"), () => {
                const url = frappe.urllib.get_full_url(
                    `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(frm.doc.formato_impresion_sugerido)}&trigger_print=1`
                );
                window.open(url, "_blank");
            }, __("Impresion"));
        }

        if (frm.doc.expediente_auditoria) {
            frm.add_custom_button(__("Abrir Expediente"), () => {
                frappe.set_route("Form", "Expediente Auditoria", frm.doc.expediente_auditoria);
            }, __("Auditoria"));
        }

        if (frm.doc.estado_emision !== "Emitido") {
            frm.add_custom_button(__("Refrescar Contenido"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.informe_final_auditoria.informe_final_auditoria.refrescar_contenido_informe_final",
                    args: { informe_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Actualizando contenido sugerido..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Auditoria"));
        }

        if (canEmit && frm.doc.estado_aprobacion === "Aprobado" && frm.doc.estado_emision !== "Emitido") {
            frm.add_custom_button(__("Emitir Informe"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.informe_final_auditoria.informe_final_auditoria.emitir_informe_final_auditoria",
                    args: { informe_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Emitiendo informe final..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Auditoria"));
        }
    },

    tipo_de_informe(frm) {
        frm.trigger("toggle_type_sections");
    },

    tipo_opinion(frm) {
        frm.trigger("toggle_type_sections");
    },

    toggle_type_sections(frm) {
        const isDictamen = frm.doc.tipo_de_informe === "Dictamen de Auditoria";
        const needsOpinion = ["Informe Final General", "Dictamen de Auditoria"].includes(frm.doc.tipo_de_informe);
        const modifiedOpinion = dictamenModifiedOpinions.includes(frm.doc.tipo_opinion);
        const abstencion = frm.doc.tipo_opinion === "Abstencion";
        const normTitle = frm.doc.tipo_opinion === "Favorable" ? __("NIA 700") : __("NIA 705");

        frm.toggle_display(
            [
                "section_dictamen",
                "fundamento_opinion",
                "section_modificacion_dictamen",
                "asunto_que_origina_modificacion",
                "fundamento_salvedad",
                "efecto_generalizado",
                "limitacion_alcance_material",
                "section_parrafos_dictamen",
                "parrafo_enfasis",
                "parrafo_otros_asuntos",
                "responsabilidades_administracion",
                "responsabilidades_auditor",
            ],
            isDictamen
        );

        frm.toggle_display(
            [
                "section_modificacion_dictamen",
                "asunto_que_origina_modificacion",
                "fundamento_salvedad",
                "efecto_generalizado",
                "limitacion_alcance_material",
            ],
            isDictamen && modifiedOpinion
        );

        frm.toggle_reqd("tipo_opinion", needsOpinion);
        frm.toggle_reqd("fundamento_opinion", isDictamen);
        frm.toggle_reqd("responsabilidades_administracion", isDictamen);
        frm.toggle_reqd("responsabilidades_auditor", isDictamen);
        frm.toggle_reqd("asunto_que_origina_modificacion", isDictamen && modifiedOpinion);
        frm.toggle_reqd("fundamento_salvedad", isDictamen && modifiedOpinion);
        frm.toggle_reqd("limitacion_alcance_material", isDictamen && abstencion);

        frm.set_df_property("fundamento_opinion", "description", isDictamen ? __("Redacta el fundamento conforme a {0}.", [normTitle]) : "");
        frm.set_df_property(
            "parrafo_enfasis",
            "description",
            isDictamen ? __("Si incluyes un parrafo de enfasis, la base normativa debe referenciar NIA 706.") : ""
        );
        frm.set_df_property(
            "parrafo_otros_asuntos",
            "description",
            isDictamen ? __("Si incluyes un parrafo de otros asuntos, la base normativa debe referenciar NIA 706.") : ""
        );

        if (!isDictamen) {
            frm.set_df_property("asunto_que_origina_modificacion", "description", "");
            frm.set_df_property("fundamento_salvedad", "description", "");
            return;
        }

        if (frm.doc.tipo_opinion === "Con Salvedades") {
            frm.set_df_property(
                "fundamento_salvedad",
                "description",
                __("Documenta el fundamento de la salvedad conforme a NIA 705 y por que el efecto es material pero no generalizado.")
            );
            frm.set_df_property(
                "asunto_que_origina_modificacion",
                "description",
                __("Resume el asunto material que origina la opinion con salvedades conforme a NIA 705.")
            );
        } else if (frm.doc.tipo_opinion === "Adversa") {
            frm.set_df_property(
                "fundamento_salvedad",
                "description",
                __("Documenta el fundamento de la opinion adversa conforme a NIA 705 y el efecto material y generalizado identificado.")
            );
            frm.set_df_property(
                "asunto_que_origina_modificacion",
                "description",
                __("Resume el asunto generalizado que invalida la razonabilidad de la informacion auditada.")
            );
        } else if (frm.doc.tipo_opinion === "Abstencion") {
            frm.set_df_property(
                "fundamento_salvedad",
                "description",
                __("Documenta la limitacion al alcance conforme a NIA 705 que impide obtener evidencia suficiente y adecuada.")
            );
            frm.set_df_property(
                "asunto_que_origina_modificacion",
                "description",
                __("Resume la limitacion al alcance material y generalizada que origina la abstencion.")
            );
        } else {
            frm.set_df_property("asunto_que_origina_modificacion", "description", "");
            frm.set_df_property("fundamento_salvedad", "description", "");
        }
    },
});
