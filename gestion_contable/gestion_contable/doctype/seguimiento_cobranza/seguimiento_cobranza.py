import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowdate

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.utils.communications import log_linked_communication
from gestion_contable.gestion_contable.utils.emailing import (
    build_seguimiento_cobranza_email_context,
    get_despacho_email_template_name,
    is_email_automation_enabled,
    resolve_email_recipients,
    send_templated_email,
)
from gestion_contable.gestion_contable.utils.security import ensure_supervisor


class SeguimientoCobranza(Document):
    def autoname(self):
        base_name = f"Cobranza - {self.sales_invoice or frappe.generate_hash(length=6)}"
        if self.fecha_gestion:
            base_name = f"{base_name} - {str(self.fecha_gestion)[:10]}"
        self.name = self._build_unique_name(base_name)

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar seguimientos de cobranza."))
        self.fecha_gestion = self.fecha_gestion or now()
        self.responsable = self.responsable or frappe.session.user
        self.sincronizar_desde_factura()
        self.validar_estado()

    def after_insert(self):
        if is_email_automation_enabled("auto_enviar_correo_cobranza", default=True):
            self.enviar_correo_cliente_si_aplica()

    def on_update(self):
        previous = None if self.is_new() else self.get_doc_before_save()
        if previous and not self._has_operational_changes(previous):
            return
        self.registrar_comunicacion_operativa()

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Seguimiento Cobranza", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Seguimiento Cobranza", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_desde_factura(self):
        if not self.sales_invoice:
            frappe.throw(_("Debes seleccionar una Sales Invoice para registrar la gestion de cobranza."), title=_("Factura Requerida"))

        invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
        if invoice.docstatus != 1:
            frappe.throw(_("La factura debe estar enviada antes de registrarle seguimiento."), title=_("Factura No Enviada"))

        self.customer = invoice.customer
        self.company = invoice.company
        self.moneda = invoice.currency
        self.monto_factura = flt(invoice.grand_total)
        self.saldo_pendiente = flt(invoice.outstanding_amount)

        encargo_name = getattr(invoice, "encargo_contable", None) if invoice.meta.has_field("encargo_contable") else None
        cliente_name = getattr(invoice, "cliente_contable", None) if invoice.meta.has_field("cliente_contable") else None
        servicio_name = getattr(invoice, "servicio_contable", None) if invoice.meta.has_field("servicio_contable") else None

        if not encargo_name and getattr(invoice, "project", None):
            encargo = frappe.db.get_value(
                "Encargo Contable",
                {"project": invoice.project},
                ["name", "cliente", "servicio_contable"],
                as_dict=True,
            )
            if encargo:
                encargo_name = encargo.name
                cliente_name = cliente_name or encargo.cliente
                servicio_name = servicio_name or encargo.servicio_contable

        self.encargo_contable = encargo_name
        self.cliente_contable = cliente_name
        self.servicio_contable = servicio_name

        if self.saldo_pendiente <= 0 and self.payment_entry and not frappe.db.exists("Payment Entry", self.payment_entry):
            frappe.throw(_("El Payment Entry indicado no existe."), title=_("Payment Entry Invalido"))

    def validar_estado(self):
        if self.payment_entry and not frappe.db.exists("Payment Entry", self.payment_entry):
            frappe.throw(_("El Payment Entry indicado no existe."), title=_("Payment Entry Invalido"))

        if self.estado_seguimiento == "Compromiso de Pago" and not self.compromiso_pago_fecha:
            frappe.throw(_("Debes definir la fecha de compromiso de pago."), title=_("Compromiso Incompleto"))

        if self.saldo_pendiente <= 0:
            self.estado_seguimiento = "Pagado"
            self.proxima_gestion = None
            return

        if not self.estado_seguimiento:
            self.estado_seguimiento = "Pendiente"

        if self.proxima_gestion and self.proxima_gestion < nowdate() and self.estado_seguimiento in ("Pendiente", "Contactado", "Compromiso de Pago"):
            self.estado_seguimiento = "Escalado"

    def enviar_correo_cliente_si_aplica(self, force_manual=False):
        if (self.canal or "") != "Correo" or not self.cliente_contable:
            return None

        defaults = get_cliente_defaults(self.cliente_contable)
        recipients = resolve_email_recipients(
            defaults.contacto_cobranza.get("email") if defaults.contacto_cobranza else None,
            defaults.email_cobranza_efectivo,
            defaults.correo_electronico,
        )
        if not recipients:
            frappe.throw(_("No hay un correo de cobranza configurado para el cliente <b>{0}</b>."
            ).format(self.cliente_contable), title=_("Correo Cobranza Requerido"))

        if self.estado_seguimiento == "Compromiso de Pago":
            template_field = "template_email_cobranza_compromiso"
            action_label = _("compromiso de pago")
        else:
            template_field = "template_email_cobranza_recordatorio"
            action_label = _("recordatorio de cobranza")

        template_name = get_despacho_email_template_name(template_field)
        note = _(
            "Se envio correo de <b>{0}</b> usando la plantilla <b>{1}</b> a <b>{2}</b>."
        ).format(action_label, template_name or _("Sin definir"), ", ".join(recipients))
        if force_manual:
            note = _("Envio manual. ") + note

        return send_templated_email(
            template_name,
            recipients,
            context=build_seguimiento_cobranza_email_context(self),
            reference_doctype="Encargo Contable" if self.encargo_contable else "Sales Invoice",
            reference_name=self.encargo_contable or self.sales_invoice,
            communication_note=note,
        )

    def registrar_comunicacion_operativa(self):
        reference_doctype = "Encargo Contable" if self.encargo_contable else "Sales Invoice"
        reference_name = self.encargo_contable or self.sales_invoice
        log_linked_communication(
            reference_doctype,
            reference_name,
            subject=f"Seguimiento de cobranza: {self.sales_invoice}",
            content=_(
                "Estado: <b>{0}</b>. Saldo pendiente: <b>{1}</b>. Proxima gestion: <b>{2}</b>. Comentarios: <b>{3}</b>."
            ).format(
                self.estado_seguimiento or _("Sin definir"),
                self.saldo_pendiente,
                self.proxima_gestion or _("Sin definir"),
                self.comentarios or _("Sin comentarios"),
            ),
        )

    def _has_operational_changes(self, previous):
        tracked_fields = (
            "estado_seguimiento",
            "comentarios",
            "proxima_gestion",
            "payment_entry",
            "compromiso_pago_monto",
            "compromiso_pago_fecha",
            "saldo_pendiente",
        )
        return any((previous.get(fieldname) or None) != (self.get(fieldname) or None) for fieldname in tracked_fields)

    def on_trash(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden eliminar seguimientos de cobranza."))


@frappe.whitelist()
def enviar_correo_seguimiento_cobranza_manual(seguimiento_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden enviar correos de cobranza."))
    seguimiento = frappe.get_doc("Seguimiento Cobranza", seguimiento_name)
    result = seguimiento.enviar_correo_cliente_si_aplica(force_manual=True)
    return {"ok": True, "subject": result.subject if result else None, "recipients": result.recipients if result else []}
