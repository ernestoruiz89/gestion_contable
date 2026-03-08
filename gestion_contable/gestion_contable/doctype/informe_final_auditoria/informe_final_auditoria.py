import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, now_datetime, nowdate

from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO, validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
ESTADOS_EXPEDIENTE_VALIDOS = ("Cerrada", "Archivada")
ESTADOS_EMISION = ("Borrador", "Listo para Emitir", "Emitido", "Reemplazado")
TIPO_INFORME_FINAL_GENERAL = "Informe Final General"
TIPO_CARTA_GERENCIA = "Carta a la Gerencia"
TIPO_INFORME_HALLAZGOS = "Informe de Hallazgos"
TIPO_INFORME_CONTROL_INTERNO = "Informe de Control Interno"
TIPO_PROCEDIMIENTOS_ACORDADOS = "Procedimientos Acordados"
TIPO_DICTAMEN_AUDITORIA = "Dictamen de Auditoria"
TIPOS_INFORME = (
    TIPO_INFORME_FINAL_GENERAL,
    TIPO_CARTA_GERENCIA,
    TIPO_INFORME_HALLAZGOS,
    TIPO_INFORME_CONTROL_INTERNO,
    TIPO_PROCEDIMIENTOS_ACORDADOS,
    TIPO_DICTAMEN_AUDITORIA,
)
TIPOS_CON_OPINION = {TIPO_INFORME_FINAL_GENERAL, TIPO_DICTAMEN_AUDITORIA}
OPINIONES_DICTAMEN_VALIDAS = ("Favorable", "Con Salvedades", "Adversa", "Abstencion")
OPINIONES_DICTAMEN_MODIFICADAS = ("Con Salvedades", "Adversa", "Abstencion")
PRINT_FORMAT_BY_REPORT_TYPE = {
    TIPO_INFORME_FINAL_GENERAL: "Informe Final Auditoria - General",
    TIPO_CARTA_GERENCIA: "Carta a la Gerencia - Auditoria",
    TIPO_INFORME_HALLAZGOS: "Informe de Hallazgos - Auditoria",
    TIPO_INFORME_CONTROL_INTERNO: "Informe de Control Interno - Auditoria",
    TIPO_PROCEDIMIENTOS_ACORDADOS: "Procedimientos Acordados - Auditoria",
    TIPO_DICTAMEN_AUDITORIA: "Dictamen de Auditoria",
}
CONTENT_FIELDS = (
    "nombre_del_informe",
    "expediente_auditoria",
    "tipo_de_informe",
    "es_informe_principal",
    "fecha_informe",
    "destinatario",
    "tipo_opinion",
    "titulo_informe",
    "resumen_ejecutivo",
    "alcance_del_trabajo",
    "base_normativa",
    "principales_hallazgos",
    "recomendaciones_clave",
    "fundamento_opinion",
    "asunto_que_origina_modificacion",
    "fundamento_salvedad",
    "efecto_generalizado",
    "limitacion_alcance_material",
    "parrafo_enfasis",
    "parrafo_otros_asuntos",
    "responsabilidades_administracion",
    "responsabilidades_auditor",
    "opinion_o_conclusion",
    "conclusion_final",
    "firmado_por",
    "cargo_firmante",
    "revisado_por",
    "notas_emision",
)
SEVERITY_ORDER = {"Critica": 0, "Alta": 1, "Media": 2, "Baja": 3}


