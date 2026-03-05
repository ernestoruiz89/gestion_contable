// Copyright (c) 2024, ernestoruiz89 and contributors
// For license information, please see license.txt

frappe.ui.form.on('Configuracion Despacho Contable', {
    generar_datos_dummy: function (frm) {
        if (frappe.session.user !== "Administrator") {
            frappe.msgprint(__("Solo el usuario Administrator puede ejecutar esta acción."));
            return;
        }

        frappe.confirm(
            __('¿Estás seguro de que deseas generar los datos dummy? Esto creará clientes, periodos, tareas y usuarios.'),
            () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.configuracion_despacho_contable.configuracion_despacho_contable.generar_datos_dummy",
                    freeze: true,
                    freeze_message: __("Generando datos dummy... (Esto puede tomar varios minutos)"),
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint(__("Datos dummy generados exitosamente."));
                        }
                    }
                });
            }
        );
    },

    limpiar_datos_dummy: function (frm) {
        if (frappe.session.user !== "Administrator") {
            frappe.msgprint(__("Solo el usuario Administrator puede ejecutar esta acción."));
            return;
        }

        frappe.confirm(
            __('⚠️ ¿Estás seguro? Esto ELIMINARÁ todas las tareas, comunicaciones, periodos, clientes contables, customers y usuarios dummy. Esta acción no se puede deshacer.'),
            () => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.doctype.configuracion_despacho_contable.configuracion_despacho_contable.limpiar_datos_dummy",
                    freeze: true,
                    freeze_message: __("Limpiando datos dummy..."),
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint(__("Datos dummy eliminados exitosamente."));
                        }
                    }
                });
            }
        );
    }
});
