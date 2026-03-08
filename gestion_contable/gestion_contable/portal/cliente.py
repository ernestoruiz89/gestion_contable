import frappe
from frappe import _
from frappe.utils import now_datetime

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
PORTAL_ENTREGABLE_UPLOAD_STATES = ("Pendiente", "Solicitado", "Vencido", "Rechazado")
PORTAL_ENTREGABLE_TERMINAL_STATES = ("Validado", "No Aplica")


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
    rows = frappe.get_all(
        "Entregable Cliente",
        filters={"cliente": cliente_name},
        fields=PORTAL_ENTREGABLE_FIELDS,
        order_by="modified desc",
        limit_page_length=limit,
    )
    _decorate_portal_entregables(cliente_name, rows)
    return rows


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


def _decorate_portal_entregables(cliente_name, rows):
    if not rows:
        return

    cliente_flags = frappe.db.get_value(
        "Cliente Contable",
        cliente_name,
        ["permite_carga_documentos"],
        as_dict=True,
    ) or frappe._dict(permite_carga_documentos=0)
    version_map = _get_eeff_version_exchange_map(
        cliente_name,
        [row.name for row in rows if row.name],
        [row.requerimiento_cliente for row in rows if row.requerimiento_cliente],
    )

    for row in rows:
        version_row = version_map.get(("entregable", row.name)) or version_map.get(("requerimiento", row.requerimiento_cliente))
        has_active_document = bool(row.documento_contable and row.estado_entregable != "Rechazado")
        row.portal_permite_carga = bool(
            cliente_flags.permite_carga_documentos
            and row.estado_entregable not in PORTAL_ENTREGABLE_TERMINAL_STATES
            and row.estado_entregable in PORTAL_ENTREGABLE_UPLOAD_STATES
            and not has_active_document
        )
        row.version_documento_eeff = version_row.name if version_row else None
        row.version_documento_eeff_label = (
            _("Version Word v{0} ({1})").format(version_row.version_documento, version_row.estado_documento)
            if version_row
            else None
        )


def _get_eeff_version_exchange_map(cliente_name, entregable_names, requerimiento_names):
    if not frappe.db.exists("DocType", "Version Documento EEFF"):
        return {}

    filters = ["pkg.cliente = %(cliente)s", "row.tipo_documento = 'Word Revision Cliente'"]
    values = {"cliente": cliente_name}
    entregables = tuple(entregable_names or [])
    requerimientos = tuple([name for name in (requerimiento_names or []) if name])

    if entregables:
        filters.append("(row.entregable_cliente in %(entregables)s or row.requerimiento_cliente in %(requerimientos)s)")
        values["entregables"] = entregables
        values["requerimientos"] = requerimientos or ("",)
    elif requerimientos:
        filters.append("row.requerimiento_cliente in %(requerimientos)s")
        values["requerimientos"] = requerimientos
    else:
        return {}

    rows = frappe.db.sql(
        f"""
        SELECT
            row.name,
            row.requerimiento_cliente,
            row.entregable_cliente,
            row.version_documento,
            row.estado_documento
        FROM `tabVersion Documento EEFF` row
        INNER JOIN `tabPaquete Estados Financieros Cliente` pkg
            ON pkg.name = row.parent
        WHERE {' AND '.join(filters)}
          AND row.estado_documento in ('Generado', 'Enviado a Cliente', 'Comentado por Cliente')
        ORDER BY row.modified DESC, row.version_documento DESC
        """,
        values,
        as_dict=True,
    )

    version_map = {}
    for row in rows:
        entregable_key = ("entregable", row.entregable_cliente) if row.entregable_cliente else None
        requerimiento_key = ("requerimiento", row.requerimiento_cliente) if row.requerimiento_cliente else None
        for key in (entregable_key, requerimiento_key):
            if key and key not in version_map:
                version_map[key] = row
    return version_map


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


@frappe.whitelist()
def subir_entregable_portal(entregable_name, titulo_documento=None, tipo_documental=None, observaciones=None, version_documento_name=None):
    uploaded_file = frappe.request.files.get("archivo") if getattr(frappe.request, "files", None) else None
    if not uploaded_file:
        frappe.throw(_("Debes adjuntar un archivo para cargar el entregable."), title=_("Archivo Requerido"))
    file_name = getattr(uploaded_file, "filename", None) or "entregable-portal"
    content = uploaded_file.stream.read() if hasattr(uploaded_file, "stream") else uploaded_file.read()
    return registrar_carga_entregable_portal(
        entregable_name,
        file_name=file_name,
        content=content,
        titulo_documento=titulo_documento,
        tipo_documental=tipo_documental,
        observaciones=observaciones,
        version_documento_name=version_documento_name,
    )


