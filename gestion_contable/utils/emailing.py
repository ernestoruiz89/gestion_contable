from email.utils import getaddresses

import frappe
from frappe import _
from frappe.utils import cstr, get_url, get_url_to_form, getdate, nowdate

from gestion_contable.gestion_contable.utils.communications import log_linked_communication


EMAIL_TEMPLATE_DEFAULTS = {
    "template_email_requerimiento_envio": {
        "name": "GC - Requerimiento Envio",
        "subject": "Requerimiento de informacion - {{ doc.nombre_del_requerimiento }}",
        "response": """
<p>Estimado {{ cliente.contacto_facturacion or cliente.customer or doc.cliente }},</p>
<p>Le compartimos el requerimiento <strong>{{ doc.nombre_del_requerimiento }}</strong>{% if doc.periodo %} correspondiente al periodo <strong>{{ doc.periodo }}</strong>{% endif %}.</p>
{% if doc.fecha_vencimiento %}
<p>Fecha de vencimiento: <strong>{{ doc.fecha_vencimiento }}</strong></p>
{% endif %}
{% if entregables %}
<p>Entregables solicitados:</p>
<ul>
{% for row in entregables %}
  <li>{{ row.tipo_entregable or "Entregable" }}{% if row.descripcion %}: {{ row.descripcion }}{% endif %}</li>
{% endfor %}
</ul>
{% endif %}
{% if doc.instrucciones_cliente %}
<p>Instrucciones:</p>
{{ doc.instrucciones_cliente }}
{% endif %}
<p>Puede dar seguimiento desde el portal: <a href="{{ portal_url }}">{{ portal_url }}</a></p>
<p>Saludos,<br>{{ frappe.utils.get_fullname() }}</p>
""".strip(),
    },
    "template_email_requerimiento_recordatorio": {
        "name": "GC - Requerimiento Recordatorio",
        "subject": "Recordatorio de requerimiento - {{ doc.nombre_del_requerimiento }}",
        "response": """
<p>Estimado {{ cliente.contacto_facturacion or cliente.customer or doc.cliente }},</p>
<p>Le recordamos que el requerimiento <strong>{{ doc.nombre_del_requerimiento }}</strong> vence el <strong>{{ doc.fecha_vencimiento }}</strong>.</p>
<p>Estado actual: <strong>{{ doc.estado_requerimiento }}</strong>.</p>
<p>Portal cliente: <a href="{{ portal_url }}">{{ portal_url }}</a></p>
<p>Quedamos atentos a la documentacion pendiente.</p>
""".strip(),
    },
    "template_email_requerimiento_vencido": {
        "name": "GC - Requerimiento Vencido",
        "subject": "Requerimiento vencido - {{ doc.nombre_del_requerimiento }}",
        "response": """
<p>Estimado {{ cliente.contacto_facturacion or cliente.customer or doc.cliente }},</p>
<p>El requerimiento <strong>{{ doc.nombre_del_requerimiento }}</strong> se encuentra vencido desde el <strong>{{ doc.fecha_vencimiento }}</strong>.</p>
<p>Por favor comparta la informacion pendiente a la mayor brevedad.</p>
<p>Portal cliente: <a href="{{ portal_url }}">{{ portal_url }}</a></p>
""".strip(),
    },
    "template_email_cobranza_recordatorio": {
        "name": "GC - Cobranza Recordatorio",
        "subject": "Recordatorio de pago - Factura {{ sales_invoice.name if sales_invoice else doc.sales_invoice }}",
        "response": """
<p>Estimado {{ cliente.contacto_cobranza or cliente.customer or doc.cliente_contable }},</p>
<p>Le recordamos el pago pendiente de la factura <strong>{{ sales_invoice.name if sales_invoice else doc.sales_invoice }}</strong>.</p>
<p>Saldo pendiente: <strong>{{ doc.saldo_pendiente }} {{ doc.moneda }}</strong></p>
{% if doc.proxima_gestion %}
<p>Proxima fecha de seguimiento: <strong>{{ doc.proxima_gestion }}</strong></p>
{% endif %}
{% if doc.comentarios %}
<p>Comentarios:</p>
<p>{{ doc.comentarios }}</p>
{% endif %}
<p>Quedamos atentos a su confirmacion.</p>
""".strip(),
    },
    "template_email_cobranza_compromiso": {
        "name": "GC - Cobranza Compromiso Pago",
        "subject": "Confirmacion de compromiso de pago - Factura {{ sales_invoice.name if sales_invoice else doc.sales_invoice }}",
        "response": """
<p>Estimado {{ cliente.contacto_cobranza or cliente.customer or doc.cliente_contable }},</p>
<p>Confirmamos el compromiso de pago registrado para la factura <strong>{{ sales_invoice.name if sales_invoice else doc.sales_invoice }}</strong>.</p>
{% if doc.compromiso_pago_monto %}
<p>Monto comprometido: <strong>{{ doc.compromiso_pago_monto }} {{ doc.moneda }}</strong></p>
{% endif %}
{% if doc.compromiso_pago_fecha %}
<p>Fecha compromiso: <strong>{{ doc.compromiso_pago_fecha }}</strong></p>
{% endif %}
{% if doc.comentarios %}
<p>Comentarios:</p>
<p>{{ doc.comentarios }}</p>
{% endif %}
<p>Quedamos atentos al pago para su correspondiente aplicacion.</p>
""".strip(),
    },
}


def get_despacho_email_template_name(config_fieldname):
    template_name = frappe.db.get_single_value("Configuracion Despacho Contable", config_fieldname)
    if template_name:
        return template_name
    return EMAIL_TEMPLATE_DEFAULTS.get(config_fieldname, {}).get("name")


