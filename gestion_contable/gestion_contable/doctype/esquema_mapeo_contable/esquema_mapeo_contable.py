import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor


class EsquemaMapeoContable(Document):
    def autoname(self):
        if self.nombre_esquema:
            self.name = self.nombre_esquema
            return
        cliente = self.cliente or "Cliente"
        marco = self.marco_contable or "Marco"
        tipo = self.tipo_paquete or "Preliminar"
        version = cint(self.version or 1)
        self.nombre_esquema = self._build_unique_name(f"Mapeo - {cliente} - {marco} - {tipo} - V{version}")
        self.name = self.nombre_esquema

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar esquemas de mapeo contable."))
        self.version = cint(self.version or 1)
        self.activo = cint(self.activo or 1)
        self.es_vigente = cint(self.es_vigente or 0)
        self.marco_contable = self.marco_contable or "NIIF para PYMES"
        self.tipo_paquete = self.tipo_paquete or "Preliminar"
        if not self.cliente:
            frappe.throw(_("Debes indicar el cliente del esquema de mapeo."), title=_("Cliente Requerido"))
        self._normalizar_reglas()
        self._validar_vigencia_unica()

    def on_update(self):
        if not self.es_vigente:
            return
        frappe.db.sql(
            """
            UPDATE `tabEsquema Mapeo Contable`
            SET es_vigente = 0
            WHERE name != %s
              AND cliente = %s
              AND IFNULL(company, '') = %s
              AND IFNULL(marco_contable, '') = %s
              AND IFNULL(tipo_paquete, '') = %s
            """,
            (self.name, self.cliente, self.company or "", self.marco_contable or "", self.tipo_paquete or ""),
        )

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar esquemas de mapeo contable."))

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Esquema Mapeo Contable", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Esquema Mapeo Contable", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def _normalizar_reglas(self):
        for idx, row in enumerate(self.reglas or [], start=1):
            row.orden_ejecucion = cint(row.orden_ejecucion or idx)
            row.activo = cint(row.activo or 0)
            row.destino_tipo = cstr(row.destino_tipo or "").strip()
            row.origen_version = cstr(row.origen_version or "Actual").strip()
            row.selector_tipo = cstr(row.selector_tipo or "Lista").strip()
            row.operacion_agregacion = cstr(row.operacion_agregacion or "Saldo Neto").strip()
            row.signo_presentacion = cstr(row.signo_presentacion or "Normal").strip()
            row.destino_codigo_sumaria = cstr(row.destino_codigo_sumaria or "").strip().upper()
            row.destino_codigo_linea_sumaria = cstr(row.destino_codigo_linea_sumaria or "").strip().upper()
            row.destino_tipo_estado = cstr(row.destino_tipo_estado or "").strip()
            row.destino_codigo_linea_estado = cstr(row.destino_codigo_linea_estado or "").strip().upper()
            row.destino_numero_nota = cstr(row.destino_numero_nota or "").strip().upper()
            row.destino_codigo_cifra = cstr(row.destino_codigo_cifra or "").strip().upper()
            row.destino_seccion_id = cstr(row.destino_seccion_id or "").strip().upper()
            row.destino_codigo_fila = cstr(row.destino_codigo_fila or "").strip().upper()
            row.destino_codigo_columna = cstr(row.destino_codigo_columna or "").strip().upper()

    def _validar_vigencia_unica(self):
        if not self.es_vigente:
            return
        existing = frappe.get_all(
            "Esquema Mapeo Contable",
            filters={
                "name": ["!=", self.name or ""],
                "cliente": self.cliente,
                "company": self.company,
                "marco_contable": self.marco_contable,
                "tipo_paquete": self.tipo_paquete,
                "es_vigente": 1,
            },
            fields=["name"],
            limit_page_length=1,
        )
        if existing:
            frappe.throw(_("Ya existe un esquema vigente para este cliente, compania, marco y tipo de paquete."), title=_("Esquema Duplicado"))
