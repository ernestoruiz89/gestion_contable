import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
import json

def execute():
    # 1. Ensure Custom Fields exist in Task
    create_task_custom_fields()
    
    # 2. Migrate existing "Tarea Contable" records to "Task"
    migrate_records()

    # 3. Update references in "Documento Contable"
    update_documento_contable_references()

def create_task_custom_fields():
    custom_fields = [
        {"fieldname": "cliente", "label": "Cliente", "fieldtype": "Link", "options": "Cliente Contable", "insert_after": "project"},
        {"fieldname": "encargo_contable", "label": "Encargo Contable", "fieldtype": "Link", "options": "Encargo Contable", "insert_after": "cliente"},
        {"fieldname": "periodo", "label": "Periodo", "fieldtype": "Link", "options": "Periodo Contable", "insert_after": "encargo_contable"},
        {"fieldname": "tipo_de_tarea", "label": "Tipo de Tarea", "fieldtype": "Select", "options": "\nImpuestos\nNómina\nCierre Contable\nAuditoría\nConciliación Bancaria\nDeclaración DGI\nEstados Financieros\nFacturación\nAtención a Requerimiento\nTrámite DGI\nConsultoría\nOtro", "insert_after": "periodo"},
        {"fieldname": "estado_aprobacion", "label": "Estado de Aprobacion", "fieldtype": "Select", "options": "Borrador\nRevision Supervisor\nRevision Socio\nAprobado\nDevuelto", "default": "Borrador", "insert_after": "tipo_de_tarea"},
        {"fieldname": "revisado_por_supervisor", "label": "Revisado por Supervisor", "fieldtype": "Link", "options": "User", "insert_after": "estado_aprobacion"},
        {"fieldname": "aprobado_por_socio", "label": "Aprobado por Socio", "fieldtype": "Link", "options": "User", "insert_after": "revisado_por_supervisor"},
        {"fieldname": "fecha_envio_revision", "label": "Fecha Envio Revision", "fieldtype": "Datetime", "insert_after": "aprobado_por_socio"},
        {"fieldname": "fecha_revision_supervisor", "label": "Fecha Revision Supervisor", "fieldtype": "Datetime", "insert_after": "fecha_envio_revision"},
        {"fieldname": "fecha_aprobacion_socio", "label": "Fecha Aprobacion Socio", "fieldtype": "Datetime", "insert_after": "fecha_revision_supervisor"},
        {"fieldname": "comentarios_supervisor", "label": "Comentarios Supervisor", "fieldtype": "Small Text", "insert_after": "fecha_aprobacion_socio"},
        {"fieldname": "comentarios_socio", "label": "Comentarios Socio", "fieldtype": "Small Text", "insert_after": "comentarios_supervisor"},
        {"fieldname": "old_tarea_id", "label": "Old Tarea ID", "fieldtype": "Data", "hidden": 1, "insert_after": "comentarios_socio"}
    ]

    for field in custom_fields:
        create_custom_field("Task", field)

def migrate_records():
    tareas = frappe.get_all("Tarea Contable", fields=["*"])
    status_map = {
        "Pendiente": "Open",
        "En Proceso": "Working",
        "En Revisión": "Pending Review",
        "Completada": "Completed",
        "Descartada": "Cancelled"
    }

    for tarea in tareas:
        task = frappe.new_doc("Task")
        task.subject = tarea.titulo
        task.status = status_map.get(tarea.estado, "Open")
        task.exp_end_date = tarea.fecha_de_vencimiento
        task.cliente = tarea.cliente
        task.encargo_contable = tarea.encargo_contable
        task.periodo = tarea.periodo
        task.tipo_de_tarea = tarea.tipo_de_tarea
        task.estado_aprobacion = tarea.estado_aprobacion
        task.revisado_por_supervisor = tarea.revisado_por_supervisor
        task.aprobado_por_socio = tarea.aprobado_por_socio
        task.fecha_envio_revision = tarea.fecha_envio_revision
        task.fecha_revision_supervisor = tarea.fecha_revision_supervisor
        task.fecha_aprobacion_socio = tarea.fecha_aprobacion_socio
        task.comentarios_supervisor = tarea.comentarios_supervisor
        task.comentarios_socio = tarea.comentarios_socio
        task.description = tarea.notas
        
        # Legacy ID reference for Documento Contable link mapping
        task.old_tarea_id = tarea.name 
        
        # Set assignee if exists
        if tarea.asignado_a:
            task.append("assignees", {
                "user": tarea.asignado_a
            })

        task.flags.ignore_permissions = True
        task.flags.ignore_mandatory = True
        task.flags.ignore_validate = True
        task.insert()

def update_documento_contable_references():
    documentos = frappe.get_all("Documento Contable", fields=["name", "tarea_contable"])
    
    for doc in documentos:
        if doc.tarea_contable:
            # Find the new Task ID that corresponds to this old Tarea Contable
            new_task = frappe.db.get_value("Task", {"old_tarea_id": doc.tarea_contable}, "name")
            if new_task:
                frappe.db.set_value("Documento Contable", doc.name, "task", new_task, update_modified=False)
