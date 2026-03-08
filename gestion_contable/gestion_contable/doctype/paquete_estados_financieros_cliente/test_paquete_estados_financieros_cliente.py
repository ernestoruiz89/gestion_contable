import frappe

from gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente import (
    emitir_paquete_estados_financieros,
)
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestPaqueteEstadosFinancierosCliente(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-EEFF-CLIENTE")
        self.periodo = self.create_periodo(self.cliente.name, mes="Agosto")

    def _crear_paquete(self, **extra_fields):
        payload = {
            "doctype": "Paquete Estados Financieros Cliente",
            "cliente": self.cliente.name,
            "periodo_contable": self.periodo.name,
            "fecha_corte": "2026-08-31",
            "marco_contable": "NIIF para PYMES",
            "tipo_paquete": "Preliminar",
            "version": 1,
            "es_version_vigente": 1,
        }
        payload.update(extra_fields)
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", doc.name)
        return doc

    def _crear_estado(self, paquete_name, tipo_estado, metodo_flujo_efectivo=None):
        payload = {
            "doctype": "Estado Financiero Cliente",
            "paquete_estados_financieros_cliente": paquete_name,
            "tipo_estado": tipo_estado,
            "lineas": [
                {
                    "descripcion": "Rubro principal",
                    "monto_actual": 100,
                    "monto_comparativo": 90,
                }
            ],
        }
        if metodo_flujo_efectivo:
            payload["metodo_flujo_efectivo"] = metodo_flujo_efectivo
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", doc.name)
        return doc

    def test_paquete_emitido_requiere_estados_base_aprobados(self):
        paquete = self._crear_paquete()
        frappe.db.set_value("Paquete Estados Financieros Cliente", paquete.name, "estado_aprobacion", "Aprobado", update_modified=False)

        self.assertRaises(frappe.ValidationError, emitir_paquete_estados_financieros, paquete.name)

        required = [
            "Estado de Situacion Financiera",
            "Estado de Resultados",
            "Estado de Cambios en el Patrimonio",
            "Estado de Flujos de Efectivo",
        ]
        for tipo_estado in required:
            estado = self._crear_estado(paquete.name, tipo_estado, metodo_flujo_efectivo="Indirecto" if tipo_estado == "Estado de Flujos de Efectivo" else None)
            frappe.db.set_value("Estado Financiero Cliente", estado.name, "estado_aprobacion", "Aprobado", update_modified=False)

        emitted = emitir_paquete_estados_financieros(paquete.name)
        self.assertEqual(emitted["estado_preparacion"], "Emitido")

    def test_no_permite_dos_versiones_vigentes_mismo_scope(self):
        self._crear_paquete(version=1)
        another = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-08-31",
                "marco_contable": "NIIF para PYMES",
                "tipo_paquete": "Preliminar",
                "version": 2,
                "es_version_vigente": 1,
            }
        )
        self.assertRaises(frappe.ValidationError, another.insert, ignore_permissions=True)
