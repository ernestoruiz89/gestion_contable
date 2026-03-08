import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, now_datetime, nowdate

from gestion_contable.gestion_contable.doctype.informe_final_auditoria.informe_final_auditoria import TIPO_DICTAMEN_AUDITORIA
from gestion_contable.gestion_contable.utils.estados_financieros import (
    calculate_package_summary,
    get_customer_identity,
    sync_package_summary,
    validate_package_math,
    validate_required_notes,
    validate_required_statement_types,
)
from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO, validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor
from gestion_contable.gestion_contable.utils.word_export import export_audited_financial_package_to_word

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_del_paquete",
    "cliente",
    "encargo_contable",
    "expediente_auditoria",
    "periodo_contable",
    "fecha_corte",
    "fecha_emision",
    "razon_social_reportante",
    "identificacion_fiscal_reportante",
    "moneda_presentacion",
    "marco_contable",
    "tipo_paquete",
    "version",
    "es_version_vigente",
    "estado_preparacion",
    "observaciones_generales",
    "informe_final_auditoria",
    "dictamen_de_auditoria",
)
ESTADOS_PREPARACION = (
    "Borrador",
    "En Preparacion",
    "En Revision",
    "Aprobado para Emision",
    "Emitido",
    "Reemplazado",
)
VERSION_DOCUMENTO_TIPOS = (
    "Word Revision Cliente",
    "PDF Paquete Completo",
    "PDF Notas Consolidadas",
    "PDF Informe Auditado",
    "Otro",
)
VERSION_DOCUMENTO_ESTADOS = (
    "Generado",
    "Enviado a Cliente",
    "Comentado por Cliente",
    "Aprobado por Cliente",
    "Emitido",
    "Reemplazado",
)