class InformeFinalAuditoria(Document):
    def autoname(self):
        base_name = (self.nombre_del_informe or "").strip()
        if not base_name:
            expediente_ref = self.expediente_auditoria or frappe.generate_hash(length=6)
            report_type = self.tipo_de_informe or TIPO_INFORME_FINAL_GENERAL
            base_name = f"{report_type} - {expediente_ref}"
        self.nombre_del_informe = self._build_unique_name(base_name)
        self.name = self.nombre_del_informe

    def validate(self):
        ensure_supervisor(
            _(
                "Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar informes finales de auditoria."
            )
        )
        previous = None if self.is_new() else self.get_doc_before_save()
        expediente = self.sincronizar_desde_expediente()
        self.validar_tipo_de_informe()
        self.actualizar_configuracion_informe()
        self.validar_expediente(expediente)
        self.sugerir_contenido(expediente, force=getattr(self.flags, "force_refresh_content", False))
        self.validar_dictamen_nia(expediente)
        self.validar_estado_emision(previous, expediente)
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            label=_("el informe final de auditoria"),
        )

    def on_update(self):
        if not self.expediente_auditoria or not frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            return

        linked_report = frappe.db.get_value("Expediente Auditoria", self.expediente_auditoria, "informe_final_auditoria")
        if self.estado_emision == "Reemplazado":
            if linked_report == self.name:
                frappe.db.set_value("Expediente Auditoria", self.expediente_auditoria, "informe_final_auditoria", None, update_modified=False)
            return

        if cint_bool(self.es_informe_principal):
            frappe.db.set_value(
                "Expediente Auditoria",
                self.expediente_auditoria,
                "informe_final_auditoria",
                self.name,
                update_modified=False,
            )
        elif linked_report == self.name:
            frappe.db.set_value("Expediente Auditoria", self.expediente_auditoria, "informe_final_auditoria", None, update_modified=False)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar informes finales de auditoria."))
        if self.expediente_auditoria and frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            if frappe.db.get_value("Expediente Auditoria", self.expediente_auditoria, "informe_final_auditoria") == self.name:
                frappe.db.set_value("Expediente Auditoria", self.expediente_auditoria, "informe_final_auditoria", None, update_modified=False)

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Informe Final Auditoria", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Informe Final Auditoria", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def obtener_expediente(self):
        if not self.expediente_auditoria:
            frappe.throw(_("Debes seleccionar un expediente de auditoria."), title=_("Expediente Requerido"))
        expediente = frappe.db.get_value(
            "Expediente Auditoria",
            self.expediente_auditoria,
            [
                "name",
                "encargo_contable",
                "cliente",
                "periodo",
                "company",
                "estado_expediente",
                "estado_aprobacion",
                "resultado_revision_tecnica",
                "objetivo_auditoria",
                "alcance_auditoria",
                "base_normativa",
                "memo_cierre",
                "total_riesgos",
                "riesgos_altos",
                "total_papeles",
                "papeles_aprobados",
                "total_hallazgos",
                "hallazgos_abiertos",
                "hallazgos_cerrados",
                "supervisor_a_cargo",
                "socio_a_cargo",
            ],
            as_dict=True,
        )
        if not expediente:
            frappe.throw(
                _("El expediente de auditoria <b>{0}</b> no existe.").format(self.expediente_auditoria),
                title=_("Expediente Invalido"),
            )
        return expediente

    def sincronizar_desde_expediente(self):
        expediente = self.obtener_expediente()
        self.encargo_contable = expediente.encargo_contable
        self.cliente = expediente.cliente
        self.periodo = expediente.periodo
        self.company = expediente.company
        self.fecha_informe = self.fecha_informe or nowdate()
        self.estado_emision = self.estado_emision or "Borrador"
        self.tipo_de_informe = self.tipo_de_informe or TIPO_INFORME_FINAL_GENERAL
        self.es_informe_principal = cint_bool(self.es_informe_principal)
        self.base_normativa = self.base_normativa or expediente.base_normativa
        self.firmado_por = self.firmado_por or expediente.socio_a_cargo
        self.revisado_por = self.revisado_por or expediente.supervisor_a_cargo
        self.cargo_firmante = self.cargo_firmante or "Socio del Despacho"
        self.destinatario = self.destinatario or _resolve_destinatario(self.cliente)
        self.formato_impresion_sugerido = PRINT_FORMAT_BY_REPORT_TYPE.get(self.tipo_de_informe)
        if self.tipo_de_informe in TIPOS_CON_OPINION:
            self.tipo_opinion = self.tipo_opinion or _suggest_opinion_type(expediente, self.tipo_de_informe)
        return expediente

    def validar_tipo_de_informe(self):
        if self.tipo_de_informe not in TIPOS_INFORME:
            frappe.throw(_("El tipo de informe seleccionado no es valido."), title=_("Tipo de Informe Invalido"))
        self.formato_impresion_sugerido = PRINT_FORMAT_BY_REPORT_TYPE.get(self.tipo_de_informe)

    def actualizar_configuracion_informe(self):
        self.es_informe_principal = cint_bool(self.es_informe_principal)
        self.efecto_generalizado = cint_bool(self.efecto_generalizado)
        self.limitacion_alcance_material = cint_bool(self.limitacion_alcance_material)
        if self.tipo_de_informe != TIPO_DICTAMEN_AUDITORIA:
            return

        has_nia_706_paragraphs = bool(cstr(self.parrafo_enfasis or "").strip() or cstr(self.parrafo_otros_asuntos or "").strip())
        if not self.base_normativa or cstr(self.base_normativa or "").strip().upper() == "NIA":
            self.base_normativa = _default_dictamen_base_normativa(self.tipo_opinion, has_nia_706_paragraphs)

        if self.tipo_opinion == "Favorable":
            self.efecto_generalizado = 0
            self.limitacion_alcance_material = 0
        elif self.tipo_opinion == "Con Salvedades":
            self.efecto_generalizado = 0
        elif self.tipo_opinion == "Adversa":
            self.efecto_generalizado = 1
            self.limitacion_alcance_material = 0
        elif self.tipo_opinion == "Abstencion":
            self.efecto_generalizado = 1
            self.limitacion_alcance_material = 1

    def validar_dictamen_nia(self, expediente):
        if self.tipo_de_informe != TIPO_DICTAMEN_AUDITORIA:
            return

        if self.tipo_opinion not in OPINIONES_DICTAMEN_VALIDAS:
            frappe.throw(
                _("El Dictamen de Auditoria solo permite opiniones: Favorable, Con Salvedades, Adversa o Abstencion."),
                title=_("Opinion Invalida"),
            )

        strict_validation = self.estado_aprobacion == ESTADO_APROBACION_APROBADO or self.estado_emision in (
            "Listo para Emitir",
            "Emitido",
        )
        base_normativa = cstr(self.base_normativa or "").upper()
        if strict_validation and "NIA" not in base_normativa:
            frappe.throw(
                _("El Dictamen de Auditoria debe indicar una base normativa alineada a NIA antes de aprobarse o emitirse."),
                title=_("Base Normativa Requerida"),
            )

        required_nia = "700" if self.tipo_opinion == "Favorable" else "705"
        if strict_validation and required_nia not in base_normativa:
            frappe.throw(
                _("La base normativa del dictamen debe referenciar NIA {0} para el tipo de opinion seleccionado.").format(required_nia),
                title=_("Norma NIA Requerida"),
            )

        has_nia_706_paragraphs = bool(cstr(self.parrafo_enfasis or "").strip() or cstr(self.parrafo_otros_asuntos or "").strip())
        if strict_validation and has_nia_706_paragraphs and "706" not in base_normativa:
            frappe.throw(
                _("Si el dictamen incluye parrafos de enfasis u otros asuntos, la base normativa debe referenciar NIA 706 antes de aprobarse o emitirse."),
                title=_("Norma NIA 706 Requerida"),
            )

        has_pending_matters = (expediente.hallazgos_abiertos or 0) > 0 or (expediente.riesgos_altos or 0) > 0
        if self.tipo_opinion == "Favorable" and has_pending_matters:
            frappe.throw(
                _(
                    "No puedes emitir un dictamen Favorable mientras existan hallazgos abiertos o riesgos altos en el expediente. Ajusta la opinion o cierra los asuntos pendientes."
                ),
                title=_("Opinion Inconsistente"),
            )

        if self.tipo_opinion in OPINIONES_DICTAMEN_MODIFICADAS and strict_validation and not cstr(self.asunto_que_origina_modificacion or "").strip():
            frappe.throw(
                _("Debes documentar el asunto que origina la modificacion del dictamen antes de aprobarlo o emitirlo."),
                title=_("Salvedad Requerida"),
            )

        if self.tipo_opinion in OPINIONES_DICTAMEN_MODIFICADAS and strict_validation and not cstr(self.fundamento_salvedad or "").strip():
            frappe.throw(
                _("Debes documentar el fundamento de la opinion modificada antes de aprobar o emitir el dictamen."),
                title=_("Fundamento Requerido"),
            )

        if self.tipo_opinion == "Con Salvedades" and self.efecto_generalizado:
            frappe.throw(
                _("Una opinion con salvedades no debe marcarse como generalizada; si el efecto es generalizado corresponde una opinion Adversa o Abstencion."),
                title=_("Salvedad Inconsistente"),
            )

        if self.tipo_opinion == "Adversa" and not self.efecto_generalizado:
            frappe.throw(
                _("Una opinion Adversa requiere marcar que el efecto es generalizado."),
                title=_("Opinion Adversa Incompleta"),
            )

        if self.tipo_opinion == "Abstencion":
            if not self.limitacion_alcance_material:
                frappe.throw(
                    _("Una Abstencion requiere documentar una limitacion material al alcance."),
                    title=_("Abstencion Incompleta"),
                )
            if not self.efecto_generalizado:
                frappe.throw(
                    _("Una Abstencion requiere marcar que la limitacion al alcance es generalizada."),
                    title=_("Abstencion Incompleta"),
                )

    def validar_expediente(self, expediente):
        if expediente.estado_expediente not in ESTADOS_EXPEDIENTE_VALIDOS:
            frappe.throw(
                _("Solo puedes emitir informes finales para expedientes cerrados o archivados."),
                title=_("Expediente No Elegible"),
            )
        if expediente.resultado_revision_tecnica != "Aprobado":
            frappe.throw(
                _("El expediente debe tener revision tecnica aprobada antes de emitir el informe final."),
                title=_("Revision Tecnica Pendiente"),
            )
        if expediente.estado_aprobacion != ESTADO_APROBACION_APROBADO:
            frappe.throw(
                _("El expediente debe estar aprobado por socio antes de emitir el informe final."),
                title=_("Aprobacion Requerida"),
            )
        active_filters = {
            "expediente_auditoria": self.expediente_auditoria,
            "name": ["!=", self.name or ""],
            "estado_emision": ["!=", "Reemplazado"],
        }
        existing_same_type = frappe.get_all(
            "Informe Final Auditoria",
            filters={**active_filters, "tipo_de_informe": self.tipo_de_informe},
            fields=["name", "tipo_de_informe"],
            limit_page_length=1,
        )
        if existing_same_type:
            frappe.throw(
                _(
                    "Ya existe un informe activo del tipo <b>{0}</b> para este expediente: <b>{1}</b>. "
                    "Reemplazalo o usa otro tipo de informe."
                ).format(self.tipo_de_informe, existing_same_type[0].name),
                title=_("Informe Duplicado"),
            )

        if self.es_informe_principal:
            existing_principal = frappe.get_all(
                "Informe Final Auditoria",
                filters={**active_filters, "es_informe_principal": 1},
                fields=["name", "tipo_de_informe"],
                limit_page_length=1,
            )
            if existing_principal:
                frappe.throw(
                    _(
                        "El expediente ya tiene un informe principal activo: <b>{0}</b> ({1}). "
                        "Marcalo como Reemplazado o retira su bandera principal antes de continuar."
                    ).format(existing_principal[0].name, existing_principal[0].tipo_de_informe),
                    title=_("Informe Principal Duplicado"),
                )

    def sugerir_contenido(self, expediente, force=False):
        hallazgos = _get_hallazgos_resumen(self.expediente_auditoria)
        suggestions = _build_suggested_content(expediente, hallazgos, self.tipo_de_informe)
        for fieldname in (
            "titulo_informe",
            "resumen_ejecutivo",
            "alcance_del_trabajo",
            "principales_hallazgos",
            "recomendaciones_clave",
            "fundamento_opinion",
            "responsabilidades_administracion",
            "responsabilidades_auditor",
            "opinion_o_conclusion",
            "conclusion_final",
        ):
            current = cstr(self.get(fieldname) or "").strip()
            if force or not current:
                self.set(fieldname, suggestions.get(fieldname))

    def validar_estado_emision(self, previous, expediente):
        if self.estado_emision not in ESTADOS_EMISION:
            frappe.throw(_("El estado de emision seleccionado no es valido."), title=_("Estado Invalido"))

        if previous and previous.estado_emision == "Emitido" and self.estado_emision not in ("Emitido", "Reemplazado"):
            frappe.throw(_("Un informe emitido solo puede pasar a estado Reemplazado."), title=_("Transicion No Permitida"))

        if self.estado_emision == "Reemplazado":
            ensure_manager(_("Solo Socio, Contador o System Manager pueden reemplazar un informe emitido."))
            return

        if self.estado_emision != "Emitido":
            if self.estado_emision == "Borrador":
                self.emitido_por = None
                self.fecha_emision = None
            return

        ensure_manager(_("Solo Socio, Contador o System Manager pueden emitir el informe final de auditoria."))
        if self.estado_aprobacion != ESTADO_APROBACION_APROBADO:
            frappe.throw(_("El informe final debe estar aprobado antes de su emision."), title=_("Aprobacion Requerida"))
        required_fields = _required_fields_for_emission(self.tipo_de_informe)
        missing = [label for fieldname, label in required_fields.items() if not cstr(self.get(fieldname) or "").strip()]
        if missing:
            frappe.throw(
                _("Debes completar los siguientes campos antes de emitir el informe: <b>{0}</b>.").format(", ".join(missing)),
                title=_("Contenido Incompleto"),
            )
        if expediente.estado_expediente not in ESTADOS_EXPEDIENTE_VALIDOS:
            frappe.throw(_("El expediente debe continuar cerrado o archivado para emitir el informe."), title=_("Expediente Invalido"))
        self.emitido_por = self.emitido_por or frappe.session.user
        self.fecha_emision = self.fecha_emision or now_datetime()


