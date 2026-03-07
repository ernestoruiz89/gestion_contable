import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, nowdate

from gestion_contable.gestion_contable.doctype.contrato_comercial.contrato_comercial import FACTOR_MENSUAL
from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO, validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "contrato_comercial", "cliente", "customer", "cotizacion", "company", "moneda", "estado_cambio",
    "fecha_solicitud", "fecha_efectiva", "motivo", "descripcion", "detalles",
)


class CambioAlcanceComercial(Document):
    def autoname(self):
        base = (self.name if self.name and self.name != "New Cambio Alcance Comercial" else "").strip()
        if not base:
            base = f"Cambio - {self.contrato_comercial or frappe.generate_hash(length=6)} - {self.fecha_solicitud or nowdate()}"
        if not frappe.db.exists("Cambio Alcance Comercial", base):
            self.name = base
            return
        index = 2
        while frappe.db.exists("Cambio Alcance Comercial", f"{base} ({index})"):
            index += 1
        self.name = f"{base} ({index})"

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar cambios de alcance."))
        validate_governance(self, content_fields=CONTENT_FIELDS, create_roles=CREATE_ROLES, draft_roles=CREATE_ROLES, label=_("el cambio de alcance"))
        self.sincronizar_desde_contrato()
        self.validar_fechas()
        self.validar_detalles()
        self.calcular_impacto()
        self.sincronizar_estado_cambio()

    def sincronizar_desde_contrato(self):
        if not self.contrato_comercial:
            return
        contrato = frappe.get_doc("Contrato Comercial", self.contrato_comercial)
        self.cliente = contrato.cliente
        self.customer = contrato.customer
        self.company = contrato.company
        self.moneda = contrato.moneda

    def validar_fechas(self):
        if self.fecha_solicitud and self.fecha_efectiva and getdate(self.fecha_solicitud) > getdate(self.fecha_efectiva):
            frappe.throw(_("La fecha efectiva no puede ser anterior a la fecha de solicitud."))

    def validar_detalles(self):
        if not self.detalles:
            frappe.throw(_("Debes agregar al menos un detalle de cambio de alcance."))
        for row in self.detalles:
            if not row.servicio_contable:
                frappe.throw(_("Cada detalle debe indicar un servicio contable."))
            row.accion = row.accion or "Modificar"
            row.modalidad_tarifa = row.modalidad_tarifa or "Fijo"
            row.periodicidad = row.periodicidad or "Mensual"
            row.fecha_inicio = row.fecha_inicio or self.fecha_efectiva or nowdate()
            if row.accion in ("Agregar", "Modificar"):
                if row.modalidad_tarifa in ("Por Hora", "Mixto") and flt(row.tarifa_hora) <= 0:
                    frappe.throw(_("Los cambios por hora o mixtos requieren tarifa por hora."))
                if row.modalidad_tarifa in ("Fijo", "Mixto") and flt(row.honorario_fijo) <= 0:
                    frappe.throw(_("Los cambios fijos o mixtos requieren honorario fijo."))

    def calcular_impacto(self):
        mensual = 0
        for row in self.detalles:
            signo = -1 if row.accion == "Retirar" else 1
            base = flt(row.honorario_fijo) + (flt(row.tarifa_hora) * flt(row.horas_incluidas))
            mensual += signo * base * FACTOR_MENSUAL.get(row.periodicidad or "Mensual", 0)
        self.impacto_mensual_estimado = mensual
        self.impacto_anual_estimado = mensual * 12

    def sincronizar_estado_cambio(self):
        if self.estado_aprobacion == ESTADO_APROBACION_APROBADO:
            if self.estado_cambio != "Aplicado":
                self.estado_cambio = "Aprobado"
        elif self.estado_cambio not in ("Cancelado",):
            self.estado_cambio = "Borrador"

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar cambios de alcance."))


@frappe.whitelist()
def aplicar_cambio_alcance(cambio_name):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden aplicar cambios de alcance."))
    cambio = frappe.get_doc("Cambio Alcance Comercial", cambio_name)
    if cambio.estado_aprobacion != ESTADO_APROBACION_APROBADO:
        frappe.throw(_("El cambio de alcance debe estar aprobado antes de aplicarse."))
    if cambio.estado_cambio == "Aplicado":
        return {"contrato": cambio.contrato_comercial, "cambio": cambio.name, "estado": cambio.estado_cambio}

    contrato = frappe.get_doc("Contrato Comercial", cambio.contrato_comercial)
    contrato.flags.ignore_governance_validation = True
    contrato.flags.skip_tariff_sync = True

    for row in cambio.detalles:
        linea = _buscar_linea_alcance(contrato, row.servicio_contable)
        if row.accion == "Agregar":
            if linea and cint_bool(linea.activa):
                frappe.throw(_("Ya existe una linea activa para el servicio <b>{0}</b> en el contrato.").format(row.servicio_contable))
            linea = contrato.append("alcances", {})
        elif not linea:
            frappe.throw(_("No existe una linea activa para el servicio <b>{0}</b> en el contrato.").format(row.servicio_contable))

        linea.servicio_contable = row.servicio_contable
        _set_text_if_present(linea, "descripcion", row.descripcion)
        _set_text_if_present(linea, "periodicidad", row.periodicidad)
        _set_text_if_present(linea, "modalidad_tarifa", row.modalidad_tarifa)
        _set_float_if_present(linea, "horas_incluidas", row.horas_incluidas)
        _set_float_if_present(linea, "tarifa_hora", row.tarifa_hora)
        _set_float_if_present(linea, "honorario_fijo", row.honorario_fijo)
        _set_float_if_present(linea, "sla_respuesta_horas", row.sla_respuesta_horas)
        _set_float_if_present(linea, "sla_entrega_dias", row.sla_entrega_dias)
        linea.fecha_inicio = row.fecha_inicio or linea.fecha_inicio or cambio.fecha_efectiva
        linea.fecha_fin = row.fecha_fin or linea.fecha_fin
        if row.accion == "Retirar":
            linea.activa = 0
            linea.horas_incluidas = 0
            linea.tarifa_hora = 0
            linea.honorario_fijo = 0
        else:
            linea.activa = 1
        if row.accion == "Retirar" and not linea.fecha_fin:
            linea.fecha_fin = row.fecha_inicio or cambio.fecha_efectiva

    contrato.save(ignore_permissions=True)
    tarifas = contrato.sincronizar_tarifas_desde_alcances(cambio_name=cambio.name)
    frappe.db.set_value("Cambio Alcance Comercial", cambio.name, {"estado_cambio": "Aplicado", "fecha_aplicacion": now_datetime()}, update_modified=False)
    return {"contrato": contrato.name, "cambio": cambio.name, "estado": "Aplicado", "tarifas": tarifas}


def _buscar_linea_alcance(contrato, servicio_contable):
    activas = [row for row in contrato.alcances if row.servicio_contable == servicio_contable and cint_bool(row.activa)]
    if activas:
        return activas[0]
    for row in contrato.alcances:
        if row.servicio_contable == servicio_contable:
            return row
    return None


def _set_text_if_present(doc, fieldname, value):
    if value not in (None, ""):
        setattr(doc, fieldname, value)


def _set_float_if_present(doc, fieldname, value):
    if value not in (None, ""):
        setattr(doc, fieldname, flt(value))


def cint_bool(value):
    return 1 if str(value) in ("1", "True", "true") or value == 1 else 0
