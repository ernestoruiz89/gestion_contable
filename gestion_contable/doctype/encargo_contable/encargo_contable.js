frappe.ui.form.on("Encargo Contable", {
    refresh(frm) {
        frm.set_query("contrato_comercial", () => ({
            filters: frm.doc.cliente
                ? { cliente: frm.doc.cliente, estado_aprobacion: "Aprobado" }
                : { estado_aprobacion: "Aprobado" },
        }));

        frm.set_query("plantilla_encargo_contable", () => ({
            filters: Object.assign(
                { activa: 1 },
                frm.doc.tipo_de_servicio ? { tipo_de_servicio: frm.doc.tipo_de_servicio } : {}
            ),
        }));

        if (frm.is_new()) {
            return;
        }

        const canPlan =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Supervisor del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        const canInvoice =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Contador del Despacho") ||
            frappe.user.has_role("Socio del Despacho");

        if (canPlan) {
            frm.add_custom_button(__("Actualizar Planeacion"), () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable.refrescar_planeacion_encargo",
                    args: { encargo_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Recalculando planeacion..."),
                    callback: () => frm.reload_doc(),
                });
            }, __("Planeacion"));

            frm.add_custom_button(__("Aplicar Plantilla"), () => {
                frappe.prompt(
                    [
                        {
                            fieldname: "plantilla_name",
                            fieldtype: "Link",
                            label: __("Plantilla"),
                            options: "Plantilla Encargo Contable",
                            reqd: 1,
                            default: frm.doc.plantilla_encargo_contable,
                        },
                        {
                            fieldname: "reemplazar_hitos",
                            fieldtype: "Check",
                            label: __("Reemplazar Hitos"),
                            default: frm.doc.hitos && frm.doc.hitos.length ? 0 : 1,
                        },
                    ],
                    (values) => {
                        frappe.call({
                            method: "gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable.aplicar_plantilla_encargo",
                            args: {
                                encargo_name: frm.doc.name,
                                plantilla_name: values.plantilla_name,
                                reemplazar_hitos: values.reemplazar_hitos,
                            },
                            freeze: true,
                            freeze_message: __("Aplicando plantilla..."),
                            callback: () => frm.reload_doc(),
                        });
                    },
                    __("Aplicar Plantilla"),
                    __("Aplicar")
                );
            }, __("Planeacion"));
        }

        if (!canInvoice) {
            return;
        }

        frm.add_custom_button(__("Actualizar Honorarios"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable.refrescar_resumen_honorarios",
                args: { encargo_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Calculando horas y honorarios..."),
                callback: () => frm.reload_doc(),
            });
        }, __("Facturacion"));

        frm.add_custom_button(__("Generar Factura"), () => {
            frappe.prompt(
                [
                    { fieldname: "posting_date", fieldtype: "Date", label: __("Fecha de Factura"), reqd: 1, default: frappe.datetime.get_today() },
                    { fieldname: "due_date", fieldtype: "Date", label: __("Fecha de Vencimiento"), reqd: 1, default: frappe.datetime.get_today() },
                    { fieldname: "incluir_horas", fieldtype: "Check", label: __("Incluir Horas"), default: 1 },
                    { fieldname: "incluir_honorario_fijo", fieldtype: "Check", label: __("Incluir Honorario Fijo"), default: 1 },
                    { fieldname: "submit", fieldtype: "Check", label: __("Enviar Factura"), description: __("Si no se marca, la factura queda en Borrador."), default: 0 },
                ],
                (values) => {
                    frappe.call({
                        method: "gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable.generar_factura_venta",
                        args: {
                            encargo_name: frm.doc.name,
                            posting_date: values.posting_date,
                            due_date: values.due_date,
                            incluir_horas: values.incluir_horas,
                            incluir_honorario_fijo: values.incluir_honorario_fijo,
                            submit: values.submit,
                        },
                        freeze: true,
                        freeze_message: __("Generando factura..."),
                        callback: (r) => {
                            if (!r.exc && r.message && r.message.sales_invoice) {
                                frappe.show_alert({ message: __("Factura creada: {0}", [r.message.sales_invoice]), indicator: "green" });
                                frm.reload_doc();
                            }
                        },
                    });
                },
                __("Generar Factura"),
                __("Crear")
            );
        }, __("Facturacion"));

        frm.add_custom_button(__("Registrar Cobro"), () => {
            frappe.call({
                method: "gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable.obtener_facturas_pendientes_cobro",
                args: { encargo_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Consultando facturas pendientes..."),
                callback: (r) => {
                    const invoices = (r.message || []).filter((row) => row.outstanding_amount > 0);
                    if (!invoices.length) {
                        frappe.msgprint(__("El encargo no tiene facturas pendientes de cobro."));
                        return;
                    }

                    frappe.prompt(
                        [
                            {
                                fieldname: "sales_invoice",
                                fieldtype: "Select",
                                label: __("Factura"),
                                reqd: 1,
                                options: invoices.map((row) => row.name).join("\n"),
                                default: invoices[0].name,
                                description: __("Selecciona la factura con saldo pendiente."),
                            },
                            { fieldname: "posting_date", fieldtype: "Date", label: __("Fecha de Cobro"), reqd: 1, default: frappe.datetime.get_today() },
                            { fieldname: "paid_amount", fieldtype: "Currency", label: __("Monto Cobrado"), description: __("Si lo dejas vacio o en 0, se toma el saldo total.") },
                            { fieldname: "reference_no", fieldtype: "Data", label: __("Referencia"), description: __("Transferencia, cheque o recibo.") },
                            { fieldname: "reference_date", fieldtype: "Date", label: __("Fecha Referencia"), default: frappe.datetime.get_today() },
                            { fieldname: "submit", fieldtype: "Check", label: __("Enviar Payment Entry"), default: 1 },
                        ],
                        (values) => {
                            frappe.call({
                                method: "gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable.crear_payment_entry_encargo",
                                args: {
                                    encargo_name: frm.doc.name,
                                    sales_invoice: values.sales_invoice,
                                    posting_date: values.posting_date,
                                    paid_amount: values.paid_amount,
                                    reference_no: values.reference_no,
                                    reference_date: values.reference_date,
                                    submit: values.submit,
                                },
                                freeze: true,
                                freeze_message: __("Creando Payment Entry..."),
                                callback: (response) => {
                                    if (!response.exc && response.message && response.message.payment_entry) {
                                        frappe.show_alert({ message: __("Cobro registrado: {0}", [response.message.payment_entry]), indicator: "green" });
                                        frm.reload_doc();
                                        frappe.set_route("Form", "Payment Entry", response.message.payment_entry);
                                    }
                                },
                            });
                        },
                        __("Registrar Cobro"),
                        __("Crear")
                    );
                },
            });
        }, __("Cobranza"));
    },
});