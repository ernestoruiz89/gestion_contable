import frappe
from frappe import _

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company, get_periodo_operativo


def sync_operational_company(doc, *, cliente=None, periodo=None, encargo_name=None, label=None):
    label = label or _("el documento")
    current_company = getattr(doc, "company", None) or None
    encargo_company = _get_encargo_company(encargo_name)
    periodo_company = _get_periodo_company(periodo)
    cliente_company = _get_cliente_company(cliente)

    for context_label, expected_company in ((_("encargo"), encargo_company), (_("periodo"), periodo_company)):
        if current_company and expected_company and current_company != expected_company:
            frappe.throw(
                _("La compania indicada en {0} no coincide con la compania del {1}: <b>{2}</b>.").format(
                    label, context_label, expected_company
                ),
                title=_("Compania Inconsistente"),
            )

    resolved_company = encargo_company or periodo_company or current_company or cliente_company or get_default_company()
    if hasattr(doc, "company"):
        doc.company = resolved_company
    return resolved_company


def _get_encargo_company(encargo_name):
    if not encargo_name or not frappe.db.exists("Encargo Contable", encargo_name):
        return None
    return frappe.db.get_value("Encargo Contable", encargo_name, "company")


def _get_periodo_company(periodo_name):
    if not periodo_name:
        return None
    periodo = get_periodo_operativo(periodo_name)
    return periodo.company if periodo else None


def _get_cliente_company(cliente_name):
    if not cliente_name:
        return None
    defaults = get_cliente_defaults(cliente_name)
    return defaults.company_default if defaults else None