@frappe.whitelist()
def generar_informe_final_desde_expediente(expediente_name, tipo_de_informe=None, es_informe_principal=1):
    ensure_supervisor(
        _(
            "Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden generar informes finales de auditoria."
        )
    )
    if not frappe.db.exists("Expediente Auditoria", expediente_name):
        frappe.throw(_("El expediente indicado no existe."), title=_("Expediente Invalido"))

    tipo_de_informe = tipo_de_informe or TIPO_INFORME_FINAL_GENERAL
    existing = frappe.get_all(
        "Informe Final Auditoria",
        filters={
            "expediente_auditoria": expediente_name,
            "tipo_de_informe": tipo_de_informe,
            "estado_emision": ["!=", "Reemplazado"],
        },
        fields=["name", "estado_emision"],
        order_by="modified desc",
        limit_page_length=1,
    )
    if existing:
        return {"name": existing[0].name, "created": 0}

    doc = frappe.get_doc(
        {
            "doctype": "Informe Final Auditoria",
            "expediente_auditoria": expediente_name,
            "tipo_de_informe": tipo_de_informe,
            "es_informe_principal": cint_bool(es_informe_principal),
        }
    )
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "created": 1}


@frappe.whitelist()
def refrescar_contenido_informe_final(informe_name):
    ensure_supervisor(
        _(
            "Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden refrescar informes finales de auditoria."
        )
    )
    informe = frappe.get_doc("Informe Final Auditoria", informe_name)
    if informe.estado_emision == "Emitido":
        frappe.throw(_("No puedes refrescar automaticamente un informe ya emitido."), title=_("Informe Emitido"))
    informe.flags.force_refresh_content = True
    informe.save(ignore_permissions=True)
    return {"name": informe.name}


