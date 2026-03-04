import frappe
from frappe.tests import IntegrationTestCase


class TestDocumentoContable(IntegrationTestCase):

    def setUp(self):
        """Crear datos de prueba."""
        if not frappe.db.exists("Cliente Contable", "Test Doc Cliente Activo"):
            frappe.get_doc({
                "doctype": "Cliente Contable",
                "nombre_del_cliente": "Test Doc Cliente Activo",
                "estado": "Activo"
            }).insert()

        if not frappe.db.exists("Cliente Contable", "Test Doc Cliente Inactivo"):
            frappe.get_doc({
                "doctype": "Cliente Contable",
                "nombre_del_cliente": "Test Doc Cliente Inactivo",
                "estado": "Inactivo"
            }).insert()

        if not frappe.db.exists("Periodo Contable", "Test Doc Periodo Abierto"):
            frappe.get_doc({
                "doctype": "Periodo Contable",
                "nombre_del_periodo": "Test Doc Periodo Abierto",
                "fecha_de_inicio": "2024-01-01",
                "fecha_de_fin": "2024-01-31",
                "estado": "Abierto"
            }).insert()

        if not frappe.db.exists("Periodo Contable", "Test Doc Periodo Cerrado"):
            frappe.get_doc({
                "doctype": "Periodo Contable",
                "nombre_del_periodo": "Test Doc Periodo Cerrado",
                "fecha_de_inicio": "2023-01-01",
                "fecha_de_fin": "2023-01-31",
                "estado": "Cerrado"
            }).insert()

    def tearDown(self):
        """Limpiar datos de prueba."""
        for name in frappe.get_all("Documento Contable", filters={"titulo_del_documento": ["like", "Test Doc%"]}, pluck="name"):
            frappe.delete_doc("Documento Contable", name, force=True)
        for dt, names in [
            ("Periodo Contable", ["Test Doc Periodo Abierto", "Test Doc Periodo Cerrado"]),
            ("Cliente Contable", ["Test Doc Cliente Activo", "Test Doc Cliente Inactivo"]),
        ]:
            for name in names:
                if frappe.db.exists(dt, name):
                    frappe.delete_doc(dt, name, force=True)

    def test_documento_valido(self):
        """Un documento con cliente activo y periodo abierto debe guardarse sin error."""
        doc = frappe.get_doc({
            "doctype": "Documento Contable",
            "titulo_del_documento": "Test Doc Válido",
            "cliente": "Test Doc Cliente Activo",
            "periodo": "Test Doc Periodo Abierto",
            "tipo": "Factura",
            "archivo_adjunto": "/files/test.pdf"
        })
        doc.insert()
        self.assertEqual(doc.titulo_del_documento, "Test Doc Válido")

    def test_documento_cliente_inactivo(self):
        """Un documento con cliente inactivo debe lanzar ValidationError."""
        doc = frappe.get_doc({
            "doctype": "Documento Contable",
            "titulo_del_documento": "Test Doc Cliente Inactivo",
            "cliente": "Test Doc Cliente Inactivo",
            "periodo": "Test Doc Periodo Abierto",
            "tipo": "Factura",
            "archivo_adjunto": "/files/test.pdf"
        })
        self.assertRaises(frappe.ValidationError, doc.insert)

    def test_documento_periodo_cerrado(self):
        """Un documento con periodo cerrado debe lanzar ValidationError."""
        doc = frappe.get_doc({
            "doctype": "Documento Contable",
            "titulo_del_documento": "Test Doc Periodo Cerrado",
            "cliente": "Test Doc Cliente Activo",
            "periodo": "Test Doc Periodo Cerrado",
            "tipo": "Factura",
            "archivo_adjunto": "/files/test.pdf"
        })
        self.assertRaises(frappe.ValidationError, doc.insert)
