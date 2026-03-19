import frappe
from frappe import _
from frappe.utils import now_datetime

from gestion_contable.gestion_contable.utils.security import (
    SOCIO_ROLES,
    SUPERVISOR_ROLES,
    get_current_user,
    has_any_role,
    is_auxiliar,
    is_system_manager,
)

ESTADO_APROBACION_BORRADOR = "Borrador"
ESTADO_APROBACION_REVISION_SUPERVISOR = "Revision Supervisor"
ESTADO_APROBACION_REVISION_SOCIO = "Revision Socio"
ESTADO_APROBACION_APROBADO = "Aprobado"
ESTADO_APROBACION_DEVUELTO = "Devuelto"

ESTADOS_APROBACION = (
    ESTADO_APROBACION_BORRADOR,
    ESTADO_APROBACION_REVISION_SUPERVISOR,
    ESTADO_APROBACION_REVISION_SOCIO,
    ESTADO_APROBACION_APROBADO,
    ESTADO_APROBACION_DEVUELTO,
)

AUDIT_FIELDS = (
    "fecha_envio_revision",
    "revisado_por_supervisor",
    "fecha_revision_supervisor",
    "aprobado_por_socio",
    "fecha_aprobacion_socio",
)

SUPERVISOR_COMMENT_FIELD = "comentarios_supervisor"
SOCIO_COMMENT_FIELD = "comentarios_socio"
TABLE_META_FIELDS = {
    "doctype",
    "name",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "parent",
    "parentfield",
    "parenttype",
    "idx",
}

TRANSICIONES_APROBACION = {
    ESTADO_APROBACION_BORRADOR: {ESTADO_APROBACION_REVISION_SUPERVISOR: None},
    ESTADO_APROBACION_DEVUELTO: {ESTADO_APROBACION_REVISION_SUPERVISOR: None},
    ESTADO_APROBACION_REVISION_SUPERVISOR: {
        ESTADO_APROBACION_DEVUELTO: SUPERVISOR_ROLES,
        ESTADO_APROBACION_REVISION_SOCIO: SUPERVISOR_ROLES,
    },
    ESTADO_APROBACION_REVISION_SOCIO: {
        ESTADO_APROBACION_DEVUELTO: SOCIO_ROLES,
        ESTADO_APROBACION_APROBADO: SOCIO_ROLES,
    },
    ESTADO_APROBACION_APROBADO: {},
}


def validate_governance(
    doc,
    *,
    content_fields,
    create_roles,
    draft_roles,
    aux_editable_fields=None,
    aux_owner_field=None,
    label=None,
):
    if getattr(getattr(doc, "flags", None), "ignore_governance_validation", False):
        return

    label = label or doc.doctype
    doc.estado_aprobacion = doc.estado_aprobacion or ESTADO_APROBACION_BORRADOR
    _validate_estado(doc.estado_aprobacion)

    if doc.is_new():
        _validate_create_permission(label, create_roles)
        if doc.estado_aprobacion != ESTADO_APROBACION_BORRADOR:
            doc.estado_aprobacion = ESTADO_APROBACION_BORRADOR
        _initialize_audit_fields(doc)
        return

    previous = doc.get_doc_before_save()
    if not previous:
        return

    previous_state = previous.estado_aprobacion or ESTADO_APROBACION_BORRADOR
    _validate_estado(previous_state)
    _restore_audit_fields(doc, previous)

    changed_content_fields = _get_changed_fields(doc, previous, content_fields)
    _validate_content_edits(
        doc,
        previous,
        changed_content_fields,
        draft_roles=draft_roles,
        aux_editable_fields=aux_editable_fields,
        aux_owner_field=aux_owner_field,
        label=label,
        current_state=previous_state,
    )

    _validate_comment_edits(doc, previous, previous_state)

    current_state = doc.estado_aprobacion or ESTADO_APROBACION_BORRADOR
    if current_state != previous_state:
        _validate_transition(doc, previous_state, current_state, label, draft_roles)
        _apply_transition_metadata(doc, previous_state, current_state)


def _validate_create_permission(label, create_roles):
    if has_any_role(create_roles):
        return
    frappe.throw(_("No tienes permisos para crear {0}.").format(label), frappe.PermissionError)


def _validate_estado(state):
    if state in ESTADOS_APROBACION:
        return
    frappe.throw(_("El estado de aprobacion <b>{0}</b> no es valido.").format(state), title=_("Estado Invalido"))