@frappe.whitelist()
def emitir_informe_final_auditoria(informe_name):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden emitir informes finales de auditoria."))
    informe = frappe.get_doc("Informe Final Auditoria", informe_name)
    informe.estado_emision = "Emitido"
    informe.save(ignore_permissions=True)
    return {
        "name": informe.name,
        "estado_emision": informe.estado_emision,
        "fecha_emision": informe.fecha_emision,
        "emitido_por": informe.emitido_por,
    }


def _resolve_destinatario(cliente_name):
    if not cliente_name or not frappe.db.exists("Cliente Contable", cliente_name):
        return None
    cliente = frappe.get_cached_doc("Cliente Contable", cliente_name)
    if cliente.contacto_facturacion:
        return cliente.contacto_facturacion
    if cliente.contacto_cobranza:
        return cliente.contacto_cobranza
    if cliente.correo_electronico:
        return cliente.correo_electronico
    if cliente.customer and frappe.db.exists("Customer", cliente.customer):
        return frappe.db.get_value("Customer", cliente.customer, "customer_name")
    return cliente.name


def _suggest_opinion_type(expediente, report_type):
    if report_type == TIPO_DICTAMEN_AUDITORIA:
        if (expediente.hallazgos_abiertos or 0) > 0 or (expediente.riesgos_altos or 0) > 0:
            return "Con Salvedades"
        return "Favorable"
    if report_type == TIPO_INFORME_FINAL_GENERAL:
        if (expediente.hallazgos_abiertos or 0) <= 0 and (expediente.riesgos_altos or 0) <= 0:
            return "Favorable"
        return "Conclusiones y Recomendaciones"
    return None


def _get_hallazgos_resumen(expediente_name):
    if not expediente_name or not frappe.db.exists("DocType", "Hallazgo Auditoria"):
        return []
    rows = frappe.get_all(
        "Hallazgo Auditoria",
        filters={"expediente_auditoria": expediente_name},
        fields=[
            "name",
            "titulo_hallazgo",
            "severidad",
            "estado_hallazgo",
            "recomendacion",
            "respuesta_administracion",
        ],
        order_by="modified desc",
        limit_page_length=50,
    )
    return sorted(rows, key=lambda row: (SEVERITY_ORDER.get(row.severidad, 99), row.titulo_hallazgo or row.name))

