import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from gestion_contable.gestion_contable.utils.security import ensure_supervisor


class PlantillaEncargoContable(Document):
    def autoname(self):
        base_name = (self.nombre_de_plantilla or "").strip()
        if not base_name:
            base_name = f"Plantilla {self.tipo_de_servicio or 'Encargo'} - {frappe.generate_hash(length=6)}"
        self.nombre_de_plantilla = self._build_unique_name(base_name)
        self.name = self.nombre_de_plantilla

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar plantillas de encargos."))
        self.validar_servicio_compatible()
        self.validar_hitos()
        self.calcular_presupuestos_sugeridos()

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Plantilla Encargo Contable", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Plantilla Encargo Contable", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def validar_servicio_compatible(self):
        if not self.servicio_contable:
            return
        tipo_servicio = frappe.db.get_value("Servicio Contable", self.servicio_contable, "tipo_de_servicio")
        if not tipo_servicio:
            frappe.throw(_("El servicio contable vinculado a la plantilla no existe."), title=_("Servicio Invalido"))
        if self.tipo_de_servicio and tipo_servicio != self.tipo_de_servicio:
            frappe.throw(_("La plantilla y el servicio contable deben tener el mismo tipo de servicio."), title=_("Plantilla Inconsistente"))

    def validar_hitos(self):
        titulos = set()
        for row in self.hitos or []:
            if not row.titulo:
                frappe.throw(_("Cada hito de plantilla debe tener titulo."))
            if row.titulo in titulos:
                frappe.throw(_("No puedes repetir hitos en la misma plantilla: <b>{0}</b>.").format(row.titulo))
            titulos.add(row.titulo)
            row.orden = cint(row.orden) or ((row.idx or 0) + 1)
            row.dias_desde_inicio = cint(row.dias_desde_inicio)
            row.duracion_dias = max(cint(row.duracion_dias), 1)
            row.peso_porcentaje = flt(row.peso_porcentaje)
            row.horas_planificadas = flt(row.horas_planificadas)
            row.monto_planificado = flt(row.monto_planificado)

    def calcular_presupuestos_sugeridos(self):
        if flt(self.presupuesto_horas_sugerido) <= 0:
            self.presupuesto_horas_sugerido = flt(sum(flt(row.horas_planificadas) for row in self.hitos or []))
        if flt(self.presupuesto_monto_sugerido) <= 0:
            self.presupuesto_monto_sugerido = flt(sum(flt(row.monto_planificado) for row in self.hitos or []))
