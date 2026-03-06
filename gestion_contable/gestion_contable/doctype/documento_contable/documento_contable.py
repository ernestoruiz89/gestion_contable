import frappe
from frappe import _
from frappe.model.document import Document

from gestion_contable.gestion_contable.utils.security import ensure_manager, is_manager


class DocumentoContable(Document):
    def validate(self):
        self.validar_cliente_activo()
        self.validar_periodo_abierto()
        self.validar_permiso_de_edicion()

    def validar_cliente_activo(self):
        if self.cliente:
            estado = frappe.db.get_value("Cliente Contable", self.cliente, "estado")
            if estado != "Activo":
                frappe.throw(
                    _("No se pueden crear documentos para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(
                        self.cliente, estado
                    ),
                    title=_("Cliente Inactivo")
                )

    def validar_periodo_abierto(self):
        if self.periodo:
            estado = frappe.db.get_value("Periodo Contable", self.periodo, "estado")
            if estado != "Abierto":
                frappe.throw(
                    _("No se pueden crear documentos en el periodo <b>{0}</b> porque su estado es <b>{1}</b>.").format(
                        self.periodo, estado
                    ),
                    title=_("Periodo Cerrado")
                )

    def validar_permiso_de_edicion(self):
        if self.is_new() or is_manager():
            return

        frappe.throw(
            _("Solo el Contador del Despacho o System Manager pueden editar documentos ya registrados."),
            frappe.PermissionError,
        )

    def on_trash(self):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden eliminar documentos."))