def _required_fields_for_emission(report_type):
    common = {
        "titulo_informe": _("Titulo Informe"),
        "firmado_por": _("Firmado por"),
        "conclusion_final": _("Conclusion Final"),
    }
    if report_type == TIPO_DICTAMEN_AUDITORIA:
        return {
            **common,
            "tipo_opinion": _("Tipo de Opinion"),
            "fundamento_opinion": _("Fundamento de la Opinion"),
            "responsabilidades_administracion": _("Responsabilidades de la Administracion"),
            "responsabilidades_auditor": _("Responsabilidades del Auditor"),
            "opinion_o_conclusion": _("Opinion del Auditor"),
        }
    if report_type == TIPO_PROCEDIMIENTOS_ACORDADOS:
        return {
            **common,
            "alcance_del_trabajo": _("Alcance del Trabajo"),
            "resumen_ejecutivo": _("Resumen Ejecutivo"),
            "opinion_o_conclusion": _("Resultados de los Procedimientos"),
        }
    if report_type == TIPO_CARTA_GERENCIA:
        return {
            **common,
            "resumen_ejecutivo": _("Resumen Ejecutivo"),
            "principales_hallazgos": _("Asuntos Comunicados"),
            "recomendaciones_clave": _("Recomendaciones Clave"),
        }
    if report_type == TIPO_INFORME_HALLAZGOS:
        return {
            **common,
            "alcance_del_trabajo": _("Alcance del Trabajo"),
            "principales_hallazgos": _("Principales Hallazgos"),
            "recomendaciones_clave": _("Recomendaciones Clave"),
        }
    if report_type == TIPO_INFORME_CONTROL_INTERNO:
        return {
            **common,
            "resumen_ejecutivo": _("Resumen Ejecutivo"),
            "alcance_del_trabajo": _("Alcance del Trabajo"),
            "principales_hallazgos": _("Observaciones de Control Interno"),
            "recomendaciones_clave": _("Recomendaciones Clave"),
        }
    return {
        **common,
        "tipo_opinion": _("Tipo de Opinion"),
        "resumen_ejecutivo": _("Resumen Ejecutivo"),
        "alcance_del_trabajo": _("Alcance del Trabajo"),
        "opinion_o_conclusion": _("Opinion o Conclusion"),
    }


def _build_suggested_content(expediente, hallazgos, report_type):
    builders = {
        TIPO_INFORME_FINAL_GENERAL: _build_general_content,
        TIPO_CARTA_GERENCIA: _build_management_letter_content,
        TIPO_INFORME_HALLAZGOS: _build_findings_content,
        TIPO_INFORME_CONTROL_INTERNO: _build_internal_control_content,
        TIPO_PROCEDIMIENTOS_ACORDADOS: _build_agreed_procedures_content,
        TIPO_DICTAMEN_AUDITORIA: _build_dictamen_content,
    }
    return builders.get(report_type, _build_general_content)(expediente, hallazgos)


def _build_general_content(expediente, hallazgos):
    cliente_label, periodo_label, principales_html, recomendaciones_html = _common_hallazgo_blocks(expediente, hallazgos)
    resumen = [
        _(
            "Se emite el presente informe final de auditoria correspondiente al cliente <b>{0}</b> para el periodo <b>{1}</b>."
        ).format(cliente_label, periodo_label),
        _(
            "El expediente cerro con <b>{0}</b> riesgos documentados, <b>{1}</b> papeles de trabajo y <b>{2}</b> hallazgos."
        ).format(expediente.total_riesgos or 0, expediente.total_papeles or 0, expediente.total_hallazgos or 0),
    ]
    if expediente.riesgos_altos:
        resumen.append(_("Se identificaron <b>{0}</b> riesgos altos o criticos que recibieron tratamiento durante la ejecucion.").format(expediente.riesgos_altos))
    if expediente.hallazgos_abiertos:
        resumen.append(_("Existen <b>{0}</b> hallazgos en seguimiento al momento de la emision.").format(expediente.hallazgos_abiertos))

    opinion = _build_general_opinion(expediente, cliente_label, periodo_label)
    conclusion = expediente.memo_cierre or _(
        "<p>Con base en la evidencia obtenida, el despacho concluye que el expediente de auditoria cuenta con soporte suficiente para documentar el cierre del encargo y las recomendaciones emitidas.</p>"
    )

    return {
        "titulo_informe": _("Informe Final de Auditoria - {0} - {1}").format(cliente_label, periodo_label),
        "resumen_ejecutivo": "".join(f"<p>{item}</p>" for item in resumen),
        "alcance_del_trabajo": expediente.alcance_auditoria
        or _(
            "<p>El trabajo comprendio planeacion, evaluacion de riesgos, ejecucion de pruebas, documentacion de evidencia, revision tecnica y cierre formal del expediente.</p>"
        ),
        "principales_hallazgos": principales_html,
        "recomendaciones_clave": recomendaciones_html,
        "opinion_o_conclusion": opinion,
        "conclusion_final": conclusion,
        "fundamento_opinion": "",
        "responsabilidades_administracion": "",
        "responsabilidades_auditor": "",
    }


