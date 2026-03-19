import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from gestion_contable.gestion_contable.utils.security import has_any_role

PAGE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Auxiliar Contable del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
ESTADOS_CERRADOS = ("Cerrada", "Archivada", "Cancelada")


def _ensure_page_access():
    if has_any_role(PAGE_ROLES):
        return
    frappe.throw(_("No tienes permisos para ver el seguimiento de auditoria."), frappe.PermissionError)


@frappe.whitelist()
def get_audit_dashboard(cliente=None, estado=None, search=None):
    _ensure_page_access()

    filters = {}
    if cliente:
        filters["cliente"] = cliente
    if estado:
        filters["estado_expediente"] = estado

    expedientes = frappe.get_all(
        "Expediente Auditoria",
        filters=filters,
        fields=[
            "name",
            "cliente",
            "periodo",
            "encargo_contable",
            "estado_expediente",
            "estado_aprobacion",
            "supervisor_a_cargo",
            "socio_a_cargo",
            "fecha_inicio_planeada",
            "fecha_fin_planeada",
            "fecha_envio_revision_tecnica",
            "resultado_revision_tecnica",
            "total_riesgos",
            "riesgos_altos",
            "total_papeles",
            "papeles_pendientes_revision",
            "papeles_aprobados",
            "total_hallazgos",
            "hallazgos_abiertos",
            "hallazgos_cerrados",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=500,
    )

    search = (search or "").strip().lower()
    today = getdate(nowdate())
    data = []

    for row in expedientes:
        cliente_label = _get_cliente_label(row.cliente)
        overdue = bool(
            row.fecha_fin_planeada
            and getdate(row.fecha_fin_planeada) < today
            and row.estado_expediente not in ESTADOS_CERRADOS
        )

        alertas = []
        if overdue:
            alertas.append("Vencido")
        if (row.hallazgos_abiertos or 0) > 0:
            alertas.append(f"Hallazgos abiertos: {row.hallazgos_abiertos}")
        if (row.papeles_pendientes_revision or 0) > 0:
            alertas.append(f"Papeles pendientes: {row.papeles_pendientes_revision}")
        if row.resultado_revision_tecnica == "Observado":
            alertas.append("Revision tecnica observada")
        if (row.riesgos_altos or 0) > 0:
            alertas.append(f"Riesgos altos: {row.riesgos_altos}")

        item = {
            "name": row.name,
            "cliente": row.cliente,
            "cliente_label": cliente_label,
            "periodo": row.periodo,
            "encargo_contable": row.encargo_contable,
            "estado_expediente": row.estado_expediente,
            "estado_aprobacion": row.estado_aprobacion,
            "supervisor_a_cargo": row.supervisor_a_cargo,
            "socio_a_cargo": row.socio_a_cargo,
            "fecha_inicio_planeada": row.fecha_inicio_planeada,
            "fecha_fin_planeada": row.fecha_fin_planeada,
            "fecha_envio_revision_tecnica": row.fecha_envio_revision_tecnica,
            "resultado_revision_tecnica": row.resultado_revision_tecnica,
            "total_riesgos": row.total_riesgos or 0,
            "riesgos_altos": row.riesgos_altos or 0,
            "total_papeles": row.total_papeles or 0,
            "papeles_pendientes_revision": row.papeles_pendientes_revision or 0,
            "papeles_aprobados": row.papeles_aprobados or 0,
            "total_hallazgos": row.total_hallazgos or 0,
            "hallazgos_abiertos": row.hallazgos_abiertos or 0,
            "hallazgos_cerrados": row.hallazgos_cerrados or 0,
            "overdue": overdue,
            "alertas": alertas,
        }

        if search and not _matches_search(item, search):
            continue
        data.append(item)

    resumen = _build_summary(data)
    return {"summary": resumen, "rows": data}


@frappe.whitelist()
def get_audit_clients():
    _ensure_page_access()
    clientes = frappe.get_all(
        "Expediente Auditoria",
        fields=["cliente"],
        order_by="cliente asc",
        limit_page_length=500,
    )
    unique = []
    seen = set()
    for row in clientes:
        if not row.cliente or row.cliente in seen:
            continue
        seen.add(row.cliente)
        unique.append({"value": row.cliente, "label": _get_cliente_label(row.cliente)})
    return unique


def _build_summary(rows):
    return {
        "total": len(rows),
        "planeacion": sum(1 for row in rows if row["estado_expediente"] == "Planeacion"),
        "ejecucion": sum(1 for row in rows if row["estado_expediente"] == "Ejecucion"),
        "revision_tecnica": sum(1 for row in rows if row["estado_expediente"] == "Revision Tecnica"),
        "cerrados": sum(1 for row in rows if row["estado_expediente"] == "Cerrada"),
        "vencidos": sum(1 for row in rows if row["overdue"]),
        "hallazgos_abiertos": sum(row["hallazgos_abiertos"] for row in rows),
        "papeles_pendientes": sum(row["papeles_pendientes_revision"] for row in rows),
        "riesgos_altos": sum(row["riesgos_altos"] for row in rows),
    }


def _matches_search(item, search):
    values = [
        item.get("name"),
        item.get("cliente_label"),
        item.get("cliente"),
        item.get("encargo_contable"),
        item.get("periodo"),
        item.get("supervisor_a_cargo"),
        item.get("socio_a_cargo"),
        item.get("estado_expediente"),
        item.get("resultado_revision_tecnica"),
    ]
    haystack = " ".join(str(value or "") for value in values).lower()
    return search in haystack


def _get_cliente_label(cliente):
    if not cliente:
        return ""
    customer_name = frappe.db.get_value("Customer", cliente, "customer_name") if frappe.db.exists("Customer", cliente) else None
    return customer_name or cliente
