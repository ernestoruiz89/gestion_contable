import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

from gestion_contable.gestion_contable.utils.estados_financieros import normalize_note_number, sync_note_cross_references, sync_package_summary, validate_state_math
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_del_estado",
    "paquete_estados_financieros_cliente",
    "tipo_estado",
    "titulo_formal",
    "subtitulo",
    "fecha_corte",
    "fecha_comparativa",
    "moneda_presentacion",
    "metodo_flujo_efectivo",
    "orden_presentacion",
    "lineas",
    "observaciones_preparacion",
)
TIPOS_ESTADO = (
    "Estado de Situacion Financiera",
    "Estado de Resultados",
    "Estado de Cambios en el Patrimonio",
    "Estado de Flujos de Efectivo",
    "Otro Estado Complementario",
)


class EstadoFinancieroCliente(Document):
    def autoname(self):
        if self.nombre_del_estado:
            self.name = self.nombre_del_estado
            return
        base_name = f"{self.tipo_estado or 'Estado Financiero'} - {self.paquete_estados_financieros_cliente or frappe.generate_hash(length=6)}"
        self.nombre_del_estado = self._build_unique_name(base_name)
        self.name = self.nombre_del_estado

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar estados financieros del cliente."))
        self.sincronizar_desde_paquete()
        self.validar_tipo_estado()
        self.normalizar_lineas()
        self.validar_unicidad_tipo()
        validate_state_math(self)
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            label=_("el estado financiero del cliente"),
        )

    def on_update(self):
        sync_package_summary(self.paquete_estados_financieros_cliente)
        sync_note_cross_references(self.paquete_estados_financieros_cliente)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar estados financieros del cliente."))
        sync_package_summary(self.paquete_estados_financieros_cliente)
        sync_note_cross_references(self.paquete_estados_financieros_cliente)

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Estado Financiero Cliente", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Estado Financiero Cliente", f"{base_name} ({index})"):
            index += 1
        return f"{base_name} ({index})"

    def sincronizar_desde_paquete(self):
        if not self.paquete_estados_financieros_cliente:
            frappe.throw(_("Debes seleccionar un paquete de estados financieros del cliente."), title=_("Paquete Requerido"))
        if not frappe.db.exists("Paquete Estados Financieros Cliente", self.paquete_estados_financieros_cliente):
            frappe.throw(_("El paquete de estados financieros indicado no existe."), title=_("Paquete Invalido"))

        package = frappe.db.get_value(
            "Paquete Estados Financieros Cliente",
            self.paquete_estados_financieros_cliente,
            ["cliente", "periodo_contable", "fecha_corte", "moneda_presentacion"],
            as_dict=True,
        )
        self.cliente = package.cliente
        self.periodo_contable = package.periodo_contable
        self.fecha_corte = self.fecha_corte or package.fecha_corte
        self.moneda_presentacion = self.moneda_presentacion or package.moneda_presentacion
        self.titulo_formal = self.titulo_formal or self.tipo_estado
        self.orden_presentacion = cint(self.orden_presentacion or 0)

    def validar_tipo_estado(self):
        if self.tipo_estado not in TIPOS_ESTADO:
            frappe.throw(_("El tipo de estado financiero seleccionado no es valido."), title=_("Tipo Invalido"))
        if self.tipo_estado == "Estado de Flujos de Efectivo" and not cstr(self.metodo_flujo_efectivo or "").strip():
            frappe.throw(_("Debes indicar el metodo del Estado de Flujos de Efectivo."), title=_("Metodo Requerido"))

    def normalizar_lineas(self):
        if not self.lineas:
            frappe.throw(_("Debes registrar al menos una linea en el estado financiero del cliente."), title=_("Lineas Requeridas"))
        seen_codes = set()
        for idx, row in enumerate(self.lineas, start=1):
            row.orden = cint(row.orden or idx)
            row.nivel = cint(row.nivel or 1)
            row.codigo_linea_estado = cstr(row.codigo_linea_estado or row.codigo_rubro or frappe.scrub(row.descripcion or f"linea_{idx}")).strip().upper()
            if row.codigo_linea_estado in seen_codes:
                frappe.throw(_("La linea con codigo <b>{0}</b> esta duplicada en el estado financiero.").format(row.codigo_linea_estado), title=_("Codigo Duplicado"))
            seen_codes.add(row.codigo_linea_estado)
            row.origen_dato = cstr(row.origen_dato or ("Manual" if cint(row.es_manual or 0) else "")).strip() or None
            row.calculo_automatico = cint(row.calculo_automatico or 0)
            row.formula_lineas = cstr(row.formula_lineas or "").strip().upper()
            if row.formula_lineas and not row.calculo_automatico:
                row.calculo_automatico = 1
            row.numero_nota_referencial = normalize_note_number(row.numero_nota_referencial)
            if cint(row.requiere_nota) and not row.numero_nota_referencial:
                line_label = cstr(row.descripcion or row.codigo_rubro or _("Fila {0}").format(idx)).strip()
                frappe.throw(
                    _("La linea <b>{0}</b> del estado <b>{1}</b> requiere un numero de nota referencial.").format(line_label, self.tipo_estado),
                    title=_("Nota Referencial Requerida"),
                )
        self.total_lineas = len(self.lineas)

    def validar_unicidad_tipo(self):
        if self.tipo_estado == "Otro Estado Complementario":
            return
        existing = frappe.get_all(
            "Estado Financiero Cliente",
            filters={
                "name": ["!=", self.name or ""],
                "paquete_estados_financieros_cliente": self.paquete_estados_financieros_cliente,
                "tipo_estado": self.tipo_estado,
            },
            fields=["name"],
            limit_page_length=1,
        )
        if existing:
            frappe.throw(_("Ya existe un estado del tipo <b>{0}</b> dentro de este paquete.").format(self.tipo_estado), title=_("Estado Duplicado"))
