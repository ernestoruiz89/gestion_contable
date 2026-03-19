import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, getdate, now_datetime, nowdate

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import validate_periodo_operativo
from gestion_contable.gestion_contable.portal.cliente import portal_user_has_doc_access
from gestion_contable.gestion_contable.utils.communications import log_linked_communication
from gestion_contable.gestion_contable.utils.emailing import (
    build_requerimiento_email_context,
    get_despacho_email_template_name,
    is_email_automation_enabled,
    resolve_email_recipients,
    send_templated_email,
)
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.operational_context import sync_operational_company
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor, get_current_user

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
    "Auxiliar Contable del Despacho",
)
CONTENT_FIELDS = (
    "nombre_del_requerimiento",
    "cliente",
    "company",
    "encargo_contable",
    "periodo",
    "prioridad",
    "canal_envio",
    "contacto_cliente",
    "responsable_interno",
    "fecha_solicitud",
    "fecha_vencimiento",
    "descripcion",
    "instrucciones_cliente",
)
ESTADOS_CIERRE = ("Cerrado", "Cancelado")
ESTADOS_RECIBIDO = ("Recibido", "Validado")
ESTADOS_CUMPLIDOS = ("Validado", "No Aplica")
ESTADOS_PENDIENTES = ("Pendiente", "Solicitado", "Rechazado", "Vencido")
TIPO_CORREO_REQUERIMIENTO = {
    "envio": "template_email_requerimiento_envio",
    "recordatorio": "template_email_requerimiento_recordatorio",
    "vencido": "template_email_requerimiento_vencido",
}

