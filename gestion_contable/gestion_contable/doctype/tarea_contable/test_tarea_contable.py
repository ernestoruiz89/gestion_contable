import frappe
from frappe.tests import IntegrationTestCase


class TestTareaContable(IntegrationTestCase):

    def setUp(self):
        """Crear datos de prueba."""
        # Cliente activo
        if not frappe.db.exists("Cliente Contable", "Test Cliente Activo"):
            frappe.get_doc({
                "doctype": "Cliente Contable",
                "nombre_del_cliente": "Test Cliente Activo",
                "estado": "Activo"
            }).insert()

        # Cliente inactivo
        if not frappe.db.exists("Cliente Contable", "Test Cliente Inactivo"):
            frappe.get_doc({
                "doctype": "Cliente Contable",
                "nombre_del_cliente": "Test Cliente Inactivo",
                "estado": "Inactivo"
            }).insert()

        # Periodo abierto
        if not frappe.db.exists("Periodo Contable", "Test Periodo Abierto"):
            frappe.get_doc({
                "doctype": "Periodo Contable",
                "nombre_del_periodo": "Test Periodo Abierto",
                "fecha_de_inicio": "2024-01-01",
                "fecha_de_fin": "2024-01-31",
                "estado": "Abierto"
            }).insert()

        # Periodo cerrado
        if not frappe.db.exists("Periodo Contable", "Test Periodo Cerrado"):
            frappe.get_doc({
                "doctype": "Periodo Contable",
                "nombre_del_periodo": "Test Periodo Cerrado",
                "fecha_de_inicio": "2023-01-01",
                "fecha_de_fin": "2023-01-31",
                "estado": "Cerrado"
            }).insert()

    def tearDown(self):
        """Limpiar datos de prueba."""
        for name in frappe.get_all("Tarea Contable", filters={"titulo": ["like", "Test Tarea%"]}, pluck="name"):
            frappe.delete_doc("Tarea Contable", name, force=True)
        for dt, names in [
            ("Periodo Contable", ["Test Periodo Abierto", "Test Periodo Cerrado"]),
            ("Cliente Contable", ["Test Cliente Activo", "Test Cliente Inactivo"]),
        ]:
            for name in names:
                if frappe.db.exists(dt, name):
                    frappe.delete_doc(dt, name, force=True)

    def test_tarea_valida(self):
        """Una tarea con cliente activo y periodo abierto debe guardarse sin error."""
        tarea = frappe.get_doc({
            "doctype": "Tarea Contable",
            "titulo": "Test Tarea Válida",
            "cliente": "Test Cliente Activo",
            "periodo": "Test Periodo Abierto",
            "fecha_de_vencimiento": "2024-01-15"
        })
        tarea.insert()
        self.assertEqual(tarea.titulo, "Test Tarea Válida")

    def test_tarea_cliente_inactivo(self):
        """Una tarea con cliente inactivo debe lanzar ValidationError."""
        tarea = frappe.get_doc({
            "doctype": "Tarea Contable",
            "titulo": "Test Tarea Cliente Inactivo",
            "cliente": "Test Cliente Inactivo",
            "periodo": "Test Periodo Abierto",
            "fecha_de_vencimiento": "2024-01-15"
        })
        self.assertRaises(frappe.ValidationError, tarea.insert)

    def test_tarea_periodo_cerrado(self):
        """Una tarea con periodo cerrado debe lanzar ValidationError."""
        tarea = frappe.get_doc({
            "doctype": "Tarea Contable",
            "titulo": "Test Tarea Periodo Cerrado",
            "cliente": "Test Cliente Activo",
            "periodo": "Test Periodo Cerrado",
            "fecha_de_vencimiento": "2023-01-15"
        })
        self.assertRaises(frappe.ValidationError, tarea.insert)
