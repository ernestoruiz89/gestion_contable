import frappe
from frappe.tests import IntegrationTestCase


class TestPeriodoContable(IntegrationTestCase):

    def test_periodo_valido(self):
        """Un periodo con fecha_de_fin posterior a fecha_de_inicio debe guardarse sin error."""
        periodo = frappe.get_doc({
            "doctype": "Periodo Contable",
            "nombre_del_periodo": "Test Periodo Válido",
            "fecha_de_inicio": "2024-01-01",
            "fecha_de_fin": "2024-01-31",
            "estado": "Abierto"
        })
        periodo.insert()
        self.assertEqual(periodo.nombre_del_periodo, "Test Periodo Válido")
        periodo.delete()

    def test_fecha_fin_anterior_a_inicio(self):
        """Un periodo con fecha_de_fin anterior a fecha_de_inicio debe lanzar ValidationError."""
        periodo = frappe.get_doc({
            "doctype": "Periodo Contable",
            "nombre_del_periodo": "Test Periodo Inválido",
            "fecha_de_inicio": "2024-01-31",
            "fecha_de_fin": "2024-01-01",
            "estado": "Abierto"
        })
        self.assertRaises(frappe.ValidationError, periodo.insert)

    def test_fecha_fin_igual_a_inicio(self):
        """Un periodo con fecha_de_fin igual a fecha_de_inicio debe lanzar ValidationError."""
        periodo = frappe.get_doc({
            "doctype": "Periodo Contable",
            "nombre_del_periodo": "Test Periodo Igual",
            "fecha_de_inicio": "2024-01-15",
            "fecha_de_fin": "2024-01-15",
            "estado": "Abierto"
        })
        self.assertRaises(frappe.ValidationError, periodo.insert)