class RequerimientoCliente(Document):
    def autoname(self):
        base_name = (self.nombre_del_requerimiento or "").strip()
        if not base_name:
            ref = self.encargo_contable or self.cliente or frappe.generate_hash(length=6)
            fecha = self.fecha_solicitud or nowdate()
            base_name = f"Req - {ref} - {fecha}"
        self.nombre_del_requerimiento = self._build_unique_name(base_name)
        self.name = self.nombre_del_requerimiento

    def validate(self):
        self.sincronizar_desde_encargo()
        self.aplicar_defaults_cliente()
        self.responsable_interno = self.responsable_interno or get_current_user()
        self.validar_cliente_activo()
        self.sincronizar_company_operativa()
        self.validar_periodo_abierto()
        self.validar_encargo_consistente()
        self.validar_fechas()
        self.aplicar_resumen(calcular_resumen_requerimiento(self.name if self.name and not self.name.startswith("new-") else None))
        self.sincronizar_estado_requerimiento()
        self.validar_cierre_cancelacion()
        self.validar_gobierno_operativo()

    def validar_gobierno_operativo(self):
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            aux_editable_fields=CONTENT_FIELDS,
            aux_owner_field="responsable_interno",
            label=_("el requerimiento"),
        )

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Requerimiento Cliente", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Requerimiento Cliente", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_desde_encargo(self):
        encargo = self.obtener_datos_encargo()
        if not encargo:
            return
        if not self.cliente:
            self.cliente = encargo.cliente
        if not self.periodo and encargo.periodo_referencia:
            self.periodo = encargo.periodo_referencia
        if not self.company and encargo.company:
            self.company = encargo.company

    def obtener_datos_encargo(self):
        if not self.encargo_contable:
            return None
        encargo = frappe.db.get_value(
            "Encargo Contable",
            self.encargo_contable,
            ["name", "cliente", "periodo_referencia", "estado", "company"],
            as_dict=True,
        )
        if not encargo:
            frappe.throw(_("El encargo contable <b>{0}</b> no existe.").format(self.encargo_contable), title=_("Encargo Invalido"))
        if self.is_new() and encargo.estado in ("Cerrado", "Cancelado"):
            frappe.throw(_("No puedes crear requerimientos para un encargo con estado <b>{0}</b>.").format(encargo.estado), title=_("Encargo Cerrado"))
        return encargo

    def validar_encargo_consistente(self):
        encargo = self.obtener_datos_encargo()
        if not encargo:
            return
        inconsistencias = []
        if self.cliente and self.cliente != encargo.cliente:
            inconsistencias.append(_("Cliente"))
        if self.periodo and encargo.periodo_referencia and self.periodo != encargo.periodo_referencia:
            inconsistencias.append(_("Periodo"))
        if self.company and encargo.company and self.company != encargo.company:
            inconsistencias.append(_("Compania"))
        if inconsistencias:
            frappe.throw(
                _("El requerimiento no coincide con el encargo <b>{0}</b>. Ajusta: <b>{1}</b>.").format(encargo.name, ", ".join(inconsistencias)),
                title=_("Inconsistencia de Trazabilidad"),
            )

    def aplicar_defaults_cliente(self):
        if not self.cliente:
            return

        defaults = get_cliente_defaults(self.cliente)
        if not defaults:
            return

        if not self.company and defaults.company_default:
            self.company = defaults.company_default
        if not self.responsable_interno and defaults.responsable_operativo_default:
            self.responsable_interno = defaults.responsable_operativo_default
        if self.is_new() and defaults.canal_envio_preferido and self.canal_envio in (None, "", "Correo"):
            self.canal_envio = defaults.canal_envio_preferido
        if not self.contacto_cliente and defaults.contacto_cliente_display:
            self.contacto_cliente = defaults.contacto_cliente_display
        if not self.fecha_vencimiento and self.fecha_solicitud and flt(defaults.sla_entrega_dias_default) > 0:
            dias = max(int(flt(defaults.sla_entrega_dias_default)), 0)
            if dias > 0:
                self.fecha_vencimiento = add_to_date(self.fecha_solicitud, days=dias, as_string=True)

    def validar_cliente_activo(self):
        if not self.cliente:
            return
        estado = frappe.db.get_value("Cliente Contable", self.cliente, "estado")
        if estado != "Activo":
            frappe.throw(_("No puedes gestionar requerimientos para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(self.cliente, estado), title=_("Cliente Inactivo"))

    def sincronizar_company_operativa(self):
        self.company = sync_operational_company(
            self,
            cliente=self.cliente,
            periodo=self.periodo,
            encargo_name=self.encargo_contable,
            label=_("el requerimiento"),
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
            label=_("el requerimiento"),
        )

    def validar_fechas(self):
        if self.fecha_solicitud and self.fecha_vencimiento and getdate(self.fecha_solicitud) > getdate(self.fecha_vencimiento):
            frappe.throw(_("La fecha de solicitud no puede ser posterior a la fecha de vencimiento."), title=_("Fechas Invalidas"))

    def aplicar_resumen(self, resumen):
        for fieldname, value in (resumen or {}).items():
            setattr(self, fieldname, value)

    def sincronizar_estado_requerimiento(self):
        if self.estado_requerimiento in ESTADOS_CIERRE:
            return
        if not self.fecha_envio:
            self.estado_requerimiento = "Borrador"
            self.fecha_cierre = None
            return
        if self.total_entregables <= 0:
            self.estado_requerimiento = "Enviado"
            self.fecha_cierre = None
            return
        if self.entregables_obligatorios_pendientes <= 0 and self.entregables_validados >= self.total_entregables:
            if self.estado_requerimiento != "Cerrado":
                self.estado_requerimiento = "Recibido"
            return
        if self.entregables_vencidos > 0:
            self.estado_requerimiento = "Vencido"
            self.fecha_cierre = None
            return
        if self.entregables_recibidos <= 0:
            self.estado_requerimiento = "Enviado"
            self.fecha_cierre = None
            return
        if self.entregables_recibidos < self.total_entregables:
            self.estado_requerimiento = "Parcial"
            self.fecha_cierre = None
            return
        self.estado_requerimiento = "Recibido"
        self.fecha_cierre = None

    def validar_cierre_cancelacion(self):
        if self.estado_requerimiento == "Cerrado":
            if self.total_entregables <= 0:
                frappe.throw(_("No puedes cerrar un requerimiento sin entregables definidos."), title=_("Entregables Requeridos"))
            if self.entregables_obligatorios_pendientes > 0:
                frappe.throw(_("No puedes cerrar el requerimiento mientras existan entregables obligatorios pendientes de validar."), title=_("Pendientes de Validacion"))
            self.fecha_cierre = self.fecha_cierre or now_datetime()
            return

        if self.estado_requerimiento == "Cancelado":
            ensure_manager(_("Solo Socio, Contador o System Manager pueden cancelar requerimientos a clientes."))
            self.fecha_cierre = self.fecha_cierre or now_datetime()
            return

        self.fecha_cierre = None

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar requerimientos a clientes."))


@frappe.whitelist()
def refrescar_resumen_requerimiento(requerimiento_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden recalcular requerimientos."))
    if not frappe.db.exists("Requerimiento Cliente", requerimiento_name):
        frappe.throw(_("El requerimiento indicado no existe."), title=_("Requerimiento Invalido"))
    requerimiento = actualizar_seguimiento_requerimiento(requerimiento_name)
    return {
        "requerimiento": requerimiento.name,
        "estado_requerimiento": requerimiento.estado_requerimiento,
        "total_entregables": requerimiento.total_entregables,
        "entregables_recibidos": requerimiento.entregables_recibidos,
        "entregables_validados": requerimiento.entregables_validados,
        "entregables_vencidos": requerimiento.entregables_vencidos,
        "entregables_obligatorios_pendientes": requerimiento.entregables_obligatorios_pendientes,
        "porcentaje_cumplimiento": requerimiento.porcentaje_cumplimiento,
    }


@frappe.whitelist()
def marcar_requerimiento_enviado(requerimiento_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden marcar requerimientos como enviados."))
    requerimiento = frappe.get_doc("Requerimiento Cliente", requerimiento_name)
    requerimiento.fecha_envio = requerimiento.fecha_envio or now_datetime()
    if requerimiento.estado_requerimiento == "Borrador":
        requerimiento.estado_requerimiento = "Enviado"
    requerimiento.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Entregable Cliente"):
        for entregable in frappe.get_all("Entregable Cliente", filters={"requerimiento_cliente": requerimiento.name}, fields=["name", "estado_entregable"]):
            if entregable.estado_entregable == "Pendiente":
                frappe.db.set_value("Entregable Cliente", entregable.name, "estado_entregable", "Solicitado", update_modified=False)

    if (requerimiento.canal_envio or "") == "Correo" and is_email_automation_enabled("auto_enviar_correo_requerimiento_envio", default=True):
        enviar_correo_requerimiento(requerimiento)
    else:
        log_linked_communication(
            "Requerimiento Cliente",
            requerimiento.name,
            subject=f"Requerimiento enviado: {requerimiento.nombre_del_requerimiento}",
            content=_(
                "Se marco el requerimiento como enviado por el canal <b>{0}</b>. {1}"
            ).format(
                requerimiento.canal_envio or _("Sin definir"),
                _("Correo pendiente de envio manual.") if (requerimiento.canal_envio or "") == "Correo" else _("Contacto cliente: <b>{0}</b>.").format(requerimiento.contacto_cliente or _("Sin definir")),
            ),
        )

    requerimiento = actualizar_seguimiento_requerimiento(requerimiento.name)
    return {"requerimiento": requerimiento.name, "estado_requerimiento": requerimiento.estado_requerimiento, "fecha_envio": requerimiento.fecha_envio}


@frappe.whitelist()
def enviar_correo_requerimiento_manual(requerimiento_name, tipo="envio"):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden enviar correos de requerimientos."))
    requerimiento = frappe.get_doc("Requerimiento Cliente", requerimiento_name)
    result = enviar_correo_requerimiento(requerimiento, config_fieldname=_resolve_requerimiento_template_field(tipo), force_manual=True)
    return {"ok": True, "subject": result.subject, "recipients": result.recipients, "template_name": result.template_name}


@frappe.whitelist()
def cerrar_requerimiento_cliente(requerimiento_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden cerrar requerimientos."))
    requerimiento = frappe.get_doc("Requerimiento Cliente", requerimiento_name)
    requerimiento.estado_requerimiento = "Cerrado"
    requerimiento.save(ignore_permissions=True)
    return {"requerimiento": requerimiento.name, "estado_requerimiento": requerimiento.estado_requerimiento, "fecha_cierre": requerimiento.fecha_cierre}


def actualizar_seguimiento_requerimiento(requerimiento_name):
    requerimiento = frappe.get_doc("Requerimiento Cliente", requerimiento_name)
    resumen = calcular_resumen_requerimiento(requerimiento_name)
    for fieldname, value in resumen.items():
        setattr(requerimiento, fieldname, value)
    requerimiento.save(ignore_permissions=True)
    return requerimiento


def calcular_resumen_requerimiento(requerimiento_name=None):
    entregables = []
    if requerimiento_name and frappe.db.exists("DocType", "Entregable Cliente"):
        entregables = frappe.get_all(
            "Entregable Cliente",
            filters={"requerimiento_cliente": requerimiento_name},
            fields=["name", "obligatorio", "estado_entregable", "fecha_compromiso"],
            limit_page_length=500,
        )

    hoy = getdate(nowdate())
    total = len(entregables)
    recibidos = 0
    validados = 0
    vencidos = 0
    obligatorios_pendientes = 0

    for row in entregables:
        estado = row.estado_entregable or "Pendiente"
        if estado in ESTADOS_RECIBIDO:
            recibidos += 1
        if estado == "Validado":
            validados += 1
        if estado == "Vencido":
            vencidos += 1
        elif estado in ESTADOS_PENDIENTES and row.fecha_compromiso and getdate(row.fecha_compromiso) < hoy:
            vencidos += 1

        if cint_bool(row.obligatorio) and estado not in ESTADOS_CUMPLIDOS:
            obligatorios_pendientes += 1

    porcentaje = 0
    if total > 0:
        porcentaje = round((validados / total) * 100, 2)

    return {
        "total_entregables": total,
        "entregables_recibidos": recibidos,
        "entregables_validados": validados,
        "entregables_vencidos": vencidos,
        "entregables_obligatorios_pendientes": obligatorios_pendientes,
        "porcentaje_cumplimiento": porcentaje,
    }


@frappe.whitelist()
def enviar_alertas_correo_requerimientos():
    if not frappe.db.exists("DocType", "Requerimiento Cliente"):
        return

    hoy = getdate(nowdate())
    manana = getdate(add_to_date(nowdate(), days=1, as_string=True))
    rows = frappe.get_all(
        "Requerimiento Cliente",
        filters={"canal_envio": "Correo", "estado_requerimiento": ["not in", list(ESTADOS_CIERRE)]},
        fields=[
            "name",
            "cliente",
            "fecha_envio",
            "fecha_vencimiento",
            "fecha_ultimo_recordatorio_correo",
            "fecha_ultimo_aviso_vencido_correo",
        ],
        limit_page_length=500,
    )

    auto_recordatorio = is_email_automation_enabled("auto_enviar_recordatorio_requerimiento", default=True)
    auto_vencido = is_email_automation_enabled("auto_enviar_aviso_vencido_requerimiento", default=True)
    if not auto_recordatorio and not auto_vencido:
        return

    for row in rows:
        if not row.fecha_envio or not row.fecha_vencimiento:
            continue

        try:
            fecha_vencimiento = getdate(row.fecha_vencimiento)
            requerimiento = frappe.get_doc("Requerimiento Cliente", row.name)
            if auto_vencido and fecha_vencimiento < hoy:
                if row.fecha_ultimo_aviso_vencido_correo and getdate(row.fecha_ultimo_aviso_vencido_correo) == hoy:
                    continue
                enviar_correo_requerimiento(requerimiento, config_fieldname="template_email_requerimiento_vencido")
                frappe.db.set_value(
                    "Requerimiento Cliente",
                    row.name,
                    "fecha_ultimo_aviso_vencido_correo",
                    nowdate(),
                    update_modified=False,
                )
            elif auto_recordatorio and fecha_vencimiento <= manana:
                if row.fecha_ultimo_recordatorio_correo and getdate(row.fecha_ultimo_recordatorio_correo) == hoy:
                    continue
                enviar_correo_requerimiento(requerimiento, config_fieldname="template_email_requerimiento_recordatorio")
                frappe.db.set_value(
                    "Requerimiento Cliente",
                    row.name,
                    "fecha_ultimo_recordatorio_correo",
                    nowdate(),
                    update_modified=False,
                )
        except Exception:
            frappe.log_error(
                title=f"Error enviando alerta de requerimiento {row.name}",
                message=frappe.get_traceback(),
            )


def enviar_correo_requerimiento(requerimiento, config_fieldname="template_email_requerimiento_envio", force_manual=False):
    defaults = get_cliente_defaults(requerimiento.cliente)
    recipients = resolve_email_recipients(
        requerimiento.contacto_cliente,
        defaults.contacto_requerimientos.get("email") if defaults.contacto_requerimientos else None,
        defaults.email_facturacion_efectivo,
        defaults.correo_electronico,
    )
    template_name = get_despacho_email_template_name(config_fieldname)
    action_label = {
        "template_email_requerimiento_envio": _("envio inicial"),
        "template_email_requerimiento_recordatorio": _("recordatorio"),
        "template_email_requerimiento_vencido": _("aviso de vencimiento"),
    }.get(config_fieldname, _("comunicacion"))

    note = _(
        "Se envio correo de <b>{0}</b> del requerimiento usando la plantilla <b>{1}</b> a <b>{2}</b>."
    ).format(action_label, template_name or _("Sin definir"), ", ".join(recipients))
    if force_manual:
        note = _("Envio manual. ") + note

    return send_templated_email(
        template_name,
        recipients,
        context=build_requerimiento_email_context(requerimiento),
        reference_doctype="Requerimiento Cliente",
        reference_name=requerimiento.name,
        communication_note=note,
    )


def _resolve_requerimiento_template_field(tipo):
    template_field = TIPO_CORREO_REQUERIMIENTO.get((tipo or "").strip().lower())
    if not template_field:
        frappe.throw(_("Tipo de correo de requerimiento invalido: <b>{0}</b>."
        ).format(tipo), title=_("Tipo Invalido"))
    return template_field


def cint_bool(value):
    return 1 if str(value) in ("1", "True", "true") or value == 1 else 0

def has_website_permission(doc, ptype, user, verbose=False):
    return portal_user_has_doc_access(doc, user=user)
