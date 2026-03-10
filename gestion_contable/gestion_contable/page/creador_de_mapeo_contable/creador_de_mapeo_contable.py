import frappe
from frappe import _
from frappe.utils import cint, cstr

from gestion_contable.gestion_contable.utils.security import has_any_role

PAGE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
EDITABLE_FIELDS = (
    "cliente",
    "company",
    "marco_contable",
    "tipo_paquete",
    "version",
    "activo",
    "es_vigente",
    "descripcion",
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
    frappe.throw(_("No tienes permisos para usar el creador de mapeo contable."), frappe.PermissionError)


@frappe.whitelist()
def get_mapping_editor_bootstrap(esquema_name=None, cliente=None):
    _ensure_page_access()

    esquema_doc = None
    if esquema_name:
        if not frappe.db.exists("Esquema Mapeo Contable", esquema_name):
            frappe.throw(_("El esquema indicado no existe."), title=_("Esquema Invalido"))
        esquema_doc = frappe.get_doc("Esquema Mapeo Contable", esquema_name)
        cliente = esquema_doc.cliente

    return {
        "cliente": cliente,
        "esquema_name": esquema_doc.name if esquema_doc else None,
        "clients": _get_clients(),
        "schemes": _get_schemes(cliente) if cliente else [],
        "scheme": _serialize_scheme(esquema_doc) if esquema_doc else None,
        "catalogs": _get_catalogs(),
    }


@frappe.whitelist()
def create_scheme_for_editor(cliente, nombre_esquema=None, company=None, marco_contable=None, tipo_paquete=None, descripcion=None):
    _ensure_page_access()
    cliente = cstr(cliente).strip()
    if not cliente or not frappe.db.exists("Cliente Contable", cliente):
        frappe.throw(_("Debes seleccionar un cliente valido."), title=_("Cliente Invalido"))

    marco_contable = cstr(marco_contable).strip() or "NIIF para PYMES"
    tipo_paquete = cstr(tipo_paquete).strip() or "Preliminar"

    payload = {
        "doctype": "Esquema Mapeo Contable",
        "cliente": cliente,
        "company": company,
        "marco_contable": marco_contable,
        "tipo_paquete": tipo_paquete,
        "version": _get_next_version(cliente, company, marco_contable, tipo_paquete),
        "activo": 1,
        "es_vigente": 0,
        "descripcion": descripcion,
    }
    if cstr(nombre_esquema).strip():
        payload["nombre_esquema"] = cstr(nombre_esquema).strip()

    doc = frappe.get_doc(payload)
    doc.insert()
    doc.reload()

    return {
        "cliente": doc.cliente,
        "esquema_name": doc.name,
        "clients": _get_clients(),
        "schemes": _get_schemes(doc.cliente),
        "scheme": _serialize_scheme(doc),
        "catalogs": _get_catalogs(),
    }


@frappe.whitelist()
def save_mapping_scheme_editor(esquema_payload):
    _ensure_page_access()
    payload = frappe.parse_json(esquema_payload) if isinstance(esquema_payload, str) else esquema_payload
    if not payload:
        frappe.throw(_("No se recibieron datos del esquema."), title=_("Datos Requeridos"))

    esquema_name = payload.get("name")
    if not esquema_name or not frappe.db.exists("Esquema Mapeo Contable", esquema_name):
        frappe.throw(_("El esquema indicado no existe."), title=_("Esquema Invalido"))

    doc = frappe.get_doc("Esquema Mapeo Contable", esquema_name)
    _apply_scheme_payload(doc, payload)
    doc.save()
    doc.reload()

    return {
        "cliente": doc.cliente,
        "esquema_name": doc.name,
        "clients": _get_clients(),
        "schemes": _get_schemes(doc.cliente),
        "scheme": _serialize_scheme(doc),
        "catalogs": _get_catalogs(),
    }


def _get_clients():
    rows = frappe.get_all(
        "Cliente Contable",
        fields=["name", "customer"],
        order_by="modified desc",
        limit_page_length=500,
    )
    return [
        {
            "value": row.name,
            "label": f"{row.name} | {row.customer}" if row.customer else row.name,
        }
        for row in rows
        if row.name
    ]


def _get_schemes(cliente=None):
    if not cliente:
        return []
    rows = frappe.get_all(
        "Esquema Mapeo Contable",
        filters={"cliente": cliente},
        fields=["name", "marco_contable", "tipo_paquete", "version", "activo", "es_vigente", "modified"],
        order_by="es_vigente desc, activo desc, modified desc",
        limit_page_length=500,
    )
    return [
        {
            "value": row.name,
            "label": _build_scheme_label(row),
            "marco_contable": row.marco_contable,
            "tipo_paquete": row.tipo_paquete,
            "version": row.version,
            "activo": row.activo,
            "es_vigente": row.es_vigente,
        }
        for row in rows
    ]


def _build_scheme_label(row):
    tags = []
    if cint(row.es_vigente):
        tags.append(_("Vigente"))
    if not cint(row.activo):
        tags.append(_("Inactivo"))
    suffix = f" [{', '.join(tags)}]" if tags else ""
    return f"{row.name} | {row.marco_contable or _('Sin marco')} | {row.tipo_paquete or _('Sin tipo')} | V{cint(row.version or 1)}{suffix}"


def _serialize_scheme(doc):
    if not doc:
        return None

    data = {field: doc.get(field) for field in EDITABLE_FIELDS}
    data.update(
        {
            "doctype": doc.doctype,
            "name": doc.name,
            "nombre_esquema": doc.nombre_esquema or doc.name,
            "reglas": [
                _serialize_child_row(row)
                for row in sorted(doc.reglas or [], key=lambda item: (cint(item.orden_ejecucion or 0), cint(item.idx or 0)))
            ],
        }
    )
    return {"doc": data}


def _serialize_child_row(row):
    data = row.as_dict(no_nulls=False) if hasattr(row, "as_dict") else dict(row)
    return {key: value for key, value in data.items() if key not in CHILD_META_FIELDS}


def _apply_scheme_payload(doc, payload):
    for fieldname in EDITABLE_FIELDS:
        if fieldname in payload:
            doc.set(fieldname, payload.get(fieldname))

    doc.set("reglas", [])
    for idx, row in enumerate(payload.get("reglas") or [], start=1):
        sanitized = {
            key: value
            for key, value in row.items()
            if key not in CHILD_META_FIELDS and not cstr(key).startswith("__")
        }
        sanitized["orden_ejecucion"] = cint(sanitized.get("orden_ejecucion") or idx)
        doc.append("reglas", sanitized)


def _get_select_options(doctype, fieldname):
    meta = frappe.get_meta(doctype)
    df = meta.get_field(fieldname)
    options = cstr(df.options or "") if df else ""
    return [row.strip() for row in options.split("\n") if row.strip()]


def _get_catalogs():
    return {
        "marcos_contables": _get_select_options("Esquema Mapeo Contable", "marco_contable"),
        "tipos_paquete": _get_select_options("Esquema Mapeo Contable", "tipo_paquete"),
        "destino_tipos": _get_select_options("Regla Mapeo Contable", "destino_tipo"),
        "origen_versiones": _get_select_options("Regla Mapeo Contable", "origen_version"),
        "selector_tipos": _get_select_options("Regla Mapeo Contable", "selector_tipo"),
        "operaciones_agregacion": _get_select_options("Regla Mapeo Contable", "operacion_agregacion"),
        "signos_presentacion": _get_select_options("Regla Mapeo Contable", "signo_presentacion"),
        "tipos_estado": _get_select_options("Regla Mapeo Contable", "destino_tipo_estado"),
    }


def _get_next_version(cliente, company, marco_contable, tipo_paquete):
    rows = frappe.get_all(
        "Esquema Mapeo Contable",
        filters={
            "cliente": cliente,
            "company": company,
            "marco_contable": marco_contable,
            "tipo_paquete": tipo_paquete,
        },
        fields=["version"],
        order_by="version desc",
        limit_page_length=1,
    )
    if not rows:
        return 1
    return cint(rows[0].version or 0) + 1
