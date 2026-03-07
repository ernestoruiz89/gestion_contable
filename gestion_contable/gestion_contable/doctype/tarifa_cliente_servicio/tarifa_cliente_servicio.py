import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from gestion_contable.gestion_contable.utils.security import ensure_manager


class TarifaClienteServicio(Document):
    def autoname(self):
        base_name = f"{self.cliente} - {self.servicio_contable}"
        if self.vigencia_desde:
            base_name = f"{base_name} - {self.vigencia_desde}"
        self.name = self._build_unique_name(base_name)

    def validate(self):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden gestionar tarifas."))
        self.validar_cliente_activo()
        self.validar_origen_contractual()
        self.sincronizar_company()
        self.sincronizar_moneda()
        self.validar_vigencia()
        self.validar_montos()
        self.validar_traslape_vigencia()

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Tarifa Cliente Servicio", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Tarifa Cliente Servicio", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def validar_cliente_activo(self):
        estado = frappe.db.get_value("Cliente Contable", self.cliente, "estado")
        if estado != "Activo":
            frappe.throw(_("No se pueden definir tarifas para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(self.cliente, estado), title=_("Cliente Inactivo"))

    def validar_origen_contractual(self):
        if not self.contrato_comercial:
            if self.cambio_alcance_comercial:
                frappe.throw(_("No puedes vincular un cambio de alcance sin indicar su contrato comercial."))
            return

        contrato = frappe.db.get_value("Contrato Comercial", self.contrato_comercial, ["name", "cliente", "company", "moneda"], as_dict=True)
        if not contrato:
            frappe.throw(_("El contrato comercial <b>{0}</b> no existe.").format(self.contrato_comercial), title=_("Contrato Invalido"))
        if contrato.cliente and self.cliente != contrato.cliente:
            frappe.throw(_("La tarifa no corresponde al cliente del contrato comercial."), title=_("Contrato Inconsistente"))
        if not self.company and contrato.company:
            self.company = contrato.company
        if not self.moneda and contrato.moneda:
            self.moneda = contrato.moneda

        if self.cambio_alcance_comercial:
            cambio = frappe.db.get_value("Cambio Alcance Comercial", self.cambio_alcance_comercial, ["name", "contrato_comercial", "cliente"], as_dict=True)
            if not cambio:
                frappe.throw(_("El cambio de alcance <b>{0}</b> no existe.").format(self.cambio_alcance_comercial), title=_("Cambio Invalido"))
            if cambio.contrato_comercial != self.contrato_comercial:
                frappe.throw(_("El cambio de alcance debe pertenecer al mismo contrato comercial de la tarifa."), title=_("Cambio Inconsistente"))
            if cambio.cliente and cambio.cliente != self.cliente:
                frappe.throw(_("El cambio de alcance no corresponde al cliente de la tarifa."), title=_("Cambio Inconsistente"))

    def sincronizar_company(self):
        if self.company:
            return
        self.company = frappe.db.get_value("Servicio Contable", self.servicio_contable, "company")
        if self.company:
            return
        self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

    def sincronizar_moneda(self):
        if self.moneda:
            return
        self.moneda = frappe.db.get_value("Servicio Contable", self.servicio_contable, "moneda")
        if self.moneda:
            return
        if self.company:
            self.moneda = frappe.db.get_value("Company", self.company, "default_currency")

    def validar_vigencia(self):
        if not self.vigencia_desde or not self.vigencia_hasta:
            return
        if getdate(self.vigencia_desde) > getdate(self.vigencia_hasta):
            frappe.throw(_("La vigencia desde no puede ser posterior a la vigencia hasta."), title=_("Vigencia Invalida"))

    def validar_montos(self):
        if flt(self.tarifa_hora) < 0:
            frappe.throw(_("La tarifa por hora no puede ser negativa."), title=_("Tarifa Invalida"))
        if flt(self.honorario_fijo) < 0:
            frappe.throw(_("El honorario fijo no puede ser negativo."), title=_("Tarifa Invalida"))
        if flt(self.tarifa_hora) <= 0 and flt(self.honorario_fijo) <= 0:
            frappe.throw(_("Debes definir al menos tarifa por hora u honorario fijo."), title=_("Tarifa Incompleta"))

    def validar_traslape_vigencia(self):
        if not self.activa:
            return
        tarifas = frappe.get_all(
            "Tarifa Cliente Servicio",
            filters={"cliente": self.cliente, "servicio_contable": self.servicio_contable, "name": ["!=", self.name], "activa": 1},
            fields=["name", "vigencia_desde", "vigencia_hasta", "contrato_comercial"],
            limit_page_length=200,
        )
        rango_actual = self._normalizar_rango(self.vigencia_desde, self.vigencia_hasta)
        for tarifa in tarifas:
            if self.contrato_comercial and tarifa.contrato_comercial and tarifa.contrato_comercial != self.contrato_comercial:
                continue
            rango_existente = self._normalizar_rango(tarifa.vigencia_desde, tarifa.vigencia_hasta)
            if self._rangos_traslapados(rango_actual, rango_existente):
                frappe.throw(_("La vigencia de esta tarifa se traslapa con <b>{0}</b>. Ajusta las fechas o desactiva la otra tarifa.").format(tarifa.name), title=_("Traslape de Vigencia"))

    def _normalizar_rango(self, desde, hasta):
        desde = getdate(desde) if desde else getdate("1900-01-01")
        hasta = getdate(hasta) if hasta else getdate("2999-12-31")
        return (desde, hasta)

    def _rangos_traslapados(self, rango_a, rango_b):
        return rango_a[0] <= rango_b[1] and rango_b[0] <= rango_a[1]

    def on_trash(self):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden eliminar tarifas."))
