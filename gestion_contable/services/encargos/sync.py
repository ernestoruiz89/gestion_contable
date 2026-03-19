import frappe

from gestion_contable.gestion_contable.services.encargos import analytics as analytics_service


def sync_from_sales_invoice(doc, method=None):
    encargo_names = _resolve_encargos_from_sales_invoice(doc)
    if encargo_names:
        frappe.enqueue(
            _refresh_financial_snapshots,
            encargo_names=list(encargo_names),
            queue="default",
            now=frappe.flags.in_test,
        )


def sync_from_payment_entry(doc, method=None):
    encargo_names = _resolve_encargos_from_payment_entry(doc)
    if encargo_names:
        frappe.enqueue(
            _refresh_financial_snapshots,
            encargo_names=list(encargo_names),
            queue="default",
            now=frappe.flags.in_test,
        )


def sync_from_timesheet(doc, method=None):
    encargo_names = _resolve_encargos_from_timesheet(doc)
    if encargo_names:
        frappe.enqueue(
            _refresh_full_snapshots,
            encargo_names=list(encargo_names),
            queue="default",
            now=frappe.flags.in_test,
        )


def sync_from_seguimiento_cobranza(doc, method=None):
    encargo_name = getattr(doc, "encargo_contable", None)
    if encargo_name:
        frappe.enqueue(
            analytics_service.refresh_cobranza_snapshot,
            encargo_name=encargo_name,
            queue="default",
            now=frappe.flags.in_test,
        )


def _refresh_financial_snapshots(encargo_names):
    for encargo_name in sorted(encargo_names):
        analytics_service.refresh_financial_snapshot(encargo_name)


def _refresh_full_snapshots(encargo_names):
    for encargo_name in sorted(encargo_names):
        analytics_service.refresh_full_snapshot(encargo_name)


def _resolve_encargos_from_sales_invoice(doc):
    encargo_names = set()
    encargo_name = getattr(doc, "encargo_contable", None)
    if encargo_name:
        encargo_names.add(encargo_name)
    project = getattr(doc, "project", None)
    if project:
        encargo_names.update(_get_encargos_by_projects({project}))
    return encargo_names


def _resolve_encargos_from_payment_entry(doc):
    invoice_names = {
        row.reference_name
        for row in (doc.get("references") or [])
        if row.reference_doctype == "Sales Invoice" and row.reference_name
    }
    if not invoice_names:
        return set()
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"name": ["in", list(invoice_names)]},
        fields=["name", "encargo_contable", "project"],
        limit_page_length=len(invoice_names),
    )
    encargo_names = {row.encargo_contable for row in invoices if row.encargo_contable}
    projects = {row.project for row in invoices if row.project}
    encargo_names.update(_get_encargos_by_projects(projects))
    return encargo_names


def _resolve_encargos_from_timesheet(doc):
    projects = set()
    if getattr(doc, "project", None):
        projects.add(doc.project)
    for field in doc.meta.get_table_fields():
        for row in doc.get(field.fieldname) or []:
            project = getattr(row, "project", None)
            if project:
                projects.add(project)
    return _get_encargos_by_projects(projects)


def _get_encargos_by_projects(projects):
    if not projects:
        return set()
    rows = frappe.get_all(
        "Encargo Contable",
        filters={"project": ["in", list(projects)]},
        fields=["name"],
        limit_page_length=len(projects) * 5,
    )
    return {row.name for row in rows}
