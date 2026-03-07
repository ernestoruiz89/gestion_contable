import frappe
from frappe import _

SYSTEM_MANAGER_ROLE = "System Manager"
CONTADOR_ROLE = "Contador del Despacho"
SUPERVISOR_ROLE = "Supervisor del Despacho"
SOCIO_ROLE = "Socio del Despacho"
AUXILIAR_ROLE = "Auxiliar Contable del Despacho"

MANAGER_ROLES = (SYSTEM_MANAGER_ROLE, CONTADOR_ROLE, SOCIO_ROLE)
SUPERVISOR_ROLES = (SYSTEM_MANAGER_ROLE, CONTADOR_ROLE, SUPERVISOR_ROLE, SOCIO_ROLE)
SOCIO_ROLES = (SYSTEM_MANAGER_ROLE, SOCIO_ROLE)


def get_current_user():
    return frappe.session.user or "Guest"


def has_any_role(roles, user=None):
    user = user or get_current_user()
    if user == "Administrator":
        return True

    user_roles = set(frappe.get_roles(user))
    return any(role in user_roles for role in roles)


def is_system_manager(user=None):
    return has_any_role((SYSTEM_MANAGER_ROLE,), user=user)


def is_manager(user=None):
    return has_any_role(MANAGER_ROLES, user=user)


def is_supervisor(user=None):
    return has_any_role(SUPERVISOR_ROLES, user=user)


def is_socio(user=None):
    return has_any_role(SOCIO_ROLES, user=user)


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
        or _("Solo Socio del Despacho, Contador del Despacho o System Manager pueden realizar esta operacion."),
        frappe.PermissionError,
    )


def ensure_supervisor(message=None):
    if is_supervisor():
        return

    frappe.throw(
        message
        or _(
            "Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden realizar esta operacion."
        ),
        frappe.PermissionError,
    )


def ensure_socio(message=None):
    if is_socio():
        return

    frappe.throw(
        message or _("Solo Socio del Despacho o System Manager pueden realizar esta operacion."),
        frappe.PermissionError,
    )
