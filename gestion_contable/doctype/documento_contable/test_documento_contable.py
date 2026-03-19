import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company


class TestDocumentoContable(IntegrationTestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.created_documentos = []
        self.created_periodos = []
        self.created_clientes = []
        self.created_customers = []
        self.created_users = []
        self.company = get_default_company() or frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.skipTest("No hay Company configurada para ejecutar pruebas de Documento Contable")

        self.cliente_activo = self._create_cliente("TEST-DOC-CLIENTE-ACTIVO")
        self.cliente_otro = self._create_cliente("TEST-DOC-CLIENTE-OTRO")
        self.periodo_abierto = self._create_periodo(self.cliente_activo, 2026, "Mayo", "Abierto")
        self.periodo_cerrado = self._create_periodo(self.cliente_activo, 2026, "Junio", "Cerrado")
        self.periodo_otro_cliente = self._create_periodo(self.cliente_otro, 2026, "Mayo", "Abierto")
        self.auxiliar_a = self._create_user("aux_doc_a@test.local", "Auxiliar", "Doc A")
        self.auxiliar_b = self._create_user("aux_doc_b@test.local", "Auxiliar", "Doc B")

    def tearDown(self):
        frappe.set_user("Administrator")
        for documento_name in reversed(self.created_documentos):
            self._safe_delete("Documento Contable", documento_name)
        for user_name in reversed(self.created_users):
            self._safe_delete("User", user_name)
        for periodo_name in reversed(self.created_periodos):
            self._safe_delete("Periodo Contable", periodo_name)
        for cliente_name in reversed(self.created_clientes):
            self._safe_delete("Cliente Contable", cliente_name)
        for customer_name in reversed(self.created_customers):
            self._safe_delete("Customer", customer_name)
        frappe.set_user(self.previous_user)

    def test_documento_valido_con_periodo_del_mismo_cliente(self):
        documento = self._create_documento(self.cliente_activo, self.periodo_abierto.name, "Test Documento Valido")
        self.assertEqual(documento.cliente, self.cliente_activo)
        self.assertEqual(documento.periodo, self.periodo_abierto.name)
        self.assertEqual(documento.archivo_adjunto, "/files/test-valido.pdf")
        self.assertEqual(len(documento.evidencias_documentales), 1)

    def test_documento_rechaza_periodo_de_otro_cliente(self):
        documento = frappe.get_doc({
            "doctype": "Documento Contable",
            "titulo_del_documento": "Test Documento Periodo Otro Cliente",
            "cliente": self.cliente_activo,
            "periodo": self.periodo_otro_cliente.name,
            "tipo": "Factura",
            "archivo_adjunto": "/files/test-periodo-otro-cliente.pdf",
        })
        self.assertRaises(frappe.ValidationError, documento.insert)

    def test_documento_rechaza_periodo_cerrado(self):
        documento = frappe.get_doc({
            "doctype": "Documento Contable",
            "titulo_del_documento": "Test Documento Periodo Cerrado",
            "cliente": self.cliente_activo,
            "periodo": self.periodo_cerrado.name,
            "tipo": "Factura",
            "archivo_adjunto": "/files/test-periodo-cerrado.pdf",
        })
        self.assertRaises(frappe.ValidationError, documento.insert)

    def test_auxiliar_solo_puede_editar_sus_documentos(self):
        frappe.set_user(self.auxiliar_a)
        documento = self._create_documento(
            self.cliente_activo,
            self.periodo_abierto.name,
            "Test Documento Auxiliar Propio",
            archivo="/files/test-aux-propio.pdf",
        )
        self.assertEqual(documento.preparado_por, self.auxiliar_a)

        frappe.set_user(self.auxiliar_b)
        documento = frappe.get_doc("Documento Contable", documento.name)
        documento.archivo_adjunto = "/files/test-aux-ajeno.pdf"
        self.assertRaises(frappe.PermissionError, documento.save, ignore_permissions=True)

    def test_auxiliar_no_puede_cambiar_campos_criticos_de_su_documento(self):
        frappe.set_user(self.auxiliar_a)
        documento = self._create_documento(
            self.cliente_activo,
            self.periodo_abierto.name,
            "Test Documento Auxiliar Campo Critico",
            archivo="/files/test-aux-critico.pdf",
        )

        documento = frappe.get_doc("Documento Contable", documento.name)
        documento.cliente = self.cliente_otro
        self.assertRaises(frappe.PermissionError, documento.save, ignore_permissions=True)

    def test_documento_admite_evidencias_documentales_multiples(self):
        documento = self._create_documento(
            self.cliente_activo,
            self.periodo_abierto.name,
            "Test Documento Multiples Evidencias",
            archivo=None,
            tipo=None,
            evidencias=[
                {
                    "descripcion_evidencia": "Factura Principal",
                    "codigo_documental": "FAC-001",
                    "tipo_documental": "Factura",
                    "origen_documental": "Cliente",
                    "es_principal": 1,
                    "numero_version": 1,
                    "es_version_vigente": 1,
                    "archivo": "/files/test-evidencia-1.pdf",
                },
                {
                    "descripcion_evidencia": "Estado de Cuenta",
                    "codigo_documental": "BANK-001",
                    "tipo_documental": "Estado de Cuenta",
                    "origen_documental": "Cliente",
                    "numero_version": 1,
                    "archivo": "/files/test-evidencia-2.pdf",
                },
            ],
        )
        self.assertEqual(len(documento.evidencias_documentales), 2)
        self.assertEqual(documento.archivo_adjunto, "/files/test-evidencia-1.pdf")
        self.assertEqual(documento.tipo, "Factura")
        self.assertEqual(documento.evidencias_documentales[0].confidencialidad, "Confidencial")
        self.assertEqual(documento.evidencias_documentales[0].es_principal, 1)
        self.assertEqual(documento.evidencias_documentales[1].es_principal, 0)

    def test_documento_rechaza_version_duplicada_para_mismo_codigo(self):
        documento = frappe.get_doc({
            "doctype": "Documento Contable",
            "titulo_del_documento": "Test Documento Version Duplicada",
            "cliente": self.cliente_activo,
            "periodo": self.periodo_abierto.name,
            "evidencias_documentales": [
                {
                    "descripcion_evidencia": "Cedula v1",
                    "codigo_documental": "AUD-001",
                    "tipo_documental": "Cedula de Auditoria",
                    "numero_version": 1,
                    "es_principal": 1,
                    "archivo": "/files/test-version-1.pdf",
                },
                {
                    "descripcion_evidencia": "Cedula v1 duplicada",
                    "codigo_documental": "AUD-001",
                    "tipo_documental": "Cedula de Auditoria",
                    "numero_version": 1,
                    "archivo": "/files/test-version-1b.pdf",
                },
            ],
        })
        self.assertRaises(frappe.ValidationError, documento.insert)

    def _create_documento(self, cliente, periodo, titulo, archivo="/files/test-valido.pdf", tipo="Factura", evidencias=None):
        payload = {
            "doctype": "Documento Contable",
            "titulo_del_documento": titulo,
            "cliente": cliente,
            "periodo": periodo,
        }
        if tipo:
            payload["tipo"] = tipo
        if archivo:
            payload["archivo_adjunto"] = archivo
        if evidencias is not None:
            payload["evidencias_documentales"] = evidencias

        documento = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.created_documentos.append(documento.name)
        return documento

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
                {"role": "Auxiliar Contable del Despacho"},
            ],
        }).insert(ignore_permissions=True)
        self.created_users.append(user.name)
        return user.name

    def _safe_delete(self, doctype, name):
        if frappe.db.exists(doctype, name):
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
