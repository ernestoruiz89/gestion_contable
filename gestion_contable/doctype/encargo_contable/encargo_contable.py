import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from gestion_contable.gestion_contable.services.encargos import analytics as analytics_service
from gestion_contable.gestion_contable.services.encargos import billing as billing_service
from gestion_contable.gestion_contable.services.encargos import commercial as commercial_service
from gestion_contable.gestion_contable.services.encargos import erpnext as erpnext_service
from gestion_contable.gestion_contable.services.encargos import planning as planning_service
from gestion_contable.gestion_contable.services.encargos.common import (
    calcular_porcentaje as common_calcular_porcentaje,
    normalizar_texto as common_normalizar_texto,
)
from gestion_contable.gestion_contable.services.encargos.constants import ENCARGO_CONTENT_FIELDS, ENCARGO_CREATE_ROLES
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor


class EncargoContable(Document):
    def autoname(self):
        base_name = (self.nombre_del_encargo or "").strip()
        if not base_name:
            servicio = self.tipo_de_servicio or "Encargo"
            cliente = self.cliente or frappe.generate_hash(length=6)
            base_name = f"{servicio} - {cliente}"
        self.nombre_del_encargo = self._build_unique_name(base_name)
        self.name = self.nombre_del_encargo

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar encargos."))
        self.validar_cliente_activo()
        self.sincronizar_desde_cliente()
        self.sincronizar_desde_servicio()
        self.sincronizar_desde_contrato()
        self.sincronizar_desde_plantilla()
        self.sincronizar_company()
        self.sincronizar_moneda()
        self.validar_periodo_referencia()
        self.validar_contrato_comercial()
        self.validar_plantilla_encargo()
        self.validar_tarifas()
        self.asegurar_project()
        self.validar_project_consistente()
        self.validar_hitos()
        self.actualizar_horas_registradas()
        self.actualizar_resumen_honorarios()
        self.actualizar_indicadores_planeacion()
        self.actualizar_indicadores_financieros()
        self.validar_gobierno_operativo()

    def validar_gobierno_operativo(self):
        validate_governance(
            self,
            content_fields=ENCARGO_CONTENT_FIELDS,
            create_roles=ENCARGO_CREATE_ROLES,
            draft_roles=ENCARGO_CREATE_ROLES,
            label=_("el encargo"),
        )

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Encargo Contable", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Encargo Contable", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def validar_cliente_activo(self):
        return commercial_service.validar_cliente_activo(self)

    def obtener_servicio(self):
        return commercial_service.obtener_servicio(self)

    def obtener_contrato_comercial(self):
        return commercial_service.obtener_contrato_comercial(self)

    def obtener_plantilla_doc(self, plantilla_name=None):
        return commercial_service.obtener_plantilla_doc(self, plantilla_name=plantilla_name)

    def construir_hitos_desde_plantilla(self, plantilla, replace=False):
        return planning_service.construir_hitos_desde_plantilla(self, plantilla, replace=replace)

    def sincronizar_desde_cliente(self):
        return commercial_service.sincronizar_desde_cliente(self)

    def sincronizar_desde_servicio(self):
        return commercial_service.sincronizar_desde_servicio(self)

    def sincronizar_desde_contrato(self):
        return commercial_service.sincronizar_desde_contrato(self)

    def sincronizar_desde_plantilla(self):
        return commercial_service.sincronizar_desde_plantilla(self)

    def obtener_alcance_contractual(self, fecha=None):
        return commercial_service.obtener_alcance_contractual(self, fecha=fecha)

    def sincronizar_company(self):
        return erpnext_service.sincronizar_company(self)

    def sincronizar_moneda(self):
        return erpnext_service.sincronizar_moneda(self)

    def validar_periodo_referencia(self):
        return commercial_service.validar_periodo_referencia(self)

    def validar_contrato_comercial(self):
        return commercial_service.validar_contrato_comercial(self)

    def validar_plantilla_encargo(self):
        return commercial_service.validar_plantilla_encargo(self)

    def obtener_tarifa_cliente_servicio(self, fecha=None):
        return commercial_service.obtener_tarifa_cliente_servicio(self, fecha=fecha)

    def resolver_tarifas(self, fecha=None):
        return commercial_service.resolver_tarifas(self, fecha=fecha)

    def validar_tarifas(self):
        return commercial_service.validar_tarifas(self)

    def asegurar_project(self):
        return erpnext_service.asegurar_project(self)

    def crear_project(self):
        return erpnext_service.crear_project(self)

    def validar_project_consistente(self):
        return erpnext_service.validar_project_consistente(self)

    def validar_hitos(self):
        return planning_service.validar_hitos(self)

    def actualizar_horas_registradas(self):
        return billing_service.actualizar_horas_registradas(self)

    def obtener_detalles_horas_pendientes(self):
        return billing_service.obtener_detalles_horas_pendientes(self)

    def calcular_horas_facturables(self):
        return billing_service.calcular_horas_facturables(self)

    def actualizar_resumen_honorarios(self):
        return billing_service.actualizar_resumen_honorarios(self)

    def actualizar_indicadores_planeacion(self):
        return planning_service.actualizar_indicadores_planeacion(self)

    def obtener_facturas_relacionadas(self, include_draft=False):
        return analytics_service.obtener_facturas_relacionadas(self, include_draft=include_draft)

    def actualizar_indicadores_financieros(self):
        return analytics_service.actualizar_indicadores_financieros(self)

    def actualizar_resumen_cobranza(self):
        return analytics_service.actualizar_resumen_cobranza(self)

    def calcular_avance_hitos(self):
        return planning_service.calcular_avance_hitos(self)

    def calcular_presupuesto_monto_estimado(self):
        return planning_service.calcular_presupuesto_monto_estimado(self)

    def calcular_monto_real_ejecutado(self):
        return planning_service.calcular_monto_real_ejecutado(self)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar encargos."))


