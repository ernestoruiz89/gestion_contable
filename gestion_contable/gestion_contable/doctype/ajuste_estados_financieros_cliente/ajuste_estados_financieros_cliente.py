import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from gestion_contable.gestion_contable.utils.estados_financieros import sync_package_summary
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_del_ajuste",
    "paquete_estados_financieros_cliente",
    "estado_financiero_cliente",
    "fecha_ajuste",
    "tipo_ajuste",
    "origen_ajuste",
    "estado_ajuste",
    "material",
    "generalizado",
    "impacta_dictamen",
    "impacta_informe_final",
    "aceptado_por_cliente",
    "registrado_en_version_final",
    "descripcion",
    "justificacion",
    "lineas_ajuste",
)
ESTADOS_AJUSTE = ("Propuesto", "Discutido", "Aceptado", "Rechazado", "Registrado", "No Registrado")


class AjusteEstadosFinancierosCliente(Document):
    def autoname(self):
        if self.nombre_del_ajuste:
            self.name = self.nombre_del_ajuste
            return
        base_name = f"Ajuste EEFF - {self.paquete_estados_financieros_cliente or frappe.generate_hash(length=6)}"
        self.nombre_del_ajuste = self._build_unique_name(base_name)
        self.name = self.nombre_del_ajuste

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar ajustes de estados financieros del cliente."))
        self.sincronizar_contexto()
        self.validar_estado_ajuste()
        self.normalizar_lineas()
        self.validar_consistencias()
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            label=_("el ajuste de estados financieros del cliente"),
        )

    def on_update(self):
        sync_package_summary(self.paquete_estados_financieros_cliente)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar ajustes de estados financieros del cliente."))
        sync_package_summary(self.paquete_estados_financieros_cliente)

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Ajuste Estados Financieros Cliente", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Ajuste Estados Financieros Cliente", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_contexto(self):
        self.fecha_ajuste = self.fecha_ajuste or nowdate()
        self.estado_ajuste = self.estado_ajuste or "Propuesto"
        if self.paquete_estados_financieros_cliente:
            if not frappe.db.exists("Paquete Estados Financieros Cliente", self.paquete_estados_financieros_cliente):
                frappe.throw(_("El paquete de estados financieros indicado no existe."), title=_("Paquete Invalido"))
            package = frappe.db.get_value(
                "Paquete Estados Financieros Cliente",
                self.paquete_estados_financieros_cliente,
                ["cliente", "encargo_contable", "expediente_auditoria", "periodo_contable", "fecha_corte"],
                as_dict=True,
            )
            self.cliente = package.cliente
            self.encargo_contable = package.encargo_contable
            self.expediente_auditoria = package.expediente_auditoria
            self.periodo_contable = package.periodo_contable
            self.fecha_corte = package.fecha_corte

        if self.estado_financiero_cliente:
            if not frappe.db.exists("Estado Financiero Cliente", self.estado_financiero_cliente):
                frappe.throw(_("El estado financiero indicado no existe."), title=_("Estado Invalido"))
            estado = frappe.db.get_value(
                "Estado Financiero Cliente",
                self.estado_financiero_cliente,
                ["paquete_estados_financieros_cliente", "cliente", "periodo_contable"],
                as_dict=True,
            )
            if self.paquete_estados_financieros_cliente and estado.paquete_estados_financieros_cliente != self.paquete_estados_financieros_cliente:
                frappe.throw(_("El estado financiero vinculado pertenece a otro paquete."), title=_("Paquete Inconsistente"))
            if not self.paquete_estados_financieros_cliente:
                self.paquete_estados_financieros_cliente = estado.paquete_estados_financieros_cliente
            self.cliente = self.cliente or estado.cliente
            self.periodo_contable = self.periodo_contable or estado.periodo_contable

        if self.generalizado or self.impacta_dictamen:
            self.material = 1

    def validar_estado_ajuste(self):
        if self.estado_ajuste not in ESTADOS_AJUSTE:
            frappe.throw(_("El estado del ajuste seleccionado no es valido."), title=_("Estado Invalido"))
        if self.registrado_en_version_final and self.estado_ajuste != "Registrado":
            frappe.throw(_("Solo puedes marcar 'Registrado en Version Final' cuando el estado del ajuste es Registrado."), title=_("Estado de Ajuste Inconsistente"))
        if self.aceptado_por_cliente and self.estado_ajuste == "Rechazado":
            frappe.throw(_("Un ajuste rechazado no puede marcarse como aceptado por el cliente."), title=_("Aceptacion Inconsistente"))

    def normalizar_lineas(self):
        if not self.lineas_ajuste:
            frappe.throw(_("Debes registrar al menos una linea en el ajuste de estados financieros del cliente."), title=_("Lineas Requeridas"))
        total = 0
        for row in self.lineas_ajuste:
            row.monto_previo = flt(row.monto_previo)
            row.monto_ajuste = flt(row.monto_ajuste)
            row.monto_ajustado = flt(row.monto_previo) + flt(row.monto_ajuste)
            total += flt(row.monto_ajuste)
        self.monto_total = total

    def validar_consistencias(self):
        if not self.paquete_estados_financieros_cliente:
            frappe.throw(_("Debes indicar el paquete de estados financieros del cliente."), title=_("Paquete Requerido"))
        if self.impacta_dictamen and not self.material:
            frappe.throw(_("Un ajuste que impacta el dictamen debe clasificarse como material."), title=_("Materialidad Requerida"))
