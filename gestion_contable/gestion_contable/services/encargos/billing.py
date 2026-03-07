import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

from gestion_contable.gestion_contable.services.encargos import erpnext as erpnext_service
from gestion_contable.gestion_contable.services.encargos.constants import (
    ESTADOS_CERRADOS,
    MODALIDADES_FIJO,
    MODALIDADES_HORAS,
)
from gestion_contable.gestion_contable.utils.finance import create_payment_entry_for_invoice, get_open_sales_invoices
from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO


def actualizar_horas_registradas(doc):
    if not doc.project:
        doc.horas_registradas = 0
        return
    row = frappe.db.sql(
        """
        SELECT COALESCE(SUM(hours), 0) AS total_hours
        FROM `tabTimesheet Detail`
        WHERE project = %s AND parenttype = 'Timesheet'
        """,
        (doc.project,),
        as_dict=True,
    )[0]
    doc.horas_registradas = flt(row.total_hours)


def obtener_detalles_horas_pendientes(doc):
    if not doc.project:
        return []
    has_billable = frappe.db.has_column("Timesheet Detail", "is_billable")
    has_sales_invoice = frappe.db.has_column("Timesheet Detail", "sales_invoice")
    has_billing_hours = frappe.db.has_column("Timesheet Detail", "billing_hours")
    condiciones = ["td.project = %(project)s", "td.parenttype = 'Timesheet'", "ts.docstatus = 1"]
    if has_billable:
        condiciones.append("COALESCE(td.is_billable, 0) = 1")
    if has_sales_invoice:
        condiciones.append("(td.sales_invoice IS NULL OR td.sales_invoice = '')")
    horas_expr = "COALESCE(NULLIF(td.billing_hours, 0), td.hours)" if has_billing_hours else "td.hours"
    return frappe.db.sql(
        f"""
        SELECT td.name, td.parent, {horas_expr} AS horas
        FROM `tabTimesheet Detail` td
        INNER JOIN `tabTimesheet` ts ON ts.name = td.parent
        WHERE {' AND '.join(condiciones)}
        """,
        {"project": doc.project},
        as_dict=True,
    )


def calcular_horas_facturables(doc):
    detalles = obtener_detalles_horas_pendientes(doc)
    return flt(sum(flt(detalle.horas) for detalle in detalles))


def actualizar_resumen_honorarios(doc):
    horas_facturables = calcular_horas_facturables(doc)
    tarifa_hora, honorario_fijo, _ = doc.resolver_tarifas()
    monto_horas = flt(horas_facturables * tarifa_hora) if doc.modalidad_honorario in MODALIDADES_HORAS else 0
    monto_fijo = flt(honorario_fijo) if doc.modalidad_honorario in MODALIDADES_FIJO else 0
    doc.horas_facturables = horas_facturables
    doc.monto_horas_pendientes = monto_horas
    doc.monto_total_pendiente = monto_horas + monto_fijo


def obtener_facturas_pendientes_cobro(encargo):
    invoices = get_open_sales_invoices(encargo_name=encargo.name, project=encargo.project)
    return [
        {
            "name": invoice.name,
            "posting_date": invoice.posting_date,
            "due_date": invoice.due_date,
            "grand_total": flt(invoice.grand_total),
            "outstanding_amount": flt(invoice.outstanding_amount),
            "status": invoice.status,
        }
        for invoice in invoices
    ]


def crear_payment_entry_encargo(encargo, sales_invoice, posting_date=None, paid_amount=None, reference_no=None, reference_date=None, submit=0):
    invoices = {row.name for row in get_open_sales_invoices(encargo_name=encargo.name, project=encargo.project)}
    if sales_invoice not in invoices:
        frappe.throw(_("La factura indicada no pertenece al encargo o no tiene saldo pendiente."), title=_("Factura Invalida"))
    return create_payment_entry_for_invoice(
        sales_invoice=sales_invoice,
        posting_date=posting_date,
        paid_amount=paid_amount,
        reference_no=reference_no,
        reference_date=reference_date,
        submit=bool(cint(submit)),
    )