@frappe.whitelist()
def refrescar_resumen_honorarios(encargo_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden recalcular indicadores de encargos."))
    encargo = _recalcular_encargo(encargo_name)
    return construir_resumen_encargo(encargo)


@frappe.whitelist()
def refrescar_planeacion_encargo(encargo_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden recalcular la planeacion del encargo."))
    encargo = _recalcular_encargo(encargo_name)
    return construir_resumen_encargo(encargo)


@frappe.whitelist()
def obtener_facturas_pendientes_cobro(encargo_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden consultar facturas pendientes."))
    encargo = frappe.get_doc("Encargo Contable", encargo_name)
    return billing_service.obtener_facturas_pendientes_cobro(encargo)


@frappe.whitelist()
def crear_payment_entry_encargo(encargo_name, sales_invoice, posting_date=None, paid_amount=None, reference_no=None, reference_date=None, submit=0):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden registrar cobros."))
    encargo = frappe.get_doc("Encargo Contable", encargo_name)
    payment_entry = billing_service.crear_payment_entry_encargo(
        encargo,
        sales_invoice,
        posting_date=posting_date,
        paid_amount=paid_amount,
        reference_no=reference_no,
        reference_date=reference_date,
        submit=submit,
    )
    encargo = analytics_service.recalcular_encargo(encargo.name)
    return {
        "payment_entry": payment_entry.name,
        "docstatus": payment_entry.docstatus,
        "encargo": encargo.name,
        "sales_invoice": sales_invoice,
        "saldo_por_cobrar": encargo.saldo_por_cobrar,
    }


@frappe.whitelist()
def aplicar_plantilla_encargo(encargo_name, plantilla_name=None, reemplazar_hitos=0):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden aplicar plantillas de encargos."))
    encargo = frappe.get_doc("Encargo Contable", encargo_name)
    plantilla = encargo.obtener_plantilla_doc(plantilla_name)
    if not plantilla:
        frappe.throw(_("Debes seleccionar una plantilla de encargo para aplicar."), title=_("Plantilla Requerida"))

    encargo.plantilla_encargo_contable = plantilla.name
    encargo.sincronizar_desde_plantilla()
    encargo.construir_hitos_desde_plantilla(plantilla, replace=bool(cint(reemplazar_hitos)))
    encargo = analytics_service.recalcular_documento(encargo, save=True)
    return {
        "encargo": encargo.name,
        "plantilla": plantilla.name,
        "hitos_totales": encargo.hitos_totales,
        "avance_hitos_pct": encargo.avance_hitos_pct,
    }


@frappe.whitelist()
def generar_factura_venta(encargo_name, posting_date=None, due_date=None, incluir_horas=1, incluir_honorario_fijo=1, submit=0):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden generar facturas."))
    encargo = frappe.get_doc("Encargo Contable", encargo_name)
    resultado = billing_service.generar_factura_venta(
        encargo,
        posting_date=posting_date,
        due_date=due_date,
        incluir_horas=incluir_horas,
        incluir_honorario_fijo=incluir_honorario_fijo,
        submit=submit,
    )
    invoice = resultado["invoice"]
    encargo.reload()
    encargo.factura_venta = invoice.name
    encargo = analytics_service.recalcular_documento(encargo, save=True)
    return {
        "sales_invoice": invoice.name,
        "docstatus": invoice.docstatus,
        "total_horas": resultado["total_horas"],
        "tarifa_hora": resultado["tarifa_hora"],
        "honorario_fijo": resultado["honorario_fijo"],
        "grand_total": invoice.grand_total,
    }


def _recalcular_encargo(encargo_name):
    return analytics_service.recalcular_encargo(encargo_name)


def construir_resumen_encargo(encargo):
    return analytics_service.construir_resumen_encargo(encargo)


def calcular_porcentaje(valor, base):
    return common_calcular_porcentaje(valor, base)


def normalizar_texto(value):
    return common_normalizar_texto(value)
