import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, nowdate

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import validate_periodo_operativo
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.operational_context import sync_operational_company
from gestion_contable.gestion_contable.utils.retention import (
    calculate_retention_deadline,
    get_document_retention_defaults,
    validate_document_retention_for_delete,
)
from gestion_contable.gestion_contable.utils.security import ensure_manager, get_current_user, is_auxiliar


DOCUMENTO_CONTENT_FIELDS = (
    "titulo_del_documento",
    "cliente",
    "company",
    "periodo",
    "encargo_contable",
    "task",
    "entregable_cliente",
    "tipo",
    "archivo_adjunto",
    "evidencias_documentales",
    "preparado_por",
)

DOCUMENTO_CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
    "Auxiliar Contable del Despacho",
)

DOCUMENTO_AUX_EDITABLE_FIELDS = (
    "titulo_del_documento",
    "tipo",
    "archivo_adjunto",
    "evidencias_documentales",
)

EVIDENCIA_TIPO_DEFAULT = "Otro"
EVIDENCIA_ORIGEN_DEFAULT = "Otro"
EVIDENCIA_CONFIDENCIALIDAD_DEFAULT = "Confidencial"
EVIDENCIA_RETENCION_DEFAULT = "Sin Definir"
ENCARGOS_CERRADOS = ("Cerrado", "Cancelado")


def get_primary_task_assignee(raw_assignments):
    if not raw_assignments:
        return None
    if isinstance(raw_assignments, (list, tuple)):
        return raw_assignments[0] if raw_assignments else None
    try:
        parsed = json.loads(raw_assignments)
    except Exception:
        return None
    return parsed[0] if isinstance(parsed, list) and parsed else None


