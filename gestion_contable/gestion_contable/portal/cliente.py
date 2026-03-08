import frappe
from frappe import _

from gestion_contable.gestion_contable.utils.communications import log_linked_communication


PORTAL_REQUIRED_FIELDS = [
    "name",
    "customer",
    "correo_electronico",
    "portal_habilitado",
    "permite_carga_documentos",
    "recordatorios_automaticos_portal",
    "usuario_portal_principal",
]
PORTAL_REQUERIMIENTO_FIELDS = [
    "name",
    "nombre_del_requerimiento",
    "company",
    "periodo",
    "estado_requerimiento",
    "fecha_envio",
    "fecha_vencimiento",
    "porcentaje_cumplimiento",
    "modified",
]
PORTAL_ENTREGABLE_FIELDS = [
    "name",
    "requerimiento_cliente",
    "company",
    "tipo_entregable",
    "descripcion",
    "estado_entregable",
    "fecha_compromiso",
    "fecha_recepcion",
    "documento_contable",
    "modified",
]
PORTAL_DOCUMENTO_FIELDS = [
    "name",
    "titulo_del_documento",
    "company",
    "periodo",
    "tipo",
    "archivo_adjunto",
    "modified",
]
PORTAL_COMMUNICATION_FIELDS = [
    "name",
    "reference_name",
    "subject",
    "content",
    "creation",
    "sender_full_name",
]
PORTAL_NAV_ITEMS = (
    {"label": _("Dashboard"), "route": "/portal-cliente"},
    {"label": _("Requerimientos"), "route": "/requerimientos-cliente"},
    {"label": _("Entregables"), "route": "/entregables-cliente"},
)


def get_portal_dashboard_context(user=None):
    cliente = require_portal_cliente(user)
    requerimientos = get_portal_requerimientos(cliente.name, limit=12)
    entregables = get_portal_entregables(cliente.name, limit=24)
    documentos = get_portal_documentos(cliente.name, limit=12)
    comunicaciones = get_portal_communications([row.name for row in requerimientos], limit=12)

    return {
        "cliente": cliente,
        "summary": get_portal_summary(cliente.name),
        "requerimientos": requerimientos,
        "entregables": entregables,
        "documentos": documentos,
        "comunicaciones": comunicaciones,
        "nav_items": get_portal_nav_items("/portal-cliente"),
    }



def get_portal_requerimientos_context(user=None):
    cliente = require_portal_cliente(user)
    requerimientos = get_portal_requerimientos(cliente.name, limit=100)
    return {
        "cliente": cliente,
        "summary": get_portal_summary(cliente.name),
        "requerimientos": requerimientos,
        "nav_items": get_portal_nav_items("/requerimientos-cliente"),
    }



def get_portal_entregables_context(user=None):
    cliente = require_portal_cliente(user)
    entregables = get_portal_entregables(cliente.name, limit=150)
    return {
        "cliente": cliente,
        "summary": get_portal_summary(cliente.name),
        "entregables": entregables,
        "nav_items": get_portal_nav_items("/entregables-cliente"),
    }



def require_portal_cliente(user=None):
    cliente = get_portal_cliente_for_user(user)
    if not cliente:
        frappe.throw(_("No existe un cliente contable habilitado para el usuario autenticado."), frappe.PermissionError)
    return cliente



