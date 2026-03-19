import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from gestion_contable.gestion_contable.utils.security import ensure_manager


class ServicioContable(Document):
    def autoname(self):
        base_name = (self.nombre_del_servicio or "").strip()
        if not base_name:
            base_name = f"{self.tipo_de_servicio or 'Servicio'} - {frappe.generate_hash(length=6)}"

        self.nombre_del_servicio = self._build_unique_name(base_name)
        self.name = self.nombre_del_servicio

    def validate(self):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden gestionar servicios."))
        self.validar_item_horas()
        self.validar_plantilla_encargo()
        self.sincronizar_company()
        self.sincronizar_moneda()
        self.validar_tarifas()

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Servicio Contable", base_name):
            return base_name

        index = 2
        while frappe.db.exists("Servicio Contable", f"{base_name} ({index})"):
            index += 1

        return f"{base_name} ({index})"

    def validar_item_horas(self):
        if not self.item_horas:
            frappe.throw(_("Debes seleccionar un Item de ERPNext para facturar las horas."))

        item = frappe.db.get_value(
            "Item",
            self.item_horas,
            ["name", "is_stock_item", "disabled"],
            as_dict=True,
        )

        if not item:
            frappe.throw(_("El Item <b>{0}</b> no existe.").format(self.item_horas), title=_("Item Invalido"))

        if flt(item.is_stock_item):
            frappe.throw(_("El Item de horas debe ser un servicio no inventariable."), title=_("Item Invalido"))

        if flt(item.disabled):
            frappe.throw(_("El Item de horas esta deshabilitado."), title=_("Item Invalido"))

    def validar_plantilla_encargo(self):
        if not self.plantilla_encargo_contable:
            return

        plantilla = frappe.db.get_value(
            "Plantilla Encargo Contable",
            self.plantilla_encargo_contable,
            ["name", "activa", "tipo_de_servicio", "servicio_contable"],
            as_dict=True,
        )
        if not plantilla:
            frappe.throw(_("La plantilla de encargo vinculada no existe."), title=_("Plantilla Invalida"))

        if not flt(plantilla.activa):
            frappe.throw(_("La plantilla de encargo vinculada debe estar activa."), title=_("Plantilla Inactiva"))

        if plantilla.tipo_de_servicio and self.tipo_de_servicio and plantilla.tipo_de_servicio != self.tipo_de_servicio:
            frappe.throw(_("La plantilla de encargo debe tener el mismo tipo de servicio del catalogo."), title=_("Plantilla Inconsistente"))

        if plantilla.servicio_contable and plantilla.servicio_contable != self.name:
            frappe.throw(_("La plantilla ya esta asociada a otro servicio contable especifico."), title=_("Plantilla Inconsistente"))

    def sincronizar_company(self):
        if self.company:
            return

        self.company = (
            frappe.defaults.get_user_default("Company")
            or frappe.db.get_single_value("Global Defaults", "default_company")
        )

        if not self.company:
            frappe.throw(_("Define una compania en el servicio o en los valores por defecto del usuario."), title=_("Compania Requerida"))

    def sincronizar_moneda(self):
        if self.moneda:
            return

        moneda = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
        if not moneda:
            moneda = frappe.db.get_single_value("Global Defaults", "default_currency")

        if moneda:
            self.moneda = moneda

    def validar_tarifas(self):
        if flt(self.tarifa_hora) < 0:
            frappe.throw(_("La tarifa por hora no puede ser negativa."), title=_("Tarifa Invalida"))

        if flt(self.honorario_fijo) < 0:
            frappe.throw(_("El honorario fijo no puede ser negativo."), title=_("Tarifa Invalida"))

        if flt(self.costo_interno_hora) < 0:
            frappe.throw(_("El costo interno por hora no puede ser negativo."), title=_("Costo Invalido"))

    def on_trash(self):
        ensure_manager(_("Solo el Contador del Despacho o System Manager pueden eliminar servicios."))