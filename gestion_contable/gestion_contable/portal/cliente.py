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


def get_portal_dashboard_context(user=None):
    user = user or frappe.session.user
    cliente = get_portal_cliente_for_user(user)
    if not cliente:
        frappe.throw(_("No existe un cliente contable habilitado para el usuario autenticado."), frappe.PermissionError)

    requerimientos = frappe.get_all(
        "Requerimiento Cliente",
        filters={"cliente": cliente.name},
        fields=[
            "name",
            "nombre_del_requerimiento",
            "company",
            "periodo",
            "estado_requerimiento",
            "fecha_envio",
            "fecha_vencimiento",
            "porcentaje_cumplimiento",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=12,
    )

    entregables = frappe.get_all(
        "Entregable Cliente",
        filters={"cliente": cliente.name},
        fields=[
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
        ],
        order_by="modified desc",
        limit_page_length=24,
    )

    documentos = frappe.get_all(
        "Documento Contable",
        filters={"cliente": cliente.name},
        fields=["name", "titulo_del_documento", "company", "periodo", "tipo", "archivo_adjunto", "modified"],
        order_by="modified desc",
        limit_page_length=12,
    )

    comunicaciones = frappe.get_all(
        "Communication",
        filters={"reference_doctype": "Requerimiento Cliente", "reference_name": ["in", [row.name for row in requerimientos] or [""]]},
        fields=["name", "reference_name", "subject", "content", "creation", "sender_full_name"],
        order_by="creation desc",
        limit_page_length=12,
    ) if frappe.db.exists("DocType", "Communication") else []

    return {
        "cliente": cliente,
        "summary": {
            "requerimientos_abiertos": sum(1 for row in requerimientos if row.estado_requerimiento not in ("Cerrado", "Cancelado")),
            "entregables_pendientes": sum(1 for row in entregables if row.estado_entregable in ("Pendiente", "Solicitado", "Rechazado", "Vencido")),
            "entregables_vencidos": sum(1 for row in entregables if row.estado_entregable == "Vencido"),
            "documentos_recibidos": len(documentos),
        },
        "requerimientos": requerimientos,
        "entregables": entregables,
        "documentos": documentos,
        "comunicaciones": comunicaciones,
    }


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


@frappe.whitelist()
def registrar_mensaje_portal(requerimiento_name, mensaje):
    cliente = get_portal_cliente_for_user()
    if not cliente:
        frappe.throw(_("No tienes acceso al portal cliente."), frappe.PermissionError)
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
