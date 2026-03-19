import frappe
from frappe import _

from gestion_contable.gestion_contable.utils.security import has_any_role

PAGE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
EDITABLE_FIELDS = (
    "paquete_estados_financieros_cliente",
    "numero_nota",
    "titulo",
    "categoria_nota",
    "orden_presentacion",
    "politica_contable",
    "contenido_narrativo",
    "observaciones_preparacion",
)
EDITABLE_TABLE_FIELDS = (
    "secciones_estructuradas",
    "columnas_tabulares",
    "filas_tabulares",
    "celdas_tabulares",
)
CHILD_META_FIELDS = {
    "doctype",
    "name",
    "parent",
    "parentfield",
    "parenttype",
    "idx",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "__islocal",
    "_user_tags",
    "_comments",
    "_assign",
    "_liked_by",
}


def _ensure_page_access():
    if has_any_role(PAGE_ROLES):
        return
    frappe.throw(_("No tienes permisos para usar el creador de notas de EEFF."), frappe.PermissionError)


@frappe.whitelist()
def get_editor_bootstrap(note_name=None, package_name=None, cliente=None):
    _ensure_page_access()

    note_doc = None
    if note_name:
        if not frappe.db.exists("Nota Estado Financiero", note_name):
            frappe.throw(_("La nota indicada no existe."), title=_("Nota Invalida"))
        note_doc = frappe.get_doc("Nota Estado Financiero", note_name)
        package_name = note_doc.paquete_estados_financieros_cliente
        cliente = note_doc.cliente

    if package_name and not cliente:
        cliente = frappe.db.get_value("Paquete Estados Financieros Cliente", package_name, "cliente")

    clients = _get_clients()
    packages = _get_packages(cliente) if cliente else []
    notes = _get_notes(package_name) if package_name else []

    return {
        "cliente": cliente,
        "package_name": package_name,
        "clients": clients,
        "packages": packages,
        "notes": notes,
        "note": _serialize_note(note_doc) if note_doc else None,
    }


@frappe.whitelist()
def create_note_for_editor(package_name, numero_nota, titulo=None, categoria_nota="Otra", contenido_inicial=None):
    _ensure_page_access()
    if not frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        frappe.throw(_("Debes seleccionar un paquete valido."), title=_("Paquete Invalido"))
    if not numero_nota:
        frappe.throw(_("Debes indicar el numero de nota."), title=_("Numero Requerido"))

    initial_content = (contenido_inicial or "").strip() or _(
        "Borrador inicial de la nota. Reemplaza este texto con el contenido definitivo."
    )

    doc = frappe.get_doc(
        {
            "doctype": "Nota Estado Financiero",
            "paquete_estados_financieros_cliente": package_name,
            "numero_nota": numero_nota,
            "titulo": titulo or _("Nota {0}").format(numero_nota),
            "categoria_nota": categoria_nota or "Otra",
            "contenido_narrativo": initial_content,
        }
    )
    doc.insert()
    cliente = frappe.db.get_value("Paquete Estados Financieros Cliente", package_name, "cliente")
    return {
        "cliente": cliente,
        "note": _serialize_note(doc),
        "notes": _get_notes(package_name),
        "packages": _get_packages(cliente),
        "clients": _get_clients(),
        "package_name": package_name,
    }


@frappe.whitelist()
def save_note_editor(note_payload):
    _ensure_page_access()
    payload = frappe.parse_json(note_payload) if isinstance(note_payload, str) else note_payload
    if not payload:
        frappe.throw(_("No se recibieron datos de la nota."), title=_("Datos Requeridos"))

    note_name = payload.get("name")
    if not note_name or not frappe.db.exists("Nota Estado Financiero", note_name):
        frappe.throw(_("La nota indicada no existe."), title=_("Nota Invalida"))

    doc = frappe.get_doc("Nota Estado Financiero", note_name)
    _apply_note_payload(doc, payload)
    doc.save()
    doc.reload()

    return {
        "cliente": doc.cliente,
        "note": _serialize_note(doc),
        "notes": _get_notes(doc.paquete_estados_financieros_cliente),
        "packages": _get_packages(doc.cliente),
        "clients": _get_clients(),
        "package_name": doc.paquete_estados_financieros_cliente,
    }