class PaqueteEstadosFinancierosCliente(Document):
    def autoname(self):
        if self.nombre_del_paquete:
            self.name = self.nombre_del_paquete
            return
            
        cliente = self.cliente or "Cliente"
        
        periodo_str = ""
        if self.periodo_contable and frappe.db.exists("Periodo Contable", self.periodo_contable):
            p = frappe.db.get_value("Periodo Contable", self.periodo_contable, ["mes", "anio"], as_dict=True)
            if p and p.mes and p.anio:
                periodo_str = f"{p.mes} {p.anio}"
                
        if not periodo_str:
            periodo_str = self.periodo_contable or self.fecha_corte or nowdate()
            
        version = self.version or 1
        base_name = f"EEFF - {cliente} - {periodo_str} - V{version}"
        self.nombre_del_paquete = self._build_unique_name(base_name)
        self.name = self.nombre_del_paquete

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar paquetes de estados financieros del cliente."))
        self.sincronizar_contexto()
        self.validar_estado_preparacion()
        self.validar_consistencias()
        self.aplicar_resumen(calculate_package_summary(self.name if self.name and not self.name.startswith("new-") else None))
        self.normalizar_versiones_documento_eeff()
        self.validar_versionado()
        self.validar_versiones_documento_eeff()
        self.validar_informes_relacionados()
        self.validar_emision()
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            label=_("el paquete de estados financieros del cliente"),
        )

    def on_update(self):
        if self.es_version_vigente:
            frappe.db.sql(
                """
                UPDATE `tabPaquete Estados Financieros Cliente`
                SET es_version_vigente = 0
                WHERE name != %s
                  AND cliente = %s
                  AND IFNULL(periodo_contable, '') = %s
                  AND IFNULL(marco_contable, '') = %s
                  AND IFNULL(tipo_paquete, '') = %s
                """,
                (self.name, self.cliente, self.periodo_contable or "", self.marco_contable or "", self.tipo_paquete or ""),
            )
        sync_package_summary(self.name)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar paquetes de estados financieros del cliente."))

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Paquete Estados Financieros Cliente", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Paquete Estados Financieros Cliente", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_contexto(self):
        self.version = self.version or 1
        self.es_version_vigente = 0 if self.estado_preparacion == "Reemplazado" else int(self.es_version_vigente or 0)
        self.estado_preparacion = self.estado_preparacion or "Borrador"
        self.fecha_corte = self.fecha_corte or nowdate()

        if self.encargo_contable and frappe.db.exists("Encargo Contable", self.encargo_contable):
            encargo = frappe.db.get_value(
                "Encargo Contable",
                self.encargo_contable,
                ["cliente", "periodo_referencia", "moneda"],
                as_dict=True,
            )
            if not self.cliente:
                self.cliente = encargo.cliente
            if not self.periodo_contable and encargo.periodo_referencia:
                self.periodo_contable = encargo.periodo_referencia
            if not self.moneda_presentacion and encargo.moneda:
                self.moneda_presentacion = encargo.moneda

        if self.expediente_auditoria and frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            expediente = frappe.db.get_value(
                "Expediente Auditoria",
                self.expediente_auditoria,
                ["cliente", "encargo_contable", "periodo", "informe_final_auditoria"],
                as_dict=True,
            )
            if not self.cliente:
                self.cliente = expediente.cliente
            if not self.encargo_contable and expediente.encargo_contable:
                self.encargo_contable = expediente.encargo_contable
            if not self.periodo_contable and expediente.periodo:
                self.periodo_contable = expediente.periodo
            if not self.informe_final_auditoria and expediente.informe_final_auditoria:
                self.informe_final_auditoria = expediente.informe_final_auditoria

        identity = get_customer_identity(self.cliente)
        self.razon_social_reportante = self.razon_social_reportante or identity["razon_social"]
        self.identificacion_fiscal_reportante = self.identificacion_fiscal_reportante or identity["identificacion_fiscal"]
        self.moneda_presentacion = self.moneda_presentacion or identity["moneda"]
        self.marco_contable = self.marco_contable or "NIIF para PYMES"
        self.tipo_paquete = self.tipo_paquete or "Preliminar"

    def validar_estado_preparacion(self):
        if self.estado_preparacion not in ESTADOS_PREPARACION:
            frappe.throw(_("El estado de preparacion seleccionado no es valido."), title=_("Estado Invalido"))
        if self.estado_preparacion == "Reemplazado":
            self.es_version_vigente = 0

    def validar_consistencias(self):
        if not self.cliente:
            frappe.throw(_("Debes indicar el cliente del paquete de estados financieros."), title=_("Cliente Requerido"))
        if self.expediente_auditoria and frappe.db.exists("Expediente Auditoria", self.expediente_auditoria):
            expediente = frappe.db.get_value(
                "Expediente Auditoria",
                self.expediente_auditoria,
                ["cliente", "encargo_contable", "periodo"],
                as_dict=True,
            )
            if self.cliente != expediente.cliente:
                frappe.throw(_("El cliente del paquete no coincide con el cliente del expediente vinculado."), title=_("Cliente Inconsistente"))
            if self.encargo_contable and expediente.encargo_contable and self.encargo_contable != expediente.encargo_contable:
                frappe.throw(_("El encargo del paquete no coincide con el encargo del expediente vinculado."), title=_("Encargo Inconsistente"))
            if self.periodo_contable and expediente.periodo and self.periodo_contable != expediente.periodo:
                frappe.throw(_("El periodo del paquete no coincide con el periodo del expediente vinculado."), title=_("Periodo Inconsistente"))
        if self.fecha_emision and cstr(self.fecha_emision) < cstr(self.fecha_corte):
            frappe.throw(_("La fecha de emision no puede ser anterior a la fecha de corte."), title=_("Fechas Invalidas"))

    def aplicar_resumen(self, summary):
        for key, value in (summary or {}).items():
            setattr(self, key, value)

    def normalizar_versiones_documento_eeff(self):
        rows = list(self.get("versiones_documento_eeff") or [])
        grouped = {}
        for index, row in enumerate(rows, start=1):
            row.tipo_documento = row.tipo_documento or "Otro"
            row.version_documento = max(cint(row.version_documento or index), 1)
            row.estado_documento = row.estado_documento or "Generado"
            row.es_version_vigente = cint(row.es_version_vigente)
            row.fecha_generacion = row.fecha_generacion or now_datetime()
            row.generado_por = row.generado_por or frappe.session.user
            if row.archivo_file and not row.nombre_archivo:
                row.nombre_archivo = frappe.db.get_value("File", row.archivo_file, "file_name")
            if row.archivo_file and not row.archivo_url:
                row.archivo_url = frappe.db.get_value("File", row.archivo_file, "file_url")
            if row.entregable_cliente and frappe.db.exists("Entregable Cliente", row.entregable_cliente) and not row.requerimiento_cliente:
                row.requerimiento_cliente = frappe.db.get_value("Entregable Cliente", row.entregable_cliente, "requerimiento_cliente")
            if row.estado_documento in ("Enviado a Cliente", "Comentado por Cliente", "Aprobado por Cliente") and not row.fecha_envio_cliente:
                row.fecha_envio_cliente = row.fecha_generacion
            if row.estado_documento in ("Comentado por Cliente", "Aprobado por Cliente") and row.documento_revision_cliente and not row.fecha_revision_cliente:
                row.fecha_revision_cliente = now_datetime()
            if row.estado_documento == "Reemplazado":
                row.es_version_vigente = 0
            grouped.setdefault(row.tipo_documento, []).append(row)

        for tipo_rows in grouped.values():
            tipo_rows.sort(key=lambda item: cint(item.version_documento), reverse=True)
            vigente = next((item for item in tipo_rows if cint(item.es_version_vigente) and item.estado_documento != "Reemplazado"), None)
            if not vigente:
                vigente = next((item for item in tipo_rows if item.estado_documento != "Reemplazado"), None)
            for item in tipo_rows:
                item.es_version_vigente = 1 if vigente and item is vigente else 0

    def validar_versiones_documento_eeff(self):
        seen_versions = set()
        for row in self.get("versiones_documento_eeff") or []:
            if row.tipo_documento not in VERSION_DOCUMENTO_TIPOS:
                frappe.throw(_("El tipo de documento <b>{0}</b> no es valido en el historial de versiones EEFF.").format(row.tipo_documento), title=_("Tipo Documento Invalido"))
            if row.estado_documento not in VERSION_DOCUMENTO_ESTADOS:
                frappe.throw(_("El estado de documento <b>{0}</b> no es valido en el historial de versiones EEFF.").format(row.estado_documento), title=_("Estado Documento Invalido"))
            key = (row.tipo_documento, cint(row.version_documento))
            if key in seen_versions:
                frappe.throw(_("No puedes repetir la version <b>{0}</b> para el tipo de documento <b>{1}</b>.").format(row.version_documento, row.tipo_documento), title=_("Version Documento Duplicada"))
            seen_versions.add(key)
            if row.archivo_file and not frappe.db.exists("File", row.archivo_file):
                frappe.throw(_("El archivo vinculado en la version <b>{0}</b> no existe.").format(row.version_documento), title=_("Archivo Invalido"))
            if row.fecha_revision_cliente and not row.fecha_envio_cliente:
                frappe.throw(_("No puedes registrar fecha de revision del cliente sin fecha de envio al cliente en la version <b>{0}</b>.").format(row.version_documento), title=_("Fechas Inconsistentes"))
            if row.requerimiento_cliente:
                requerimiento = frappe.db.get_value(
                    "Requerimiento Cliente",
                    row.requerimiento_cliente,
                    ["cliente"],
                    as_dict=True,
                )
                if not requerimiento:
                    frappe.throw(_("El requerimiento vinculado en la version <b>{0}</b> no existe.").format(row.version_documento), title=_("Requerimiento Invalido"))
                if requerimiento.cliente and requerimiento.cliente != self.cliente:
                    frappe.throw(_("La version <b>{0}</b> referencia un requerimiento de otro cliente.").format(row.version_documento), title=_("Cliente Inconsistente"))
            if row.entregable_cliente:
                entregable = frappe.db.get_value(
                    "Entregable Cliente",
                    row.entregable_cliente,
                    ["cliente", "requerimiento_cliente"],
                    as_dict=True,
                )
                if not entregable:
                    frappe.throw(_("El entregable vinculado en la version <b>{0}</b> no existe.").format(row.version_documento), title=_("Entregable Invalido"))
                if entregable.cliente and entregable.cliente != self.cliente:
                    frappe.throw(_("La version <b>{0}</b> referencia un entregable de otro cliente.").format(row.version_documento), title=_("Cliente Inconsistente"))
                if row.requerimiento_cliente and entregable.requerimiento_cliente and row.requerimiento_cliente != entregable.requerimiento_cliente:
                    frappe.throw(_("La version <b>{0}</b> tiene requerimiento y entregable inconsistentes.").format(row.version_documento), title=_("Intercambio Inconsistente"))
            if row.documento_revision_cliente:
                documento = frappe.db.get_value(
                    "Documento Contable",
                    row.documento_revision_cliente,
                    ["cliente", "entregable_cliente"],
                    as_dict=True,
                )
                if not documento:
                    frappe.throw(_("El documento de revision del cliente en la version <b>{0}</b> no existe.").format(row.version_documento), title=_("Documento Invalido"))
                if documento.cliente and documento.cliente != self.cliente:
                    frappe.throw(_("La version <b>{0}</b> referencia un documento de otro cliente.").format(row.version_documento), title=_("Cliente Inconsistente"))
                if row.entregable_cliente and documento.entregable_cliente and row.entregable_cliente != documento.entregable_cliente:
                    frappe.throw(_("La version <b>{0}</b> no coincide con el entregable del documento de revision del cliente.").format(row.version_documento), title=_("Documento Inconsistente"))
            if row.estado_documento in ("Enviado a Cliente", "Comentado por Cliente", "Aprobado por Cliente") and not row.fecha_envio_cliente:
                frappe.throw(_("Debes indicar fecha de envio al cliente en la version <b>{0}</b>.").format(row.version_documento), title=_("Fecha Requerida"))
            if row.estado_documento == "Comentado por Cliente" and not row.documento_revision_cliente:
                frappe.throw(_("Debes vincular el documento devuelto por el cliente en la version <b>{0}</b> marcada como comentada.").format(row.version_documento), title=_("Documento Requerido"))


    def validar_versionado(self):
        if not self.es_version_vigente:
            return
        existing = frappe.get_all(
            "Paquete Estados Financieros Cliente",
            filters={
                "name": ["!=", self.name or ""],
                "cliente": self.cliente,
                "periodo_contable": self.periodo_contable,
                "marco_contable": self.marco_contable,
                "tipo_paquete": self.tipo_paquete,
                "es_version_vigente": 1,
            },
            fields=["name", "version"],
            limit_page_length=1,
        )
        if existing:
            frappe.throw(
                _("Ya existe una version vigente para este cliente, periodo, marco y tipo de paquete: <b>{0}</b> (version {1}).").format(existing[0].name, existing[0].version),
                title=_("Version Vigente Duplicada"),
            )

    def validar_informes_relacionados(self):
        for fieldname, expected_type in (("dictamen_de_auditoria", TIPO_DICTAMEN_AUDITORIA), ("informe_final_auditoria", None)):
            link_name = self.get(fieldname)
            if not link_name:
                continue
            if not frappe.db.exists("Informe Final Auditoria", link_name):
                frappe.throw(_("El informe vinculado en {0} no existe.").format(fieldname), title=_("Informe Invalido"))
            informe = frappe.db.get_value(
                "Informe Final Auditoria",
                link_name,
                ["tipo_de_informe", "estado_emision", "expediente_auditoria"],
                as_dict=True,
            )
            if expected_type and informe.tipo_de_informe != expected_type:
                frappe.throw(_("El campo {0} debe vincular un Informe Final Auditoria del tipo <b>{1}</b>.").format(fieldname, expected_type), title=_("Tipo de Informe Invalido"))
            if self.expediente_auditoria and informe.expediente_auditoria and informe.expediente_auditoria != self.expediente_auditoria:
                frappe.throw(_("El informe vinculado en {0} pertenece a un expediente distinto al paquete.").format(fieldname), title=_("Expediente Inconsistente"))
            if self.estado_preparacion == "Emitido" and informe.estado_emision != "Emitido":
                frappe.throw(_("El informe vinculado en {0} debe estar emitido antes de emitir el paquete.").format(fieldname), title=_("Informe No Emitido"))

    def validar_emision(self):
        if self.estado_preparacion != "Emitido":
            if self.estado_preparacion == "Borrador":
                self.fecha_emision = None
            return

        ensure_manager(_("Solo Socio, Contador o System Manager pueden emitir paquetes de estados financieros del cliente."))
        if self.estado_aprobacion != ESTADO_APROBACION_APROBADO:
            frappe.throw(_("El paquete debe estar aprobado antes de emitirse."), title=_("Aprobacion Requerida"))
        validate_required_statement_types(self)
        validate_required_notes(self)
        validate_package_math(self)
        if self.tipo_paquete == "Auditado" and not self.dictamen_de_auditoria:
            frappe.throw(_("Un paquete auditado requiere vincular un Dictamen de Auditoria emitido."), title=_("Dictamen Requerido"))
        self.fecha_emision = self.fecha_emision or nowdate()


