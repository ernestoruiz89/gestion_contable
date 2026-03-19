import frappe
from frappe import _
from frappe.utils import add_to_date, getdate, nowdate

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults

RETENTION_POLICY_YEARS = {
    "Operacion": 2,
    "Fiscal": 5,
    "Auditoria": 7,
    "Legal": 10,
}
RETENTION_ALERT_WINDOW_DAYS = 30


def get_retention_reference_date(periodo_name=None):
    if periodo_name and frappe.db.exists("Periodo Contable", periodo_name):
        fecha_fin = frappe.db.get_value("Periodo Contable", periodo_name, "fecha_de_fin")
        if fecha_fin:
            return getdate(fecha_fin)
    return getdate(nowdate())


def calculate_retention_deadline(policy, *, periodo_name=None, reference_date=None):
    policy = (policy or "").strip()
    if not policy or policy in ("Sin Definir", "Permanente"):
        return None

    years = RETENTION_POLICY_YEARS.get(policy)
    if not years:
        return None

    anchor = getdate(reference_date) if reference_date else get_retention_reference_date(periodo_name)
    return add_to_date(anchor, years=years, as_string=True)


def get_document_retention_defaults(cliente_name=None):
    defaults = get_cliente_defaults(cliente_name) if cliente_name else frappe._dict()
    return frappe._dict(
        politica_retencion=(defaults.politica_retencion_documental if defaults else None) or "Sin Definir",
        confidencialidad=(defaults.clasificacion_confidencialidad_default if defaults else None) or "Confidencial",
    )


def validate_document_retention_for_delete(documento):
    blocked_rows = []
    today = getdate(nowdate())
    for row in documento.get("evidencias_documentales") or []:
        if (row.politica_retencion or "").strip() == "Permanente":
            blocked_rows.append(row.descripcion_evidencia or row.codigo_documental or row.name)
            continue
        if row.conservar_hasta and getdate(row.conservar_hasta) >= today:
            blocked_rows.append(row.descripcion_evidencia or row.codigo_documental or row.name)

    if not blocked_rows:
        return

    frappe.throw(
        _("No puedes eliminar el documento mientras existan evidencias bajo retencion activa o permanente: <b>{0}</b>.").format(
            ", ".join(blocked_rows)
        ),
        title=_("Retencion Activa"),
    )


def sync_retention_alerts():
    if not frappe.db.exists("DocType", "ToDo"):
        return

    today = getdate(nowdate())
    limit_date = add_to_date(today, days=RETENTION_ALERT_WINDOW_DAYS, as_string=True)
    rows = frappe.db.sql(
        """
        SELECT
            ev.name,
            ev.parent,
            ev.descripcion_evidencia,
            ev.codigo_documental,
            ev.conservar_hasta,
            ev.politica_retencion,
            doc.cliente,
            doc.preparado_por
        FROM `tabEvidencia Documental` ev
        INNER JOIN `tabDocumento Contable` doc ON doc.name = ev.parent
        WHERE ev.parenttype = 'Documento Contable'
          AND IFNULL(ev.politica_retencion, '') NOT IN ('', 'Sin Definir')
          AND ev.politica_retencion != 'Permanente'
          AND ev.conservar_hasta IS NOT NULL
          AND ev.conservar_hasta <= %(limit_date)s
        """,
        {"limit_date": limit_date},
        as_dict=True,
    )

    for row in rows:
        _create_retention_todo(row, today)


def _create_retention_todo(row, today):
    evidence_marker = f"[RET:{row.name}]"
    existing = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "Documento Contable",
            "reference_name": row.parent,
            "description": ["like", f"%{evidence_marker}%"],
        },
        fields=["name", "status"],
        limit_page_length=1,
    )
    if existing and existing[0].status != "Cancelled":
        return

    due_date = getdate(row.conservar_hasta)
    estado = _("vencida") if due_date < today else _("proxima a vencer")
    descripcion = _(
        "Revision de retencion {0}: evidencia <b>{1}</b> ({2}) del documento <b>{3}</b> con fecha de conservacion <b>{4}</b>. {5}"
    ).format(
        estado,
        row.descripcion_evidencia or row.codigo_documental or row.name,
        row.politica_retencion,
        row.parent,
        row.conservar_hasta,
        evidence_marker,
    )

    owner = _resolve_retention_owner(row)
    todo = frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": owner,
            "reference_type": "Documento Contable",
            "reference_name": row.parent,
            "description": descripcion,
            "date": row.conservar_hasta,
            "status": "Open",
        }
    )
    todo.insert(ignore_permissions=True)


def _resolve_retention_owner(row):
    if row.preparado_por and frappe.db.exists("User", row.preparado_por):
        return row.preparado_por

    defaults = get_cliente_defaults(row.cliente) if row.cliente else frappe._dict()
    for candidate in (
        defaults.responsable_operativo_default if defaults else None,
        defaults.responsable_cobranza_interno if defaults else None,
        "Administrator",
    ):
        if candidate and frappe.db.exists("User", candidate):
            return candidate
    return "Administrator"