def _initialize_audit_fields(doc):
    for fieldname in AUDIT_FIELDS:
        if doc.meta.has_field(fieldname):
            doc.set(fieldname, None)
    if doc.meta.has_field(SUPERVISOR_COMMENT_FIELD) and not doc.get(SUPERVISOR_COMMENT_FIELD):
        doc.set(SUPERVISOR_COMMENT_FIELD, None)
    if doc.meta.has_field(SOCIO_COMMENT_FIELD) and not doc.get(SOCIO_COMMENT_FIELD):
        doc.set(SOCIO_COMMENT_FIELD, None)


def _restore_audit_fields(doc, previous):
    for fieldname in AUDIT_FIELDS:
        if doc.meta.has_field(fieldname):
            doc.set(fieldname, previous.get(fieldname))


def _get_changed_fields(doc, previous, fields):
    changed_fields = []
    for fieldname in fields:
        field = doc.meta.get_field(fieldname)
        if not field:
            continue
        current_value = doc.get(fieldname)
        previous_value = previous.get(fieldname)
        if field.fieldtype == "Table":
            current_value = _serialize_table_value(current_value)
            previous_value = _serialize_table_value(previous_value)
        if current_value != previous_value:
            changed_fields.append(fieldname)
    return changed_fields


def _serialize_table_value(rows):
    serialized = []
    for row in rows or []:
        data = row.as_dict() if hasattr(row, "as_dict") else dict(row)
        clean = {key: value for key, value in data.items() if key not in TABLE_META_FIELDS}
        serialized.append(clean)
    return serialized


def _validate_content_edits(
    doc,
    previous,
    changed_fields,
    *,
    draft_roles,
    aux_editable_fields,
    aux_owner_field,
    label,
    current_state,
):
    if not changed_fields or is_system_manager():
        return

    if current_state in (
        ESTADO_APROBACION_REVISION_SUPERVISOR,
        ESTADO_APROBACION_REVISION_SOCIO,
        ESTADO_APROBACION_APROBADO,
    ):
        frappe.throw(
            _(
                "No puedes modificar el contenido de {0} mientras esta en <b>{1}</b>. "
                "Devuelvelo primero y luego ajusta el contenido."
            ).format(label, current_state),
            frappe.PermissionError,
        )

    if not has_any_role(draft_roles):
        frappe.throw(_("No tienes permisos para modificar {0}.").format(label), frappe.PermissionError)

    if not is_auxiliar():
        return

    owner_user = None
    if aux_owner_field:
        owner_user = previous.get(aux_owner_field) or doc.get(aux_owner_field)
    if owner_user and owner_user != get_current_user():
        frappe.throw(_("Solo puedes trabajar {0} asignado a tu usuario.").format(label), frappe.PermissionError)

    if aux_editable_fields is None:
        return

    invalid_fields = [fieldname for fieldname in changed_fields if fieldname not in set(aux_editable_fields)]
    if not invalid_fields:
        return

    labels = ", ".join(_get_field_label(doc, fieldname) for fieldname in invalid_fields)
    frappe.throw(
        _("Como Auxiliar solo puedes modificar campos operativos; bloqueados: <b>{0}</b>.").format(labels),
        frappe.PermissionError,
    )


def _validate_comment_edits(doc, previous, current_state):
    changed_supervisor = doc.meta.has_field(SUPERVISOR_COMMENT_FIELD) and doc.get(SUPERVISOR_COMMENT_FIELD) != previous.get(SUPERVISOR_COMMENT_FIELD)
    changed_socio = doc.meta.has_field(SOCIO_COMMENT_FIELD) and doc.get(SOCIO_COMMENT_FIELD) != previous.get(SOCIO_COMMENT_FIELD)

    if changed_supervisor:
        if current_state != ESTADO_APROBACION_REVISION_SUPERVISOR:
            frappe.throw(_("Los comentarios del supervisor solo pueden modificarse durante la revision de supervisor."), frappe.PermissionError)
        if not has_any_role(SUPERVISOR_ROLES):
            frappe.throw(_("No tienes permisos para registrar comentarios de supervisor."), frappe.PermissionError)

    if changed_socio:
        if current_state != ESTADO_APROBACION_REVISION_SOCIO:
            frappe.throw(_("Los comentarios del socio solo pueden modificarse durante la revision de socio."), frappe.PermissionError)
        if not has_any_role(SOCIO_ROLES):
            frappe.throw(_("No tienes permisos para registrar comentarios de socio."), frappe.PermissionError)


