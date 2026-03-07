import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from dateutil.relativedelta import relativedelta

from gestion_contable.gestion_contable.utils.security import ensure_manager


MESES = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}


class PeriodoContable(Document):
    def autoname(self):
        self.calcular_campos()
        if self.nombre_del_periodo:
            self.name = self.nombre_del_periodo

    def before_save(self):
        self.calcular_campos()

    def validate(self):
        ensure_manager()
        self.company = self.company or get_default_company()
        self.validar_cliente()
        self.validar_company()
        self.validar_anio()
        self.calcular_campos()

    def calcular_campos(self):
        if self.anio and self.mes:
            base_name = f"{self.mes} {self.anio}"
            scope = [value for value in (self.company, self.cliente, base_name) if value]
            self.nombre_del_periodo = " - ".join(scope)
            num_mes = MESES.get(self.mes)
            if num_mes:
                self.fecha_de_inicio = date(int(self.anio), num_mes, 1)
                siguiente_mes = self.fecha_de_inicio + relativedelta(months=1)
                self.fecha_de_fin = siguiente_mes - relativedelta(days=1)

    def validar_anio(self):
        if self.anio and (int(self.anio) < 2000 or int(self.anio) > 2099):
            frappe.throw(
                _("El anio debe estar entre 2000 y 2099."),
                title=_("Error de Validacion"),
            )

    def validar_cliente(self):
        if not self.cliente:
            frappe.throw(_("Debes seleccionar el cliente del periodo."), title=_("Cliente Requerido"))

    def validar_company(self):
        if not self.company:
            frappe.throw(_("Debes seleccionar la compania operativa del periodo."), title=_("Compania Requerida"))
        if not frappe.db.exists("Company", self.company):
            frappe.throw(_("La compania <b>{0}</b> no existe.").format(self.company), title=_("Compania Invalida"))

    def on_trash(self):
        ensure_manager()


def get_default_company():
    return frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")


def get_periodo_operativo(periodo_name):
    if not periodo_name:
        return None
    periodo = frappe.db.get_value(
        "Periodo Contable",
        periodo_name,
        ["name", "nombre_del_periodo", "estado", "cliente", "company", "anio", "mes"],
        as_dict=True,
    )
    if not periodo:
        frappe.throw(_("El periodo contable <b>{0}</b> no existe.").format(periodo_name), title=_("Periodo Invalido"))
    return periodo


def validate_periodo_operativo(periodo_name, *, cliente=None, company=None, allow_closed=False, label=None):
    periodo = get_periodo_operativo(periodo_name)
    if not periodo:
        return None

    label = label or _("el documento")

    if not allow_closed and periodo.estado != "Abierto":
        frappe.throw(
            _("No puedes gestionar {0} en el periodo <b>{1}</b> porque su estado es <b>{2}</b>.").format(
                label, periodo.name, periodo.estado
            ),
            title=_("Periodo Cerrado"),
        )

    if cliente and periodo.cliente and periodo.cliente != cliente:
        frappe.throw(
            _("El periodo <b>{0}</b> pertenece al cliente <b>{1}</b> y no coincide con <b>{2}</b>.").format(
                periodo.name, periodo.cliente, cliente
            ),
            title=_("Periodo Inconsistente"),
        )

    if company and periodo.company and periodo.company != company:
        frappe.throw(
            _("El periodo <b>{0}</b> pertenece a la compania <b>{1}</b> y no coincide con <b>{2}</b>.").format(
                periodo.name, periodo.company, company
            ),
            title=_("Periodo Inconsistente"),
        )

    return periodo
