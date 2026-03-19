import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

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
    "riesgo_control_auditoria",
    "papel_trabajo_auditoria",
    "titulo_hallazgo",
    "severidad",
    "criterio",
    "condicion",
    "causa",
    "efecto",
    "recomendacion",
)
ESTADOS_EXPEDIENTE_BLOQUEADOS = ("Cerrada", "Archivada", "Cancelada")


class HallazgoAuditoria(Document):
    def autoname(self):
        self.codigo = self._build_codigo(self.codigo)
        self.name = self.codigo

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar hallazgos de auditoria."))
        expediente = self.sincronizar_desde_expediente()
        self.validar_expediente_abierto(expediente)
        self.validar_relaciones_trazabilidad()
        self.validar_estado_hallazgo()
        validate_governance(self, content_fields=CONTENT_FIELDS, create_roles=CREATE_ROLES, draft_roles=CREATE_ROLES, label=_("el hallazgo"))

    def on_update(self):
        self.actualizar_resumen_expediente()

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar hallazgos de auditoria."))

    def after_delete(self):
        self.actualizar_resumen_expediente()

    def _build_codigo(self, current_code=None):
        if current_code:
            return current_code
        prefix = (self.expediente_auditoria or "AUD").replace(" ", "-")
        index = frappe.db.count("Hallazgo Auditoria", {"expediente_auditoria": self.expediente_auditoria}) + 1
        candidate = f"{prefix}-HA-{index:03d}"
        while frappe.db.exists("Hallazgo Auditoria", candidate):
            index += 1
            candidate = f"{prefix}-HA-{index:03d}"
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
        self.estado_hallazgo = self.estado_hallazgo or "Borrador"
        return expediente

    def validar_expediente_abierto(self, expediente):
        if expediente.estado_expediente in ESTADOS_EXPEDIENTE_BLOQUEADOS:
            frappe.throw(_("No puedes registrar ni modificar hallazgos cuando el expediente esta en estado <b>{0}</b>.").format(expediente.estado_expediente), title=_("Expediente Cerrado"))

    def validar_relaciones_trazabilidad(self):
        if self.riesgo_control_auditoria:
            riesgo = frappe.db.get_value("Riesgo Control Auditoria", self.riesgo_control_auditoria, ["name", "expediente_auditoria"], as_dict=True)
            if not riesgo:
                frappe.throw(_("La linea riesgo-control vinculada no existe."), title=_("Riesgo Invalido"))
            if riesgo.expediente_auditoria != self.expediente_auditoria:
                frappe.throw(_("La linea riesgo-control debe pertenecer al mismo expediente del hallazgo."), title=_("Trazabilidad Invalida"))
        if self.papel_trabajo_auditoria:
            papel = frappe.db.get_value("Papel Trabajo Auditoria", self.papel_trabajo_auditoria, ["name", "expediente_auditoria"], as_dict=True)
            if not papel:
                frappe.throw(_("El papel de trabajo vinculado no existe."), title=_("Papel Invalido"))
            if papel.expediente_auditoria != self.expediente_auditoria:
                frappe.throw(_("El papel de trabajo debe pertenecer al mismo expediente del hallazgo."), title=_("Trazabilidad Invalida"))

    def validar_estado_hallazgo(self):
        if self.estado_hallazgo in ("Resuelto", "Cerrado"):
            self.fecha_cierre_hallazgo = self.fecha_cierre_hallazgo or nowdate()
        if self.estado_hallazgo == "Cerrado" and not (self.respuesta_administracion or "").strip():
            frappe.throw(_("Debes documentar la respuesta de administracion antes de cerrar el hallazgo."), title=_("Respuesta Requerida"))

    def actualizar_resumen_expediente(self):
        if not self.expediente_auditoria or not frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            return
        frappe.db.set_value("Expediente Auditoria", self.expediente_auditoria, calcular_resumen_expediente(self.expediente_auditoria), update_modified=False)
