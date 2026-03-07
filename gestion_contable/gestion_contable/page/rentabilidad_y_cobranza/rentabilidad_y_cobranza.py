import frappe
from frappe import _
from frappe.utils import flt

from gestion_contable.gestion_contable.utils.security import has_any_role

PAGE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)


def _ensure_page_access():
    if has_any_role(PAGE_ROLES):
        return
    frappe.throw(_("No tienes permisos para ver la rentabilidad y cobranza."), frappe.PermissionError)


@frappe.whitelist()
def get_dashboard(cliente=None, servicio_contable=None, estado=None, tipo_de_servicio=None, solo_vencidos=0, search=None):
    _ensure_page_access()
    filters = {}
    if cliente:
        filters["cliente"] = cliente
    if servicio_contable:
        filters["servicio_contable"] = servicio_contable
    if estado:
        filters["estado"] = estado
    if tipo_de_servicio:
        filters["tipo_de_servicio"] = tipo_de_servicio

    encargos = frappe.get_all(
        "Encargo Contable",
        filters=filters,
        fields=[
            "name", "cliente", "servicio_contable", "tipo_de_servicio", "estado", "estado_aprobacion", "responsable", "moneda",
            "horas_registradas", "costo_interno_total", "monto_real_ejecutado", "hitos_vencidos", "avance_hitos_pct",
            "ingreso_facturado", "cobrado_total", "saldo_por_cobrar", "wip_monto", "margen_facturado", "margen_cobrado",
            "facturas_emitidas", "facturas_abiertas", "facturas_vencidas", "cartera_vencida",
            "aging_current", "aging_0_30", "aging_31_60", "aging_61_90", "aging_91_plus",
            "ultima_gestion_cobranza", "proxima_gestion_cobranza",
        ],
        order_by="modified desc",
        limit_page_length=500,
    )

    cliente_map = _get_cliente_map({row.cliente for row in encargos if row.cliente})
    search = (search or "").strip().lower()
    rows = []

    for row in encargos:
        item = {
            "name": row.name,
            "cliente": row.cliente,
            "cliente_label": cliente_map.get(row.cliente, row.cliente or ""),
            "servicio_contable": row.servicio_contable,
            "tipo_de_servicio": row.tipo_de_servicio,
            "estado": row.estado,
            "estado_aprobacion": row.estado_aprobacion,
            "responsable": row.responsable,
            "moneda": row.moneda,
            "horas_registradas": flt(row.horas_registradas),
            "costo_interno_total": flt(row.costo_interno_total),
            "monto_real_ejecutado": flt(row.monto_real_ejecutado),
            "ingreso_facturado": flt(row.ingreso_facturado),
            "cobrado_total": flt(row.cobrado_total),
            "saldo_por_cobrar": flt(row.saldo_por_cobrar),
            "wip_monto": flt(row.wip_monto),
            "margen_facturado": flt(row.margen_facturado),
            "margen_cobrado": flt(row.margen_cobrado),
            "facturas_emitidas": row.facturas_emitidas or 0,
            "facturas_abiertas": row.facturas_abiertas or 0,
            "facturas_vencidas": row.facturas_vencidas or 0,
            "cartera_vencida": flt(row.cartera_vencida),
            "aging_current": flt(row.aging_current),
            "aging_0_30": flt(row.aging_0_30),
            "aging_31_60": flt(row.aging_31_60),
            "aging_61_90": flt(row.aging_61_90),
            "aging_91_plus": flt(row.aging_91_plus),
            "hitos_vencidos": row.hitos_vencidos or 0,
            "avance_hitos_pct": flt(row.avance_hitos_pct),
            "ultima_gestion_cobranza": row.ultima_gestion_cobranza,
            "proxima_gestion_cobranza": row.proxima_gestion_cobranza,
        }
        item["alertas"] = _build_alerts(item)
        if solo_vencidos and item["cartera_vencida"] <= 0:
            continue
        if search and not _matches_search(item, search):
            continue
        rows.append(item)

    return {
        "summary": _build_summary(rows),
        "rows": rows,
        "by_cliente": _aggregate(rows, "cliente", "cliente_label"),
        "by_servicio": _aggregate(rows, "servicio_contable", "servicio_contable"),
    }


@frappe.whitelist()
def get_filters_data():
    _ensure_page_access()
    clientes = frappe.get_all("Encargo Contable", fields=["cliente"], order_by="cliente asc", limit_page_length=500)
    servicios = frappe.get_all("Encargo Contable", fields=["servicio_contable"], order_by="servicio_contable asc", limit_page_length=500)
    cliente_map = _get_cliente_map({row.cliente for row in clientes if row.cliente})
    return {
        "clientes": [{"value": row.cliente, "label": cliente_map.get(row.cliente, row.cliente)} for row in clientes if row.cliente],
        "servicios": [{"value": row.servicio_contable, "label": row.servicio_contable} for row in servicios if row.servicio_contable],
    }


def _build_summary(rows):
    summary = {
        "encargos": len(rows), "ingreso_facturado": 0, "cobrado_total": 0, "saldo_por_cobrar": 0, "wip_monto": 0,
        "costo_interno_total": 0, "margen_facturado": 0, "cartera_vencida": 0, "aging_current": 0,
        "aging_0_30": 0, "aging_31_60": 0, "aging_61_90": 0, "aging_91_plus": 0,
    }
    for row in rows:
        for key in summary:
            if key == "encargos":
                continue
            summary[key] += flt(row.get(key))
    return summary


def _aggregate(rows, key, label_key):
    grouped = {}
    for row in rows:
        bucket_key = row.get(key) or _("Sin Definir")
        bucket = grouped.setdefault(bucket_key, {"key": bucket_key, "label": row.get(label_key) or bucket_key, "ingreso_facturado": 0, "cobrado_total": 0, "saldo_por_cobrar": 0, "margen_facturado": 0, "cartera_vencida": 0, "wip_monto": 0})
        for field in ("ingreso_facturado", "cobrado_total", "saldo_por_cobrar", "margen_facturado", "cartera_vencida", "wip_monto"):
            bucket[field] += flt(row.get(field))
    return sorted(grouped.values(), key=lambda item: item["ingreso_facturado"], reverse=True)[:20]


def _build_alerts(row):
    alerts = []
    if flt(row.get("cartera_vencida")) > 0:
        alerts.append("Cartera vencida")
    if (row.get("facturas_vencidas") or 0) > 0:
        alerts.append(f"Facturas vencidas: {row['facturas_vencidas']}")
    if (row.get("hitos_vencidos") or 0) > 0:
        alerts.append(f"Hitos vencidos: {row['hitos_vencidos']}")
    if flt(row.get("margen_facturado")) < 0:
        alerts.append("Margen negativo")
    if row.get("proxima_gestion_cobranza") and str(row.get("proxima_gestion_cobranza")) < frappe.utils.nowdate():
        alerts.append("Gestion de cobranza vencida")
    return alerts


def _matches_search(row, search):
    values = [row.get("name"), row.get("cliente_label"), row.get("cliente"), row.get("servicio_contable"), row.get("tipo_de_servicio"), row.get("estado"), row.get("responsable")]
    return search in " ".join(str(value or "") for value in values).lower()


def _get_cliente_map(clientes):
    if not clientes:
        return {}
    records = frappe.get_all("Customer", filters={"name": ["in", list(clientes)]}, fields=["name", "customer_name"], limit_page_length=len(clientes))
    return {row.name: row.customer_name or row.name for row in records}
