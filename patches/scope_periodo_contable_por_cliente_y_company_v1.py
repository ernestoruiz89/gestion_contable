import frappe

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company


REFERENCE_TARGETS = (
    {
        "doctype": "Encargo Contable",
        "fieldname": "periodo_referencia",
        "cliente_field": "cliente",
        "company_field": "company",
    },
    {
        "doctype": "Task",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "company_field": "company",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Tarea Contable",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Documento Contable",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Requerimiento Cliente",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Entregable Cliente",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Expediente Auditoria",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "company_field": "company",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Riesgo Control Auditoria",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "company_field": "company",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Papel Trabajo Auditoria",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "company_field": "company",
        "encargo_field": "encargo_contable",
    },
    {
        "doctype": "Hallazgo Auditoria",
        "fieldname": "periodo",
        "cliente_field": "cliente",
        "company_field": "company",
        "encargo_field": "encargo_contable",
    },
)


def execute():
    default_company = get_default_company() or frappe.db.get_value("Company", {}, "name")
    if not default_company:
        return

    legacy_periodos = frappe.get_all(
        "Periodo Contable",
        fields=["name", "cliente", "company", "anio", "mes", "estado"],
        limit_page_length=0,
    )
    encargo_company_cache = {}

    for legacy in legacy_periodos:
        if legacy.cliente and legacy.company:
            continue
        migrar_periodo_legacy(legacy, default_company, encargo_company_cache)


def migrar_periodo_legacy(periodo_legacy, default_company, encargo_company_cache):
    for target in REFERENCE_TARGETS:
        if not frappe.db.exists("DocType", target["doctype"]):
            continue

        fields = ["name", target["cliente_field"]]
        if target.get("company_field"):
            fields.append(target["company_field"])
        if target.get("encargo_field"):
            fields.append(target["encargo_field"])
        fields = list(dict.fromkeys(fields))

        rows = frappe.get_all(
            target["doctype"],
            filters={target["fieldname"]: periodo_legacy.name},
            fields=fields,
            limit_page_length=0,
        )

        for row in rows:
            cliente = row.get(target["cliente_field"])
            if not cliente:
                continue

            company = row.get(target.get("company_field")) if target.get("company_field") else None
            if not company and target.get("encargo_field"):
                company = get_encargo_company(row.get(target["encargo_field"]), encargo_company_cache)
            company = company or periodo_legacy.company or default_company

            scoped_periodo = get_or_create_scoped_periodo(periodo_legacy, cliente, company)
            if row.get(target["fieldname"]) != scoped_periodo:
                frappe.db.set_value(target["doctype"], row.name, target["fieldname"], scoped_periodo, update_modified=False)


def get_or_create_scoped_periodo(periodo_legacy, cliente, company):
    existing = frappe.db.get_value(
        "Periodo Contable",
        {
            "cliente": cliente,
            "company": company,
            "anio": periodo_legacy.anio,
            "mes": periodo_legacy.mes,
        },
        "name",
    )
    if existing:
        return existing

    periodo = frappe.get_doc(
        {
            "doctype": "Periodo Contable",
            "cliente": cliente,
            "company": company,
            "anio": periodo_legacy.anio,
            "mes": periodo_legacy.mes,
            "estado": periodo_legacy.estado or "Abierto",
        }
    ).insert(ignore_permissions=True)
    return periodo.name


def get_encargo_company(encargo_name, cache):
    if not encargo_name:
        return None
    if encargo_name not in cache:
        cache[encargo_name] = frappe.db.get_value("Encargo Contable", encargo_name, "company")
    return cache[encargo_name]