def generar_factura_venta(encargo, posting_date=None, due_date=None, incluir_horas=1, incluir_honorario_fijo=1, submit=0):
    if encargo.estado_aprobacion != ESTADO_APROBACION_APROBADO:
        frappe.throw(_("Solo puedes facturar encargos aprobados por Socio."), title=_("Aprobacion Requerida"))
    if encargo.contrato_comercial:
        encargo.validar_contrato_comercial()
    if encargo.estado in ESTADOS_CERRADOS:
        frappe.throw(_("No puedes facturar un encargo con estado <b>{0}</b>.").format(encargo.estado), title=_("Encargo Cerrado"))
    if not encargo.servicio_contable:
        frappe.throw(_("Debes asignar un servicio contable antes de facturar."), title=_("Servicio Requerido"))

    customer = frappe.db.get_value("Cliente Contable", encargo.cliente, "customer")
    if not customer:
        frappe.throw(_("El cliente contable no tiene Customer de ERPNext configurado."), title=_("Cliente Incompleto"))

    servicio = encargo.obtener_servicio()
    tarifa_hora, honorario_fijo, fuente = encargo.resolver_tarifas(fecha=posting_date)
    incluir_horas = bool(cint(incluir_horas))
    incluir_honorario_fijo = bool(cint(incluir_honorario_fijo))
    submit = bool(cint(submit))
    detalles_horas = obtener_detalles_horas_pendientes(encargo) if incluir_horas else []
    total_horas = flt(sum(flt(detalle.horas) for detalle in detalles_horas))
    usar_horas = incluir_horas and encargo.modalidad_honorario in MODALIDADES_HORAS and total_horas > 0
    usar_fijo = incluir_honorario_fijo and encargo.modalidad_honorario in MODALIDADES_FIJO and honorario_fijo > 0

    if usar_horas and tarifa_hora <= 0:
        frappe.throw(_("La tarifa por hora resuelta es 0. Revisa la configuracion de tarifas."), title=_("Tarifa Invalida"))
    if not usar_horas and not usar_fijo:
        frappe.throw(_("No hay conceptos facturables para este encargo con los parametros seleccionados."), title=_("Sin Datos para Facturar"))

    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = customer
    invoice.company = encargo.company
    invoice.posting_date = posting_date or nowdate()
    invoice.due_date = due_date or invoice.posting_date
    if invoice.meta.has_field("project") and encargo.project:
        invoice.project = encargo.project

    remarks = _("Factura generada desde Encargo Contable {0}. Fuente de tarifa: {1}.").format(encargo.name, fuente)
    if encargo.contrato_comercial:
        remarks += " " + _("Contrato comercial: {0}.").format(encargo.contrato_comercial)
    invoice.remarks = remarks
    erpnext_service.set_invoice_links(invoice, encargo)

    if usar_horas:
        invoice.append("items", {"item_code": servicio.item_horas, "qty": total_horas, "rate": tarifa_hora, "description": _("Horas facturables del encargo {0} ({1} horas)").format(encargo.name, total_horas)})
    if usar_fijo:
        invoice.append("items", {"item_code": servicio.item_honorario_fijo or servicio.item_horas, "qty": 1, "rate": honorario_fijo, "description": _("Honorario fijo del encargo {0}").format(encargo.name)})

    invoice.set_missing_values()
    invoice.calculate_taxes_and_totals()
    invoice.insert(ignore_permissions=True)
    if submit:
        invoice.submit()

    if usar_horas:
        sales_invoice_item = invoice.items[0].name if invoice.items else None
        marcar_horas_facturadas(detalles_horas, invoice.name, sales_invoice_item)

    return {
        "invoice": invoice,
        "total_horas": total_horas,
        "tarifa_hora": tarifa_hora,
        "honorario_fijo": honorario_fijo,
    }


def marcar_horas_facturadas(detalles_horas, sales_invoice, sales_invoice_item=None):
    if not detalles_horas or not frappe.db.has_column("Timesheet Detail", "sales_invoice"):
        return
    has_sales_invoice_item = frappe.db.has_column("Timesheet Detail", "sales_invoice_item")
    for detalle in detalles_horas:
        valores = {"sales_invoice": sales_invoice}
        if has_sales_invoice_item and sales_invoice_item:
            valores["sales_invoice_item"] = sales_invoice_item
        frappe.db.set_value("Timesheet Detail", detalle.name, valores, update_modified=False)
