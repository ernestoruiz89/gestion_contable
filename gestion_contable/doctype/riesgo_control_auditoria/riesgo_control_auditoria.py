import frappe
from frappe import _
from frappe.model.document import Document

from gestion_contable.gestion_contable.doctype.expediente_auditoria.expediente_auditoria import calcular_resumen_expediente
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "expediente_auditoria",
    "area_auditoria",
    "proceso",
    "afirmacion",
    "riesgo",
    "control_clave",
    "tipo_control",
    "frecuencia_control",
    "riesgo_inherente",
    "riesgo_residual",
    "respuesta_auditoria",
    "procedimiento_planificado",
    "estado_evaluacion",
    "papel_trabajo_principal",
)
ESTADOS_EXPEDIENTE_BLOQUEADOS = ("Cerrada", "Archivada", "Cancelada")


class RiesgoControlAuditoria(Document):
    def autoname(self):
        self.codigo = self._build_codigo(self.codigo)
        self.name = self.codigo

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar la matriz riesgo-control."))
        expediente = self.sincronizar_desde_expediente()
        self.validar_expediente_abierto(expediente)
        self.validar_papel_principal()
        validate_governance(self, content_fields=CONTENT_FIELDS, create_roles=CREATE_ROLES, draft_roles=CREATE_ROLES, label=_("la linea riesgo-control"))

    def on_update(self):
        self.actualizar_resumen_expediente()

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar lineas de la matriz riesgo-control."))

    def after_delete(self):
        self.actualizar_resumen_expediente()

    def _build_codigo(self, current_code=None):
        if current_code:
            return current_code
        prefix = (self.expediente_auditoria or "AUD").replace(" ", "-")
        index = frappe.db.count("Riesgo Control Auditoria", {"expediente_auditoria": self.expediente_auditoria}) + 1
        candidate = f"{prefix}-RC-{index:03d}"
        while frappe.db.exists("Riesgo Control Auditoria", candidate):
            index += 1
            candidate = f"{prefix}-RC-{index:03d}"
        return candidate

    def obtener_expediente(self):
        if not self.expediente_auditoria:
            frappe.throw(_("Debes indicar el expediente de auditoria."), title=_("Expediente Requerido"))
        expediente = frappe.db.get_value(
            "Expediente Auditoria",
            self.expediente_auditoria,
            ["name", "encargo_contable", "cliente", "periodo", "company", "estado_expediente"],
            as_dict=True,
        )
        if not expediente:
            frappe.throw(_("El expediente de auditoria <b>{0}</b> no existe.").format(self.expediente_auditoria), title=_("Expediente Invalido"))
        return expediente

    def sincronizar_desde_expediente(self):
        expediente = self.obtener_expediente()
        self.encargo_contable = expediente.encargo_contable
        self.cliente = expediente.cliente
        self.periodo = expediente.periodo
        self.company = expediente.company
        self.estado_evaluacion = self.estado_evaluacion or "Planeado"
        return expediente

    def validar_expediente_abierto(self, expediente):
        if expediente.estado_expediente in ESTADOS_EXPEDIENTE_BLOQUEADOS:
            frappe.throw(_("No puedes modificar la matriz riesgo-control cuando el expediente esta en estado <b>{0}</b>.").format(expediente.estado_expediente), title=_("Expediente Cerrado"))
        if self.papel_trabajo_principal:
            data = frappe.db.get_value("Papel Trabajo Auditoria", self.papel_trabajo_principal, ["name", "expediente_auditoria"], as_dict=True)
            if not data:
                frappe.throw(_("El papel de trabajo principal seleccionado no existe."), title=_("Papel Invalido"))
            if data.expediente_auditoria != self.expediente_auditoria:
                frappe.throw(_("El papel de trabajo principal debe pertenecer al mismo expediente."), title=_("Trazabilidad Invalida"))

    def validar_papel_principal(self):
        if self.estado_evaluacion == "Validado" and not self.papel_trabajo_principal:
            frappe.throw(_("Debes vincular un papel de trabajo principal antes de validar la linea riesgo-control."), title=_("Papel Requerido"))

    def actualizar_resumen_expediente(self):
        if not self.expediente_auditoria or not frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            return
        frappe.db.set_value("Expediente Auditoria", self.expediente_auditoria, calcular_resumen_expediente(self.expediente_auditoria), update_modified=False)
