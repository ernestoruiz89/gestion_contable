import frappe

from gestion_contable.gestion_contable.utils.emailing import EMAIL_TEMPLATE_DEFAULTS


EMAIL_TEMPLATE_META_FIELDS = ("subject", "response", "response_html", "use_html", "enabled")
EMAIL_AUTOMATION_FIELDS = (
    "auto_enviar_correo_requerimiento_envio",
    "auto_enviar_recordatorio_requerimiento",
    "auto_enviar_aviso_vencido_requerimiento",
    "auto_enviar_correo_cobranza",
)


def ensure_standard_email_templates():
    if not frappe.db.exists("DocType", "Email Template"):
        return

    meta = frappe.get_meta("Email Template")
    for config_fieldname, definition in EMAIL_TEMPLATE_DEFAULTS.items():
        template_name = definition["name"]
        if not frappe.db.exists("Email Template", template_name):
            payload = {"doctype": "Email Template", "name": template_name}
            for fieldname in EMAIL_TEMPLATE_META_FIELDS:
                if not meta.has_field(fieldname):
                    continue
                if fieldname == "response_html":
                    continue
                if fieldname == "use_html":
                    payload[fieldname] = 1
                    continue
                if fieldname == "enabled":
                    payload[fieldname] = 1
                    continue
                payload[fieldname] = definition.get(fieldname) or definition.get("response") or ""
            frappe.get_doc(payload).insert(ignore_permissions=True)

        if frappe.db.exists("DocType", "Configuracion Despacho Contable"):
            current = frappe.db.get_single_value("Configuracion Despacho Contable", config_fieldname)
            if not current:
                frappe.db.set_single_value("Configuracion Despacho Contable", config_fieldname, template_name)

    if frappe.db.exists("DocType", "Configuracion Despacho Contable"):
        for fieldname in EMAIL_AUTOMATION_FIELDS:
            if frappe.db.get_single_value("Configuracion Despacho Contable", fieldname) in (None, ""):
                frappe.db.set_single_value("Configuracion Despacho Contable", fieldname, 1)
