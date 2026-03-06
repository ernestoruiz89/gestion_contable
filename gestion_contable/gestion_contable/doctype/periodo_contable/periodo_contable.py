import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from dateutil.relativedelta import relativedelta

from gestion_contable.gestion_contable.utils.security import ensure_manager


MESES = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
}


class PeriodoContable(Document):
    def autoname(self):
        if self.anio and self.mes:
            self.nombre_del_periodo = f"{self.mes} {self.anio}"
            self.name = self.nombre_del_periodo

    def before_save(self):
        self.calcular_campos()

    def validate(self):
        ensure_manager()
        self.validar_anio()

    def calcular_campos(self):
        if self.anio and self.mes:
            # Nombre del periodo: "Marzo 2025"
            self.nombre_del_periodo = f"{self.mes} {self.anio}"

            # Fecha de inicio: primer dia del mes
            num_mes = MESES.get(self.mes)
            if num_mes:
                self.fecha_de_inicio = date(int(self.anio), num_mes, 1)
                # Fecha de fin: ultimo dia del mes
                siguiente_mes = self.fecha_de_inicio + relativedelta(months=1)
                self.fecha_de_fin = siguiente_mes - relativedelta(days=1)

    def validar_anio(self):
        if self.anio and (int(self.anio) < 2000 or int(self.anio) > 2099):
            frappe.throw(
                _("El anio debe estar entre 2000 y 2099."),
                title=_("Error de Validacion")
            )

    def on_trash(self):
        ensure_manager()
