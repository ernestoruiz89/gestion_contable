import frappe
from frappe.utils import cint, flt

from gestion_contable.gestion_contable.services.encargos.common import calcular_porcentaje
from gestion_contable.gestion_contable.utils.finance import build_invoice_summary, get_related_sales_invoices

FINANCIAL_SNAPSHOT_FIELDS = (
    "facturas_emitidas",
    "facturas_abiertas",
    "facturas_vencidas",
    "ingreso_facturado",
    "cobrado_total",
    "saldo_por_cobrar",
    "cartera_vencida",
    "aging_current",
    "aging_0_30",
    "aging_31_60",
    "aging_61_90",
    "aging_91_plus",
    "costo_interno_total",
    "wip_monto",
    "margen_ejecutado",
    "margen_ejecutado_pct",
    "margen_facturado",
    "margen_facturado_pct",
    "margen_cobrado",
    "margen_cobrado_pct",
    "ultima_gestion_cobranza",
    "proxima_gestion_cobranza",
)
OPERATIONAL_SNAPSHOT_FIELDS = (
    "horas_registradas",
    "horas_facturables",
    "monto_horas_pendientes",
    "monto_total_pendiente",
    "presupuesto_horas",
    "presupuesto_monto",
    "hitos_totales",
    "hitos_completados",
    "hitos_vencidos",
    "avance_hitos_pct",
    "consumo_horas_pct",
    "desviacion_horas",
    "desviacion_horas_pct",
    "monto_real_ejecutado",
    "consumo_monto_pct",
    "desviacion_monto",
    "desviacion_monto_pct",
)
COBRANZA_SNAPSHOT_FIELDS = (
    "ultima_gestion_cobranza",
    "proxima_gestion_cobranza",
)
FULL_SNAPSHOT_FIELDS = tuple(dict.fromkeys(OPERATIONAL_SNAPSHOT_FIELDS + FINANCIAL_SNAPSHOT_FIELDS))


def obtener_facturas_relacionadas(doc, include_draft=False):
    encargo_name = doc.name if getattr(doc, "name", None) and not doc.is_new() else None
    return get_related_sales_invoices(encargo_name=encargo_name, project=doc.project, include_draft=include_draft)


def actualizar_indicadores_financieros(doc):
    resumen = build_invoice_summary(obtener_facturas_relacionadas(doc, include_draft=False))
    doc.facturas_emitidas = cint(resumen.get("facturas_emitidas"))
    doc.facturas_abiertas = cint(resumen.get("facturas_abiertas"))
    doc.facturas_vencidas = cint(resumen.get("facturas_vencidas"))
    doc.ingreso_facturado = flt(resumen.get("ingreso_facturado"))
    doc.cobrado_total = flt(resumen.get("cobrado_total"))
    doc.saldo_por_cobrar = flt(resumen.get("saldo_por_cobrar"))
    doc.cartera_vencida = flt(resumen.get("cartera_vencida"))
    doc.aging_current = flt(resumen.get("aging_current"))
    doc.aging_0_30 = flt(resumen.get("aging_0_30"))
    doc.aging_31_60 = flt(resumen.get("aging_31_60"))
    doc.aging_61_90 = flt(resumen.get("aging_61_90"))
    doc.aging_91_plus = flt(resumen.get("aging_91_plus"))
    doc.costo_interno_total = flt(doc.horas_registradas) * flt(doc.costo_interno_hora)
    doc.wip_monto = max(flt(doc.monto_real_ejecutado) - flt(doc.ingreso_facturado), 0)
    doc.margen_ejecutado = flt(doc.monto_real_ejecutado) - flt(doc.costo_interno_total)
    doc.margen_ejecutado_pct = calcular_porcentaje(doc.margen_ejecutado, doc.monto_real_ejecutado)
    doc.margen_facturado = flt(doc.ingreso_facturado) - flt(doc.costo_interno_total)
    doc.margen_facturado_pct = calcular_porcentaje(doc.margen_facturado, doc.ingreso_facturado)
    doc.margen_cobrado = flt(doc.cobrado_total) - flt(doc.costo_interno_total)
    doc.margen_cobrado_pct = calcular_porcentaje(doc.margen_cobrado, doc.cobrado_total)
    actualizar_resumen_cobranza(doc)