def _validate_transition(doc, previous_state, current_state, label, draft_roles):
    allowed_roles = TRANSICIONES_APROBACION.get(previous_state, {}).get(current_state)
    if allowed_roles is None:
        allowed_roles = draft_roles

    if current_state == ESTADO_APROBACION_APROBADO and previous_state != ESTADO_APROBACION_REVISION_SOCIO:
        frappe.throw(_("Solo puedes aprobar {0} despues de la revision de socio.").format(label), frappe.PermissionError)
    if current_state == ESTADO_APROBACION_REVISION_SOCIO and previous_state != ESTADO_APROBACION_REVISION_SUPERVISOR:
        frappe.throw(_("{0} debe pasar por revision de supervisor antes de llegar a socio.").format(label), frappe.PermissionError)

    if current_state == ESTADO_APROBACION_DEVUELTO:
        if previous_state == ESTADO_APROBACION_REVISION_SUPERVISOR:
            comments = (doc.get(SUPERVISOR_COMMENT_FIELD) or "").strip()
            if not comments:
                frappe.throw(_("Debes indicar comentarios del supervisor para devolver {0}.").format(label), frappe.PermissionError)
        elif previous_state == ESTADO_APROBACION_REVISION_SOCIO:
            comments = (doc.get(SOCIO_COMMENT_FIELD) or "").strip()
            if not comments:
                frappe.throw(_("Debes indicar comentarios del socio para devolver {0}.").format(label), frappe.PermissionError)

    if current_state != previous_state and current_state not in TRANSICIONES_APROBACION.get(previous_state, {}):
        frappe.throw(
            _("La transicion de <b>{0}</b> a <b>{1}</b> no esta permitida para {2}.").format(previous_state, current_state, label),
            frappe.PermissionError,
        )

    if has_any_role(allowed_roles):
        return
    frappe.throw(
        _("No tienes permisos para mover {0} de <b>{1}</b> a <b>{2}</b>.").format(label, previous_state, current_state),
        frappe.PermissionError,
    )


def _apply_transition_metadata(doc, previous_state, current_state):
    current_user = get_current_user()
    current_time = now_datetime()

    if current_state == ESTADO_APROBACION_REVISION_SUPERVISOR:
        if doc.meta.has_field("fecha_envio_revision"):
            doc.fecha_envio_revision = current_time
        if previous_state == ESTADO_APROBACION_DEVUELTO:
            if doc.meta.has_field("revisado_por_supervisor"):
                doc.revisado_por_supervisor = None
            if doc.meta.has_field("fecha_revision_supervisor"):
                doc.fecha_revision_supervisor = None
            if doc.meta.has_field("aprobado_por_socio"):
                doc.aprobado_por_socio = None
            if doc.meta.has_field("fecha_aprobacion_socio"):
                doc.fecha_aprobacion_socio = None
            if doc.meta.has_field(SOCIO_COMMENT_FIELD):
                doc.comentarios_socio = None
        return

    if previous_state == ESTADO_APROBACION_REVISION_SUPERVISOR and current_state in (ESTADO_APROBACION_DEVUELTO, ESTADO_APROBACION_REVISION_SOCIO):
        if doc.meta.has_field("revisado_por_supervisor"):
            doc.revisado_por_supervisor = current_user
        if doc.meta.has_field("fecha_revision_supervisor"):
            doc.fecha_revision_supervisor = current_time
        if current_state == ESTADO_APROBACION_DEVUELTO and doc.meta.has_field("aprobado_por_socio"):
            doc.aprobado_por_socio = None
        if current_state == ESTADO_APROBACION_DEVUELTO and doc.meta.has_field("fecha_aprobacion_socio"):
            doc.fecha_aprobacion_socio = None
        return

    if previous_state == ESTADO_APROBACION_REVISION_SOCIO and current_state in (ESTADO_APROBACION_DEVUELTO, ESTADO_APROBACION_APROBADO):
        if doc.meta.has_field("aprobado_por_socio"):
            doc.aprobado_por_socio = current_user
        if doc.meta.has_field("fecha_aprobacion_socio"):
            doc.fecha_aprobacion_socio = current_time


def _get_field_label(doc, fieldname):
    field = doc.meta.get_field(fieldname)
    return field.label if field and field.label else fieldname

