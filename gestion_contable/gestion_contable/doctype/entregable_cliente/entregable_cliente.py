import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente import actualizar_seguimiento_requerimiento
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, get_current_user, has_any_role, is_auxiliar

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
    "Auxiliar Contable del Despacho",
)
CONTENT_FIELDS = (
    "requerimiento_cliente",
    "company",
    "tipo_entregable",
    "descripcion",
    "obligatorio",
    "fecha_compromiso",
)
AUX_FIELDS = CONTENT_FIELDS + (
    "responsable_cliente",
    "estado_entregable",
    "documento_contable",
    "observaciones",
    "notas_revision",
)
ESTADOS_BLOQUEADOS = ("Cerrado", "Cancelado")


class EntregableCliente(Document):
    def autoname(self):
        self.codigo = self._build_codigo(self.codigo)
        self.name = self.codigo

    def validate(self):
        if not has_any_role(CREATE_ROLES):
            frappe.throw(_("No tienes permisos para gestionar entregables de clientes."), frappe.PermissionError)
        requerimiento = self.sincronizar_desde_requerimiento()
        self.validar_requerimiento_abierto(requerimiento)
        self.validar_documento_consistente()
        self.sincronizar_estado_entregable()
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            aux_editable_fields=AUX_FIELDS,
            aux_owner_field="responsable_interno",
            label=_("el entregable"),
        )
        if is_auxiliar() and self.estado_entregable in ("Validado", "No Aplica"):
            frappe.throw(_("Como Auxiliar no puedes validar ni marcar entregables como No Aplica."), frappe.PermissionError)

    def on_update(self):
        if self.documento_contable and frappe.db.exists("Documento Contable", self.documento_contable):
            documento = frappe.db.get_value("Documento Contable", self.documento_contable, ["name", "entregable_cliente"], as_dict=True)
            if documento and documento.entregable_cliente != self.name:
                frappe.db.set_value("Documento Contable", documento.name, "entregable_cliente", self.name, update_modified=False)
        self.actualizar_resumen_requerimiento()

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar entregables de clientes."))

    def after_delete(self):
        self.actualizar_resumen_requerimiento()

    def _build_codigo(self, current_code=None):
        if current_code:
            return current_code
        prefix = (self.requerimiento_cliente or "REQ").replace(" ", "-")
        index = frappe.db.count("Entregable Cliente", {"requerimiento_cliente": self.requerimiento_cliente}) + 1
        candidate = f"{prefix}-EC-{index:03d}"
        while frappe.db.exists("Entregable Cliente", candidate):
            index += 1
            candidate = f"{prefix}-EC-{index:03d}"
        return candidate

    def obtener_requerimiento(self):
        if not self.requerimiento_cliente:
            frappe.throw(_("Debes indicar el requerimiento cliente."), title=_("Requerimiento Requerido"))
        requerimiento = frappe.db.get_value(
            "Requerimiento Cliente",
            self.requerimiento_cliente,
            [
                "name",
                "cliente",
                "company",
                "encargo_contable",
                "periodo",
                "responsable_interno",
                "estado_requerimiento",
                "fecha_solicitud",
                "fecha_vencimiento",
                "fecha_envio",
            ],
            as_dict=True,
        )
        if not requerimiento:
            frappe.throw(_("El requerimiento cliente <b>{0}</b> no existe.").format(self.requerimiento_cliente), title=_("Requerimiento Invalido"))
        return requerimiento

    def sincronizar_desde_requerimiento(self):
        requerimiento = self.obtener_requerimiento()
        self.cliente = requerimiento.cliente
        self.company = requerimiento.company
        self.encargo_contable = requerimiento.encargo_contable
        self.periodo = requerimiento.periodo
        self.responsable_interno = requerimiento.responsable_interno or get_current_user()
        if not self.fecha_solicitud:
            self.fecha_solicitud = requerimiento.fecha_envio or requerimiento.fecha_solicitud
        if not self.fecha_compromiso:
            self.fecha_compromiso = requerimiento.fecha_vencimiento
        self.estado_entregable = self.estado_entregable or ("Solicitado" if requerimiento.fecha_envio else "Pendiente")
        return requerimiento

    def validar_requerimiento_abierto(self, requerimiento):
        if requerimiento.estado_requerimiento in ESTADOS_BLOQUEADOS:
            frappe.throw(_("No puedes modificar entregables cuando el requerimiento esta en estado <b>{0}</b>." ).format(requerimiento.estado_requerimiento), title=_("Requerimiento Cerrado"))

    def validar_documento_consistente(self):
        if not self.documento_contable:
            return
        documento = frappe.db.get_value(
            "Documento Contable",
            self.documento_contable,
            ["name", "cliente", "company", "periodo", "encargo_contable"],
            as_dict=True,
        )
        if not documento:
            frappe.throw(_("El documento contable vinculado no existe."), title=_("Documento Invalido"))
        inconsistencias = []
        if self.cliente and documento.cliente and self.cliente != documento.cliente:
            inconsistencias.append(_("Cliente"))
        if self.company and documento.company and self.company != documento.company:
            inconsistencias.append(_("Compania"))
        if self.periodo and documento.periodo and self.periodo != documento.periodo:
            inconsistencias.append(_("Periodo"))
        if self.encargo_contable and documento.encargo_contable and self.encargo_contable != documento.encargo_contable:
            inconsistencias.append(_("Encargo"))
        if inconsistencias:
            frappe.throw(_("El documento vinculado al entregable no coincide en: <b>{0}</b>.").format(", ".join(inconsistencias)), title=_("Inconsistencia de Trazabilidad"))

    def sincronizar_estado_entregable(self):
        hoy = getdate(nowdate())
        self.fecha_solicitud = self.fecha_solicitud or nowdate()
        if self.documento_contable and self.estado_entregable in ("Pendiente", "Solicitado", "Vencido", "Rechazado"):
            self.estado_entregable = "Recibido"
        if self.estado_entregable in ("Recibido", "Validado"):
            self.fecha_recepcion = self.fecha_recepcion or nowdate()
        if self.estado_entregable == "Validado":
            if self.obligatorio and not self.documento_contable:
                frappe.throw(_("Debes vincular un Documento Contable antes de validar un entregable obligatorio."), title=_("Documento Requerido"))
            self.validado_por = self.validado_por or get_current_user()
            self.fecha_validacion = self.fecha_validacion or nowdate()
        else:
            self.fecha_validacion = None
            self.validado_por = None
        if self.estado_entregable == "Rechazado" and not (self.notas_revision or "").strip():
            frappe.throw(_("Debes indicar notas de revision cuando rechazas un entregable."), title=_("Notas Requeridas"))
        if self.estado_entregable not in ("Recibido", "Validado", "No Aplica") and self.fecha_compromiso and getdate(self.fecha_compromiso) < hoy:
            self.estado_entregable = "Vencido"

    def actualizar_resumen_requerimiento(self):
        if not self.requerimiento_cliente or not frappe.db.exists("Requerimiento Cliente", self.requerimiento_cliente):
            return
        actualizar_seguimiento_requerimiento(self.requerimiento_cliente)

def has_website_permission(doc, ptype, user, verbose=False):
    if not user or user == "Guest":
        return False
    if frappe.get_all("Portal User", filters={"user": user, "parent": doc.cliente}):
        return True
    return False
