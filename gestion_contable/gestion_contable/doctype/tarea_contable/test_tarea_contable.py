import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company


class TestTareaContable(IntegrationTestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.created_tareas = []
        self.created_periodos = []
        self.created_clientes = []
        self.created_customers = []
        self.company = get_default_company() or frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.skipTest("No hay Company configurada para ejecutar pruebas de Tarea Contable")

        self.cliente_activo = self._create_cliente("TEST-TAREA-CLIENTE-ACTIVO")
        self.cliente_otro = self._create_cliente("TEST-TAREA-CLIENTE-OTRO")
        self.periodo_abierto = self._create_periodo(self.cliente_activo, 2026, "Marzo", "Abierto")
        self.periodo_cerrado = self._create_periodo(self.cliente_activo, 2026, "Abril", "Cerrado")
        self.periodo_otro_cliente = self._create_periodo(self.cliente_otro, 2026, "Marzo", "Abierto")

    def tearDown(self):
        for tarea_name in reversed(self.created_tareas):
            self._safe_delete("Tarea Contable", tarea_name)
        for periodo_name in reversed(self.created_periodos):
            self._safe_delete("Periodo Contable", periodo_name)
        for cliente_name in reversed(self.created_clientes):
            self._safe_delete("Cliente Contable", cliente_name)
        for customer_name in reversed(self.created_customers):
            self._safe_delete("Customer", customer_name)
        frappe.set_user(self.previous_user)

    def test_tarea_valida_con_periodo_del_mismo_cliente(self):
        tarea = self._create_tarea(self.cliente_activo, self.periodo_abierto.name, "Test Tarea Valida")
        self.assertEqual(tarea.cliente, self.cliente_activo)
        self.assertEqual(tarea.periodo, self.periodo_abierto.name)

    def test_tarea_rechaza_periodo_de_otro_cliente(self):
        tarea = frappe.get_doc({
            "doctype": "Tarea Contable",
            "titulo": "Test Tarea Periodo Otro Cliente",
            "cliente": self.cliente_activo,
            "periodo": self.periodo_otro_cliente.name,
            "tipo_de_tarea": "Impuestos",
            "estado": "Pendiente",
            "fecha_de_vencimiento": "2026-03-15",
        })
        self.assertRaises(frappe.ValidationError, tarea.insert)

    def test_tarea_rechaza_periodo_cerrado(self):
        tarea = frappe.get_doc({
            "doctype": "Tarea Contable",
            "titulo": "Test Tarea Periodo Cerrado",
            "cliente": self.cliente_activo,
            "periodo": self.periodo_cerrado.name,
            "tipo_de_tarea": "Impuestos",
            "estado": "Pendiente",
            "fecha_de_vencimiento": "2026-04-15",
        })
        self.assertRaises(frappe.ValidationError, tarea.insert)

    def _create_tarea(self, cliente, periodo, titulo):
        tarea = frappe.get_doc({
            "doctype": "Tarea Contable",
            "titulo": titulo,
            "cliente": cliente,
            "periodo": periodo,
            "tipo_de_tarea": "Impuestos",
            "estado": "Pendiente",
            "fecha_de_vencimiento": "2026-03-15",
        }).insert(ignore_permissions=True)
        self.created_tareas.append(tarea.name)
        return tarea

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