def registrar_carga_entregable_portal(
    entregable_name,
    *,
    file_name,
    content,
    titulo_documento=None,
    tipo_documental=None,
    observaciones=None,
    version_documento_name=None,
):
    cliente = require_portal_cliente()
    if not cliente.permite_carga_documentos:
        frappe.throw(_("La carga documental por portal no esta habilitada para este cliente."), frappe.PermissionError)

    entregable = frappe.get_doc("Entregable Cliente", entregable_name)
    if entregable.cliente != cliente.name:
        frappe.throw(_("El entregable indicado no pertenece a tu cliente portal."), frappe.PermissionError)
    if entregable.estado_entregable in PORTAL_ENTREGABLE_TERMINAL_STATES:
        frappe.throw(_("El entregable seleccionado ya no admite cargas desde portal."), title=_("Entregable Cerrado"))
    if entregable.estado_entregable not in PORTAL_ENTREGABLE_UPLOAD_STATES:
        frappe.throw(_("El estado actual del entregable no admite una nueva carga documental."), title=_("Estado No Permitido"))
    if not content:
        frappe.throw(_("El archivo adjunto esta vacio."), title=_("Archivo Invalido"))

    _unlink_rejected_entregable_document(entregable)

    from frappe.utils.file_manager import save_file

    file_doc = save_file(file_name, content, "Entregable Cliente", entregable.name, is_private=1)
    documento = _create_portal_document(
        entregable=entregable,
        file_doc=file_doc,
        titulo_documento=titulo_documento,
        tipo_documental=tipo_documental,
        observaciones=observaciones,
    )
    _reattach_file_to_document(file_doc.name, documento.name)

    version_row = _sync_portal_version_exchange(
        entregable=entregable,
        documento=documento,
        version_documento_name=version_documento_name,
    )

    log_linked_communication(
        "Requerimiento Cliente",
        entregable.requerimiento_cliente,
        subject=_("Carga recibida en portal para {0}").format(entregable.name),
        content=_(
            "El cliente cargo el documento <b>{0}</b> para el entregable <b>{1}</b>. Documento generado: <b>{2}</b>."
        ).format(file_doc.file_name, entregable.name, documento.name),
        sender=frappe.session.user,
        sender_full_name=frappe.utils.get_fullname(frappe.session.user),
        communication_medium="Portal",
    )

    return {
        "ok": True,
        "entregable": entregable.name,
        "documento_contable": documento.name,
        "file_url": file_doc.file_url,
        "version_documento_eeff": version_row.name if version_row else None,
    }


def _unlink_rejected_entregable_document(entregable):
    if entregable.estado_entregable != "Rechazado" or not entregable.documento_contable:
        return
    documento = frappe.get_doc("Documento Contable", entregable.documento_contable)
    documento.entregable_cliente = None
    documento.flags.ignore_governance_validation = True
    documento.save(ignore_permissions=True)


def _create_portal_document(*, entregable, file_doc, titulo_documento=None, tipo_documental=None, observaciones=None):
    titulo = (titulo_documento or "").strip() or _build_portal_document_title(entregable)
    tipo = (tipo_documental or "").strip() or "Otro"

    documento = frappe.get_doc(
        {
            "doctype": "Documento Contable",
            "titulo_del_documento": titulo,
            "cliente": entregable.cliente,
            "company": entregable.company,
            "periodo": entregable.periodo,
            "encargo_contable": entregable.encargo_contable,
            "entregable_cliente": entregable.name,
            "tipo": tipo,
            "archivo_adjunto": file_doc.file_url,
            "preparado_por": frappe.session.user,
            "evidencias_documentales": [
                {
                    "descripcion_evidencia": observaciones or titulo,
                    "tipo_documental": tipo,
                    "origen_documental": "Cliente",
                    "numero_version": 1,
                    "es_version_vigente": 1,
                    "es_principal": 1,
                    "archivo": file_doc.file_url,
                    "observaciones": observaciones,
                }
            ],
        }
    )
    documento.flags.ignore_governance_validation = True
    documento.insert(ignore_permissions=True)
    return documento


def _build_portal_document_title(entregable):
    timestamp = now_datetime().strftime("%Y%m%d %H%M%S")
    base = entregable.tipo_entregable or entregable.name
    return f"Portal - {base} - {timestamp}"


def _reattach_file_to_document(file_name, documento_name):
    if not frappe.db.exists("File", file_name):
        return
    file_doc = frappe.get_doc("File", file_name)
    file_doc.attached_to_doctype = "Documento Contable"
    file_doc.attached_to_name = documento_name
    file_doc.save(ignore_permissions=True)


def _sync_portal_version_exchange(*, entregable, documento, version_documento_name=None):
    if not frappe.db.exists("DocType", "Paquete Estados Financieros Cliente"):
        return None

    from gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente import (
        sincronizar_version_documento_eeff_con_intercambio_cliente,
    )

    return sincronizar_version_documento_eeff_con_intercambio_cliente(
        cliente=entregable.cliente,
        requerimiento_cliente=entregable.requerimiento_cliente,
        entregable_cliente=entregable.name,
        documento_revision_cliente=documento.name,
        version_documento_name=version_documento_name,
        nuevo_estado="Comentado por Cliente",
    )
