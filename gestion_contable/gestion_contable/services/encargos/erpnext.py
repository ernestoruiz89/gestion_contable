import frappe
from frappe import _


def sincronizar_company(doc):
    if doc.company:
        return
    doc.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    if not doc.company:
        frappe.throw(_("Define una compania en el encargo o en los valores por defecto del usuario."), title=_("Compania Requerida"))


def sincronizar_moneda(doc):
    if doc.moneda:
        return
    if doc.company:
        moneda = frappe.db.get_value("Company", doc.company, "default_currency")
        if moneda:
            doc.moneda = moneda


def asegurar_project(doc):
    if doc.project:
        return
    doc.project = crear_project(doc)


def crear_project(doc):
    project_name = doc.nombre_del_encargo or f"Encargo - {doc.cliente}"
    customer = frappe.db.get_value("Cliente Contable", doc.cliente, "customer") if doc.cliente else None
    project_doc = frappe.get_doc({
        "doctype": "Project",
        "project_name": project_name,
        "status": "Open",
        "expected_start_date": doc.fecha_de_inicio,
        "expected_end_date": doc.fecha_fin_estimada,
        "company": doc.company,
        "customer": customer,
    })
    project_doc.insert()
    return project_doc.name


def validar_project_consistente(doc):
    if not doc.project:
        return
    project = frappe.db.get_value("Project", doc.project, ["name", "company", "customer"], as_dict=True)
    if not project:
        frappe.throw(_("El proyecto <b>{0}</b> no existe.").format(doc.project), title=_("Proyecto Invalido"))
    customer = frappe.db.get_value("Cliente Contable", doc.cliente, "customer") if doc.cliente else None
    if doc.company and project.company and project.company != doc.company:
        frappe.throw(_("La compania del encargo no coincide con la del proyecto vinculado."), title=_("Inconsistencia de Proyecto"))
    if customer and project.customer and project.customer != customer:
        frappe.throw(_("El cliente del encargo no coincide con el customer del proyecto."), title=_("Inconsistencia de Proyecto"))


def set_invoice_links(invoice, encargo):
    if invoice.meta.has_field("encargo_contable"):
        invoice.encargo_contable = encargo.name
    if invoice.meta.has_field("cliente_contable"):
        invoice.cliente_contable = encargo.cliente
    if invoice.meta.has_field("servicio_contable"):
        invoice.servicio_contable = encargo.servicio_contable
    if invoice.meta.has_field("contrato_comercial"):
        invoice.contrato_comercial = encargo.contrato_comercial
    if invoice.meta.has_field("tipo_de_servicio"):
        invoice.tipo_de_servicio = encargo.tipo_de_servicio
