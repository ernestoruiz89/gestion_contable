from urllib.parse import quote_plus

import frappe
from frappe import _

from gestion_contable.gestion_contable.portal.cliente import (
    get_portal_entregables_context,
    subir_entregable_portal,
)


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    context.title = _("Entregables Cliente")

    if frappe.session.user == "Guest":
        frappe.throw(_("Debes iniciar sesion para acceder al portal cliente."), frappe.PermissionError)

    if frappe.request.method == "POST":
        _handle_upload_post()
        return context

    context.update(get_portal_entregables_context())
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.upload_status = (frappe.form_dict.get("upload") or "").strip().lower() or None
    context.upload_message = frappe.form_dict.get("message")
    context.upload_target = frappe.form_dict.get("entregable")
    return context


def _handle_upload_post():
    try:
        result = subir_entregable_portal(
            frappe.form_dict.get("entregable_name"),
            titulo_documento=frappe.form_dict.get("titulo_documento"),
            tipo_documental=frappe.form_dict.get("tipo_documental"),
            observaciones=frappe.form_dict.get("observaciones"),
            version_documento_name=frappe.form_dict.get("version_documento_name"),
        )
        _redirect(
            "/entregables-cliente?upload=ok&entregable={0}&message={1}".format(
                quote_plus(result["entregable"]),
                quote_plus(_("Documento recibido y vinculado correctamente.")),
            )
        )
    except Exception as exc:
        _redirect(
            "/entregables-cliente?upload=error&message={0}".format(
                quote_plus(str(exc))
            )
        )



def _redirect(location):
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = location
