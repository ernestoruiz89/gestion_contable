import frappe

from gestion_contable.gestion_contable.page.rentabilidad_y_cobranza.rentabilidad_y_cobranza import get_dashboard
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestRentabilidadYCobranza(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-RENTABILIDAD-CLIENTE")
        self.encargo_a = self.create_encargo(self.cliente.name, nombre_del_encargo="Encargo Rentabilidad A")
        self.encargo_b = self.create_encargo(self.cliente.name, nombre_del_encargo="Encargo Rentabilidad B")
        self.auxiliar = self.create_user("rentabilidad_aux@test.local", "Auxiliar", "Rentabilidad", role="Auxiliar Contable del Despacho")

        frappe.db.set_value(
            "Encargo Contable",
            self.encargo_a.name,
            {
                "ingreso_facturado": 1000,
                "cobrado_total": 600,
                "saldo_por_cobrar": 400,
                "wip_monto": 150,
                "costo_interno_total": 300,
                "margen_facturado": 700,
                "cartera_vencida": 100,
                "aging_0_30": 100,
                "facturas_vencidas": 1,
                "hitos_vencidos": 1,
                "proxima_gestion_cobranza": "2026-01-01",
            },
            update_modified=False,
        )
        frappe.db.set_value(
            "Encargo Contable",
            self.encargo_b.name,
            {
                "ingreso_facturado": 500,
                "cobrado_total": 500,
                "saldo_por_cobrar": 0,
                "wip_monto": 50,
                "costo_interno_total": 200,
                "margen_facturado": 300,
                "cartera_vencida": 0,
                "aging_current": 0,
                "facturas_vencidas": 0,
                "hitos_vencidos": 0,
            },
            update_modified=False,
        )

    def test_dashboard_agrega_snapshots_por_cliente(self):
        dashboard = get_dashboard(cliente=self.cliente.name)
        self.assertEqual(dashboard["summary"]["encargos"], 2)
        self.assertEqual(dashboard["summary"]["ingreso_facturado"], 1500)
        self.assertEqual(dashboard["summary"]["cobrado_total"], 1100)
        self.assertEqual(dashboard["summary"]["saldo_por_cobrar"], 400)
        self.assertEqual(dashboard["summary"]["cartera_vencida"], 100)
        self.assertEqual(len(dashboard["rows"]), 2)
        row_a = next(row for row in dashboard["rows"] if row["name"] == self.encargo_a.name)
        self.assertIn("Cartera vencida", row_a["alertas"])

    def test_dashboard_restringido_para_auxiliar(self):
        frappe.set_user(self.auxiliar.name)
        self.assertRaises(frappe.PermissionError, get_dashboard)
