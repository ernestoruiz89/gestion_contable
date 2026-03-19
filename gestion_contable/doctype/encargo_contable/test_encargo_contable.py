import frappe

from gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable import generar_factura_venta
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestEncargoContable(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.responsable = self.create_user("encargo_operativo@test.local", "Responsable", "Encargo")
        self.cliente = self.create_cliente(
            "TEST-ENCARGO-CLIENTE",
            company_default=self.company,
            moneda_preferida=self.default_currency,
            responsable_operativo_default=self.responsable.name,
        )
        self.servicio = self.create_servicio("Servicio Encargo Test", tipo_de_servicio="Consultoria", tarifa_hora=150, costo_interno_hora=60)

    def test_encargo_hereda_defaults_del_cliente(self):
        encargo = self.create_encargo(self.cliente.name)
        self.assertEqual(encargo.company, self.company)
        self.assertEqual(encargo.moneda, self.default_currency)
        self.assertEqual(encargo.responsable, self.responsable.name)
        self.assertTrue(encargo.project)

    def test_facturacion_requiere_aprobacion_socio(self):
        encargo = self.create_encargo(
            self.cliente.name,
            servicio_contable=self.servicio.name,
            modalidad_honorario="Por Hora",
            tarifa_hora=150,
        )
        self.assertRaises(frappe.ValidationError, generar_factura_venta, encargo.name)
