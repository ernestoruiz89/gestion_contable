import frappe
from frappe import _

from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import validate_periodo_operativo
from gestion_contable.gestion_contable.utils.operational_context import sync_operational_company


CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
    "Auxiliar Contable del Despacho",
)
CONTENT_FIELDS = (
    "subject",
    "cliente",
    "company",
    "encargo_contable",
    "periodo",
    "tipo_de_tarea",
    "exp_end_date",
    "description",
)


def validate_tarea_despacho(doc, method=None):
    # Only apply these validations if the Task belongs to the Despacho workflows (has a client)
    if not doc.get("cliente") and not doc.get("encargo_contable"):
        return

    _sincronizar_desde_encargo(doc)
    _validar_cliente_activo(doc)
    
    doc.company = sync_operational_company(
        doc,
        cliente=doc.get("cliente"),
        periodo=doc.get("periodo"),
        encargo_name=doc.get("encargo_contable"),
        label=_("la tarea contable"),
    )

    if doc.get("periodo"):
        validate_periodo_operativo(
            doc.get("periodo"),
            cliente=doc.get("cliente"),
            company=doc.get("company"),
            label=_("la tarea contable"),
        )

    _validar_encargo_consistente(doc)

    validate_governance(
        doc,
        content_fields=CONTENT_FIELDS,
        create_roles=CREATE_ROLES,
        draft_roles=CREATE_ROLES,
        aux_editable_fields=CONTENT_FIELDS + ("status", "_assign", "comentarios_supervisor", "comentarios_socio"),
        aux_owner_field=None,
        label=_("la tarea contable"),
    )


def _sincronizar_desde_encargo(doc):
    if not doc.get("encargo_contable"):
        return
    encargo = frappe.db.get_value(
        "Encargo Contable",
        doc.get("encargo_contable"),
        ["name", "cliente", "periodo_referencia", "estado", "company"],
        as_dict=True,
    )
    if not encargo:
        frappe.throw(_("El encargo contable <b>{0}</b> no existe.").format(doc.get("encargo_contable")), title=_("Encargo Invalido"))
    
    if doc.is_new() and encargo.estado in ("Cerrado", "Cancelado"):
        frappe.throw(_("No puedes crear tareas operativas para un encargo con estado <b>{0}</b>.").format(encargo.estado), title=_("Encargo Cerrado"))

    if not doc.get("cliente"):
        doc.cliente = encargo.cliente
    if not doc.get("periodo") and encargo.periodo_referencia:
        doc.periodo = encargo.periodo_referencia
    if not doc.get("company") and encargo.company:
        doc.company = encargo.company


def _validar_cliente_activo(doc):
    if not doc.get("cliente"):
        return
    estado = frappe.db.get_value("Cliente Contable", doc.get("cliente"), "estado")
    if estado != "Activo":
        frappe.throw(_("No puedes gestionar tareas operativas para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(doc.get("cliente"), estado), title=_("Cliente Inactivo"))


def _validar_encargo_consistente(doc):
    if not doc.get("encargo_contable"):
        return
    encargo = frappe.db.get_value(
        "Encargo Contable",
        doc.get("encargo_contable"),
        ["cliente", "periodo_referencia", "company"],
        as_dict=True,
    )
    if not encargo:
        return
    inconsistencias = []
    if doc.get("cliente") and doc.get("cliente") != encargo.cliente:
        inconsistencias.append(_("Cliente"))
    if doc.get("periodo") and encargo.periodo_referencia and doc.get("periodo") != encargo.periodo_referencia:
        inconsistencias.append(_("Periodo"))
    if doc.get("company") and encargo.company and doc.get("company") != encargo.company:
        inconsistencias.append(_("Compania"))
    if inconsistencias:
        frappe.throw(
            _("La tarea no coincide con el encargo <b>{0}</b>. Ajusta: <b>{1}</b>.")
            .format(doc.get("encargo_contable"), ", ".join(inconsistencias)),
            title=_("Inconsistencia de Trazabilidad"),
        )
