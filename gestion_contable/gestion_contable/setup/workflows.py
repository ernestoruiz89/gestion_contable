import frappe

from gestion_contable.gestion_contable.utils.governance import (
    ESTADO_APROBACION_APROBADO,
    ESTADO_APROBACION_BORRADOR,
    ESTADO_APROBACION_DEVUELTO,
    ESTADO_APROBACION_REVISION_SOCIO,
    ESTADO_APROBACION_REVISION_SUPERVISOR,
)
from gestion_contable.gestion_contable.utils.security import (
    AUXILIAR_ROLE,
    CONTADOR_ROLE,
    SOCIO_ROLE,
    SUPERVISOR_ROLE,
    SYSTEM_MANAGER_ROLE,
)

DRAFT_EDIT_ROLES_WITH_AUX = (
    AUXILIAR_ROLE,
    CONTADOR_ROLE,
    SUPERVISOR_ROLE,
    SOCIO_ROLE,
    SYSTEM_MANAGER_ROLE,
)
DRAFT_EDIT_ROLES_INTERNAL = (
    CONTADOR_ROLE,
    SUPERVISOR_ROLE,
    SOCIO_ROLE,
    SYSTEM_MANAGER_ROLE,
)
SUPERVISOR_APPROVAL_ROLES = (
    CONTADOR_ROLE,
    SUPERVISOR_ROLE,
    SOCIO_ROLE,
    SYSTEM_MANAGER_ROLE,
)
SOCIO_APPROVAL_ROLES = (
    SOCIO_ROLE,
    SYSTEM_MANAGER_ROLE,
)
WORKFLOW_STATE_STYLES = {
    ESTADO_APROBACION_BORRADOR: "Inverse",
    ESTADO_APROBACION_REVISION_SUPERVISOR: "Warning",
    ESTADO_APROBACION_REVISION_SOCIO: "Primary",
    ESTADO_APROBACION_APROBADO: "Success",
    ESTADO_APROBACION_DEVUELTO: "Danger",
}
WORKFLOW_DEFINITIONS = (
    {
        "workflow_name": "GC - Aprobacion Tarea Contable",
        "document_type": "Tarea Contable",
        "draft_edit_roles": DRAFT_EDIT_ROLES_WITH_AUX,
    },
    {
        "workflow_name": "GC - Aprobacion Documento Contable",
        "document_type": "Documento Contable",
        "draft_edit_roles": DRAFT_EDIT_ROLES_WITH_AUX,
    },
    {
        "workflow_name": "GC - Aprobacion Requerimiento Cliente",
        "document_type": "Requerimiento Cliente",
        "draft_edit_roles": DRAFT_EDIT_ROLES_WITH_AUX,
    },
    {
        "workflow_name": "GC - Aprobacion Entregable Cliente",
        "document_type": "Entregable Cliente",
        "draft_edit_roles": DRAFT_EDIT_ROLES_WITH_AUX,
    },
    {
        "workflow_name": "GC - Aprobacion Encargo Contable",
        "document_type": "Encargo Contable",
        "draft_edit_roles": DRAFT_EDIT_ROLES_INTERNAL,
    },
    {
        "workflow_name": "GC - Aprobacion Contrato Comercial",
        "document_type": "Contrato Comercial",
        "draft_edit_roles": DRAFT_EDIT_ROLES_INTERNAL,
    },
    {
        "workflow_name": "GC - Aprobacion Cambio Alcance Comercial",
        "document_type": "Cambio Alcance Comercial",
        "draft_edit_roles": DRAFT_EDIT_ROLES_INTERNAL,
    },
    {
        "workflow_name": "GC - Aprobacion Expediente Auditoria",
        "document_type": "Expediente Auditoria",
        "draft_edit_roles": DRAFT_EDIT_ROLES_INTERNAL,
    },
    {
        "workflow_name": "GC - Aprobacion Riesgo Control Auditoria",
        "document_type": "Riesgo Control Auditoria",
        "draft_edit_roles": DRAFT_EDIT_ROLES_INTERNAL,
    },
    {
        "workflow_name": "GC - Aprobacion Papel Trabajo Auditoria",
        "document_type": "Papel Trabajo Auditoria",
        "draft_edit_roles": DRAFT_EDIT_ROLES_WITH_AUX,
    },
    {
        "workflow_name": "GC - Aprobacion Hallazgo Auditoria",
        "document_type": "Hallazgo Auditoria",
        "draft_edit_roles": DRAFT_EDIT_ROLES_INTERNAL,
    },
)


def ensure_native_workflows():
    if not _workflow_doctypes_available():
        return

    _ensure_workflow_states()
    for definition in WORKFLOW_DEFINITIONS:
        _sync_workflow(definition)


def _workflow_doctypes_available():
    return frappe.db.exists("DocType", "Workflow") and frappe.db.exists("DocType", "Workflow State")


def _ensure_workflow_states():
    for state_name, style in WORKFLOW_STATE_STYLES.items():
        workflow_state = _get_or_new_workflow_state(state_name)
        _set_if_available(workflow_state, "workflow_state_name", state_name)
        _set_if_available(workflow_state, "style", style)
        _save_doc(workflow_state)


