import frappe

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company
from gestion_contable.gestion_contable.utils.retention import calculate_retention_deadline, get_document_retention_defaults


CORE_DOCTYPES = (
    "Tarea Contable",
    "Requerimiento Cliente",
    "Entregable Cliente",
    "Documento Contable",
)


def execute():
    _backfill_operational_company()
    _backfill_document_retention()
    _backfill_papel_evidence()


def _backfill_operational_company():
    for doctype in CORE_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        meta = frappe.get_meta(doctype)
        if not meta.has_field("company"):
            continue

        fields = ["name"]
        for fieldname in ("cliente", "periodo", "encargo_contable"):
            if meta.has_field(fieldname):
                fields.append(fieldname)
        rows = frappe.get_all(doctype, fields=fields, limit_page_length=0)

        for row in rows:
            company = _infer_company(row)
            if company:
                frappe.db.set_value(doctype, row.name, "company", company, update_modified=False)


def _infer_company(row):
    encargo_name = row.get("encargo_contable")
    if encargo_name and frappe.db.exists("Encargo Contable", encargo_name):
        company = frappe.db.get_value("Encargo Contable", encargo_name, "company")
        if company:
            return company

    periodo_name = row.get("periodo")
    if periodo_name and frappe.db.exists("Periodo Contable", periodo_name):
        company = frappe.db.get_value("Periodo Contable", periodo_name, "company")
        if company:
            return company

    cliente_name = row.get("cliente")
    if cliente_name:
        defaults = get_cliente_defaults(cliente_name)
        if defaults and defaults.company_default:
            return defaults.company_default

    return get_default_company()


def _backfill_document_retention():
    if not frappe.db.exists("DocType", "Documento Contable"):
        return

    for row in frappe.get_all("Documento Contable", fields=["name"], limit_page_length=0):
        doc = frappe.get_doc("Documento Contable", row.name)
        defaults = get_document_retention_defaults(doc.cliente)
        dirty = False

        for evidence in doc.evidencias_documentales or []:
            if not evidence.confidencialidad:
                evidence.confidencialidad = defaults.confidencialidad
                dirty = True
            if not evidence.politica_retencion:
                evidence.politica_retencion = defaults.politica_retencion
                dirty = True
            if evidence.politica_retencion not in (None, "", "Sin Definir", "Permanente") and not evidence.conservar_hasta:
                evidence.conservar_hasta = calculate_retention_deadline(evidence.politica_retencion, periodo_name=doc.periodo)
                dirty = True

        if dirty:
            doc.flags.ignore_governance_validation = True
            doc.save(ignore_permissions=True)


def _backfill_papel_evidence():
    if not frappe.db.exists("DocType", "Papel Trabajo Auditoria"):
        return

    for row in frappe.get_all("Papel Trabajo Auditoria", fields=["name", "documento_contable", "evidencia_documental_file"], limit_page_length=0):
        if not row.documento_contable or row.evidencia_documental_file:
            continue

        documento = frappe.get_doc("Documento Contable", row.documento_contable)
        primary = next((item for item in documento.evidencias_documentales or [] if item.archivo_file), None)
        if not primary:
            continue

        frappe.db.set_value(
            "Papel Trabajo Auditoria",
            row.name,
            {
                "evidencia_documental_file": primary.archivo_file,
                "codigo_evidencia_documental": primary.codigo_documental or primary.descripcion_evidencia,
                "version_evidencia_documental": primary.numero_version,
                "hash_evidencia_sha256": primary.hash_sha256,
            },
            update_modified=False,
        )
