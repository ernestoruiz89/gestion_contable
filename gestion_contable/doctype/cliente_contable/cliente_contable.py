import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from gestion_contable.gestion_contable.utils.security import ensure_manager


CLIENTE_DEFAULT_FIELDS = (
    "customer",
    "estado",
    "frecuencia_de_cierre",
    "company_default",
    "regimen_fiscal",
    "clasificacion_riesgo",
    "ejecutivo_comercial_default",
    "responsable_operativo_default",
    "responsable_cobranza_interno",
    "sla_respuesta_horas_default",
    "sla_entrega_dias_default",
    "canal_envio_preferido",
    "moneda_preferida",
    "contacto_facturacion",
    "email_facturacion",
    "contacto_cobranza",
    "email_cobranza",
    "termino_pago_dias",
    "dias_gracia_cobranza",
    "politica_retencion_documental",
    "clasificacion_confidencialidad_default",
    "portal_habilitado",
    "permite_carga_documentos",
    "recordatorios_automaticos_portal",
    "usuario_portal_principal",
    "correo_electronico",
    "telefono",
)


class ClienteContable(Document):
    def validate(self):
        ensure_manager()
        self.validar_metricas()
        self.validar_contactos_funcionales()
        self.sincronizar_contacto_principal()
        self.validar_portal()

    def on_trash(self):
        ensure_manager()

    def validar_metricas(self):
        numeric_fields = {
            "sla_respuesta_horas_default": _("SLA respuesta horas default"),
            "sla_entrega_dias_default": _("SLA entrega dias default"),
            "termino_pago_dias": _("Termino pago dias"),
            "dias_gracia_cobranza": _("Dias gracia cobranza"),
        }
        for fieldname, label in numeric_fields.items():
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} no puede ser negativo.").format(label), title=_("Valor Invalido"))

    def validar_contactos_funcionales(self):
        principales = []
        activos = []
        for row in self.contactos_funcionales or []:
            row.nombre_contacto = (row.nombre_contacto or "").strip()
            row.email_contacto = (row.email_contacto or "").strip() or None
            row.telefono_contacto = (row.telefono_contacto or "").strip() or None
            row.contacto_rol = row.contacto_rol or "Otro"
            row.activo = cint(row.activo)
            row.es_principal = cint(row.es_principal)
            row.recibe_requerimientos = cint(row.recibe_requerimientos)
            row.recibe_cobranza = cint(row.recibe_cobranza)

            if row.es_principal and not row.activo:
                row.activo = 1

            if row.activo and not row.nombre_contacto and not row.email_contacto:
                frappe.throw(
                    _("Cada contacto funcional activo debe indicar nombre o correo."),
                    title=_("Contacto Invalido"),
                )

            if row.activo:
                activos.append(row)
            if row.es_principal:
                principales.append(row)

        if len(principales) > 1:
            frappe.throw(_("Solo puedes marcar un contacto funcional principal por cliente."), title=_("Contacto Duplicado"))

        if activos and not principales:
            activos[0].es_principal = 1

    def sincronizar_contacto_principal(self):
        principal = resolve_functional_contact(self, purpose="general")
        if not principal:
            return
        self.correo_electronico = self.correo_electronico or principal.email_contacto
        self.telefono = self.telefono or principal.telefono_contacto

    def validar_portal(self):
        if not cint(self.portal_habilitado):
            return
        principal = resolve_functional_contact(self, purpose="requerimientos") or resolve_functional_contact(self, purpose="general")
        if not (self.usuario_portal_principal or self.correo_electronico or (principal and principal.email_contacto)):
            frappe.throw(
                _("Debes definir un usuario portal o al menos un contacto con correo para habilitar el portal del cliente."),
                title=_("Portal Incompleto"),
            )


def get_cliente_defaults(cliente_name):
    if not cliente_name or not frappe.db.exists("Cliente Contable", cliente_name):
        return frappe._dict()

    cliente = frappe.get_cached_doc("Cliente Contable", cliente_name)
    defaults = frappe._dict({fieldname: cliente.get(fieldname) for fieldname in CLIENTE_DEFAULT_FIELDS})

    contacto_general = resolve_functional_contact(cliente, purpose="general")
    contacto_requerimientos = resolve_functional_contact(cliente, purpose="requerimientos") or contacto_general
    contacto_cobranza = resolve_functional_contact(cliente, purpose="cobranza") or contacto_general

    defaults.contacto_general = _build_contact_payload(contacto_general)
    defaults.contacto_requerimientos = _build_contact_payload(contacto_requerimientos)
    defaults.contacto_cobranza = _build_contact_payload(contacto_cobranza)
    defaults.contacto_cliente_display = format_contact_display(contacto_requerimientos, cliente.correo_electronico)
    defaults.email_facturacion_efectivo = (defaults.contacto_general.get("email") if defaults.contacto_general else None) or cliente.email_facturacion or cliente.correo_electronico
    defaults.email_cobranza_efectivo = (defaults.contacto_cobranza.get("email") if defaults.contacto_cobranza else None) or cliente.email_cobranza or cliente.correo_electronico
    return defaults


def resolve_functional_contact(cliente_doc, purpose="general"):
    contactos = [row for row in (cliente_doc.get("contactos_funcionales") or []) if cint(row.activo)]
    if not contactos:
        return None

    if purpose == "requerimientos":
        purpose_contacts = [row for row in contactos if cint(row.recibe_requerimientos)]
    elif purpose == "cobranza":
        purpose_contacts = [row for row in contactos if cint(row.recibe_cobranza)]
    else:
        purpose_contacts = contactos

    candidatos = purpose_contacts or contactos
    principal = next((row for row in candidatos if cint(row.es_principal)), None)
    return principal or candidatos[0]


def format_contact_display(contacto, fallback_email=None):
    if contacto:
        nombre = (contacto.nombre_contacto or "").strip()
        email = (contacto.email_contacto or "").strip()
        if nombre and email:
            return f"{nombre} <{email}>"
        if nombre:
            return nombre
        if email:
            return email
    return fallback_email or None


def _build_contact_payload(contacto):
    if not contacto:
        return frappe._dict()
    return frappe._dict(
        nombre=contacto.nombre_contacto,
        email=contacto.email_contacto,
        telefono=contacto.telefono_contacto,
        rol=contacto.contacto_rol,
    )
