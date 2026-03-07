import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company


class TestClienteContable(IntegrationTestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.created_customers = []
        self.created_clientes = []
        self.created_periodos = []
        self.created_users = []
        self.created_requerimientos = []
        self.company = get_default_company() or frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.skipTest("No hay Company configurada para ejecutar pruebas de Cliente Contable")

        self.responsable_operativo = self._create_user("cliente_operativo@test.local", "Operativo", "Cliente")
        self.responsable_cobranza = self._create_user("cliente_cobranza@test.local", "Cobranza", "Cliente")
        self.ejecutivo = self._create_user("cliente_comercial@test.local", "Comercial", "Cliente")
        self.cliente = self._create_cliente_contable()
        self.periodo = self._create_periodo(self.cliente, 2026, "Mayo", "Abierto")

    def tearDown(self):
        frappe.set_user("Administrator")
        for requerimiento_name in reversed(self.created_requerimientos):
            self._safe_delete("Requerimiento Cliente", requerimiento_name)
        for periodo_name in reversed(self.created_periodos):
            self._safe_delete("Periodo Contable", periodo_name)
        for cliente_name in reversed(self.created_clientes):
            self._safe_delete("Cliente Contable", cliente_name)
        for customer_name in reversed(self.created_customers):
            self._safe_delete("Customer", customer_name)
        for user_name in reversed(self.created_users):
            self._safe_delete("User", user_name)
        frappe.set_user(self.previous_user)

    def test_cliente_defaults_resuelven_contactos_y_responsables(self):
        defaults = get_cliente_defaults(self.cliente)
        self.assertEqual(defaults.company_default, self.company)
        self.assertEqual(defaults.responsable_operativo_default, self.responsable_operativo)
        self.assertEqual(defaults.responsable_cobranza_interno, self.responsable_cobranza)
        self.assertEqual(defaults.ejecutivo_comercial_default, self.ejecutivo)
        self.assertEqual(defaults.contacto_cliente_display, "Ana Finanzas <ana@cliente.test>")
        self.assertEqual(defaults.email_cobranza_efectivo, "cobranza@cliente.test")
        self.assertEqual(defaults.contacto_cobranza.nombre, "Luis Cobranza")

    def test_requerimiento_toma_defaults_del_cliente(self):
        requerimiento = frappe.get_doc({
            "doctype": "Requerimiento Cliente",
            "nombre_del_requerimiento": "REQ-CLIENTE-DEFAULTS",
            "cliente": self.cliente,
            "periodo": self.periodo.name,
            "fecha_solicitud": "2026-05-01",
        }).insert(ignore_permissions=True)
        self.created_requerimientos.append(requerimiento.name)

        self.assertEqual(requerimiento.responsable_interno, self.responsable_operativo)
        self.assertEqual(requerimiento.canal_envio, "Portal")
        self.assertEqual(requerimiento.contacto_cliente, "Ana Finanzas <ana@cliente.test>")
        self.assertEqual(str(requerimiento.fecha_vencimiento), "2026-05-04")

    def _create_cliente_contable(self):
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
        territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "TEST-CLIENTE-CONTABLE-AMPLIADO",
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
            "company_default": self.company,
            "regimen_fiscal": "Servicios Profesionales",
            "clasificacion_riesgo": "Medio",
            "ejecutivo_comercial_default": self.ejecutivo,
            "responsable_operativo_default": self.responsable_operativo,
            "responsable_cobranza_interno": self.responsable_cobranza,
            "sla_respuesta_horas_default": 8,
            "sla_entrega_dias_default": 3,
            "canal_envio_preferido": "Portal",
            "contacto_facturacion": "Ana Finanzas",
            "email_facturacion": "facturacion@cliente.test",
            "contacto_cobranza": "Luis Cobranza",
            "email_cobranza": "cobranza@cliente.test",
            "termino_pago_dias": 30,
            "dias_gracia_cobranza": 5,
            "politica_retencion_documental": "Fiscal",
            "clasificacion_confidencialidad_default": "Confidencial",
            "portal_habilitado": 1,
            "permite_carga_documentos": 1,
            "recordatorios_automaticos_portal": 1,
            "contactos_funcionales": [
                {
                    "nombre_contacto": "Ana Finanzas",
                    "contacto_rol": "Contabilidad",
                    "email_contacto": "ana@cliente.test",
                    "telefono_contacto": "555-0101",
                    "es_principal": 1,
                    "recibe_requerimientos": 1,
                    "activo": 1,
                },
                {
                    "nombre_contacto": "Luis Cobranza",
                    "contacto_rol": "Cobranza",
                    "email_contacto": "cobranza@cliente.test",
                    "telefono_contacto": "555-0202",
                    "recibe_cobranza": 1,
                    "activo": 1,
                },
            ],
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

    def _create_user(self, email, first_name, last_name):
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            "roles": [
                {"role": "Contador del Despacho"},
            ],
        }).insert(ignore_permissions=True)
        self.created_users.append(user.name)
        return user.name

    def _safe_delete(self, doctype, name):
        if frappe.db.exists(doctype, name):
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