def get_portal_cliente_for_user(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    cliente_name = frappe.db.get_value(
        "Cliente Contable",
        {"portal_habilitado": 1, "usuario_portal_principal": user},
        "name",
    )
    if not cliente_name:
        cliente_name = frappe.db.get_value(
            "Cliente Contable",
            {"portal_habilitado": 1, "correo_electronico": user},
            "name",
        )
    if not cliente_name:
        matches = frappe.db.sql(
            """
            SELECT parent
            FROM `tabContacto Funcional Cliente`
            WHERE parenttype = 'Cliente Contable'
              AND IFNULL(email_contacto, '') = %(email)s
              AND parent IN (
                SELECT name FROM `tabCliente Contable`
                WHERE portal_habilitado = 1
              )
            LIMIT 1
            """,
            {"email": user},
        )
        cliente_name = matches[0][0] if matches else None

    if not cliente_name:
        return None

    return frappe.get_doc("Cliente Contable", cliente_name)



def portal_user_has_cliente_access(cliente_name, user=None):
    if not cliente_name:
        return False
    cliente = get_portal_cliente_for_user(user)
    return bool(cliente and cliente.name == cliente_name)



def portal_user_has_doc_access(doc_or_name, doctype=None, user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    if isinstance(doc_or_name, str):
        if not doctype or not frappe.db.exists(doctype, doc_or_name):
            return False
        doc = frappe.db.get_value(doctype, doc_or_name, ["name", "cliente"], as_dict=True)
    else:
        doc = doc_or_name

    cliente_name = getattr(doc, "cliente", None) if doc else None
    if not cliente_name and isinstance(doc, dict):
        cliente_name = doc.get("cliente")
    return portal_user_has_cliente_access(cliente_name, user=user)



def get_portal_requerimientos(cliente_name, limit=100):
    return frappe.get_all(
        "Requerimiento Cliente",
        filters={"cliente": cliente_name},
        fields=PORTAL_REQUERIMIENTO_FIELDS,
        order_by="modified desc",
        limit_page_length=limit,
    )



def get_portal_entregables(cliente_name, limit=150):
    return frappe.get_all(
        "Entregable Cliente",
        filters={"cliente": cliente_name},
        fields=PORTAL_ENTREGABLE_FIELDS,
        order_by="modified desc",
        limit_page_length=limit,
    )



def get_portal_documentos(cliente_name, limit=40):
    return frappe.get_all(
        "Documento Contable",
        filters={"cliente": cliente_name},
        fields=PORTAL_DOCUMENTO_FIELDS,
        order_by="modified desc",
        limit_page_length=limit,
    )



def get_portal_communications(requerimiento_names, limit=40):
    if not requerimiento_names or not frappe.db.exists("DocType", "Communication"):
        return []

    return frappe.get_all(
        "Communication",
        filters={"reference_doctype": "Requerimiento Cliente", "reference_name": ["in", requerimiento_names]},
        fields=PORTAL_COMMUNICATION_FIELDS,
        order_by="creation desc",
        limit_page_length=limit,
    )



def get_portal_summary(cliente_name):
    requerimientos = frappe.get_all(
        "Requerimiento Cliente",
        filters={"cliente": cliente_name},
        fields=["estado_requerimiento"],
        limit_page_length=0,
    )
    entregables = frappe.get_all(
        "Entregable Cliente",
        filters={"cliente": cliente_name},
        fields=["estado_entregable"],
        limit_page_length=0,
    )
    documentos_recibidos = frappe.db.count("Documento Contable", {"cliente": cliente_name})

    return {
        "requerimientos_abiertos": sum(1 for row in requerimientos if row.estado_requerimiento not in ("Cerrado", "Cancelado")),
        "entregables_pendientes": sum(1 for row in entregables if row.estado_entregable in ("Pendiente", "Solicitado", "Rechazado", "Vencido")),
        "entregables_vencidos": sum(1 for row in entregables if row.estado_entregable == "Vencido"),
        "documentos_recibidos": documentos_recibidos,
    }



def get_portal_nav_items(active_route=None):
    return [
        {
            "label": item["label"],
            "route": item["route"],
            "active": item["route"] == active_route,
        }
        for item in PORTAL_NAV_ITEMS
    ]


@frappe.whitelist()
def registrar_mensaje_portal(requerimiento_name, mensaje):
    cliente = require_portal_cliente()
    if not frappe.db.exists("Requerimiento Cliente", {"name": requerimiento_name, "cliente": cliente.name}):
        frappe.throw(_("El requerimiento indicado no pertenece a tu cliente portal."), frappe.PermissionError)

    mensaje = (mensaje or "").strip()
    if not mensaje:
        frappe.throw(_("Debes escribir un mensaje."), title=_("Mensaje Requerido"))

    log_linked_communication(
        "Requerimiento Cliente",
        requerimiento_name,
        subject=f"Mensaje portal cliente: {cliente.name}",
        content=frappe.utils.escape_html(mensaje),
        sender=frappe.session.user,
        sender_full_name=frappe.utils.get_fullname(frappe.session.user),
    )
    return {"ok": True}
