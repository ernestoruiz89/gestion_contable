import importlib.util
import os

import frappe
from frappe import _

from gestion_contable.gestion_contable.setup.email_templates import EMAIL_TEMPLATE_DEFAULTS
from gestion_contable.gestion_contable.setup.workflows import WORKFLOW_DEFINITIONS
from gestion_contable.gestion_contable.utils.security import has_any_role
from gestion_contable.hooks import portal_menu_items

PAGE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
REQUIRED_DOCTYPES = (
    "Cliente Contable",
    "Periodo Contable",
    "Encargo Contable",
    "Documento Contable",
    "Requerimiento Cliente",
    "Entregable Cliente",
    "Expediente Auditoria",
    "Informe Final Auditoria",
    "Hallazgo Auditoria",
    "Papel Trabajo Auditoria",
    "Paquete Estados Financieros Cliente",
    "Estado Financiero Cliente",
    "Nota Estado Financiero",
    "Ajuste Estados Financieros Cliente",
    "Version Documento EEFF",
)
REQUIRED_REPORTS = (
    "Cartera Gerencial por Encargo",
    "Estado Gerencial de Auditoria",
    "Seguimiento Gerencial de Requerimientos",
    "Margen por Encargo y Servicio",
)
REQUIRED_PAGES = (
    "panel-de-tareas",
    "seguimiento-de-auditoria",
    "rentabilidad-y-cobranza",
    "salida-a-produccion",
)
REQUIRED_PRINT_FORMATS = (
    "Contrato Comercial - Contabilidad",
    "Contrato Comercial - Auditoria",
    "Contrato Comercial - Trabajo Especial",
    "Contrato Comercial - Consultoria",
    "Informe Final Auditoria - Emision",
    "Informe Final Auditoria - General",
    "Carta a la Gerencia - Auditoria",
    "Informe de Hallazgos - Auditoria",
    "Informe de Control Interno - Auditoria",
    "Procedimientos Acordados - Auditoria",
    "Dictamen de Auditoria",
    "Paquete Estados Financieros Cliente - Completo",
    "Paquete Estados Financieros Cliente - Notas Consolidadas",
    "Estado Financiero Cliente - Situacion Financiera",
    "Estado Financiero Cliente - Resultados",
    "Estado Financiero Cliente - Cambios en el Patrimonio",
    "Estado Financiero Cliente - Flujos de Efectivo",
    "Nota Estado Financiero - Individual",
    "Informe Completo de EEFF Auditados",
)
OPTIONAL_DEPENDENCIES = (
    ("docx", "python-docx"),
)
PATCHES_TO_REVIEW = (
    "gestion_contable.gestion_contable.patches.scope_periodo_contable_por_cliente_y_company_v1",
    "gestion_contable.gestion_contable.patches.refresh_encargo_financial_snapshots_v1",
    "gestion_contable.gestion_contable.patches.migrate_documento_contable_evidencias_v1",
    "gestion_contable.gestion_contable.patches.backfill_operational_context_and_retention_v1",
    "gestion_contable.gestion_contable.patches.reload_panel_de_gestion_workspace_v5",
)
UAT_SECTIONS = (
    {
        "title": "Comercial y Contratos",
        "items": (
            {
                "id": "uat-com-01",
                "title": "Contrato comercial hereda defaults del cliente",
                "steps": "Crear contrato nuevo desde un cliente con company, moneda, SLA y responsables cargados.",
                "expected": "El contrato completa company, moneda, responsable operativo y SLA sin captura manual.",
            },
            {
                "id": "uat-com-02",
                "title": "Formato sugerido e impresion",
                "steps": "Guardar un contrato de auditoria o contabilidad y usar el boton de formato sugerido.",
                "expected": "El formato sugerido coincide con el tipo de servicio y abre el print format correcto.",
            },
        ),
    },
    {
        "title": "Operacion y Encargos",
        "items": (
            {
                "id": "uat-ops-01",
                "title": "Task como modelo unico de tarea",
                "steps": "Crear tarea desde panel y validar que se guarda en Task y aparece en formulario relacionado.",
                "expected": "No se genera ningun registro en Tarea Contable y la trazabilidad usa Task.",
            },
            {
                "id": "uat-ops-02",
                "title": "Periodo por cliente y compania",
                "steps": "Crear dos periodos del mismo mes para clientes o companias distintas y registrar operaciones.",
                "expected": "Cada operacion valida contra su propio periodo operativo, sin cruces globales.",
            },
        ),
    },
    {
        "title": "Auditoria Formal",
        "items": (
            {
                "id": "uat-aud-01",
                "title": "Cierre de expediente e informe final",
                "steps": "Cerrar expediente con revision tecnica aprobada y generar informe final desde el expediente.",
                "expected": "Se crea un Informe Final Auditoria ligado al expediente, con contenido sugerido y workflow activo.",
            },
            {
                "id": "uat-aud-02",
                "title": "Emision controlada del informe",
                "steps": "Aprobar el informe por workflow y usar Emitir Informe.",
                "expected": "El informe pasa a Emitido y el expediente no puede archivarse sin ese estado emitido.",
            },
        ),
    },
    {
        "title": "Portal y Requerimientos",
        "items": (
            {
                "id": "uat-portal-01",
                "title": "Portal cliente y permisos",
                "steps": "Ingresar con usuario portal configurado y navegar Dashboard, Requerimientos y Entregables.",
                "expected": "El usuario ve solo su cliente y las rutas publicadas funcionan sin error 404 o permisos inconsistentes.",
            },
            {
                "id": "uat-portal-02",
                "title": "Carga documental desde portal",
                "steps": "Subir un archivo desde Entregables del Cliente contra un entregable abierto.",
                "expected": "Se crea Documento Contable, el entregable pasa a Recibido y queda Communication asociada al requerimiento.",
            },
        ),
    },
    {
        "title": "Facturacion, Cobranza y Rentabilidad",
        "items": (
            {
                "id": "uat-fin-01",
                "title": "Snapshots financieros consistentes",
                "steps": "Crear factura, registrar pago y revisar encargo + page de rentabilidad.",
                "expected": "Los montos coinciden entre el formulario del encargo y la page, sin recalculos divergentes.",
            },
            {
                "id": "uat-fin-02",
                "title": "Seguimiento de cobranza con plantilla",
                "steps": "Crear seguimiento de cobranza con canal Correo y revisar Communication.",
                "expected": "El correo usa la plantilla configurada y deja trazabilidad en Communication.",
            },
        ),
    },
    {
        "title": "Estados Financieros del Cliente",
        "items": (
            {
                "id": "uat-eeff-01",
                "title": "Paquete completo y notas",
                "steps": "Crear paquete, registrar los cuatro estados base, notas requeridas y emitir el paquete.",
                "expected": "El paquete valida estados, notas y cuadraturas antes de pasar a Emitido.",
            },
            {
                "id": "uat-eeff-02",
                "title": "Versiones Word y entrega al cliente",
                "steps": "Generar Word de revision, vincularlo al intercambio con cliente y subir una respuesta desde portal.",
                "expected": "La Version Documento EEFF queda ligada al requerimiento/entregable y registra comentario o aprobacion del cliente.",
            },
        ),
    },
    {
        "title": "Gobierno y Compliance",
        "items": (
            {
                "id": "uat-gob-01",
                "title": "Workflow y segregacion por rol",
                "steps": "Probar Borrador, Revision Supervisor, Revision Socio y Aprobado en tarea, documento, encargo e informe final.",
                "expected": "Cada rol solo puede ejecutar sus transiciones y los campos bloqueados no se editan fuera de estado permitido.",
            },
            {
                "id": "uat-gob-02",
                "title": "Retencion documental y artefactos auditados",
                "steps": "Intentar eliminar un documento con retencion activa y validar impresion/exportacion final solo cuando corresponda.",
                "expected": "El borrado se bloquea segun politica y la documentacion auditada solo se emite bajo estados formales validos.",
            },
        ),
    },
)