def _build_management_letter_content(expediente, hallazgos):
    cliente_label, periodo_label, principales_html, recomendaciones_html = _common_hallazgo_blocks(expediente, hallazgos)
    resumen = _(
        "<p>Se comunica a la gerencia de <b>{0}</b> un resumen de los asuntos relevantes observados durante el trabajo de auditoria del periodo <b>{1}</b>, junto con recomendaciones de mejora para fortalecer controles y seguimiento.</p>"
    ).format(cliente_label, periodo_label)
    conclusion = _(
        "<p>La gerencia debe evaluar el plan de accion y asignar responsables para atender las observaciones comunicadas en esta carta.</p>"
    )
    return {
        "titulo_informe": _("Carta a la Gerencia - {0} - {1}").format(cliente_label, periodo_label),
        "resumen_ejecutivo": resumen,
        "alcance_del_trabajo": expediente.alcance_auditoria or _("<p>Las observaciones se derivan del trabajo ejecutado en el expediente de auditoria y de la revision de procesos y evidencia disponible.</p>"),
        "principales_hallazgos": principales_html,
        "recomendaciones_clave": recomendaciones_html,
        "opinion_o_conclusion": _("<p>La presente comunicacion no constituye un dictamen independiente; resume asuntos relevantes para conocimiento de la administracion.</p>"),
        "conclusion_final": conclusion,
        "fundamento_opinion": "",
        "responsabilidades_administracion": "",
        "responsabilidades_auditor": "",
    }


def _build_findings_content(expediente, hallazgos):
    cliente_label, periodo_label, principales_html, recomendaciones_html = _common_hallazgo_blocks(expediente, hallazgos)
    return {
        "titulo_informe": _("Informe de Hallazgos - {0} - {1}").format(cliente_label, periodo_label),
        "resumen_ejecutivo": _("<p>El presente informe consolida los hallazgos identificados durante la auditoria y su estado de atencion al cierre del expediente.</p>"),
        "alcance_del_trabajo": expediente.alcance_auditoria or _("<p>El trabajo incluyo pruebas de cumplimiento, revision de evidencia y documentacion de desviaciones relevantes.</p>"),
        "principales_hallazgos": principales_html,
        "recomendaciones_clave": recomendaciones_html,
        "opinion_o_conclusion": _("<p>Los hallazgos expuestos deben atenderse conforme a su severidad y plan de accion definido por la administracion.</p>"),
        "conclusion_final": _("<p>Este documento sirve como base para seguimiento formal de observaciones y cierre de acciones correctivas.</p>"),
        "fundamento_opinion": "",
        "responsabilidades_administracion": "",
        "responsabilidades_auditor": "",
    }

def _build_internal_control_content(expediente, hallazgos):
    cliente_label, periodo_label, principales_html, recomendaciones_html = _common_hallazgo_blocks(expediente, hallazgos)
    return {
        "titulo_informe": _("Informe de Control Interno - {0} - {1}").format(cliente_label, periodo_label),
        "resumen_ejecutivo": _("<p>Se evaluo el diseno y operacion de controles relevantes identificando oportunidades de mejora y observaciones a ser corregidas por la administracion.</p>"),
        "alcance_del_trabajo": _("<p>La evaluacion considero procesos, controles clave, evidencia disponible y respuesta de la administracion sobre debilidades detectadas.</p>"),
        "principales_hallazgos": principales_html,
        "recomendaciones_clave": recomendaciones_html,
        "opinion_o_conclusion": _("<p>Las observaciones descritas no invalidan por si solas la operacion del negocio, pero requieren seguimiento para robustecer el sistema de control interno.</p>"),
        "conclusion_final": _("<p>La organizacion debe priorizar las mejoras propuestas segun el nivel de riesgo y la madurez de sus controles.</p>"),
        "fundamento_opinion": "",
        "responsabilidades_administracion": "",
        "responsabilidades_auditor": "",
    }


def _build_agreed_procedures_content(expediente, hallazgos):
    cliente_label, periodo_label, principales_html, _ = _common_hallazgo_blocks(expediente, hallazgos)
    return {
        "titulo_informe": _("Procedimientos Acordados - {0} - {1}").format(cliente_label, periodo_label),
        "resumen_ejecutivo": _("<p>El despacho ejecuto los procedimientos previamente acordados con el cliente y presenta a continuacion los resultados facticos obtenidos.</p>"),
        "alcance_del_trabajo": _("<p>El trabajo se limito a los procedimientos especificamente acordados para el expediente y no tuvo alcance de auditoria integral ni de aseguramiento independiente adicional.</p>"),
        "principales_hallazgos": principales_html,
        "recomendaciones_clave": _("<p>No se emite opinion. Cualquier recomendacion adicional debe evaluarse segun el alcance contractual del encargo.</p>"),
        "opinion_o_conclusion": _("<p>Los resultados anteriores reflejan exclusivamente los hechos observados al aplicar los procedimientos acordados.</p>"),
        "conclusion_final": _("<p>El uso de este informe debe limitarse a las partes que acordaron dichos procedimientos.</p>"),
        "fundamento_opinion": "",
        "responsabilidades_administracion": "",
        "responsabilidades_auditor": "",
    }


