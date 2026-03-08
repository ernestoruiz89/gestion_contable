import frappe
from frappe import _

from gestion_contable.gestion_contable.portal.cliente import get_portal_entregables_context


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    context.title = _("Entregables Cliente")

    if frappe.session.user == "Guest":
        frappe.throw(_("Debes iniciar sesion para acceder al portal cliente."), frappe.PermissionError)

    context.update(get_portal_entregables_context())
    return context