def actualizar_resumen_cobranza(doc):
    doc.ultima_gestion_cobranza = None
    doc.proxima_gestion_cobranza = None
    if not getattr(doc, "name", None) or not frappe.db.exists("DocType", "Seguimiento Cobranza"):
        return

    ultima = frappe.get_all(
        "Seguimiento Cobranza",
        filters={"encargo_contable": doc.name},
        fields=["fecha_gestion"],
        order_by="fecha_gestion desc, modified desc",
        limit_page_length=1,
    )
    if ultima:
        doc.ultima_gestion_cobranza = ultima[0].fecha_gestion

    proxima = frappe.get_all(
        "Seguimiento Cobranza",
        filters={
            "encargo_contable": doc.name,
            "estado_seguimiento": ["not in", ["Pagado", "Cerrado"]],
            "proxima_gestion": ["is", "set"],
        },
        fields=["proxima_gestion"],
        order_by="proxima_gestion asc, modified asc",
        limit_page_length=1,
    )
    if proxima:
        doc.proxima_gestion_cobranza = proxima[0].proxima_gestion


def persist_snapshot_fields(doc, fieldnames, update_modified=True):
    if not getattr(doc, "name", None):
        return {}
    values = {fieldname: doc.get(fieldname) for fieldname in fieldnames if doc.meta.has_field(fieldname)}
    if values:
        frappe.db.set_value(doc.doctype, doc.name, values, update_modified=update_modified)
    return values


def refresh_financial_snapshot(encargo_name, update_modified=True):
    doc = frappe.get_doc("Encargo Contable", encargo_name)
    doc.actualizar_indicadores_financieros()
    persist_snapshot_fields(doc, FINANCIAL_SNAPSHOT_FIELDS, update_modified=update_modified)
    return doc


def refresh_cobranza_snapshot(encargo_name, update_modified=True):
    doc = frappe.get_doc("Encargo Contable", encargo_name)
    doc.actualizar_resumen_cobranza()
    persist_snapshot_fields(doc, COBRANZA_SNAPSHOT_FIELDS, update_modified=update_modified)
    return doc


def refresh_full_snapshot(encargo_name, update_modified=True):
    doc = frappe.get_doc("Encargo Contable", encargo_name)
    doc.actualizar_horas_registradas()
    doc.actualizar_resumen_honorarios()
    doc.actualizar_indicadores_planeacion()
    doc.actualizar_indicadores_financieros()
    persist_snapshot_fields(doc, FULL_SNAPSHOT_FIELDS, update_modified=update_modified)
    return doc


def recalcular_documento(doc, save=False):
    doc.actualizar_horas_registradas()
    doc.actualizar_resumen_honorarios()
    doc.actualizar_indicadores_planeacion()
    doc.actualizar_indicadores_financieros()
    if save:
        doc.save(ignore_permissions=True)
    return doc


def recalcular_encargo(encargo_name):
    encargo = frappe.get_doc("Encargo Contable", encargo_name)
    return recalcular_documento(encargo, save=True)


def rebuild_all_snapshots(update_modified=False, encargo_names=None):
    encargo_names = encargo_names or frappe.get_all("Encargo Contable", fields=["name"], order_by="name asc")
    if encargo_names and isinstance(encargo_names[0], dict):
        encargo_names = [row["name"] for row in encargo_names]
    processed = []
    for encargo_name in encargo_names or []:
        refresh_full_snapshot(encargo_name, update_modified=update_modified)
        processed.append(encargo_name)
    return processed


def construir_resumen_encargo(encargo):
    return {
        "encargo": encargo.name,
        "presupuesto_horas": encargo.presupuesto_horas,
        "presupuesto_monto": encargo.presupuesto_monto,
        "horas_registradas": encargo.horas_registradas,
        "monto_real_ejecutado": encargo.monto_real_ejecutado,
        "desviacion_horas": encargo.desviacion_horas,
        "desviacion_monto": encargo.desviacion_monto,
        "avance_hitos_pct": encargo.avance_hitos_pct,
        "hitos_totales": encargo.hitos_totales,
        "hitos_completados": encargo.hitos_completados,
        "costo_interno_total": encargo.costo_interno_total,
        "wip_monto": encargo.wip_monto,
        "ingreso_facturado": encargo.ingreso_facturado,
        "cobrado_total": encargo.cobrado_total,
        "saldo_por_cobrar": encargo.saldo_por_cobrar,
        "cartera_vencida": encargo.cartera_vencida,
        "margen_facturado": encargo.margen_facturado,
        "margen_cobrado": encargo.margen_cobrado,
    }