def _ensure_page_access():
    if has_any_role(PAGE_ROLES):
        return
    frappe.throw(_("No tienes permisos para revisar la salida a produccion."), frappe.PermissionError)


@frappe.whitelist()
def get_release_readiness():
    _ensure_page_access()
    groups = [
        _check_doctypes(),
        _check_workflows(),
        _check_reports(),
        _check_pages(),
        _check_portal_routes(),
        _check_print_formats(),
        _check_email_templates(),
        _check_optional_dependencies(),
        _check_patches(),
    ]
    return {
        "summary": _summarize(groups),
        "groups": groups,
        "uat_sections": UAT_SECTIONS,
        "commands": [
            "bench --site <sitio> migrate",
            "bench --site <sitio> clear-cache",
            "bench --site <sitio> run-tests --app gestion_contable",
        ],
        "notes": [
            "Esta vista valida estructura y configuracion minima; no sustituye la ejecucion real de UAT en el sitio.",
            "La exportacion Word requiere la dependencia opcional python-docx instalada en el entorno del sitio.",
            "La configuracion dummy se mantiene habilitable por feature flag y no forma parte de esta salida a produccion.",
        ],
    }


def _check_doctypes():
    items = [_presence_check("DocType", name, frappe.db.exists("DocType", name)) for name in REQUIRED_DOCTYPES]
    return _group("Doctypes Criticos", items)


