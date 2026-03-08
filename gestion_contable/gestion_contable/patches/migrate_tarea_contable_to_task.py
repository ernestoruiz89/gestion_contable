import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


TASK_TYPE_OPTIONS = "Impuestos\nN\u00f3mina\nCierre Contable\nAuditor\u00eda\nConciliaci\u00f3n Bancaria\nDeclaraci\u00f3n DGI\nEstados Financieros\nFacturaci\u00f3n\nAtenci\u00f3n a Requerimiento\nTr\u00e1mite DGI\nConsultor\u00eda\nOtro"
TASK_CUSTOM_FIELDS = (
    {
        "fieldname": "cliente",
        "label": "Cliente",
        "fieldtype": "Link",
        "options": "Cliente Contable",
        "insert_after": "project",
        "in_list_view": 1,
    },
    {
        "fieldname": "company",
        "label": "Compania",
        "fieldtype": "Link",
        "options": "Company",
        "insert_after": "cliente",
    },
    {
        "fieldname": "encargo_contable",
        "label": "Encargo Contable",
        "fieldtype": "Link",
        "options": "Encargo Contable",
        "insert_after": "company",
    },
    {
        "fieldname": "periodo",
        "label": "Periodo",
        "fieldtype": "Link",
        "options": "Periodo Contable",
        "insert_after": "encargo_contable",
        "in_list_view": 1,
    },
    {
        "fieldname": "tipo_de_tarea",
        "label": "Tipo de Tarea",
        "fieldtype": "Select",
        "options": TASK_TYPE_OPTIONS,
        "insert_after": "periodo",
    },
    {
        "fieldname": "estado_aprobacion",
        "label": "Estado de Aprobacion",
        "fieldtype": "Select",
        "options": "Borrador\nRevision Supervisor\nRevision Socio\nAprobado\nDevuelto",
        "default": "Borrador",
        "insert_after": "tipo_de_tarea",
        "read_only": 1,
        "in_list_view": 1,
    },
    {
        "fieldname": "fecha_envio_revision",
        "label": "Fecha Envio Revision",
        "fieldtype": "Datetime",
        "insert_after": "estado_aprobacion",
        "read_only": 1,
    },
    {
        "fieldname": "revisado_por_supervisor",
        "label": "Revisado por Supervisor",
        "fieldtype": "Link",
        "options": "User",
        "insert_after": "fecha_envio_revision",
        "read_only": 1,
        "permlevel": 1,
    },
    {
        "fieldname": "fecha_revision_supervisor",
        "label": "Fecha Revision Supervisor",
        "fieldtype": "Datetime",
        "insert_after": "revisado_por_supervisor",
        "read_only": 1,
        "permlevel": 1,
    },
    {
        "fieldname": "aprobado_por_socio",
        "label": "Aprobado por Socio",
        "fieldtype": "Link",
        "options": "User",
        "insert_after": "fecha_revision_supervisor",
        "read_only": 1,
        "permlevel": 2,
    },
    {
        "fieldname": "fecha_aprobacion_socio",
        "label": "Fecha Aprobacion Socio",
        "fieldtype": "Datetime",
        "insert_after": "aprobado_por_socio",
        "read_only": 1,
        "permlevel": 2,
    },
    {
        "fieldname": "comentarios_supervisor",
        "label": "Comentarios Supervisor",
        "fieldtype": "Small Text",
        "insert_after": "fecha_aprobacion_socio",
        "permlevel": 1,
    },
    {
        "fieldname": "comentarios_socio",
        "label": "Comentarios Socio",
        "fieldtype": "Small Text",
        "insert_after": "comentarios_supervisor",
        "permlevel": 2,
    },
    {
        "fieldname": "old_tarea_id",
        "label": "Old Tarea ID",
        "fieldtype": "Data",
        "insert_after": "comentarios_socio",
        "hidden": 1,
        "read_only": 1,
    },
)
LEGACY_PENDING_REVIEW_MOJIBAKE = "En Revisión".encode("utf-8").decode("latin-1")
LEGACY_STATUS_MAP = {
    "Pendiente": "Open",
    "En Proceso": "Working",
    "En Revisión": "Pending Review",
    # Compatibilidad con sitios legacy donde el estado quedó guardado con mojibake.
    LEGACY_PENDING_REVIEW_MOJIBAKE: "Pending Review",
    "Completada": "Completed",
    "Descartada": "Cancelled",
}
REFERENCE_MAPPERS = (
    ("Communication", "reference_doctype", "reference_name"),
    ("Comment", "reference_doctype", "reference_name"),
    ("File", "attached_to_doctype", "attached_to_name"),
    ("ToDo", "reference_type", "reference_name"),
)


