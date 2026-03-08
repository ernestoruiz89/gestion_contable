import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

from gestion_contable.gestion_contable.utils.estados_financieros import (
    get_note_line_references,
    get_required_note_numbers,
    normalize_note_number,
    sync_package_summary,
)
from gestion_contable.gestion_contable.utils.governance import validate_governance
from gestion_contable.gestion_contable.utils.security import ensure_manager, ensure_supervisor

CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
CONTENT_FIELDS = (
    "nombre_de_la_nota",
    "paquete_estados_financieros_cliente",
    "numero_nota",
    "titulo",
    "categoria_nota",
    "orden_presentacion",
    "es_requerida",
    "politica_contable",
    "contenido_narrativo",
    "cifras_nota",
    "observaciones_preparacion",
)
CATEGORIAS_NOTA = (
    "Base de Preparacion",
    "Politicas Contables",
    "Efectivo",
    "Cuentas por Cobrar",
    "Inventarios",
    "Propiedad Planta y Equipo",
    "Pasivos",
    "Patrimonio",
    "Ingresos",
    "Gastos",
    "Impuestos",
    "Partes Relacionadas",
    "Contingencias",
    "Hechos Posteriores",
    "Otra",
)


class NotaEstadoFinanciero(Document):
    def autoname(self):
        if self.nombre_de_la_nota:
            self.name = self.nombre_de_la_nota
            return
        numero = normalize_note_number(self.numero_nota) or "SN"
        base_name = f"Nota {numero} - {self.paquete_estados_financieros_cliente or frappe.generate_hash(length=6)}"
        self.nombre_de_la_nota = self._build_unique_name(base_name)
        self.name = self.nombre_de_la_nota

    def validate(self):
        ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden gestionar notas a los estados financieros del cliente."))
        self.sincronizar_desde_paquete()
        self.validar_categoria()
        self.normalizar_cifras()
        self.validar_contenido()
        self.validar_unicidad_numero()
        self.sincronizar_referencias_cruzadas()
        validate_governance(
            self,
            content_fields=CONTENT_FIELDS,
            create_roles=CREATE_ROLES,
            draft_roles=CREATE_ROLES,
            label=_("la nota a los estados financieros del cliente"),
        )

    def on_update(self):
        sync_package_summary(self.paquete_estados_financieros_cliente)

    def on_trash(self):
        ensure_manager(_("Solo Socio, Contador o System Manager pueden eliminar notas a los estados financieros del cliente."))
        sync_package_summary(self.paquete_estados_financieros_cliente)

    def _build_unique_name(self, base_name):
        if not frappe.db.exists("Nota Estado Financiero", base_name):
            return base_name
        index = 2
        while frappe.db.exists("Nota Estado Financiero", f"{base_name} ({index})"):
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
            ["cliente", "periodo_contable"],
            as_dict=True,
        )
        self.cliente = package.cliente
        self.periodo_contable = package.periodo_contable
        self.numero_nota = normalize_note_number(self.numero_nota)
        if not self.numero_nota:
            frappe.throw(_("Debes indicar el numero de nota."), title=_("Numero Requerido"))
        if not cstr(self.titulo or "").strip():
            self.titulo = f"Nota {self.numero_nota}"
        self.orden_presentacion = cint(self.orden_presentacion or 0)
        if not self.orden_presentacion and self.numero_nota.isdigit():
            self.orden_presentacion = cint(self.numero_nota)
        required_numbers, _missing = get_required_note_numbers(self.paquete_estados_financieros_cliente)
        self.es_requerida = int(self.numero_nota in required_numbers)

    def sincronizar_referencias_cruzadas(self):
        references = get_note_line_references(self.paquete_estados_financieros_cliente, self.numero_nota)
        current = [
            {
                "estado_financiero_cliente": row.estado_financiero_cliente,
                "tipo_estado": row.tipo_estado,
                "numero_linea": cint(row.numero_linea or 0),
                "codigo_rubro": row.codigo_rubro,
                "descripcion_linea_estado": row.descripcion_linea_estado,
                "linea_estado_name": row.linea_estado_name,
                "tipo_referencia": row.tipo_referencia,
                "obligatoria": cint(row.obligatoria or 0),
            }
            for row in self.referencias_cruzadas or []
        ]
        changed = current != references
        if changed:
            self.set("referencias_cruzadas", [])
            for reference in references:
                self.append("referencias_cruzadas", reference)
        self.total_referencias = len(references)
        return changed

    def validar_categoria(self):
        if self.categoria_nota and self.categoria_nota not in CATEGORIAS_NOTA:
            frappe.throw(_("La categoria de nota seleccionada no es valida."), title=_("Categoria Invalida"))
        self.categoria_nota = self.categoria_nota or "Otra"

    def normalizar_cifras(self):
        for idx, row in enumerate(self.cifras_nota or [], start=1):
            row.orden = cint(row.orden or idx)
            if not cstr(row.concepto or "").strip():
                frappe.throw(_("Cada cifra de nota debe indicar el concepto."), title=_("Concepto Requerido"))
        self.total_cifras = len(self.cifras_nota or [])

    def validar_contenido(self):
        has_narrative = bool(cstr(self.contenido_narrativo or "").strip())
        has_policy = bool(cstr(self.politica_contable or "").strip())
        has_figures = bool(self.cifras_nota)
        if not any((has_narrative, has_policy, has_figures)):
            frappe.throw(
                _("La nota debe incluir contenido narrativo, politica contable o al menos una cifra tabular."),
                title=_("Contenido Requerido"),
            )

    def validar_unicidad_numero(self):
        existing = frappe.get_all(
            "Nota Estado Financiero",
            filters={
                "name": ["!=", self.name or ""],
                "paquete_estados_financieros_cliente": self.paquete_estados_financieros_cliente,
                "numero_nota": self.numero_nota,
            },
            fields=["name"],
            limit_page_length=1,
        )
        if existing:
            frappe.throw(
                _("Ya existe una nota numero <b>{0}</b> dentro de este paquete.").format(self.numero_nota),
                title=_("Nota Duplicada"),
            )
