import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO, validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_del_contrato", "cliente", "customer", "lead", "oportunidad", "cotizacion", "contrato_erpnext",
    "company", "moneda", "estado_comercial", "fecha_inicio", "fecha_fin", "ejecutivo_comercial",
    "responsable_operativo", "sla_respuesta_horas", "sla_entrega_dias", "renovacion_automatica", "notas", "alcances",
)
FACTOR_MENSUAL = {
    "Mensual": 1,
    "Bimestral": 0.5,
    "Trimestral": 1 / 3,
    "Semestral": 1 / 6,
    "Anual": 1 / 12,
    "Por Evento": 0,
}
PRINT_FORMAT_BY_SERVICE_TYPE = {
    "Contabilidad": "Contrato Comercial - Contabilidad",
    "Auditoria": "Contrato Comercial - Auditoria",
    "Trabajo Especial": "Contrato Comercial - Trabajo Especial",
    "Consultoria": "Contrato Comercial - Consultoria",
}


class ContratoComercial(Document):
    def autoname(self):
        base = (self.nombre_del_contrato or "").strip()
        if not base:
            ref = self.cliente or self.customer or self.lead or frappe.generate_hash(length=6)
            fecha = self.fecha_inicio or nowdate()
            base = f"Contrato - {ref} - {fecha}"
        self.nombre_del_contrato = self._build_unique_name(base)
        self.name = self.nombre_del_contrato

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar contratos comerciales."))
        validate_governance(self, content_fields=CONTENT_FIELDS, create_roles=CREATE_ROLES, draft_roles=CREATE_ROLES, label=_("el contrato comercial"))
        self.sincronizar_desde_cliente()
        self.sincronizar_company_moneda()
        self.validar_fechas()
        self.validar_referencias_comerciales()
        self.validar_alcances()
        self.actualizar_formato_impresion_sugerido()
        self.calcular_resumen_comercial()
        self.sincronizar_estado_comercial()

    def on_update(self):
        if getattr(self.flags, "skip_tariff_sync", False):
            return
        if self.estado_aprobacion == ESTADO_APROBACION_APROBADO and self.estado_comercial in ("Aprobado", "Vigente"):
            self.sincronizar_tarifas_desde_alcances()

    def _build_unique_name(self, base):
        if not frappe.db.exists("Contrato Comercial", base):
            return base
        index = 2
        while frappe.db.exists("Contrato Comercial", f"{base} ({index})"):
            index += 1
        return f"{base} ({index})"

    def sincronizar_desde_cliente(self):
        if not self.cliente:
            return

        defaults = get_cliente_defaults(self.cliente)
        customer = defaults.customer or frappe.db.get_value("Cliente Contable", self.cliente, "customer")
        if not customer:
            frappe.throw(_("El cliente contable debe tener Customer vinculado para gestionar contratos."))
        self.customer = customer
        if not self.company and defaults.company_default:
            self.company = defaults.company_default
        if not self.moneda and defaults.moneda_preferida:
            self.moneda = defaults.moneda_preferida
        if not self.ejecutivo_comercial and defaults.ejecutivo_comercial_default:
            self.ejecutivo_comercial = defaults.ejecutivo_comercial_default
        if not self.responsable_operativo and defaults.responsable_operativo_default:
            self.responsable_operativo = defaults.responsable_operativo_default
        if flt(self.sla_respuesta_horas) <= 0 and flt(defaults.sla_respuesta_horas_default) > 0:
            self.sla_respuesta_horas = flt(defaults.sla_respuesta_horas_default)
        if flt(self.sla_entrega_dias) <= 0 and flt(defaults.sla_entrega_dias_default) > 0:
            self.sla_entrega_dias = flt(defaults.sla_entrega_dias_default)

    def sincronizar_company_moneda(self):
        if not self.company:
            self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
        if self.company and not self.moneda:
            self.moneda = frappe.db.get_value("Company", self.company, "default_currency")

    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin and getdate(self.fecha_inicio) > getdate(self.fecha_fin):
            frappe.throw(_("La fecha de inicio no puede ser posterior a la fecha de fin."), title=_("Fechas Invalidas"))

    def validar_referencias_comerciales(self):
        for doctype, value in (("Lead", self.lead), ("Opportunity", self.oportunidad), ("Quotation", self.cotizacion), ("Contract", self.contrato_erpnext)):
            if value and not frappe.db.exists(doctype, value):
                frappe.throw(_("La referencia <b>{0}</b> no existe en {1}.").format(value, doctype))

        for doctype, value in (("Opportunity", self.oportunidad), ("Quotation", self.cotizacion), ("Contract", self.contrato_erpnext)):
            if not value or not self.customer:
                continue
            party_type, party_name = self.obtener_referencia_comercial(doctype, value)
            if party_type == "Customer" and party_name and party_name != self.customer:
                frappe.throw(_("{0} <b>{1}</b> no corresponde al customer del contrato.").format(doctype, value), title=_("Referencia Inconsistente"))

    def obtener_referencia_comercial(self, doctype, name):
        doc = frappe.get_doc(doctype, name)
        if doc.meta.has_field("party_type") and doc.meta.has_field("party_name"):
            return doc.get("party_type"), doc.get("party_name")
        if doc.meta.has_field("quotation_to") and doc.meta.has_field("party_name"):
            return doc.get("quotation_to"), doc.get("party_name")
        if doc.meta.has_field("opportunity_from") and doc.meta.has_field("party_name"):
            return doc.get("opportunity_from"), doc.get("party_name")
        if doc.meta.has_field("customer"):
            return "Customer", doc.get("customer")
        return None, None

    def validar_alcances(self):
        if not self.alcances:
            frappe.throw(_("Debes definir al menos una linea de alcance para el contrato."))

        servicios_activos = set()
        for row in self.alcances:
            if not row.servicio_contable:
                frappe.throw(_("Cada linea de alcance debe indicar un servicio contable."))
            if cint_bool(row.activa) and row.servicio_contable in servicios_activos:
                frappe.throw(_("No puedes repetir un servicio activo en el mismo contrato: <b>{0}</b>.").format(row.servicio_contable), title=_("Servicio Duplicado"))
            if cint_bool(row.activa):
                servicios_activos.add(row.servicio_contable)

            row.fecha_inicio = row.fecha_inicio or self.fecha_inicio
            if self.fecha_fin and not row.fecha_fin:
                row.fecha_fin = self.fecha_fin
            row.sla_respuesta_horas = row.sla_respuesta_horas or self.sla_respuesta_horas
            row.sla_entrega_dias = row.sla_entrega_dias or self.sla_entrega_dias
            row.modalidad_tarifa = row.modalidad_tarifa or "Fijo"
            row.periodicidad = row.periodicidad or "Mensual"
            row.activa = cint_bool(row.activa) or 0

            if row.fecha_inicio and row.fecha_fin and getdate(row.fecha_inicio) > getdate(row.fecha_fin):
                frappe.throw(_("Una linea de alcance tiene fecha de inicio posterior a su fecha de fin."))
            if self.fecha_inicio and row.fecha_inicio and getdate(row.fecha_inicio) < getdate(self.fecha_inicio):
                frappe.throw(_("La vigencia de una linea no puede iniciar antes del contrato."))
            if self.fecha_fin and row.fecha_fin and getdate(row.fecha_fin) > getdate(self.fecha_fin):
                frappe.throw(_("La vigencia de una linea no puede terminar despues del contrato."))
            if row.modalidad_tarifa in ("Por Hora", "Mixto") and flt(row.tarifa_hora) <= 0:
                frappe.throw(_("Debes indicar tarifa por hora en las lineas por hora o mixtas."))
            if row.modalidad_tarifa in ("Fijo", "Mixto") and flt(row.honorario_fijo) <= 0:
                frappe.throw(_("Debes indicar honorario fijo en las lineas fijas o mixtas."))

    def actualizar_formato_impresion_sugerido(self):
        self.formato_impresion_sugerido = None
        tipos_servicio = self.obtener_tipos_servicio_relevantes()
        if len(tipos_servicio) != 1:
            return

        tipo_de_servicio = next(iter(tipos_servicio))
        self.formato_impresion_sugerido = PRINT_FORMAT_BY_SERVICE_TYPE.get(tipo_de_servicio)

    def obtener_tipos_servicio_relevantes(self):
        servicios_activos = [row.servicio_contable for row in self.alcances if row.servicio_contable and cint_bool(row.activa)]
        servicios = servicios_activos or [row.servicio_contable for row in self.alcances if row.servicio_contable]
        if not servicios:
            return set()

        tipos = frappe.get_all(
            "Servicio Contable",
            filters={"name": ["in", list(set(servicios))]},
            fields=["tipo_de_servicio"],
        )
        return {row.tipo_de_servicio for row in tipos if row.tipo_de_servicio}

    def calcular_resumen_comercial(self):
        mensual = 0
        for row in self.alcances:
            if not cint_bool(row.activa):
                continue
            base = flt(row.honorario_fijo) + (flt(row.tarifa_hora) * flt(row.horas_incluidas))
            mensual += base * FACTOR_MENSUAL.get(row.periodicidad or "Mensual", 0)
        self.valor_mensual_estimado = mensual
        self.valor_anual_estimado = mensual * 12

    def sincronizar_estado_comercial(self):
        if self.estado_aprobacion != ESTADO_APROBACION_APROBADO:
            if self.estado_comercial not in ("En Negociacion", "Cancelado", "Suspendido"):
                self.estado_comercial = "Borrador"
            return
        if self.estado_comercial in ("Cancelado", "Suspendido"):
            return
        hoy = getdate(nowdate())
        inicio = getdate(self.fecha_inicio) if self.fecha_inicio else hoy
        fin = getdate(self.fecha_fin) if self.fecha_fin else None
        if fin and fin < hoy:
            self.estado_comercial = "Vencido"
        elif inicio <= hoy and (not fin or fin >= hoy):
            self.estado_comercial = "Vigente"
        else:
            self.estado_comercial = "Aprobado"

    def sincronizar_tarifas_desde_alcances(self, cambio_name=None):
        if not self.cliente:
            return []

        activas = []
        creadas = []
        for row in self.alcances:
            if not row.servicio_contable:
                continue
            if not cint_bool(row.activa):
                if row.tarifa_cliente_servicio:
                    frappe.db.set_value("Tarifa Cliente Servicio", row.tarifa_cliente_servicio, "activa", 0, update_modified=False)
                continue

            tarifa = row.tarifa_cliente_servicio or frappe.db.get_value("Tarifa Cliente Servicio", {"contrato_comercial": self.name, "servicio_contable": row.servicio_contable}, "name")
            doc = frappe.get_doc("Tarifa Cliente Servicio", tarifa) if tarifa else frappe.new_doc("Tarifa Cliente Servicio")
            doc.cliente = self.cliente
            doc.servicio_contable = row.servicio_contable
            doc.company = self.company
            doc.moneda = self.moneda
            doc.tarifa_hora = flt(row.tarifa_hora)
            doc.honorario_fijo = flt(row.honorario_fijo)
            doc.vigencia_desde = row.fecha_inicio or self.fecha_inicio
            doc.vigencia_hasta = row.fecha_fin or self.fecha_fin
            doc.descripcion = row.descripcion or _("Tarifa vigente desde contrato {0}").format(self.name)
            doc.contrato_comercial = self.name
            doc.cambio_alcance_comercial = cambio_name or None
            doc.activa = 1
            if tarifa:
                doc.save(ignore_permissions=True)
            else:
                doc.insert(ignore_permissions=True)
            row.tarifa_cliente_servicio = doc.name
            if row.name:
                frappe.db.set_value(row.doctype, row.name, "tarifa_cliente_servicio", doc.name, update_modified=False)
            activas.append(row.servicio_contable)
            creadas.append(doc.name)

        for existing in frappe.get_all("Tarifa Cliente Servicio", filters={"contrato_comercial": self.name, "activa": 1}, fields=["name", "servicio_contable"]):
            if existing.servicio_contable not in activas:
                frappe.db.set_value("Tarifa Cliente Servicio", existing.name, "activa", 0, update_modified=False)
        return creadas

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar contratos comerciales."))


@frappe.whitelist()
def sincronizar_tarifas_contrato(contrato_name):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden sincronizar tarifas contractuales."))
    contrato = frappe.get_doc("Contrato Comercial", contrato_name)
    if contrato.estado_aprobacion != ESTADO_APROBACION_APROBADO:
        frappe.throw(_("El contrato debe estar aprobado antes de sincronizar tarifas."))
    tarifas = contrato.sincronizar_tarifas_desde_alcances()
    return {"contrato": contrato.name, "tarifas": tarifas, "total": len(tarifas)}


def cint_bool(value):
    return 1 if str(value) in ("1", "True", "true") or value == 1 else 0