def _build_dictamen_content(expediente, hallazgos):
    cliente_label, periodo_label, principales_html, recomendaciones_html = _common_hallazgo_blocks(expediente, hallazgos)
    tipo_opinion = _suggest_opinion_type(expediente, TIPO_DICTAMEN_AUDITORIA) or "Favorable"
    efecto_generalizado = 1 if tipo_opinion in ("Adversa", "Abstencion") else 0
    limitacion_alcance = 1 if tipo_opinion == "Abstencion" else 0
    base_normativa = _default_dictamen_base_normativa(tipo_opinion)

    return {
        "titulo_informe": _("Dictamen de Auditoria - {0} - {1}").format(cliente_label, periodo_label),
        "resumen_ejecutivo": _build_dictamen_resumen(tipo_opinion, cliente_label, periodo_label, base_normativa),
        "alcance_del_trabajo": _("<p>El trabajo se desarrollo conforme al plan de auditoria, incluyendo evaluacion de riesgos, pruebas documentadas, revision tecnica y cierre formal del expediente.</p>"),
        "base_normativa": base_normativa,
        "principales_hallazgos": principales_html,
        "recomendaciones_clave": recomendaciones_html,
        "fundamento_opinion": _build_fundamento_opinion(expediente, tipo_opinion),
        "asunto_que_origina_modificacion": "",
        "fundamento_salvedad": "",
        "efecto_generalizado": efecto_generalizado,
        "limitacion_alcance_material": limitacion_alcance,
        "parrafo_enfasis": "",
        "parrafo_otros_asuntos": "",
        "responsabilidades_administracion": _build_dictamen_responsabilidades_administracion(),
        "responsabilidades_auditor": _build_dictamen_responsabilidades_auditor(tipo_opinion),
        "opinion_o_conclusion": _build_opinion_dictamen_nia(cliente_label, periodo_label, tipo_opinion),
        "conclusion_final": _build_dictamen_conclusion(tipo_opinion),
    }


def _build_general_opinion(expediente, cliente_label, periodo_label):
    if (expediente.hallazgos_abiertos or 0) > 0:
        return _(
            "<p>El cierre del expediente para <b>{0}</b> del periodo <b>{1}</b> concluye con observaciones y acciones de seguimiento que deben mantenerse bajo monitoreo hasta su cierre formal.</p>"
        ).format(cliente_label, periodo_label)
    if (expediente.total_hallazgos or 0) > 0:
        return _(
            "<p>El trabajo realizado permite emitir una conclusion favorable con observaciones atendidas durante el cierre del expediente para <b>{0}</b> en el periodo <b>{1}</b>.</p>"
        ).format(cliente_label, periodo_label)
    return _(
        "<p>Con base en la evidencia documentada y la revision tecnica aprobada, el despacho emite una conclusion favorable sobre el cierre del expediente de auditoria de <b>{0}</b> para el periodo <b>{1}</b>.</p>"
    ).format(cliente_label, periodo_label)


def _build_fundamento_opinion(expediente, tipo_opinion):
    nia_label = "NIA 700" if tipo_opinion == "Favorable" else "NIA 705"
    base = [
        _("El dictamen se fundamenta en el expediente de auditoria aprobado y en la evidencia obtenida durante la ejecucion del encargo conforme a {0}.").format(nia_label),
        _("Se documentaron {0} riesgos, {1} papeles de trabajo y {2} hallazgos.").format(
            expediente.total_riesgos or 0,
            expediente.total_papeles or 0,
            expediente.total_hallazgos or 0,
        ),
    ]
    if tipo_opinion in OPINIONES_DICTAMEN_MODIFICADAS:
        base.append(_("La opinion se modifica de acuerdo con la naturaleza, materialidad y, cuando corresponde, generalizacion de los asuntos descritos en este informe."))
    if expediente.hallazgos_abiertos:
        base.append(_("A la fecha de emision subsisten {0} hallazgos en seguimiento que inciden en la evaluacion del dictamen.").format(expediente.hallazgos_abiertos))
    return "".join(f"<p>{item}</p>" for item in base)


def _build_fundamento_salvedad(expediente, hallazgos, tipo_opinion):
    detalles = [
        _("La opinion se modifica debido a los asuntos documentados en el expediente y a su efecto sobre la informacion evaluada."),
    ]
    if hallazgos:
        detalles.append(_("Hallazgo principal: {0}.").format(hallazgos[0].titulo_hallazgo or hallazgos[0].name))
    if tipo_opinion == "Abstencion":
        detalles.append(_("La administracion no proporciono evidencia suficiente y adecuada en aspectos materiales, generando una limitacion al alcance de caracter generalizado."))
    elif tipo_opinion == "Adversa":
        detalles.append(_("Los efectos identificados son materiales y generalizados para la informacion objeto del encargo."))
    else:
        detalles.append(_("Los efectos identificados son materiales pero no generalizados para la informacion objeto del encargo."))
    return "".join(f"<p>{item}</p>" for item in detalles)


def _default_dictamen_base_normativa(tipo_opinion, has_nia_706=False):
    base = "NIA 700" if tipo_opinion == "Favorable" else "NIA 705"
    if has_nia_706:
        return f"{base} / NIA 706"
    return base


def _build_dictamen_resumen(tipo_opinion, cliente_label, periodo_label, base_normativa):
    if tipo_opinion == "Favorable":
        return _(
            "<p>Se presenta el dictamen correspondiente al encargo de auditoria ejecutado para <b>{0}</b> en el periodo <b>{1}</b>, con redaccion alineada a <b>{2}</b> para una opinion no modificada.</p>"
        ).format(cliente_label, periodo_label, base_normativa)
    return _(
        "<p>Se presenta el dictamen correspondiente al encargo de auditoria ejecutado para <b>{0}</b> en el periodo <b>{1}</b>, con redaccion alineada a <b>{2}</b> por tratarse de una opinion modificada.</p>"
    ).format(cliente_label, periodo_label, base_normativa)


