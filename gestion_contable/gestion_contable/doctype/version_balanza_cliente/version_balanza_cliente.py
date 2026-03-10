import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from gestion_contable.gestion_contable.services.balanza.importing import importar_version_balanza, sync_version_summary
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

ESTADOS_VERSION = ("Borrador", "Importada", "Validada", "Publicada", "Reemplazada")
TIPOS_VERSION = ("Original", "Ajustada", "Reclasificada", "Final Publicada")
ROLES_PERIODO = ("Actual", "Comparativo", "Otro")


class VersionBalanzaCliente(Document):
    def autoname(self):
        if self.nombre_version:
            self.name = self.nombre_version
            return
        cliente = self.cliente or "Cliente"
        periodo = self.periodo_contable or "Periodo"
        rol = self.rol_periodo or "Actual"
        version = cint(self.version or 1)
        self.nombre_version = self._build_unique_name(f"Balanza - {cliente} - {periodo} - {rol} - V{version}")
        self.name = self.nombre_version

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar versiones de balanza."))
        self.sincronizar_contexto()
        self.validar_catalogos()
        if self.name and not self.name.startswith("new-") and frappe.db.exists("Version Balanza Cliente", self.name):
            summary = sync_version_summary(self.name)
            for key, value in summary.items():
                setattr(self, key, value)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar versiones de balanza."))
        for name in frappe.get_all("Linea Balanza Cliente", filters={"version_balanza_cliente": self.name}, pluck="name", limit_page_length=20000):
            frappe.delete_doc("Linea Balanza Cliente", name, ignore_permissions=True, force=True)

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Version Balanza Cliente", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Version Balanza Cliente", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_contexto(self):
        self.version = cint(self.version or 1)
        self.tipo_version = self.tipo_version or "Original"
        self.rol_periodo = self.rol_periodo or "Actual"
        self.estado_version = self.estado_version or "Borrador"

        if self.paquete_estados_financieros_cliente and frappe.db.exists("Paquete Estados Financieros Cliente", self.paquete_estados_financieros_cliente):
            package = frappe.db.get_value(
                "Paquete Estados Financieros Cliente",
                self.paquete_estados_financieros_cliente,
                ["cliente", "encargo_contable", "periodo_contable", "fecha_corte"],
                as_dict=True,
            )
            self.cliente = self.cliente or package.cliente
            self.encargo_contable = self.encargo_contable or package.encargo_contable
            self.periodo_contable = self.periodo_contable or package.periodo_contable
            self.fecha_corte = self.fecha_corte or package.fecha_corte

        if self.encargo_contable and frappe.db.exists("Encargo Contable", self.encargo_contable):
            encargo = frappe.db.get_value(
                "Encargo Contable",
                self.encargo_contable,
                ["cliente", "periodo_referencia", "company"],
                as_dict=True,
            )
            self.cliente = self.cliente or encargo.cliente
            self.periodo_contable = self.periodo_contable or encargo.periodo_referencia
            self.company = self.company or encargo.company

    def validar_catalogos(self):
        if self.tipo_version not in TIPOS_VERSION:
            frappe.throw(_("El tipo de version seleccionado no es valido."), title=_("Tipo Invalido"))
        if self.rol_periodo not in ROLES_PERIODO:
            frappe.throw(_("El rol de periodo seleccionado no es valido."), title=_("Periodo Invalido"))
        if self.estado_version not in ESTADOS_VERSION:
            frappe.throw(_("El estado de version seleccionado no es valido."), title=_("Estado Invalido"))
        if not self.cliente:
            frappe.throw(_("Debes indicar el cliente de la version de balanza."), title=_("Cliente Requerido"))
        if not self.periodo_contable:
            frappe.throw(_("Debes indicar el periodo contable de la version de balanza."), title=_("Periodo Requerido"))


@frappe.whitelist()
def publicar_version_balanza(version_name):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden publicar versiones de balanza."))
    if not frappe.db.exists("Version Balanza Cliente", version_name):
        frappe.throw(_("La version de balanza indicada no existe."), title=_("Version Invalida"))

    version_doc = frappe.get_doc("Version Balanza Cliente", version_name)
    summary = sync_version_summary(version_name)
    if not cint(summary.get("total_lineas")):
        frappe.throw(_("No puedes publicar una balanza sin lineas importadas."), title=_("Balanza Vacia"))

    version_doc.estado_version = "Publicada"
    version_doc.tipo_version = "Final Publicada"
    version_doc.es_version_vigente = 1
    version_doc.ultima_publicacion = now_datetime()
    version_doc.publicado_por = frappe.session.user
    version_doc.save(ignore_permissions=True)

    frappe.db.sql(
        """
        UPDATE `tabVersion Balanza Cliente`
        SET es_version_vigente = 0
        WHERE name != %s
          AND cliente = %s
          AND IFNULL(company, '') = %s
          AND IFNULL(periodo_contable, '') = %s
          AND IFNULL(rol_periodo, '') = %s
        """,
        (version_doc.name, version_doc.cliente, version_doc.company or "", version_doc.periodo_contable or "", version_doc.rol_periodo or ""),
    )

    if version_doc.paquete_estados_financieros_cliente and frappe.db.exists("Paquete Estados Financieros Cliente", version_doc.paquete_estados_financieros_cliente):
        fieldname = "version_balanza_comparativa" if version_doc.rol_periodo == "Comparativo" else "version_balanza_actual"
        frappe.db.set_value("Paquete Estados Financieros Cliente", version_doc.paquete_estados_financieros_cliente, fieldname, version_doc.name, update_modified=False)

    return {"name": version_doc.name, "estado_version": version_doc.estado_version, "es_version_vigente": version_doc.es_version_vigente}


@frappe.whitelist()
def importar_version_balanza_desde_archivo(version_name, replace=1):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden importar versiones de balanza."))
    return importar_version_balanza(version_name, replace=cint(replace))
