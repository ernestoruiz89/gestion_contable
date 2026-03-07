import frappe

from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestContratoComercial(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.ejecutivo = self.create_user("contrato_comercial@test.local", "Ejecutivo", "Comercial")
        self.responsable = self.create_user("contrato_operativo@test.local", "Responsable", "Operativo")
        self.cliente = self.create_cliente(
            "TEST-CONTRATO-CLIENTE",
            company_default=self.company,
            moneda_preferida=self.default_currency,
            ejecutivo_comercial_default=self.ejecutivo.name,
            responsable_operativo_default=self.responsable.name,
            sla_respuesta_horas_default=6,
            sla_entrega_dias_default=2,
        )
        self.servicio = self.create_servicio("Servicio Contrato Test", honorario_fijo=500)

    def test_contrato_hereda_defaults_del_cliente(self):
        contrato = self.create_contrato(self.cliente.name, self.servicio.name)
        self.assertEqual(contrato.customer, self.cliente.customer)
        self.assertEqual(contrato.company, self.company)
        self.assertEqual(contrato.moneda, self.default_currency)
        self.assertEqual(contrato.ejecutivo_comercial, self.ejecutivo.name)
        self.assertEqual(contrato.responsable_operativo, self.responsable.name)
        self.assertEqual(contrato.sla_respuesta_horas, 6)
        self.assertEqual(contrato.sla_entrega_dias, 2)

    def test_contrato_no_permita_aprobar_sin_revision_socio(self):
        contrato = self.create_contrato(self.cliente.name, self.servicio.name)
        contrato = frappe.get_doc("Contrato Comercial", contrato.name)
        contrato.estado_aprobacion = "Aprobado"
        self.assertRaises(frappe.PermissionError, contrato.save, ignore_permissions=True)


    def test_contrato_sugiere_formato_por_tipo_de_servicio(self):
        servicio_contabilidad = self.create_servicio("Servicio Contrato Contabilidad", tipo_de_servicio="Contabilidad", honorario_fijo=750)
        contrato = self.create_contrato(self.cliente.name, servicio_contabilidad.name)
        self.assertEqual(contrato.formato_impresion_sugerido, "Contrato Comercial - Contabilidad")

    def test_contrato_no_sugiere_formato_si_mezcla_tipos(self):
        servicio_contabilidad = self.create_servicio("Servicio Contrato Mixto A", tipo_de_servicio="Contabilidad", honorario_fijo=750)
        servicio_consultoria = self.create_servicio("Servicio Contrato Mixto B", tipo_de_servicio="Consultoria", honorario_fijo=500)
        contrato = self.create_contrato(
            self.cliente.name,
            servicio_contabilidad.name,
            alcances=[
                {
                    "servicio_contable": servicio_contabilidad.name,
                    "descripcion": "Alcance contable",
                    "activa": 1,
                    "periodicidad": "Mensual",
                    "modalidad_tarifa": "Fijo",
                    "honorario_fijo": 750,
                },
                {
                    "servicio_contable": servicio_consultoria.name,
                    "descripcion": "Alcance consultivo",
                    "activa": 1,
                    "periodicidad": "Mensual",
                    "modalidad_tarifa": "Fijo",
                    "honorario_fijo": 500,
                },
            ],
        )
        self.assertFalse(contrato.formato_impresion_sugerido)