def _build_opinion_dictamen_nia(cliente_label, periodo_label, tipo_opinion):
    if tipo_opinion == "Favorable":
        return _(
            "<p>En nuestra opinion, los estados e informacion objeto del encargo presentan razonablemente, en todos los aspectos materiales, la situacion evaluada de <b>{0}</b> correspondiente al periodo <b>{1}</b>, de conformidad con el marco de referencia aplicable.</p>"
        ).format(cliente_label, periodo_label)
    if tipo_opinion == "Con Salvedades":
        return _(
            "<p>En nuestra opinion con salvedades, excepto por los efectos del asunto descrito en la seccion de fundamento de la opinion modificada, la informacion objeto del encargo presenta razonablemente, en todos los aspectos materiales, la situacion evaluada de <b>{0}</b> correspondiente al periodo <b>{1}</b>.</p>"
        ).format(cliente_label, periodo_label)
    if tipo_opinion == "Adversa":
        return _(
            "<p>En nuestra opinion adversa, debido a la importancia y generalizacion del asunto descrito en la seccion de fundamento de la opinion modificada, la informacion objeto del encargo no presenta razonablemente la situacion evaluada de <b>{0}</b> correspondiente al periodo <b>{1}</b>.</p>"
        ).format(cliente_label, periodo_label)
    return _(
        "<p>No expresamos una opinion sobre la informacion objeto del encargo de <b>{0}</b> correspondiente al periodo <b>{1}</b>, debido a la importancia y generalizacion de la limitacion al alcance descrita en la seccion de fundamento de la abstencion.</p>"
    ).format(cliente_label, periodo_label)


def _build_dictamen_responsabilidades_administracion():
    return _(
        "<p>La administracion es responsable de la preparacion y presentacion razonable de la informacion objeto del encargo conforme al marco de referencia aplicable, asi como del control interno que considere necesario para permitir dicha preparacion libre de incorreccion material, debida a fraude o error.</p>"
    )


def _build_dictamen_responsabilidades_auditor(tipo_opinion):
    base = [
        _("Nuestra responsabilidad consiste en expresar una opinion sobre la informacion objeto del encargo con base en la auditoria realizada."),
        _("Condujimos nuestro trabajo de conformidad con las Normas Internacionales de Auditoria, las cuales requieren cumplir requerimientos de etica, planificar y ejecutar la auditoria para obtener seguridad razonable sobre si la informacion esta libre de incorreccion material."),
    ]
    if tipo_opinion == "Abstencion":
        base.append(_("Debido a la limitacion al alcance descrita en este informe, no fue posible obtener evidencia de auditoria suficiente y adecuada para sustentar una opinion."))
    return "".join(f"<p>{item}</p>" for item in base)


def _build_dictamen_conclusion(tipo_opinion):
    if tipo_opinion == "Favorable":
        return _("<p>El presente dictamen favorable se emite con base en la evidencia suficiente y adecuada contenida en el expediente aprobado.</p>")
    if tipo_opinion == "Con Salvedades":
        return _("<p>El presente dictamen con salvedades se emite considerando la evidencia disponible y los efectos materiales no generalizados descritos en este informe.</p>")
    if tipo_opinion == "Adversa":
        return _("<p>El presente dictamen adverso se emite por los efectos materiales y generalizados documentados en el expediente aprobado.</p>")
    return _("<p>La presente abstencion de opinion se emite porque no fue posible obtener evidencia suficiente y adecuada para sustentar una opinion de auditoria.</p>")


def _common_hallazgo_blocks(expediente, hallazgos):
    cliente_label = _get_cliente_label(expediente.cliente)
    periodo_label = expediente.periodo or _("sin periodo")
    top_hallazgos = hallazgos[:5]

    principales = []
    recomendaciones = []
    for row in top_hallazgos:
        titulo = row.titulo_hallazgo or row.name
        principales.append(
            _("<li><b>{0}</b> ({1}) - Estado: {2}</li>").format(
                frappe.utils.escape_html(titulo),
                frappe.utils.escape_html(row.severidad or _("Sin severidad")),
                frappe.utils.escape_html(row.estado_hallazgo or _("Sin estado")),
            )
        )
        if cstr(row.recomendacion or "").strip():
            recomendaciones.append(f"<li>{row.recomendacion}</li>")

    if not principales:
        principales_html = _("<p>No se documentaron hallazgos materiales abiertos al cierre del expediente.</p>")
    else:
        principales_html = "<ul>{0}</ul>".format("".join(principales))

    if not recomendaciones:
        recomendaciones_html = _(
            "<p>Se recomienda mantener el seguimiento interno sobre controles, documentacion soporte y planes de accion derivados del expediente.</p>"
        )
    else:
        recomendaciones_html = "<ul>{0}</ul>".format("".join(recomendaciones[:5]))

    return cliente_label, periodo_label, principales_html, recomendaciones_html


def _get_cliente_label(cliente_name):
    if not cliente_name:
        return ""
    customer = frappe.db.get_value("Cliente Contable", cliente_name, "customer")
    if customer and frappe.db.exists("Customer", customer):
        return frappe.db.get_value("Customer", customer, "customer_name") or cliente_name
    if frappe.db.exists("Customer", cliente_name):
        return frappe.db.get_value("Customer", cliente_name, "customer_name") or cliente_name
    return cliente_name


def cint_bool(value):
    return 1 if str(value) in ("1", "True", "true") or value == 1 else 0