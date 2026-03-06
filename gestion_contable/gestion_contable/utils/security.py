import frappe
from frappe import _

MANAGER_ROLES = ("System Manager", "Contador del Despacho")
AUXILIAR_ROLE = "Auxiliar Contable del Despacho"


def get_current_user():
    return frappe.session.user or "Guest"


def has_any_role(roles, user=None):
    user = user or get_current_user()
    if user == "Administrator":
        return True

    user_roles = set(frappe.get_roles(user))
    return any(role in user_roles for role in roles)


def is_manager(user=None):
    return has_any_role(MANAGER_ROLES, user=user)


def is_auxiliar(user=None):
    user = user or get_current_user()
    if user == "Administrator":
        return False

    return AUXILIAR_ROLE in set(frappe.get_roles(user))


def ensure_manager(message=None):
    if is_manager():
        return

    frappe.throw(
        message
        or _("Solo el Contador del Despacho o System Manager pueden realizar esta operacion."),
        frappe.PermissionError,
    )
