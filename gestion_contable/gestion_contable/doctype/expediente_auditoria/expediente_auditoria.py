import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO, validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor, has_any_role, SUPERVISOR_ROLES

ESTADOS_EXPEDIENTE_CERRADOS = ("Cerrada", "Archivada", "Cancelada")
CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_del_expediente",
    "encargo_contable",
    "socio_a_cargo",
    "supervisor_a_cargo",
    "fecha_inicio_planeada",
    "fecha_fin_planeada",
    "objetivo_auditoria",
    "alcance_auditoria",
    "materialidad_monetaria",
    "enfoque_auditoria",
    "base_normativa",
    "estrategia_muestreo",
    "memorando_planeacion",
    "informe_final_auditoria",
)


class ExpedienteAuditoria(Document):
    def autoname(self):
        base_name = (self.nombre_del_expediente or "").strip()
        if not base_name:
            ref = self.encargo_contable or frappe.generate_hash(length=6)
            periodo = self.periodo or self.fecha_inicio_planeada or nowdate()
            base_name = f"Auditoria - {ref} - {periodo}"
        self.nombre_del_expediente = self._build_unique_name(base_name)
        self.name = self.nombre_del_expediente

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar expedientes de auditoria."))
        previous = None if self.is_new() else self.get_doc_before_save()
        self.sincronizar_desde_encargo()
        self.validar_encargo_auditoria()
        self.validar_fechas()
        self.actualizar_metadatos_revision(previous)
        self.aplicar_resumen(calcular_resumen_expediente(self.name if self.name and not self.name.startswith("new-") else None))
        self.validar_revision_tecnica()
        self.validar_cierre(previous)
        validate_governance(self, content_fields=CONTENT_FIELDS, create_roles=CREATE_ROLES, draft_roles=CREATE_ROLES, label=_("el expediente de auditoria"))

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Expediente Auditoria", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Expediente Auditoria", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def obtener_encargo(self):
        if not self.encargo_contable:
            frappe.throw(_("Debes seleccionar un encargo contable para el expediente."), title=_("Encargo Requerido"))
        encargo = frappe.db.get_value(
            "Encargo Contable",
            self.encargo_contable,
            ["name", "cliente", "periodo_referencia", "company", "project", "fecha_de_inicio", "fecha_fin_estimada", "tipo_de_servicio", "estado"],
            as_dict=True,
        )
        if not encargo:
            frappe.throw(_("El encargo contable <b>{0}</b> no existe.").format(self.encargo_contable), title=_("Encargo Invalido"))
        return encargo

    def sincronizar_desde_encargo(self):
        encargo = self.obtener_encargo()
        if not self.cliente:
            self.cliente = encargo.cliente
        if not self.periodo and encargo.periodo_referencia:
            self.periodo = encargo.periodo_referencia
        if not self.company and encargo.company:
            self.company = encargo.company
        if not self.project and encargo.project:
            self.project = encargo.project
        if not self.fecha_inicio_planeada and encargo.fecha_de_inicio:
            self.fecha_inicio_planeada = encargo.fecha_de_inicio
        if not self.fecha_fin_planeada and encargo.fecha_fin_estimada:
            self.fecha_fin_planeada = encargo.fecha_fin_estimada
        self.estado_expediente = self.estado_expediente or "Planeacion"
        self.resultado_revision_tecnica = self.resultado_revision_tecnica or "Pendiente"

    def validar_encargo_auditoria(self):
        encargo = self.obtener_encargo()
        if encargo.tipo_de_servicio != "Auditoria":
            frappe.throw(_("Solo puedes crear expedientes de auditoria para encargos del tipo Auditoria."), title=_("Tipo de Servicio Invalido"))
        if self.cliente and self.cliente != encargo.cliente:
            frappe.throw(_("El cliente del expediente no coincide con el cliente del encargo."), title=_("Inconsistencia de Cliente"))
        if self.periodo and encargo.periodo_referencia and self.periodo != encargo.periodo_referencia:
            frappe.throw(_("El periodo del expediente no coincide con el periodo referencia del encargo."), title=_("Inconsistencia de Periodo"))
        if self.company and encargo.company and self.company != encargo.company:
            frappe.throw(_("La compania del expediente no coincide con la del encargo."), title=_("Inconsistencia de Compania"))
        if self.project and encargo.project and self.project != encargo.project:
            frappe.throw(_("El proyecto ERPNext del expediente no coincide con el del encargo."), title=_("Inconsistencia de Proyecto"))
        if self.is_new() and encargo.estado == "Cancelado":
            frappe.throw(_("No puedes abrir un expediente de auditoria para un encargo cancelado."), title=_("Encargo No Disponible"))

    def validar_fechas(self):
        if self.fecha_inicio_planeada and self.fecha_fin_planeada and getdate(self.fecha_inicio_planeada) > getdate(self.fecha_fin_planeada):
            frappe.throw(_("La fecha de inicio planeada no puede ser posterior a la fecha fin planeada."), title=_("Fechas Invalidas"))

    def actualizar_metadatos_revision(self, previous=None):
        previous_state = previous.estado_expediente if previous else None
        if self.estado_expediente == "Revision Tecnica" and previous_state != "Revision Tecnica" and not self.fecha_envio_revision_tecnica:
            self.fecha_envio_revision_tecnica = now_datetime()
        if self.resultado_revision_tecnica in ("Aprobado", "Observado"):
            self.revisado_tecnicamente_por = self.revisado_tecnicamente_por or frappe.session.user
            self.fecha_revision_tecnica = self.fecha_revision_tecnica or now_datetime()

    def aplicar_resumen(self, resumen):
        for key, value in (resumen or {}).items():
            setattr(self, key, value)

    def validar_revision_tecnica(self):
        self.resultado_revision_tecnica = self.resultado_revision_tecnica or "Pendiente"
        if self.resultado_revision_tecnica == "Pendiente":
            return
        if not has_any_role(SUPERVISOR_ROLES):
            frappe.throw(_("Solo Supervisor, Socio, Contador o System Manager pueden registrar la revision tecnica."), frappe.PermissionError)
        if self.estado_expediente not in ("Revision Tecnica", "Cerrada", "Archivada"):
            frappe.throw(_("El expediente debe estar en Revision Tecnica antes de registrar el resultado tecnico."), title=_("Revision Tecnica Invalida"))
        if self.resultado_revision_tecnica == "Observado" and not (self.comentarios_revision_tecnica or "").strip():
            frappe.throw(_("Debes documentar comentarios de revision tecnica cuando el resultado es Observado."), title=_("Comentarios Requeridos"))

    def validar_cierre(self, previous=None):
        if self.estado_expediente == "Planeacion":
            self.fecha_cierre = None
            self.cerrado_por = None
            return

        if self.estado_expediente == "Revision Tecnica":
            if self.total_papeles <= 0:
                frappe.throw(_("No puedes enviar un expediente a Revision Tecnica sin papeles de trabajo registrados."), title=_("Papeles Requeridos"))
            return

        if self.estado_expediente == "Cerrada":
            if self.resultado_revision_tecnica != "Aprobado":
                frappe.throw(_("El expediente debe tener revision tecnica Aprobada antes del cierre."), title=_("Revision Tecnica Pendiente"))
            if self.estado_aprobacion != ESTADO_APROBACION_APROBADO:
                frappe.throw(_("El expediente debe estar aprobado por Socio antes del cierre."), title=_("Aprobacion Requerida"))
            if self.total_riesgos <= 0:
                frappe.throw(_("La auditoria formal requiere al menos una linea en la matriz riesgo-control."), title=_("Matriz Incompleta"))
            if self.total_papeles <= 0:
                frappe.throw(_("La auditoria formal requiere al menos un papel de trabajo."), title=_("Papeles Requeridos"))
            if self.papeles_pendientes_revision > 0:
                frappe.throw(_("No puedes cerrar el expediente mientras existan papeles pendientes de revision o ajuste."), title=_("Revision Incompleta"))
            if self.hallazgos_abiertos > 0:
                frappe.throw(_("No puedes cerrar el expediente mientras existan hallazgos abiertos o en seguimiento."), title=_("Hallazgos Pendientes"))
            if not (self.memo_cierre or "").strip():
                frappe.throw(_("Debes documentar el memo de cierre para cerrar el expediente."), title=_("Memo Requerido"))
            self.cerrado_por = self.cerrado_por or frappe.session.user
            self.fecha_cierre = self.fecha_cierre or now_datetime()
            return

        if self.estado_expediente == "Archivada":
            if previous and previous.estado_expediente != "Cerrada":
                frappe.throw(_("Solo puedes archivar un expediente previamente cerrado."), title=_("Archivado Invalido"))
            if not self.informe_final_auditoria:
                frappe.throw(_("Debes emitir el informe final de auditoria antes de archivar el expediente."), title=_("Informe Final Requerido"))
            informe = frappe.db.get_value("Informe Final Auditoria", self.informe_final_auditoria, ["name", "estado_emision"], as_dict=True)
            if not informe or informe.estado_emision != "Emitido":
                frappe.throw(_("El informe final vinculado debe existir y estar emitido antes de archivar el expediente."), title=_("Informe Final Invalido"))
            ensure_manager(_("Solo Socio, Contador o System Manager pueden archivar expedientes de auditoria."))
            return

        if self.estado_expediente == "Cancelada":
            ensure_manager(_("Solo Socio, Contador o System Manager pueden cancelar expedientes de auditoria."))

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar expedientes de auditoria."))


