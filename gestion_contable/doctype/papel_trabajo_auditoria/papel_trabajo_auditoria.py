import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate

from gestion_contable.gestion_contable.doctype.expediente_auditoria.expediente_auditoria import calcular_resumen_expediente
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, has_any_role, is_auxiliar

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
    "Auxiliar Contable del Despacho",
)
AUX_FIELDS = (
    "expediente_auditoria",
    "riesgo_control_auditoria",
    "documento_contable",
    "evidencia_documental_file",
    "task",
    "tipo_papel",
    "referencia",
    "titulo",
    "objetivo_prueba",
    "procedimiento_ejecutado",
    "resultado",
    "conclusion",
    "estado_papel",
    "notas",
)
CONTENT_FIELDS = AUX_FIELDS + (
    "codigo_evidencia_documental",
    "version_evidencia_documental",
    "hash_evidencia_sha256",
    "preparado_por",
    "fecha_preparacion",
    "revisado_por",
    "fecha_revision",
)
ESTADOS_EXPEDIENTE_BLOQUEADOS = ("Cerrada", "Archivada", "Cancelada")


class PapelTrabajoAuditoria(Document):
    def autoname(self):
        self.codigo = self._build_codigo(self.codigo)
        self.name = self.codigo

    def validate(self):
        if not has_any_role(CREATE_ROLES):
            frappe.throw(_("No tienes permisos para gestionar papeles de trabajo de auditoria."), frappe.PermissionError)
        expediente = self.sincronizar_desde_expediente()
        self.sincronizar_preparacion()
        self.validar_expediente_abierto(expediente)
        self.validar_relaciones_trazabilidad()
        self.validar_estado_papel()
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            aux_editable_fields=AUX_FIELDS,
            aux_owner_field="preparado_por",
            label=_("el papel de trabajo"),
        )
        if is_auxiliar() and self.estado_papel in ("Aprobado", "Cerrado"):
            frappe.throw(_("Como Auxiliar no puedes aprobar ni cerrar papeles de trabajo."), frappe.PermissionError)

    def on_update(self):
        self.actualizar_resumen_expediente()

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar papeles de trabajo."))

    def after_delete(self):
        self.actualizar_resumen_expediente()

    def _build_codigo(self, current_code=None):
        if current_code:
            return current_code
        prefix = (self.expediente_auditoria or "AUD").replace(" ", "-")
        index = frappe.db.count("Papel Trabajo Auditoria", {"expediente_auditoria": self.expediente_auditoria}) + 1
        candidate = f"{prefix}-PT-{index:03d}"
        while frappe.db.exists("Papel Trabajo Auditoria", candidate):
            index += 1
            candidate = f"{prefix}-PT-{index:03d}"
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
        self.estado_papel = self.estado_papel or "Borrador"
        return expediente

    def sincronizar_preparacion(self):
        self.preparado_por = self.preparado_por or frappe.session.user
        if self.estado_papel != "Borrador" and not self.fecha_preparacion:
            self.fecha_preparacion = nowdate()
        if self.revisado_por and not self.fecha_revision:
            self.fecha_revision = now_datetime()

    def validar_expediente_abierto(self, expediente):
        if expediente.estado_expediente in ESTADOS_EXPEDIENTE_BLOQUEADOS:
            frappe.throw(_("No puedes registrar ni modificar papeles de trabajo cuando el expediente esta en estado <b>{0}</b>." ).format(expediente.estado_expediente), title=_("Expediente Cerrado"))

    def validar_relaciones_trazabilidad(self):
        if self.riesgo_control_auditoria:
            riesgo = frappe.db.get_value("Riesgo Control Auditoria", self.riesgo_control_auditoria, ["name", "expediente_auditoria"], as_dict=True)
            if not riesgo:
                frappe.throw(_("La linea riesgo-control vinculada no existe."), title=_("Riesgo Invalido"))
            if riesgo.expediente_auditoria != self.expediente_auditoria:
                frappe.throw(_("La linea riesgo-control debe pertenecer al mismo expediente."), title=_("Trazabilidad Invalida"))

        documento = None
        if self.documento_contable:
            documento = frappe.db.get_value(
                "Documento Contable",
                self.documento_contable,
                ["name", "encargo_contable", "cliente", "company", "periodo"],
                as_dict=True,
            )
            if not documento:
                frappe.throw(_("El documento contable vinculado no existe."), title=_("Documento Invalido"))
            self._validar_contexto_relacionado(documento.encargo_contable, documento.cliente, documento.company, documento.periodo, _("documento contable"))

        if self.evidencia_documental_file:
            if not self.documento_contable:
                frappe.throw(_("Debes seleccionar el documento contable antes de vincular una evidencia especifica."), title=_("Documento Requerido"))
            evidencia = self._obtener_evidencia_documental()
            self.codigo_evidencia_documental = evidencia.get("codigo_documental") or evidencia.get("descripcion_evidencia")
            self.version_evidencia_documental = evidencia.get("numero_version") or 1
            self.hash_evidencia_sha256 = evidencia.get("hash_sha256")
        else:
            self.codigo_evidencia_documental = None
            self.version_evidencia_documental = None
            self.hash_evidencia_sha256 = None
            if self.documento_contable:
                frappe.throw(_("Debes seleccionar la evidencia especifica del documento para cerrar la trazabilidad del papel de trabajo."), title=_("Evidencia Requerida"))

        if self.task:
            tarea = frappe.db.get_value("Task", self.task, ["name", "encargo_contable", "cliente", "company", "periodo"], as_dict=True)
            if not tarea:
                frappe.throw(_("La tarea vinculada no existe."), title=_("Tarea Invalida"))
            self._validar_contexto_relacionado(tarea.encargo_contable, tarea.cliente, tarea.company, tarea.periodo, _("tarea vinculada"))

    def _validar_contexto_relacionado(self, encargo_contable, cliente, company, periodo, label):
        if encargo_contable and self.encargo_contable and encargo_contable != self.encargo_contable:
            frappe.throw(_("La referencia de {0} debe pertenecer al mismo encargo del expediente.").format(label), title=_("Trazabilidad Invalida"))
        if cliente and self.cliente and cliente != self.cliente:
            frappe.throw(_("La referencia de {0} debe pertenecer al mismo cliente del expediente.").format(label), title=_("Trazabilidad Invalida"))
        if company and self.company and company != self.company:
            frappe.throw(_("La referencia de {0} debe pertenecer a la misma compania del expediente.").format(label), title=_("Trazabilidad Invalida"))
        if periodo and self.periodo and periodo != self.periodo:
            frappe.throw(_("La referencia de {0} debe pertenecer al mismo periodo del expediente.").format(label), title=_("Trazabilidad Invalida"))

    def _obtener_evidencia_documental(self):
        documento = frappe.get_doc("Documento Contable", self.documento_contable)
        for row in documento.evidencias_documentales or []:
            if row.archivo_file == self.evidencia_documental_file:
                return {
                    "name": row.name,
                    "codigo_documental": row.codigo_documental,
                    "descripcion_evidencia": row.descripcion_evidencia,
                    "numero_version": row.numero_version,
                    "hash_sha256": row.hash_sha256,
                }
        frappe.throw(_("La evidencia seleccionada no pertenece al documento contable vinculado."), title=_("Evidencia Invalida"))

    def validar_estado_papel(self):
        if self.estado_papel in ("Aprobado", "Cerrado") and not self.revisado_por:
            frappe.throw(_("Debes indicar quien reviso tecnicamente el papel antes de aprobarlo o cerrarlo."), title=_("Revision Requerida"))
        if self.estado_papel == "Cerrado" and not (self.conclusion or "").strip():
            frappe.throw(_("Debes documentar la conclusion para cerrar el papel de trabajo."), title=_("Conclusion Requerida"))

    def actualizar_resumen_expediente(self):
        if not self.expediente_auditoria or not frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            return
        frappe.db.set_value("Expediente Auditoria", self.expediente_auditoria, calcular_resumen_expediente(self.expediente_auditoria), update_modified=False)


@frappe.whitelist()
def get_documento_evidencias(documento_contable):
    if not documento_contable or not frappe.db.exists("Documento Contable", documento_contable):
        return []

    documento = frappe.get_doc("Documento Contable", documento_contable)
    evidencias = []
    for row in documento.evidencias_documentales or []:
        if not row.archivo_file:
            continue
        label = row.descripcion_evidencia or row.codigo_documental or row.archivo_file
        if row.numero_version:
            label = f"{label} (v{row.numero_version})"
        evidencias.append(
            {
                "file": row.archivo_file,
                "label": label,
                "codigo_documental": row.codigo_documental,
                "numero_version": row.numero_version,
                "hash_sha256": row.hash_sha256,
            }
        )
    return evidencias
