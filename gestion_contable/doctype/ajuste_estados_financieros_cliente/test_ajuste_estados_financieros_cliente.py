import frappe

from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestAjusteEstadosFinancierosCliente(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-AJUSTE-EEFF")
        self.periodo = self.create_periodo(self.cliente.name, mes="Septiembre")
        self.paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-09-30",
                "version": 1,
                "es_version_vigente": 1,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", self.paquete.name)

        self.estado = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Resultados",
                "lineas": [
                    {
                        "descripcion": "Utilidad antes de ajuste",
                        "monto_actual": 500,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", self.estado.name)

    def test_ajuste_calcula_total_y_actualiza_resumen_paquete(self):
        ajuste = frappe.get_doc(
            {
                "doctype": "Ajuste Estados Financieros Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "estado_financiero_cliente": self.estado.name,
                "estado_ajuste": "No Registrado",
                "material": 1,
                "descripcion": "Ajuste de reconocimiento de gasto",
                "lineas_ajuste": [
                    {
                        "estado_financiero_cliente": self.estado.name,
                        "descripcion_linea": "Gasto no provisionado",
                        "monto_previo": 500,
                        "monto_ajuste": -75,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Ajuste Estados Financieros Cliente", ajuste.name)

        self.assertEqual(float(ajuste.monto_total), -75.0)
        package = frappe.get_doc("Paquete Estados Financieros Cliente", self.paquete.name)
        self.assertEqual(int(package.total_ajustes), 1)
        self.assertEqual(int(package.ajustes_no_registrados), 1)
        self.assertEqual(int(package.ajustes_materiales_no_registrados), 1)

    def test_registrado_en_version_final_exige_estado_registrado(self):
        ajuste = frappe.get_doc(
            {
                "doctype": "Ajuste Estados Financieros Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "estado_financiero_cliente": self.estado.name,
                "estado_ajuste": "Aceptado",
                "registrado_en_version_final": 1,
                "descripcion": "Ajuste inconsistente",
                "lineas_ajuste": [
                    {
                        "descripcion_linea": "Linea de prueba",
                        "monto_previo": 0,
                        "monto_ajuste": 10,
                    }
                ],
            }
        )
        self.assertRaises(frappe.ValidationError, ajuste.insert, ignore_permissions=True)