def execute():
    if not frappe.db.exists("DocType", "Task"):
        return

    ensure_task_custom_fields()
    task_map = migrate_legacy_tareas()
    backfill_documento_contable_refs(task_map)
    relink_supporting_records(task_map)


def ensure_task_custom_fields():
    for definition in TASK_CUSTOM_FIELDS:
        upsert_custom_field("Task", definition)



def upsert_custom_field(doctype, definition):
    fieldname = definition["fieldname"]
    custom_field_name = f"{doctype}-{fieldname}"
    custom_field = (
        frappe.get_doc("Custom Field", custom_field_name)
        if frappe.db.exists("Custom Field", custom_field_name)
        else frappe.new_doc("Custom Field")
    )
    custom_field.dt = doctype
    for key, value in definition.items():
        setattr(custom_field, key, value)
    if custom_field.is_new():
        custom_field.insert(ignore_permissions=True)
    else:
        custom_field.save(ignore_permissions=True)



def migrate_legacy_tareas():
    if not frappe.db.exists("DocType", "Tarea Contable"):
        return {}

    legacy_fields = [
        "name",
        "titulo",
        "cliente",
        "company",
        "encargo_contable",
        "periodo",
        "tipo_de_tarea",
        "estado",
        "fecha_de_vencimiento",
        "estado_aprobacion",
        "fecha_envio_revision",
        "revisado_por_supervisor",
        "fecha_revision_supervisor",
        "aprobado_por_socio",
        "fecha_aprobacion_socio",
        "comentarios_supervisor",
        "comentarios_socio",
        "asignado_a",
        "notas",
    ]
    task_map = {}
    for legacy in frappe.get_all("Tarea Contable", fields=legacy_fields, order_by="creation asc", limit_page_length=0):
        task_name = frappe.db.get_value("Task", {"old_tarea_id": legacy.name}, "name") or find_equivalent_task(legacy)
        if task_name:
            backfill_existing_task(task_name, legacy)
        else:
            task_name = create_task_from_legacy(legacy)
        task_map[legacy.name] = task_name
    return task_map



def find_equivalent_task(legacy):
    candidates = frappe.get_all(
        "Task",
        filters={
            "subject": legacy.titulo or legacy.name,
            "cliente": legacy.cliente,
            "periodo": legacy.periodo,
        },
        fields=["name", "encargo_contable", "tipo_de_tarea", "status", "exp_end_date", "description", "old_tarea_id"],
        limit_page_length=10,
    )
    expected_status = map_legacy_status(legacy.estado)
    for task in candidates:
        if task.old_tarea_id:
            continue
        if normalize_value(task.encargo_contable) != normalize_value(legacy.encargo_contable):
            continue
        if normalize_value(task.tipo_de_tarea) != normalize_value(legacy.tipo_de_tarea):
            continue
        if normalize_value(task.status) != normalize_value(expected_status):
            continue
        if normalize_value(task.exp_end_date) != normalize_value(legacy.fecha_de_vencimiento):
            continue
        if normalize_value(task.description) != normalize_value(legacy.notas):
            continue
        return task.name
    return None



