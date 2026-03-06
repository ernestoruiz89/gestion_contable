import frappe
from frappe import _
from frappe.model.document import Document

from gestion_contable.gestion_contable.utils.security import (
    ensure_manager,
    get_current_user,
    is_auxiliar,
    is_manager,
)


CAMPOS_RESTRINGIDOS_AUXILIAR = {
    "cliente": "Cliente",
    "periodo": "Periodo",
    "tipo_de_tarea": "Tipo de Tarea",
    "fecha_de_vencimiento": "Fecha de Vencimiento",
    "asignado_a": "Asignado a",
}


class TareaContable(Document):
    def autoname(self):
        # Auto-generar el titulo si estan presentes los campos clave
        if self.tipo_de_tarea and self.cliente and self.periodo:
            self.titulo = f"{self.tipo_de_tarea} - {self.cliente} - {self.periodo}"
            self.name = self.titulo

    def validate(self):
        self.validar_cliente_activo()
        self.validar_periodo_abierto()
        self.validar_control_operativo()

    def validar_cliente_activo(self):
        if self.cliente:
            estado = frappe.db.get_value("Cliente Contable", self.cliente, "estado")
            if estado != "Activo":
                frappe.throw(
                    _("No se pueden crear tareas para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(
                        self.cliente, estado
                    ),
                    title=_("Cliente Inactivo")
                )

    def validar_periodo_abierto(self):
        if self.periodo:
            estado = frappe.db.get_value("Periodo Contable", self.periodo, "estado")
            if estado != "Abierto":
                frappe.throw(
                    _("No se pueden crear tareas en el periodo <b>{0}</b> porque su estado es <b>{1}</b>.").format(
                        self.periodo, estado
                    ),
                    title=_("Periodo Cerrado")
                )

    def validar_control_operativo(self):
        if is_manager():
            return

        if not is_auxiliar():
            frappe.throw(
                _("No tienes permisos para modificar tareas contables."),
                frappe.PermissionError,
            )

        if self.is_new():
            frappe.throw(
                _("Solo el Contador del Despacho o System Manager pueden crear tareas."),
                frappe.PermissionError,
            )

        anterior = self.get_doc_before_save()
        if not anterior:
            return

        usuario_actual = get_current_user()
        if anterior.asignado_a != usuario_actual:
            frappe.throw(
                _("Solo puedes actualizar tareas asignadas a tu usuario."),
                frappe.PermissionError,
            )

        cambios_restringidos = []
        for fieldname, etiqueta in CAMPOS_RESTRINGIDOS_AUXILIAR.items():
            if self.get(fieldname) != anterior.get(fieldname):
                cambios_restringidos.append(etiqueta)

        if cambios_restringidos:
            frappe.throw(
                _("No puedes cambiar estos campos: <b>{0}</b>.").format(", ".join(cambios_restringidos)),
                frappe.PermissionError,
            )

        if anterior.estado == "Completada" and self.estado != "Completada":
            frappe.throw(
                _("Una tarea completada solo puede ser reabierta por el Contador del Despacho o System Manager."),
                frappe.PermissionError,
            )

        if self.estado == "Completada" and anterior.estado != "Completada":
            frappe.throw(
                _("Solo el Contador del Despacho o System Manager pueden marcar una tarea como Completada. Usa En Revision para solicitar aprobacion."),
                frappe.PermissionError,
            )

    def before_rename(self, old, new, merge=False):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden renombrar tareas."))

    def on_trash(self):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden eliminar tareas."))
