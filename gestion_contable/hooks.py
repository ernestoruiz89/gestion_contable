app_name = "gestion_contable"
app_title = "Gestion Contable"
app_publisher = "Despacho"
app_description = "Aplicacion completa para la gestion de clientes, periodos y tareas contables."
app_email = "contacto@despacho.com"
app_license = "mit"

after_install = "gestion_contable.gestion_contable.setup.bootstrap.after_install"
after_migrate = "gestion_contable.gestion_contable.setup.bootstrap.after_migrate"

doc_events = {
    "Sales Invoice": {
        "on_submit": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_sales_invoice",
        "on_cancel": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_sales_invoice",
        "on_update_after_submit": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_sales_invoice",
    },
    "Payment Entry": {
        "on_submit": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_payment_entry",
        "on_cancel": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_payment_entry",
        "on_update_after_submit": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_payment_entry",
    },
    "Timesheet": {
        "on_update": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_timesheet",
        "on_submit": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_timesheet",
        "on_cancel": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_timesheet",
        "on_update_after_submit": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_timesheet",
        "on_trash": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_timesheet",
    },
    "Seguimiento Cobranza": {
        "on_update": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_seguimiento_cobranza",
        "on_trash": "gestion_contable.gestion_contable.services.encargos.sync.sync_from_seguimiento_cobranza",
    },
    "Task": {
        "validate": "gestion_contable.gestion_contable.overrides.task.validate_tarea_despacho"
    }
}

scheduler_events = {
    "daily": [
        "gestion_contable.gestion_contable.utils.retention.sync_retention_alerts",
        "gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente.enviar_alertas_correo_requerimientos",
    ]
}

fixtures = [
    {
        "doctype": "Role",
        "filters": [["name", "in", [
            "Contador del Despacho",
            "Supervisor del Despacho",
            "Socio del Despacho",
            "Auxiliar Contable del Despacho"
        ]]],
    },
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["Sales Invoice", "Task"]], 
            ["fieldname", "in", [
                "encargo_contable",
                "cliente_contable",
                "cliente",
                "company",
                "servicio_contable",
                "contrato_comercial",
                "periodo",
                "tipo_de_servicio",
                "tipo_de_tarea",
                "estado_aprobacion",
                "fecha_envio_revision",
                "revisado_por_supervisor",
                "fecha_revision_supervisor",
                "aprobado_por_socio",
                "fecha_aprobacion_socio",
                "comentarios_supervisor",
                "comentarios_socio",
                "old_tarea_id"
        ]]],
    }
]

portal_menu_items = [
    {"title": "Portal Cliente", "route": "/portal-cliente"},
    {"title": "Requerimientos", "route": "/requerimientos-cliente"},
    {"title": "Mis Entregables", "route": "/entregables-cliente"},
]

has_website_permission = {
    "Requerimiento Cliente": "gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente.has_website_permission",
    "Entregable Cliente": "gestion_contable.gestion_contable.doctype.entregable_cliente.entregable_cliente.has_website_permission"
}