def backfill_existing_task(task_name, legacy):
    task = frappe.db.get_value(
        "Task",
        task_name,
        [
            "name",
            "cliente",
            "company",
            "encargo_contable",
            "periodo",
            "tipo_de_tarea",
            "status",
            "exp_end_date",
            "description",
            "estado_aprobacion",
            "fecha_envio_revision",
            "revisado_por_supervisor",
            "fecha_revision_supervisor",
            "aprobado_por_socio",
            "fecha_aprobacion_socio",
            "comentarios_supervisor",
            "comentarios_socio",
            "old_tarea_id",
            "_assign",
        ],
        as_dict=True,
    )
    if not task:
        return

    updates = {}
    field_map = {
        "cliente": legacy.cliente,
        "company": legacy.company,
        "encargo_contable": legacy.encargo_contable,
        "periodo": legacy.periodo,
        "tipo_de_tarea": legacy.tipo_de_tarea,
        "estado_aprobacion": legacy.estado_aprobacion,
        "fecha_envio_revision": legacy.fecha_envio_revision,
        "revisado_por_supervisor": legacy.revisado_por_supervisor,
        "fecha_revision_supervisor": legacy.fecha_revision_supervisor,
        "aprobado_por_socio": legacy.aprobado_por_socio,
        "fecha_aprobacion_socio": legacy.fecha_aprobacion_socio,
        "comentarios_supervisor": legacy.comentarios_supervisor,
        "comentarios_socio": legacy.comentarios_socio,
        "old_tarea_id": legacy.name,
    }
    for fieldname, value in field_map.items():
        if value and not task.get(fieldname):
            updates[fieldname] = value

    if legacy.asignado_a and not task.get("_assign"):
        updates["_assign"] = json.dumps([legacy.asignado_a])

    if updates:
        frappe.db.set_value("Task", task_name, updates, update_modified=False)



def create_task_from_legacy(legacy):
    task = frappe.new_doc("Task")
    task.subject = legacy.titulo or legacy.name
    task.cliente = legacy.cliente
    task.company = legacy.company
    task.encargo_contable = legacy.encargo_contable
    task.periodo = legacy.periodo
    task.tipo_de_tarea = legacy.tipo_de_tarea
    task.status = map_legacy_status(legacy.estado)
    task.exp_end_date = legacy.fecha_de_vencimiento
    task.description = legacy.notas
    task.estado_aprobacion = legacy.estado_aprobacion or "Borrador"
    task.fecha_envio_revision = legacy.fecha_envio_revision
    task.revisado_por_supervisor = legacy.revisado_por_supervisor
    task.fecha_revision_supervisor = legacy.fecha_revision_supervisor
    task.aprobado_por_socio = legacy.aprobado_por_socio
    task.fecha_aprobacion_socio = legacy.fecha_aprobacion_socio
    task.comentarios_supervisor = legacy.comentarios_supervisor
    task.comentarios_socio = legacy.comentarios_socio
    task.old_tarea_id = legacy.name
    task.flags.ignore_mandatory = True
    task.insert(ignore_permissions=True)
    if legacy.asignado_a:
        frappe.db.set_value("Task", task.name, "_assign", json.dumps([legacy.asignado_a]), update_modified=False)
    return task.name



def backfill_documento_contable_refs(task_map):
    if not frappe.db.exists("DocType", "Documento Contable"):
        return
    if not frappe.db.has_column("Documento Contable", "task") or not frappe.db.has_column("Documento Contable", "tarea_contable"):
        return

    rows = frappe.db.sql(
        """
        select name, task, tarea_contable
        from `tabDocumento Contable`
        where ifnull(tarea_contable, '') != ''
        """,
        as_dict=True,
    )
    for row in rows:
        if row.task:
            continue
        task_name = resolve_task_name(task_map, row.tarea_contable)
        if task_name:
            frappe.db.set_value("Documento Contable", row.name, "task", task_name, update_modified=False)



def relink_supporting_records(task_map):
    if not task_map:
        return

    legacy_names = list(task_map.keys())
    for doctype, doctype_field, name_field in REFERENCE_MAPPERS:
        if not frappe.db.exists("DocType", doctype):
            continue
        if not frappe.db.has_column(doctype, doctype_field) or not frappe.db.has_column(doctype, name_field):
            continue

        rows = frappe.get_all(
            doctype,
            filters={doctype_field: "Tarea Contable", name_field: ["in", legacy_names]},
            fields=["name", name_field],
            limit_page_length=0,
        )
        for row in rows:
            task_name = resolve_task_name(task_map, row.get(name_field))
            if not task_name:
                continue
            frappe.db.set_value(
                doctype,
                row.name,
                {doctype_field: "Task", name_field: task_name},
                update_modified=False,
            )



def resolve_task_name(task_map, legacy_name):
    if not legacy_name:
        return None
    return task_map.get(legacy_name) or frappe.db.get_value("Task", {"old_tarea_id": legacy_name}, "name")



def map_legacy_status(status):
    return LEGACY_STATUS_MAP.get(status, "Open")



def normalize_value(value):
    return str(value or "")