@frappe.whitelist()
def refrescar_resumen_expediente(expediente_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden recalcular el expediente de auditoria."))
    if not frappe.db.exists("Expediente Auditoria", expediente_name):
        frappe.throw(_("El expediente de auditoria indicado no existe."), title=_("Expediente Invalido"))
    resumen = calcular_resumen_expediente(expediente_name)
    frappe.db.set_value("Expediente Auditoria", expediente_name, resumen, update_modified=False)
    return resumen


@frappe.whitelist()
def enviar_revision_tecnica(expediente_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden enviar expedientes a revision tecnica."))
    expediente = frappe.get_doc("Expediente Auditoria", expediente_name)
    expediente.estado_expediente = "Revision Tecnica"
    expediente.fecha_envio_revision_tecnica = now_datetime()
    expediente.save(ignore_permissions=True)
    return {"expediente": expediente.name, "estado_expediente": expediente.estado_expediente}


@frappe.whitelist()
def cerrar_expediente_auditoria(expediente_name):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden cerrar expedientes de auditoria."))
    expediente = frappe.get_doc("Expediente Auditoria", expediente_name)
    expediente.estado_expediente = "Cerrada"
    expediente.save(ignore_permissions=True)
    return {"expediente": expediente.name, "estado_expediente": expediente.estado_expediente, "fecha_cierre": expediente.fecha_cierre}


@frappe.whitelist()
def generar_informe_final(expediente_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden generar el informe final de auditoria."))
    from gestion_contable.gestion_contable.doctype.informe_final_auditoria.informe_final_auditoria import generar_informe_final_desde_expediente

    return generar_informe_final_desde_expediente(expediente_name)


def calcular_resumen_expediente(expediente_name=None):
    if not expediente_name or not frappe.db.exists("Expediente Auditoria", expediente_name):
        return {
            "total_riesgos": 0,
            "riesgos_altos": 0,
            "total_papeles": 0,
            "papeles_pendientes_revision": 0,
            "papeles_aprobados": 0,
            "total_hallazgos": 0,
            "hallazgos_abiertos": 0,
            "hallazgos_cerrados": 0,
        }

    total_riesgos = frappe.db.count("Riesgo Control Auditoria", {"expediente_auditoria": expediente_name}) if frappe.db.exists("DocType", "Riesgo Control Auditoria") else 0
    riesgos_altos = 0
    if total_riesgos:
        riesgos_altos = frappe.db.sql(
            """
            SELECT COUNT(name)
            FROM `tabRiesgo Control Auditoria`
            WHERE expediente_auditoria = %s
              AND (riesgo_inherente IN ('Alto', 'Critico') OR riesgo_residual IN ('Alto', 'Critico'))
            """,
            (expediente_name,),
        )[0][0]

    total_papeles = frappe.db.count("Papel Trabajo Auditoria", {"expediente_auditoria": expediente_name}) if frappe.db.exists("DocType", "Papel Trabajo Auditoria") else 0
    papeles_aprobados = 0
    papeles_pendientes = 0
    if total_papeles:
        papeles_aprobados = frappe.db.sql(
            """
            SELECT COUNT(name)
            FROM `tabPapel Trabajo Auditoria`
            WHERE expediente_auditoria = %s
              AND estado_papel IN ('Aprobado', 'Cerrado')
            """,
            (expediente_name,),
        )[0][0]
        papeles_pendientes = frappe.db.sql(
            """
            SELECT COUNT(name)
            FROM `tabPapel Trabajo Auditoria`
            WHERE expediente_auditoria = %s
              AND estado_papel NOT IN ('Aprobado', 'Cerrado')
            """,
            (expediente_name,),
        )[0][0]

    total_hallazgos = frappe.db.count("Hallazgo Auditoria", {"expediente_auditoria": expediente_name}) if frappe.db.exists("DocType", "Hallazgo Auditoria") else 0
    hallazgos_abiertos = 0
    hallazgos_cerrados = 0
    if total_hallazgos:
        hallazgos_abiertos = frappe.db.sql(
            """
            SELECT COUNT(name)
            FROM `tabHallazgo Auditoria`
            WHERE expediente_auditoria = %s
              AND estado_hallazgo NOT IN ('Resuelto', 'Cerrado', 'Descartado')
            """,
            (expediente_name,),
        )[0][0]
        hallazgos_cerrados = frappe.db.sql(
            """
            SELECT COUNT(name)
            FROM `tabHallazgo Auditoria`
            WHERE expediente_auditoria = %s
              AND estado_hallazgo IN ('Resuelto', 'Cerrado')
            """,
            (expediente_name,),
        )[0][0]

    return {
        "total_riesgos": total_riesgos,
        "riesgos_altos": riesgos_altos,
        "total_papeles": total_papeles,
        "papeles_pendientes_revision": papeles_pendientes,
        "papeles_aprobados": papeles_aprobados,
        "total_hallazgos": total_hallazgos,
        "hallazgos_abiertos": hallazgos_abiertos,
        "hallazgos_cerrados": hallazgos_cerrados,
    }





