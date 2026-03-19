import frappe

from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestEstadoFinancieroCliente(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-MATH-EEFF")
        self.periodo = self.create_periodo(self.cliente.name, mes="Noviembre")
        self.paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-11-30",
                "version": 1,
                "es_version_vigente": 1,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", self.paquete.name)

    def test_estado_situacion_financiera_debe_cuadrar(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Situacion Financiera",
                "lineas": [
                    {"descripcion": "Total Activo", "naturaleza": "Activo", "es_total": 1, "monto_actual": 100},
                    {"descripcion": "Total Pasivo", "naturaleza": "Pasivo", "es_total": 1, "monto_actual": 35},
                    {"descripcion": "Total Patrimonio", "naturaleza": "Patrimonio", "es_total": 1, "monto_actual": 55},
                ],
            }
        )
        self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

    def test_estado_situacion_financiera_valido_se_guarda(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Situacion Financiera",
                "lineas": [
                    {"descripcion": "Total Activo", "naturaleza": "Activo", "es_total": 1, "monto_actual": 100, "monto_comparativo": 90},
                    {"descripcion": "Total Pasivo", "naturaleza": "Pasivo", "es_total": 1, "monto_actual": 60, "monto_comparativo": 50},
                    {"descripcion": "Total Patrimonio", "naturaleza": "Patrimonio", "es_total": 1, "monto_actual": 40, "monto_comparativo": 40},
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", doc.name)
        self.assertEqual(doc.tipo_estado, "Estado de Situacion Financiera")

    def test_total_o_subtotal_debe_tener_monto(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Resultados",
                "lineas": [
                    {"descripcion": "Ingresos", "naturaleza": "Ingreso", "es_total": 1},
                ],
            }
        )
        self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)


    def test_estado_resultados_debe_cuadrar_con_resultado_final(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Resultados",
                "lineas": [
                    {"descripcion": "Total Ingresos", "naturaleza": "Ingreso", "es_total": 1, "monto_actual": 500},
                    {"descripcion": "Total Gastos", "naturaleza": "Gasto", "es_total": 1, "monto_actual": 300},
                    {"descripcion": "Utilidad del Periodo", "naturaleza": "Otro", "es_resultado_final": 1, "monto_actual": 150},
                ],
            }
        )
        self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

    def test_estado_resultados_valido_se_guarda(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Resultados",
                "lineas": [
                    {"descripcion": "Total Ingresos", "naturaleza": "Ingreso", "es_total": 1, "monto_actual": 500, "monto_comparativo": 450},
                    {"descripcion": "Total Gastos", "naturaleza": "Gasto", "es_total": 1, "monto_actual": 300, "monto_comparativo": 280},
                    {"descripcion": "Utilidad del Periodo", "naturaleza": "Otro", "es_resultado_final": 1, "monto_actual": 200, "monto_comparativo": 170},
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", doc.name)
        self.assertEqual(doc.tipo_estado, "Estado de Resultados")

    def test_flujo_efectivo_debe_conciliar_variacion_neta(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Flujos de Efectivo",
                "metodo_flujo_efectivo": "Indirecto",
                "lineas": [
                    {"descripcion": "Efectivo Inicial", "naturaleza": "Activo", "es_efectivo_inicial": 1, "monto_actual": 100},
                    {"descripcion": "Variacion Neta", "naturaleza": "Otro", "es_variacion_neta_efectivo": 1, "monto_actual": 50},
                    {"descripcion": "Efectivo Final", "naturaleza": "Activo", "es_efectivo_final": 1, "monto_actual": 120},
                ],
            }
        )
        self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

    def test_flujo_efectivo_valido_se_guarda(self):
        doc = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Estado de Flujos de Efectivo",
                "metodo_flujo_efectivo": "Indirecto",
                "lineas": [
                    {"descripcion": "Efectivo Inicial", "naturaleza": "Activo", "es_efectivo_inicial": 1, "monto_actual": 100, "monto_comparativo": 80},
                    {"descripcion": "Variacion Neta", "naturaleza": "Otro", "es_variacion_neta_efectivo": 1, "monto_actual": 50, "monto_comparativo": 20},
                    {"descripcion": "Efectivo Final", "naturaleza": "Activo", "es_efectivo_final": 1, "monto_actual": 150, "monto_comparativo": 100},
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", doc.name)
        self.assertEqual(doc.tipo_estado, "Estado de Flujos de Efectivo")