def is_email_automation_enabled(config_fieldname, default=True):
    value = frappe.db.get_single_value("Configuracion Despacho Contable", config_fieldname)
    if value in (None, ""):
        return bool(default)
    return bool(frappe.utils.cint(value))


@frappe.whitelist()
def get_despacho_email_automation_status():
    return frappe._dict(
        auto_enviar_correo_requerimiento_envio=is_email_automation_enabled("auto_enviar_correo_requerimiento_envio", default=True),
        auto_enviar_recordatorio_requerimiento=is_email_automation_enabled("auto_enviar_recordatorio_requerimiento", default=True),
        auto_enviar_aviso_vencido_requerimiento=is_email_automation_enabled("auto_enviar_aviso_vencido_requerimiento", default=True),
        auto_enviar_correo_cobranza=is_email_automation_enabled("auto_enviar_correo_cobranza", default=True),
    )


def resolve_email_recipients(*values):
    recipients = []
    seen = set()
    for value in values:
        for chunk in _iter_candidate_values(value):
            for _, email in getaddresses([chunk]):
                email = (email or "").strip()
                if not email:
                    continue
                key = email.lower()
                if key in seen:
                    continue
                seen.add(key)
                recipients.append(email)
    return recipients


def ensure_email_template_available(template_name):
    if template_name and frappe.db.exists("Email Template", template_name):
        return template_name
    from gestion_contable.gestion_contable.setup.email_templates import ensure_standard_email_templates

    ensure_standard_email_templates()
    return template_name


def send_templated_email(
    template_name,
    recipients,
    *,
    context=None,
    reference_doctype=None,
    reference_name=None,
    sender=None,
    sender_full_name=None,
    communication_note=None,
):
    template_name = ensure_email_template_available(template_name)
    if not template_name:
        frappe.throw(_("No se definio una plantilla de correo para esta accion."), title=_("Plantilla Requerida"))

    recipients = resolve_email_recipients(recipients)
    if not recipients:
        frappe.throw(_("No fue posible resolver destinatarios validos para el correo."), title=_("Destinatarios Requeridos"))

    if not frappe.db.exists("Email Template", template_name):
        frappe.throw(_("La plantilla de correo <b>{0}</b> no existe.").format(template_name), title=_("Plantilla Invalida"))

    template_doc = frappe.get_cached_doc("Email Template", template_name)
    template_context = frappe._dict(context or {})
    template_context.setdefault("site_url", get_url())
    template_context.setdefault("today", getdate(nowdate()))
    subject = frappe.render_template(cstr(getattr(template_doc, "subject", "") or ""), template_context).strip()
    message = frappe.render_template(cstr(_get_template_body(template_doc) or ""), template_context).strip()

    if not subject or not message:
        frappe.throw(_("La plantilla <b>{0}</b> no produjo asunto o contenido valido.").format(template_name), title=_("Plantilla Incompleta"))

    frappe.sendmail(
        recipients=recipients,
        sender=sender,
        subject=subject,
        message=message,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
    )

    note = communication_note or _("Se envio correo usando la plantilla <b>{0}</b> a <b>{1}</b>.").format(
        template_name, ", ".join(recipients)
    )
    if reference_doctype and reference_name:
        log_linked_communication(
            reference_doctype,
            reference_name,
            subject=f"Correo enviado: {subject}",
            content=note,
            recipients=", ".join(recipients),
            sender=sender,
            sender_full_name=sender_full_name,
            communication_medium="Email",
        )

    return frappe._dict(subject=subject, message=message, recipients=recipients, template_name=template_name)


def build_requerimiento_email_context(requerimiento):
    cliente = frappe.get_cached_doc("Cliente Contable", requerimiento.cliente) if requerimiento.cliente else frappe._dict()
    entregables = []
    if frappe.db.exists("DocType", "Entregable Cliente"):
        entregables = frappe.get_all(
            "Entregable Cliente",
            filters={"requerimiento_cliente": requerimiento.name},
            fields=["name", "tipo_entregable", "descripcion", "estado_entregable", "fecha_compromiso"],
            order_by="idx asc",
            limit_page_length=500,
        )
    return frappe._dict(
        doc=requerimiento,
        cliente=cliente,
        entregables=entregables,
        portal_url=get_url("/portal-cliente"),
        requerimiento_url=get_url_to_form("Requerimiento Cliente", requerimiento.name),
    )


def build_seguimiento_cobranza_email_context(seguimiento):
    cliente = frappe.get_cached_doc("Cliente Contable", seguimiento.cliente_contable) if seguimiento.cliente_contable else frappe._dict()
    sales_invoice = frappe.get_doc("Sales Invoice", seguimiento.sales_invoice) if seguimiento.sales_invoice else None
    encargo = frappe.get_doc("Encargo Contable", seguimiento.encargo_contable) if seguimiento.encargo_contable else None
    return frappe._dict(
        doc=seguimiento,
        cliente=cliente,
        sales_invoice=sales_invoice,
        encargo=encargo,
        sales_invoice_url=get_url_to_form("Sales Invoice", seguimiento.sales_invoice) if seguimiento.sales_invoice else None,
    )


def _get_template_body(template_doc):
    for fieldname in ("response", "response_html", "message"):
        value = getattr(template_doc, fieldname, None)
        if value:
            return value
    return ""


def _iter_candidate_values(value):
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]
    normalized = []
    for entry in values:
        entry = cstr(entry or "").strip()
        if not entry:
            continue
        normalized.extend([chunk.strip() for chunk in entry.replace(";", ",").split(",") if chunk.strip()])
    return normalized


