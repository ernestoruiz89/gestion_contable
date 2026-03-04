import frappe
from frappe import _
from frappe.model.document import Document


class PeriodoContable(Document):
    def validate(self):
        self.validar_fechas()

    def validar_fechas(self):
        if self.fecha_de_inicio and self.fecha_de_fin:
            if self.fecha_de_fin <= self.fecha_de_inicio:
                frappe.throw(
                    _("La Fecha de Fin debe ser posterior a la Fecha de Inicio."),
                    title=_("Error de Validación")
                )