@frappe.whitelist()
def get_package_notes(package_name):
    _ensure_page_access()
    return _get_notes(package_name)


def _get_clients():
    rows = frappe.get_all(
        "Paquete Estados Financieros Cliente",
        fields=["cliente"],
        filters={"cliente": ["is", "set"]},
        distinct=True,
        order_by="cliente asc",
        limit_page_length=500,
    )
    return [{"value": row.cliente, "label": row.cliente} for row in rows if row.cliente]


def _get_packages(cliente=None):
    if not cliente:
        return []
    rows = frappe.get_all(
        "Paquete Estados Financieros Cliente",
        fields=["name", "cliente", "periodo_contable", "version", "estado_preparacion", "estado_aprobacion", "modified"],
        filters={"cliente": cliente},
        order_by="periodo_contable desc, modified desc",
        limit_page_length=500,
    )
    return [
        {
            "value": row.name,
            "label": _build_package_label(row),
            "cliente": row.cliente,
            "periodo_contable": row.periodo_contable,
            "version": row.version,
            "estado_preparacion": row.estado_preparacion,
            "estado_aprobacion": row.estado_aprobacion,
        }
        for row in rows
    ]


def _build_package_label(row):
    period = row.periodo_contable or _("Sin periodo")
    version = row.version or 1
    return f"{row.name} | {period} | V{version}"


def _get_notes(package_name):
    if not package_name:
        return []
    rows = frappe.get_all(
        "Nota Estado Financiero",
        filters={"paquete_estados_financieros_cliente": package_name},
        fields=["name", "numero_nota", "titulo", "categoria_nota", "orden_presentacion", "estado_aprobacion"],
        order_by="orden_presentacion asc, numero_nota asc, modified desc",
        limit_page_length=500,
    )
    return [
        {
            "name": row.name,
            "numero_nota": row.numero_nota,
            "titulo": row.titulo,
            "categoria_nota": row.categoria_nota,
            "orden_presentacion": row.orden_presentacion,
            "estado_aprobacion": row.estado_aprobacion,
            "label": f"Nota {row.numero_nota} - {row.titulo}",
        }
        for row in rows
    ]


def _serialize_note(doc):
    if not doc:
        return None

    note = {field: doc.get(field) for field in EDITABLE_FIELDS}
    note.update(
        {
            "doctype": doc.doctype,
            "name": doc.name,
            "cliente": doc.cliente,
            "periodo_contable": doc.periodo_contable,
            "nombre_de_la_nota": doc.nombre_de_la_nota,
            "es_requerida": doc.es_requerida,
            "estado_aprobacion": doc.estado_aprobacion,
            "comentarios_supervisor": doc.comentarios_supervisor,
            "comentarios_socio": doc.comentarios_socio,
            "total_referencias": doc.total_referencias,
            "referencias_cruzadas": [_serialize_child_row(row) for row in doc.referencias_cruzadas or []],
            "cifras_nota": [_serialize_child_row(row) for row in doc.cifras_nota or []],
        }
    )
    for fieldname in EDITABLE_TABLE_FIELDS:
        note[fieldname] = [_serialize_child_row(row) for row in doc.get(fieldname) or []]

    return {
        "doc": note,
    }


def _serialize_child_row(row):
    data = row.as_dict(no_nulls=False) if hasattr(row, "as_dict") else dict(row)
    return {key: value for key, value in data.items() if key not in CHILD_META_FIELDS}


def _apply_note_payload(doc, payload):
    for fieldname in EDITABLE_FIELDS:
        if fieldname in payload:
            doc.set(fieldname, payload.get(fieldname))

    for fieldname in EDITABLE_TABLE_FIELDS:
        if fieldname not in payload:
            continue
        doc.set(fieldname, [])
        for row in payload.get(fieldname) or []:
            sanitized = {key: value for key, value in row.items() if key not in CHILD_META_FIELDS}
            doc.append(fieldname, sanitized)
