import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, nowdate

AGING_KEYS = ("aging_current", "aging_0_30", "aging_31_60", "aging_61_90", "aging_91_plus")


def get_related_sales_invoices(encargo_name=None, project=None, include_draft=False):
    if not encargo_name and not project:
        return []

    has_encargo = frappe.db.has_column("Sales Invoice", "encargo_contable")
    has_project = frappe.db.has_column("Sales Invoice", "project")

    conditions = ["si.docstatus < 2" if include_draft else "si.docstatus = 1"]
    params = {}

    if has_encargo and encargo_name and has_project and project:
        conditions.append(
            "(si.encargo_contable = %(encargo_name)s OR "
            "((si.encargo_contable IS NULL OR si.encargo_contable = '') AND si.project = %(project)s))"
        )
        params.update({"encargo_name": encargo_name, "project": project})
    elif has_encargo and encargo_name:
        conditions.append("si.encargo_contable = %(encargo_name)s")
        params["encargo_name"] = encargo_name
    elif has_project and project:
        conditions.append("si.project = %(project)s")
        params["project"] = project
    else:
        return []

    return frappe.db.sql(
        f"""
        SELECT
            si.name,
            si.customer,
            si.currency,
            si.company,
            si.posting_date,
            si.due_date,
            si.grand_total,
            si.outstanding_amount,
            si.status,
            si.docstatus
        FROM `tabSales Invoice` si
        WHERE {' AND '.join(conditions)}
        ORDER BY si.posting_date DESC, si.modified DESC
        """,
        params,
        as_dict=True,
    )


def build_invoice_summary(invoices, today=None):
    today = getdate(today or nowdate())
    summary = {
        "facturas_emitidas": 0,
        "facturas_abiertas": 0,
        "facturas_vencidas": 0,
        "ingreso_facturado": 0,
        "cobrado_total": 0,
        "saldo_por_cobrar": 0,
        "cartera_vencida": 0,
        "ultima_factura": None,
        "ultimo_vencimiento": None,
    }
    for key in AGING_KEYS:
        summary[key] = 0

    for invoice in invoices or []:
        total = flt(invoice.grand_total)
        outstanding = flt(invoice.outstanding_amount)
        collected = flt(total - outstanding)

        summary["facturas_emitidas"] += 1
        summary["ingreso_facturado"] += total
        summary["cobrado_total"] += collected
        summary["saldo_por_cobrar"] += outstanding
        summary["ultima_factura"] = _max_date(summary["ultima_factura"], invoice.posting_date)
        summary["ultimo_vencimiento"] = _max_date(summary["ultimo_vencimiento"], invoice.due_date)

        if outstanding > 0:
            summary["facturas_abiertas"] += 1
            _apply_aging(summary, invoice, outstanding, today)

    return summary


def get_open_sales_invoices(encargo_name=None, project=None):
    invoices = get_related_sales_invoices(encargo_name=encargo_name, project=project, include_draft=False)
    return [invoice for invoice in invoices if flt(invoice.outstanding_amount) > 0]


def create_payment_entry_for_invoice(sales_invoice, posting_date=None, paid_amount=None, reference_no=None, reference_date=None, submit=False):
    invoice = frappe.get_doc("Sales Invoice", sales_invoice)
    if invoice.docstatus != 1:
        frappe.throw(_("La factura debe estar enviada antes de registrar un cobro."), title=_("Factura No Enviada"))
    if flt(invoice.outstanding_amount) <= 0:
        frappe.throw(_("La factura {0} no tiene saldo pendiente.").format(invoice.name), title=_("Sin Saldo"))

    try:
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    except Exception as exc:
        frappe.throw(_("No fue posible cargar ERPNext para crear el Payment Entry: {0}").format(exc))

    requested_amount = flt(paid_amount)
    if requested_amount <= 0:
        requested_amount = flt(invoice.outstanding_amount)

    try:
        payment_entry = get_payment_entry("Sales Invoice", invoice.name, party_amount=requested_amount)
    except TypeError:
        payment_entry = get_payment_entry("Sales Invoice", invoice.name)

    payment_entry.posting_date = posting_date or nowdate()
    if reference_no and payment_entry.meta.has_field("reference_no"):
        payment_entry.reference_no = reference_no
    if reference_date and payment_entry.meta.has_field("reference_date"):
        payment_entry.reference_date = reference_date

    allocated = min(requested_amount, flt(invoice.outstanding_amount))
    _set_payment_amounts(payment_entry, allocated)
    for row in payment_entry.references or []:
        if row.reference_doctype != "Sales Invoice" or row.reference_name != invoice.name:
            continue
        row.allocated_amount = allocated
        row.total_amount = flt(invoice.grand_total)
        row.outstanding_amount = flt(invoice.outstanding_amount)
        break

    if payment_entry.meta.has_field("remarks"):
        payment_entry.remarks = _("Cobro registrado para la factura {0}.").format(invoice.name)

    payment_entry.insert(ignore_permissions=True)
    if submit:
        payment_entry.submit()
    return payment_entry


def _set_payment_amounts(payment_entry, allocated):
    if payment_entry.meta.has_field("paid_amount"):
        payment_entry.paid_amount = allocated
    if payment_entry.meta.has_field("received_amount"):
        payment_entry.received_amount = allocated
    if hasattr(payment_entry, "set_amounts"):
        payment_entry.set_amounts()



def _apply_aging(summary, invoice, outstanding, today):
    due_date = getdate(invoice.due_date) if invoice.due_date else None
    if not due_date or due_date >= today:
        summary["aging_current"] += outstanding
        return

    summary["facturas_vencidas"] += 1
    summary["cartera_vencida"] += outstanding
    days_overdue = date_diff(today, due_date)
    if days_overdue <= 30:
        summary["aging_0_30"] += outstanding
    elif days_overdue <= 60:
        summary["aging_31_60"] += outstanding
    elif days_overdue <= 90:
        summary["aging_61_90"] += outstanding
    else:
        summary["aging_91_plus"] += outstanding



def _max_date(current_value, candidate):
    if not candidate:
        return current_value
    if not current_value:
        return candidate
    return candidate if getdate(candidate) > getdate(current_value) else current_value