class DocumentoContable(Document):
    def validate(self):
        self.sincronizar_desde_encargo()
        self.sincronizar_desde_tarea()
        self.sincronizar_desde_entregable()
        self.sincronizar_company_operativa()
        self.asegurar_preparado_por()
        self.sincronizar_evidencias_documentales()
        self.validar_propiedad_auxiliar()
        self.validar_cliente_activo()
        self.validar_periodo_abierto()
        self.validar_encargo_consistente()
        self.validar_tarea_consistente()
        self.validar_entregable_consistente()
        self.validar_gobierno_operativo()

    def before_rename(self, old, new, merge=False):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden renombrar documentos contables."))

    def on_update(self):
        previous = None if self.is_new() else self.get_doc_before_save()
        if previous and previous.entregable_cliente and previous.entregable_cliente != self.entregable_cliente:
            self._desvincular_entregable(previous.entregable_cliente)
        self._sincronizar_entregable_vinculado()

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar documentos contables."))
        validate_document_retention_for_delete(self)
        if self.entregable_cliente:
            self._desvincular_entregable(self.entregable_cliente)

    def validar_gobierno_operativo(self):
        validate_governance(
            self,
            content_fields=DOCUMENTO_CONTENT_FIELDS,
            create_roles=DOCUMENTO_CREATE_ROLES,
            draft_roles=DOCUMENTO_CREATE_ROLES,
            aux_editable_fields=DOCUMENTO_AUX_EDITABLE_FIELDS,
            aux_owner_field="preparado_por",
            label=_("el documento"),
        )

    def validar_propiedad_auxiliar(self):
        if not is_auxiliar():
            return
        if self.preparado_por and self.preparado_por != get_current_user():
            frappe.throw(
                _("Como Auxiliar solo puedes crear o actualizar documentos preparados por tu usuario."),
                frappe.PermissionError,
            )

    def asegurar_preparado_por(self):
        if self.preparado_por:
            return
        self.preparado_por = self.resolver_preparado_por()

    def resolver_preparado_por(self):
        tarea = self.obtener_datos_tarea(throw_if_missing=False)
        if tarea:
            asignado_a = get_primary_task_assignee(tarea.get("_assign"))
            if asignado_a:
                return asignado_a

        entregable = self.obtener_datos_entregable(throw_if_missing=False)
        if entregable and entregable.responsable_interno:
            return entregable.responsable_interno

        if not self.is_new() and self.name and frappe.db.exists("Documento Contable", self.name):
            historico = frappe.db.get_value(
                "Documento Contable",
                self.name,
                ["preparado_por", "modified_by", "owner"],
                as_dict=True,
            )
            if historico:
                for candidate in (historico.preparado_por, historico.modified_by, historico.owner):
                    if candidate and candidate != "Guest":
                        return candidate

        current_user = get_current_user()
        if current_user and current_user != "Guest":
            return current_user
        return None

    def sincronizar_desde_encargo(self):
        encargo = self.obtener_datos_encargo(throw_if_missing=False)
        if not encargo:
            return
        if not self.cliente:
            self.cliente = encargo.cliente
        if not self.periodo and encargo.periodo_referencia:
            self.periodo = encargo.periodo_referencia
        if not self.company and encargo.company:
            self.company = encargo.company

    def sincronizar_desde_tarea(self):
        tarea = self.obtener_datos_tarea(throw_if_missing=False)
        if not tarea:
            return
        if not self.encargo_contable and tarea.encargo_contable:
            self.encargo_contable = tarea.encargo_contable
        if not self.cliente:
            self.cliente = tarea.cliente
        if not self.company and tarea.company:
            self.company = tarea.company
        if not self.periodo:
            self.periodo = tarea.periodo

    def sincronizar_desde_entregable(self):
        entregable = self.obtener_datos_entregable(throw_if_missing=False)
        if not entregable:
            return
        if not self.encargo_contable and entregable.encargo_contable:
            self.encargo_contable = entregable.encargo_contable
        if not self.cliente:
            self.cliente = entregable.cliente
        if not self.company and entregable.company:
            self.company = entregable.company
        if not self.periodo:
            self.periodo = entregable.periodo

    def obtener_datos_encargo(self, throw_if_missing=True):
        if not self.encargo_contable:
            return None
        encargo = frappe.db.get_value(
            "Encargo Contable",
            self.encargo_contable,
            ["name", "cliente", "periodo_referencia", "estado", "company"],
            as_dict=True,
        )
        if not encargo and throw_if_missing:
            frappe.throw(
                _("El encargo contable <b>{0}</b> no existe.").format(self.encargo_contable),
                title=_("Encargo Invalido"),
            )
        if encargo and self.is_new() and encargo.estado in ENCARGOS_CERRADOS:
            frappe.throw(
                _("No se pueden registrar documentos en un encargo con estado <b>{0}</b>." ).format(encargo.estado),
                title=_("Encargo Cerrado"),
            )
        return encargo

    def obtener_datos_tarea(self, throw_if_missing=True):
        if not self.task:
            return None
        tarea = frappe.db.get_value(
            "Task",
            self.task,
            ["name", "encargo_contable", "cliente", "company", "periodo", "_assign"],
            as_dict=True,
        )
        if tarea:
            tarea.asignado_a = get_primary_task_assignee(tarea.get("_assign"))
        if not tarea and throw_if_missing:
            frappe.throw(
                _("La tarea operativa <b>{0}</b> no existe.").format(self.task),
                title=_("Tarea Invalida"),
            )
        return tarea

    def obtener_datos_entregable(self, throw_if_missing=True):
        if not self.entregable_cliente:
            return None
        entregable = frappe.db.get_value(
            "Entregable Cliente",
            self.entregable_cliente,
            [
                "name",
                "encargo_contable",
                "cliente",
                "company",
                "periodo",
                "responsable_interno",
                "documento_contable",
                "estado_entregable",
                "fecha_solicitud",
                "requerimiento_cliente",
            ],
            as_dict=True,
        )
        if not entregable and throw_if_missing:
            frappe.throw(
                _("El entregable cliente <b>{0}</b> no existe.").format(self.entregable_cliente),
                title=_("Entregable Invalido"),
            )
        return entregable

    def validar_cliente_activo(self):
        if not self.cliente:
            return
        estado = frappe.db.get_value("Cliente Contable", self.cliente, "estado")
        if estado != "Activo":
            frappe.throw(
                _("No se pueden registrar documentos para el cliente <b>{0}</b> porque su estado es <b>{1}</b>." ).format(
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
            label=_("el documento"),
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
            label=_("el documento"),
        )

    def validar_encargo_consistente(self):
        encargo = self.obtener_datos_encargo(throw_if_missing=False)
        if not encargo:
            return

        inconsistencias = []
        if self.cliente and self.cliente != encargo.cliente:
            inconsistencias.append(_("Cliente"))
        if self.company and encargo.company and self.company != encargo.company:
            inconsistencias.append(_("Compania"))
        if self.periodo and encargo.periodo_referencia and self.periodo != encargo.periodo_referencia:
            inconsistencias.append(_("Periodo"))

        if inconsistencias:
            frappe.throw(
                _("El documento no coincide con el encargo <b>{0}</b>. Ajusta: <b>{1}</b>." ).format(
                    encargo.name, ", ".join(inconsistencias)
                ),
                title=_("Inconsistencia de Trazabilidad"),
            )

    def validar_tarea_consistente(self):
        tarea = self.obtener_datos_tarea(throw_if_missing=False)
        if not tarea:
            return

        inconsistencias = []
        if self.encargo_contable and tarea.encargo_contable and self.encargo_contable != tarea.encargo_contable:
            inconsistencias.append(_("Encargo"))
        if self.cliente and tarea.cliente and self.cliente != tarea.cliente:
            inconsistencias.append(_("Cliente"))
        if self.company and tarea.company and self.company != tarea.company:
            inconsistencias.append(_("Compania"))
        if self.periodo and tarea.periodo and self.periodo != tarea.periodo:
            inconsistencias.append(_("Periodo"))

        if inconsistencias:
            frappe.throw(
                _("La tarea vinculada no coincide con el documento en: <b>{0}</b>." ).format(", ".join(inconsistencias)),
                title=_("Inconsistencia de Trazabilidad"),
            )

    def validar_entregable_consistente(self):
        entregable = self.obtener_datos_entregable(throw_if_missing=False)
        if not entregable:
            return

        if entregable.documento_contable and entregable.documento_contable != self.name:
            frappe.throw(
                _("El entregable cliente ya esta vinculado al documento <b>{0}</b>." ).format(entregable.documento_contable),
                title=_("Entregable Ya Vinculado"),
            )

        inconsistencias = []
        if self.encargo_contable and entregable.encargo_contable and self.encargo_contable != entregable.encargo_contable:
            inconsistencias.append(_("Encargo"))
        if self.cliente and entregable.cliente and self.cliente != entregable.cliente:
            inconsistencias.append(_("Cliente"))
        if self.company and entregable.company and self.company != entregable.company:
            inconsistencias.append(_("Compania"))
        if self.periodo and entregable.periodo and self.periodo != entregable.periodo:
            inconsistencias.append(_("Periodo"))

        if inconsistencias:
            frappe.throw(
                _("El entregable vinculado no coincide con el documento en: <b>{0}</b>." ).format(", ".join(inconsistencias)),
                title=_("Inconsistencia de Trazabilidad"),
            )

    def sincronizar_evidencias_documentales(self):
        previous = None if self.is_new() else self.get_doc_before_save()
        if not self.evidencias_documentales and self.archivo_adjunto:
            self.append("evidencias_documentales", self._build_default_evidence_row(self.archivo_adjunto))

        if self.evidencias_documentales and self._legacy_attachment_changed(previous) and self.archivo_adjunto:
            principal = self._get_primary_evidence()
            if principal:
                principal.archivo = self.archivo_adjunto

        if self.evidencias_documentales and self._legacy_type_changed(previous) and self.tipo:
            principal = self._get_primary_evidence()
            if principal:
                principal.tipo_documental = self.tipo

        self._normalizar_evidencias(previous)

        if not self.evidencias_documentales and self.archivo_adjunto:
            self.append("evidencias_documentales", self._build_default_evidence_row(self.archivo_adjunto))
            self._normalizar_evidencias(previous)

        principal = self._get_primary_evidence()
        if principal:
            self.archivo_adjunto = principal.archivo
            self.tipo = principal.tipo_documental or self.tipo or EVIDENCIA_TIPO_DEFAULT

        if not self.archivo_adjunto:
            frappe.throw(
                _("Debes adjuntar al menos una evidencia documental para el documento contable."),
                title=_("Evidencia Requerida"),
            )

    def _build_default_evidence_row(self, archivo):
        defaults = self._get_retention_defaults()
        return {
            "descripcion_evidencia": self.titulo_del_documento or _("Evidencia Principal"),
            "tipo_documental": self.tipo or EVIDENCIA_TIPO_DEFAULT,
            "origen_documental": EVIDENCIA_ORIGEN_DEFAULT,
            "confidencialidad": defaults.confidencialidad,
            "politica_retencion": defaults.politica_retencion,
            "conservar_hasta": self._resolve_retention_deadline(defaults.politica_retencion),
            "numero_version": 1,
            "es_version_vigente": 1,
            "es_principal": 1,
            "archivo": archivo,
        }

    def _normalizar_evidencias(self, previous=None):
        previous_by_name = {}
        previous_by_archivo = {}
        if previous:
            for previous_row in previous.get("evidencias_documentales") or []:
                if previous_row.name:
                    previous_by_name[previous_row.name] = previous_row
                if previous_row.archivo and previous_row.archivo not in previous_by_archivo:
                    previous_by_archivo[previous_row.archivo] = previous_row

        defaults = self._get_retention_defaults()
        cleaned_rows = []
        for index, row in enumerate(self.evidencias_documentales or [], start=1):
            if not self._row_has_content(row):
                continue

            row.descripcion_evidencia = (row.descripcion_evidencia or "").strip() or self.titulo_del_documento or f"Evidencia {index}"
            row.codigo_documental = (row.codigo_documental or "").strip() or None
            row.tipo_documental = row.tipo_documental or self.tipo or EVIDENCIA_TIPO_DEFAULT
            row.origen_documental = row.origen_documental or EVIDENCIA_ORIGEN_DEFAULT
            row.confidencialidad = row.confidencialidad or defaults.confidencialidad or EVIDENCIA_CONFIDENCIALIDAD_DEFAULT
            row.politica_retencion = row.politica_retencion or defaults.politica_retencion or EVIDENCIA_RETENCION_DEFAULT
            row.numero_version = max(cint(row.numero_version or 1), 1)
            row.es_principal = cint(row.es_principal)
            row.es_version_vigente = cint(row.es_version_vigente)

            if row.politica_retencion == "Permanente":
                row.conservar_hasta = None
            elif not row.conservar_hasta:
                row.conservar_hasta = self._resolve_retention_deadline(row.politica_retencion)

            if not row.archivo and index == 1 and self.archivo_adjunto:
                row.archivo = self.archivo_adjunto
            if not row.archivo:
                frappe.throw(
                    _("Cada evidencia documental debe tener un archivo adjunto."),
                    title=_("Archivo Requerido"),
                )

            previous_row = previous_by_name.get(row.name) or previous_by_archivo.get(row.archivo)
            if previous_row and previous_row.archivo == row.archivo:
                row.conservar_hasta = row.conservar_hasta or previous_row.conservar_hasta

            file_doc = self._resolve_file_document(row.archivo)
            row.archivo_file = file_doc.name if file_doc else (previous_row.archivo_file if previous_row and previous_row.archivo == row.archivo else None)
            row.hash_sha256 = self._compute_evidence_hash(file_doc) or (previous_row.hash_sha256 if previous_row and previous_row.archivo == row.archivo else None)
            cleaned_rows.append(row)

        self.set("evidencias_documentales", cleaned_rows)
        self._asegurar_evidencia_principal()
        self._validar_versionado_evidencias()

    def _get_retention_defaults(self):
        return get_document_retention_defaults(self.cliente)

    def _resolve_retention_deadline(self, policy):
        return calculate_retention_deadline(policy, periodo_name=self.periodo)

    def _row_has_content(self, row):
        return any(
            (
                row.archivo,
                row.descripcion_evidencia,
                row.codigo_documental,
                row.tipo_documental,
                row.hash_sha256,
            )
        )

    def _asegurar_evidencia_principal(self):
        rows = self.evidencias_documentales or []
        if not rows:
            return
        principal_index = next((index for index, row in enumerate(rows) if cint(row.es_principal)), 0)
        for index, row in enumerate(rows):
            row.es_principal = 1 if index == principal_index else 0

    def _validar_versionado_evidencias(self):
        grouped_rows = {}
        seen_versions = set()

        for row in self.evidencias_documentales or []:
            codigo = (row.codigo_documental or "").strip()
            if not codigo:
                row.es_version_vigente = 1 if cint(row.es_principal) else cint(row.es_version_vigente)
                continue

            version_key = (codigo, cint(row.numero_version))
            if version_key in seen_versions:
                frappe.throw(
                    _("No puedes repetir la version <b>{0}</b> para el codigo documental <b>{1}</b> dentro del mismo documento." ).format(
                        row.numero_version, codigo
                    ),
                    title=_("Version Duplicada"),
                )
            seen_versions.add(version_key)
            grouped_rows.setdefault(codigo, []).append(row)

        for rows in grouped_rows.values():
            rows.sort(key=lambda item: cint(item.numero_version), reverse=True)
            vigente = next((item for item in rows if cint(item.es_version_vigente)), rows[0])
            for row in rows:
                row.es_version_vigente = 1 if row is vigente else 0

    def _get_primary_evidence(self):
        rows = self.evidencias_documentales or []
        for row in rows:
            if cint(row.es_principal):
                return row
        return rows[0] if rows else None

    def _legacy_attachment_changed(self, previous):
        return bool(previous and self.archivo_adjunto and self.archivo_adjunto != previous.archivo_adjunto)

    def _legacy_type_changed(self, previous):
        return bool(previous and self.tipo and self.tipo != previous.tipo)

    def _resolve_file_document(self, file_url):
        if not file_url or not frappe.db.exists("DocType", "File"):
            return None
        file_rows = frappe.get_all(
            "File",
            filters={"file_url": file_url},
            fields=["name"],
            order_by="creation desc",
            limit_page_length=1,
        )
        if not file_rows:
            return None
        return frappe.get_doc("File", file_rows[0].name)

    def _compute_evidence_hash(self, file_doc):
        if not file_doc:
            return None
        try:
            content = file_doc.get_content()
        except Exception:
            return None
        if content is None:
            return None
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def _sincronizar_entregable_vinculado(self):
        entregable = self.obtener_datos_entregable(throw_if_missing=False)
        if not entregable:
            return

        update_fields = {}
        if entregable.documento_contable != self.name:
            update_fields["documento_contable"] = self.name

        if entregable.estado_entregable in ("Pendiente", "Solicitado", "Vencido", "Rechazado"):
            update_fields["estado_entregable"] = "Recibido"
            update_fields["fecha_recepcion"] = nowdate()

        if update_fields:
            frappe.db.set_value("Entregable Cliente", entregable.name, update_fields, update_modified=False)
            self._actualizar_requerimiento_relacionado(entregable.requerimiento_cliente)

    def _desvincular_entregable(self, entregable_name):
        entregable = frappe.db.get_value(
            "Entregable Cliente",
            entregable_name,
            ["name", "documento_contable", "estado_entregable", "fecha_solicitud", "requerimiento_cliente"],
            as_dict=True,
        )
        if not entregable or entregable.documento_contable != self.name:
            return

        update_fields = {"documento_contable": None}
        if entregable.estado_entregable == "Validado":
            update_fields.update({"estado_entregable": "Rechazado", "fecha_validacion": None, "validado_por": None})
        elif entregable.estado_entregable == "Recibido":
            update_fields["estado_entregable"] = "Solicitado" if entregable.fecha_solicitud else "Pendiente"
            update_fields["fecha_recepcion"] = None

        frappe.db.set_value("Entregable Cliente", entregable.name, update_fields, update_modified=False)
        self._actualizar_requerimiento_relacionado(entregable.requerimiento_cliente)

    def _actualizar_requerimiento_relacionado(self, requerimiento_name):
        if not requerimiento_name or not frappe.db.exists("Requerimiento Cliente", requerimiento_name):
            return
        from gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente import actualizar_seguimiento_requerimiento

        actualizar_seguimiento_requerimiento(requerimiento_name)
