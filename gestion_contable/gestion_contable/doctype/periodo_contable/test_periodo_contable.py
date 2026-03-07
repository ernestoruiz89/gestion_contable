import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company


class TestPeriodoContable(IntegrationTestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.created_periodos = []
        self.created_clientes = []
        self.created_customers = []
        self.company = get_default_company() or frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.skipTest("No hay Company configurada para ejecutar pruebas de Periodo Contable")

        self.cliente_a = self._create_cliente("TEST-PC-CLIENTE-A")
        self.cliente_b = self._create_cliente("TEST-PC-CLIENTE-B")

    def tearDown(self):
        for periodo_name in reversed(self.created_periodos):
            self._safe_delete("Periodo Contable", periodo_name)
        for cliente_name in reversed(self.created_clientes):
            self._safe_delete("Cliente Contable", cliente_name)
        for customer_name in reversed(self.created_customers):
            self._safe_delete("Customer", customer_name)
        frappe.set_user(self.previous_user)

    def test_periodo_genera_nombre_por_company_cliente_y_mes(self):
        periodo = self._create_periodo(self.cliente_a, 2026, "Enero", "Abierto")
        self.assertEqual(periodo.nombre_del_periodo, f"{self.company} - {self.cliente_a} - Enero 2026")
        self.assertEqual(periodo.fecha_de_inicio.isoformat(), "2026-01-01")
        self.assertEqual(periodo.fecha_de_fin.isoformat(), "2026-01-31")

    def test_periodo_permita_mismo_mes_para_clientes_distintos(self):
        periodo_a = self._create_periodo(self.cliente_a, 2026, "Febrero", "Abierto")
        periodo_b = self._create_periodo(self.cliente_b, 2026, "Febrero", "Cerrado")

        self.assertNotEqual(periodo_a.name, periodo_b.name)
        self.assertIn(self.cliente_a, periodo_a.name)
        self.assertIn(self.cliente_b, periodo_b.name)

    def _create_cliente(self, customer_name):
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
        territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_group": customer_group,
            "customer_type": "Company",
            "territory": territory,
        }).insert(ignore_permissions=True)
        self.created_customers.append(customer.name)

        cliente = frappe.get_doc({
            "doctype": "Cliente Contable",
            "customer": customer.name,
            "estado": "Activo",
            "frecuencia_de_cierre": "Mensual",
        }).insert(ignore_permissions=True)
        self.created_clientes.append(cliente.name)
        return cliente.name

    def _create_periodo(self, cliente, anio, mes, estado):
        periodo = frappe.get_doc({
            "doctype": "Periodo Contable",
            "cliente": cliente,
            "company": self.company,
            "anio": anio,
            "mes": mes,
            "estado": estado,
        }).insert(ignore_permissions=True)
        self.created_periodos.append(periodo.name)
        return periodo

    def _safe_delete(self, doctype, name):
        if frappe.db.exists(doctype, name):
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