def sincronizar_version_documento_eeff_con_intercambio_cliente(
    *,
    cliente,
    requerimiento_cliente=None,
    entregable_cliente=None,
    documento_revision_cliente=None,
    version_documento_name=None,
    nuevo_estado=None,
):
    if not cliente or not frappe.db.exists("DocType", "Version Documento EEFF"):
        return None

    conditions = ["pkg.cliente = %(cliente)s", "row.tipo_documento = 'Word Revision Cliente'"]
    values = {"cliente": cliente}
    if version_documento_name:
        conditions.append("row.name = %(version_documento_name)s")
        values["version_documento_name"] = version_documento_name
    elif entregable_cliente:
        conditions.append("row.entregable_cliente = %(entregable_cliente)s")
        values["entregable_cliente"] = entregable_cliente
    elif requerimiento_cliente:
        conditions.append("row.requerimiento_cliente = %(requerimiento_cliente)s")
        values["requerimiento_cliente"] = requerimiento_cliente
    else:
        return None

    row = frappe.db.sql(
        f"""
        SELECT row.name, row.requerimiento_cliente, row.entregable_cliente, row.version_documento, row.estado_documento
        FROM `tabVersion Documento EEFF` row
        INNER JOIN `tabPaquete Estados Financieros Cliente` pkg
            ON pkg.name = row.parent
        WHERE {' AND '.join(conditions)}
          AND row.estado_documento != 'Reemplazado'
        ORDER BY row.version_documento DESC, row.modified DESC
        LIMIT 1
        """,
        values,
        as_dict=True,
    )
    if not row:
        return None

    updates = {}
    if requerimiento_cliente:
        updates["requerimiento_cliente"] = requerimiento_cliente
    if entregable_cliente:
        updates["entregable_cliente"] = entregable_cliente
    if documento_revision_cliente:
        updates["documento_revision_cliente"] = documento_revision_cliente
    if nuevo_estado:
        updates["estado_documento"] = nuevo_estado
    if (nuevo_estado or row[0].get("estado_documento")) in ("Enviado a Cliente", "Comentado por Cliente", "Aprobado por Cliente"):
        updates.setdefault("fecha_envio_cliente", now_datetime())
    if (nuevo_estado or row[0].get("estado_documento")) in ("Comentado por Cliente", "Aprobado por Cliente"):
        updates["fecha_revision_cliente"] = now_datetime()

    if updates:
        frappe.db.set_value("Version Documento EEFF", row[0].name, updates, update_modified=False)

    return frappe.db.get_value(
        "Version Documento EEFF",
        row[0].name,
        [
            "name",
            "requerimiento_cliente",
            "entregable_cliente",
            "documento_revision_cliente",
            "estado_documento",
            "fecha_envio_cliente",
            "fecha_revision_cliente",
        ],
        as_dict=True,
    )


@frappe.whitelist()
def refrescar_resumen_paquete_estados_financieros(package_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden recalcular paquetes de estados financieros del cliente."))
    if not frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        frappe.throw(_("El paquete indicado no existe."), title=_("Paquete Invalido"))
    return sync_package_summary(package_name)


@frappe.whitelist()
def emitir_paquete_estados_financieros(package_name):
    ensure_manager(_("Solo Socio, Contador o System Manager pueden emitir paquetes de estados financieros del cliente."))
    package = frappe.get_doc("Paquete Estados Financieros Cliente", package_name)
    package.estado_preparacion = "Emitido"
    package.save(ignore_permissions=True)
    return {"name": package.name, "estado_preparacion": package.estado_preparacion, "fecha_emision": package.fecha_emision}


@frappe.whitelist()
def exportar_informe_completo_eeff_auditados_word(package_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden exportar el informe completo auditado a Word."))
    if not frappe.db.exists("Paquete Estados Financieros Cliente", package_name):
        frappe.throw(_("El paquete indicado no existe."), title=_("Paquete Invalido"))
    return export_audited_financial_package_to_word(package_name)