def _get_or_new_workflow_state(state_name):
    existing_name = frappe.db.exists("Workflow State", state_name)
    if not existing_name:
        existing_name = frappe.db.get_value("Workflow State", {"workflow_state_name": state_name}, "name")

    if existing_name:
        return frappe.get_doc("Workflow State", existing_name)

    doc = frappe.new_doc("Workflow State")
    if doc.meta.has_field("workflow_state_name"):
        doc.workflow_state_name = state_name
    return doc


def _sync_workflow(definition):
    document_type = definition["document_type"]
    if not frappe.db.exists("DocType", document_type):
        return

    meta = frappe.get_meta(document_type)
    if not meta.has_field("estado_aprobacion"):
        return

    workflow = _get_or_new_workflow(definition)
    _set_if_available(workflow, "workflow_name", definition["workflow_name"])
    _set_if_available(workflow, "document_type", document_type)
    _set_if_available(workflow, "is_active", 1)
    _set_if_available(workflow, "workflow_state_field", "estado_aprobacion")
    _set_if_available(workflow, "send_email_alert", 0)

    _replace_child_rows(workflow, "states", _build_state_rows(definition))
    _replace_child_rows(workflow, "transitions", _build_transition_rows(definition))
    _save_doc(workflow)


def _get_or_new_workflow(definition):
    expected_name = definition["workflow_name"]
    existing_name = frappe.db.exists("Workflow", expected_name)
    if not existing_name:
        existing = frappe.get_all(
            "Workflow",
            filters={"document_type": definition["document_type"]},
            fields=["name"],
            order_by="modified desc",
            limit_page_length=1,
        )
        existing_name = existing[0].name if existing else None

    return frappe.get_doc("Workflow", existing_name) if existing_name else frappe.new_doc("Workflow")


def _build_state_rows(definition):
    rows = []
    rows.extend(_state_rows_for_roles(ESTADO_APROBACION_BORRADOR, definition["draft_edit_roles"]))
    rows.extend(_state_rows_for_roles(ESTADO_APROBACION_DEVUELTO, definition["draft_edit_roles"]))
    rows.extend(_state_rows_for_roles(ESTADO_APROBACION_REVISION_SUPERVISOR, SUPERVISOR_APPROVAL_ROLES))
    rows.extend(_state_rows_for_roles(ESTADO_APROBACION_REVISION_SOCIO, SOCIO_APPROVAL_ROLES))
    rows.extend(_state_rows_for_roles(ESTADO_APROBACION_APROBADO, (SYSTEM_MANAGER_ROLE,)))
    return rows


def _state_rows_for_roles(state_name, roles):
    rows = []
    for role in roles:
        row = {
            "state": state_name,
            "doc_status": 0,
            "allow_edit": role,
        }
        rows.append(row)
    return rows


def _build_transition_rows(definition):
    rows = []
    rows.extend(_transition_rows(ESTADO_APROBACION_BORRADOR, "Enviar a Revision", ESTADO_APROBACION_REVISION_SUPERVISOR, definition["draft_edit_roles"]))
    rows.extend(_transition_rows(ESTADO_APROBACION_DEVUELTO, "Reenviar a Revision", ESTADO_APROBACION_REVISION_SUPERVISOR, definition["draft_edit_roles"]))
    rows.extend(_transition_rows(ESTADO_APROBACION_REVISION_SUPERVISOR, "Enviar a Socio", ESTADO_APROBACION_REVISION_SOCIO, SUPERVISOR_APPROVAL_ROLES))
    rows.extend(_transition_rows(ESTADO_APROBACION_REVISION_SUPERVISOR, "Devolver", ESTADO_APROBACION_DEVUELTO, SUPERVISOR_APPROVAL_ROLES))
    rows.extend(_transition_rows(ESTADO_APROBACION_REVISION_SOCIO, "Aprobar", ESTADO_APROBACION_APROBADO, SOCIO_APPROVAL_ROLES))
    rows.extend(_transition_rows(ESTADO_APROBACION_REVISION_SOCIO, "Devolver", ESTADO_APROBACION_DEVUELTO, SOCIO_APPROVAL_ROLES))
    return rows


def _transition_rows(state_name, action, next_state, roles):
    rows = []
    for role in roles:
        rows.append(
            {
                "state": state_name,
                "action": action,
                "next_state": next_state,
                "allowed": role,
            }
        )
    return rows


def _replace_child_rows(doc, fieldname, rows):
    field = doc.meta.get_field(fieldname)
    if not field:
        return

    child_meta = frappe.get_meta(field.options)
    doc.set(fieldname, [])
    for row in rows:
        clean = {key: value for key, value in row.items() if child_meta.has_field(key)}
        doc.append(fieldname, clean)


def _set_if_available(doc, fieldname, value):
    if doc.meta.has_field(fieldname):
        setattr(doc, fieldname, value)


def _save_doc(doc):
    if doc.is_new():
        doc.insert(ignore_permissions=True)
        return
    doc.save(ignore_permissions=True)
