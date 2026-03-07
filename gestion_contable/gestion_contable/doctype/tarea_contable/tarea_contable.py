import frappe
from frappe import _
from frappe.model.document import Document

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import validate_periodo_operativo
from gestion_contable.gestion_contable.utils.governance import (
    ESTADO_APROBACION_APROBADO,
    ESTADO_APROBACION_DEVUELTO,
    validate_governance,
)
from gestion_contable.gestion_contable.utils.operational_context import sync_operational_company
from gestion_contable.gestion_contable.utils.security import ensure_manager, is_auxiliar


TAREA_CONTENT_FIELDS = (
    "titulo",
    "cliente",
    "company",
    "periodo",
    "encargo_contable",
    "tipo_de_tarea",
    "estado",
    "fecha_de_vencimiento",
    "asignado_a",
    "notas",
)

TAREA_CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)

TAREA_DRAFT_ROLES = TAREA_CREATE_ROLES + ("Auxiliar Contable del Despacho",)
AUXILIAR_EDITABLE_FIELDS = ("estado", "notas")


class TareaContable(Document):
    def autoname(self):
        base_title = (self.titulo or "").strip()

        if not base_title and self.tipo_de_tarea and self.cliente and self.periodo:
            base_title = f"{self.tipo_de_tarea} - {self.cliente} - {self.periodo}"

        if not base_title:
            base_title = f"Tarea - {frappe.generate_hash(length=8)}"

        unique_title = self._build_unique_title(base_title)
        self.titulo = unique_title
        self.name = unique_title

    def _build_unique_title(self, base_title):
        candidate = base_title

        if not frappe.db.exists("Tarea Contable", candidate):
            return candidate

        index = 2
        while frappe.db.exists("Tarea Contable", f"{base_title} ({index})"):
            index += 1

        return f"{base_title} ({index})"

    def validate(self):
        self.validar_encargo_consistente()
        self.validar_cliente_activo()
        self.sincronizar_company_operativa()
        self.validar_periodo_abierto()
        self.validar_gobierno_operativo()
        self.sincronizar_estado_operativo()

    def validar_gobierno_operativo(self):
        validate_governance(
            self,
            content_fields=TAREA_CONTENT_FIELDS,
            create_roles=TAREA_CREATE_ROLES,
            draft_roles=TAREA_DRAFT_ROLES,
            aux_editable_fields=AUXILIAR_EDITABLE_FIELDS,
            aux_owner_field="asignado_a",
            label=_("la tarea"),
        )

        if is_auxiliar() and self.estado == "Descartada":
            frappe.throw(
                _("Solo Supervisor, Socio, Contador o System Manager pueden descartar tareas."),
                frappe.PermissionError,
            )

    def sincronizar_estado_operativo(self):
        previous = None if self.is_new() else self.get_doc_before_save()

        if self.estado_aprobacion == ESTADO_APROBACION_APROBADO:
            self.estado = "Completada"
            return

        if previous and previous.estado_aprobacion == ESTADO_APROBACION_APROBADO and self.estado == "Completada":
            self.estado = "En Revisi\u00f3n"

        if self.estado == "Completada" and self.estado_aprobacion != ESTADO_APROBACION_APROBADO:
            frappe.throw(
                _("Solo una tarea aprobada por Socio puede quedar Completada."),
                frappe.PermissionError,
            )

        if previous and previous.estado_aprobacion == ESTADO_APROBACION_DEVUELTO and self.estado == "Completada":
            self.estado = "En Revisi\u00f3n"

    def validar_encargo_consistente(self):
        if not self.encargo_contable:
            return

        encargo = frappe.db.get_value(
            "Encargo Contable",
            self.encargo_contable,
            ["name", "cliente", "periodo_referencia", "estado", "company"],
            as_dict=True,
        )

        if not encargo:
            frappe.throw(
                _("El encargo contable <b>{0}</b> no existe.").format(self.encargo_contable),
                title=_("Encargo Invalido"),
            )

        if self.is_new() and encargo.estado in ("Cerrado", "Cancelado"):
            frappe.throw(
                _("No se pueden crear tareas en un encargo <b>{0}</b> con estado <b>{1}</b>.").format(
                    encargo.name, encargo.estado
                ),
                title=_("Encargo Cerrado"),
            )

        if self.cliente and self.cliente != encargo.cliente:
            frappe.throw(
                _("El cliente de la tarea no coincide con el cliente del encargo seleccionado."),
                title=_("Inconsistencia de Encargo"),
            )
        if not self.cliente:
            self.cliente = encargo.cliente

        if encargo.periodo_referencia:
            if self.periodo and self.periodo != encargo.periodo_referencia:
                frappe.throw(
                    _("El periodo de la tarea no coincide con el periodo referencia del encargo."),
                    title=_("Inconsistencia de Encargo"),
                )
            if not self.periodo:
                self.periodo = encargo.periodo_referencia

        if encargo.company:
            if self.company and self.company != encargo.company:
                frappe.throw(
                    _("La compania de la tarea no coincide con la compania del encargo seleccionado."),
                    title=_("Inconsistencia de Encargo"),
                )
            self.company = encargo.company

    def validar_cliente_activo(self):
        if self.cliente:
            estado = frappe.db.get_value("Cliente Contable", self.cliente, "estado")
            if estado != "Activo":
                frappe.throw(
                    _("No se pueden crear tareas para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(
                        self.cliente, estado
                    ),
                    title=_("Cliente Inactivo"),
                )

    def sincronizar_company_operativa(self):
        self.company = sync_operational_company(
            self,
            cliente=self.cliente,
            periodo=self.periodo,
            encargo_name=self.encargo_contable,
            label=_("la tarea"),
        )

    def obtener_company_periodo(self):
        return self.company

    def validar_periodo_abierto(self):
        if not self.periodo:
            return
        validate_periodo_operativo(
            self.periodo,
            cliente=self.cliente,
            company=self.obtener_company_periodo(),
            label=_("la tarea"),
        )

    def before_rename(self, old, new, merge=False):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden renombrar tareas."))

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar tareas."))