def _check_workflows():
    items = []
    for definition in WORKFLOW_DEFINITIONS:
        workflow_name = definition["workflow_name"]
        active = frappe.db.get_value("Workflow", workflow_name, "is_active") if frappe.db.exists("Workflow", workflow_name) else None
        items.append(_status_check("Workflow", workflow_name, "pass" if active else "fail", "Activo" if active else "No encontrado o inactivo"))
    return _group("Workflows", items)


def _check_reports():
    items = [_presence_check("Report", name, frappe.db.exists("Report", name)) for name in REQUIRED_REPORTS]
    return _group("Reportes Gerenciales", items)


def _check_pages():
    items = [_presence_check("Page", name, frappe.db.exists("Page", name)) for name in REQUIRED_PAGES]
    return _group("Pages Desk", items)


def _check_portal_routes():
    items = []
    published_routes = [item.get("route", "").lstrip("/") for item in portal_menu_items]
    for route in published_routes:
        path = frappe.get_app_path("gestion_contable", "gestion_contable", "www", route, "index.py")
        items.append(_status_check("Portal", route, "pass" if os.path.exists(path) else "fail", path))
    return _group("Portal Cliente", items)


def _check_print_formats():
    items = [_presence_check("Print Format", name, frappe.db.exists("Print Format", name)) for name in REQUIRED_PRINT_FORMATS]
    return _group("Print Formats", items)


def _check_email_templates():
    items = []
    for definition in EMAIL_TEMPLATE_DEFAULTS.values():
        name = definition["name"]
        items.append(_presence_check("Email Template", name, frappe.db.exists("Email Template", name)))
    return _group("Email Templates", items)


def _check_optional_dependencies():
    items = []
    for module_name, display_name in OPTIONAL_DEPENDENCIES:
        installed = importlib.util.find_spec(module_name) is not None
        message = "Instalada" if installed else "Dependencia opcional no instalada"
        status = "pass" if installed else "warn"
        items.append(_status_check("Optional Dependency", display_name, status, message))
    return _group("Dependencias Opcionales", items)


def _check_patches():
    patch_file = frappe.get_app_path("gestion_contable", "patches.txt")
    registered = set()
    if os.path.exists(patch_file):
        with open(patch_file, "r", encoding="utf-8") as handle:
            registered = {line.strip() for line in handle.readlines() if line.strip() and not line.startswith("[")}
    patch_log_available = frappe.db.exists("DocType", "Patch Log")
    items = []
    for patch_name in PATCHES_TO_REVIEW:
        if patch_name not in registered:
            items.append(_status_check("Patch", patch_name, "fail", "No registrado en patches.txt"))
            continue
        if not patch_log_available:
            items.append(_status_check("Patch", patch_name, "warn", "Patch Log no disponible para validar aplicacion"))
            continue
        applied = bool(frappe.db.exists("Patch Log", patch_name))
        items.append(_status_check("Patch", patch_name, "pass" if applied else "fail", "Aplicado" if applied else "Pendiente de aplicar"))
    return _group("Migraciones", items)


def _presence_check(kind, name, exists):
    return _status_check(kind, name, "pass" if exists else "fail", "Disponible" if exists else "No encontrado")


def _status_check(kind, name, status, message):
    return {"kind": kind, "name": name, "status": status, "message": message}


def _group(title, items):
    status = "pass"
    if any(item["status"] == "fail" for item in items):
        status = "fail"
    elif any(item["status"] == "warn" for item in items):
        status = "warn"
    return {"title": title, "status": status, "items": items}


def _summarize(groups):
    items = [item for group in groups for item in group["items"]]
    return {
        "total": len(items),
        "pass": sum(1 for item in items if item["status"] == "pass"),
        "warn": sum(1 for item in items if item["status"] == "warn"),
        "fail": sum(1 for item in items if item["status"] == "fail"),
    }
