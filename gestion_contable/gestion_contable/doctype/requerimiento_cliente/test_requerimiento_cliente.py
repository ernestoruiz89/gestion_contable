import frappe

from gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente import (
    enviar_correo_requerimiento_manual,
    marcar_requerimiento_enviado,
)
from gestion_contable.gestion_contable.setup.email_templates import ensure_standard_email_templates
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestRequerimientoCliente(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        ensure_standard_email_templates()

    def test_requerimiento_hereda_company_del_cliente(self):
        cliente = self.create_cliente("TEST-REQ-CLIENTE", company_default=self.company)
        periodo = self.create_periodo(cliente.name, mes="Julio")

        requerimiento = frappe.get_doc(
            {
                "doctype": "Requerimiento Cliente",
                "nombre_del_requerimiento": "Req Test Company",
                "cliente": cliente.name,
                "periodo": periodo.name,
                "fecha_solicitud": "2026-07-05",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Requerimiento Cliente", requerimiento.name)

        self.assertEqual(requerimiento.company, self.company)

    def test_marcar_requerimiento_enviado_por_correo_usa_template(self):
        cliente = self.create_cliente(
            "TEST-REQ-EMAIL",
            company_default=self.company,
            correo_electronico="cliente@test.local",
            contacto_facturacion="Ana Cliente",
            contactos_funcionales=[
                {
                    "nombre_contacto": "Ana Cliente",
                    "email_contacto": "ana@cliente.test",
                    "es_principal": 1,
                    "recibe_requerimientos": 1,
                    "activo": 1,
                }
            ],
        )
        periodo = self.create_periodo(cliente.name, mes="Agosto")
        requerimiento = frappe.get_doc(
            {
                "doctype": "Requerimiento Cliente",
                "nombre_del_requerimiento": "Req Test Email",
                "cliente": cliente.name,
                "periodo": periodo.name,
                "fecha_solicitud": "2026-08-05",
                "fecha_vencimiento": "2026-08-10",
                "canal_envio": "Correo",
                "contacto_cliente": "Ana Cliente <ana@cliente.test>",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Requerimiento Cliente", requerimiento.name)

        original_sendmail = frappe.sendmail
        captured = {}

        def fake_sendmail(**kwargs):
            captured.update(kwargs)

        frappe.sendmail = fake_sendmail
        try:
            result = marcar_requerimiento_enviado(requerimiento.name)
        finally:
            frappe.sendmail = original_sendmail

        self.assertEqual(result["estado_requerimiento"], "Enviado")
        self.assertIn("ana@cliente.test", captured.get("recipients", []))
        self.assertIn("Req Test Email", captured.get("subject", ""))

        comunicaciones = frappe.get_all(
            "Communication",
            filters={
                "reference_doctype": "Requerimiento Cliente",
                "reference_name": requerimiento.name,
                "communication_medium": "Email",
            },
            pluck="name",
        )
        for name in comunicaciones:
            self.track_doc("Communication", name)
        self.assertTrue(comunicaciones)

    def test_requerimiento_permite_modo_manual_desde_configuracion(self):
        previous = frappe.db.get_single_value("Configuracion Despacho Contable", "auto_enviar_correo_requerimiento_envio")
        frappe.db.set_single_value("Configuracion Despacho Contable", "auto_enviar_correo_requerimiento_envio", 0)

        cliente = self.create_cliente(
            "TEST-REQ-MANUAL",
            company_default=self.company,
            correo_electronico="manual@test.local",
            contactos_funcionales=[
                {
                    "nombre_contacto": "Manual Cliente",
                    "email_contacto": "manual@cliente.test",
                    "es_principal": 1,
                    "recibe_requerimientos": 1,
                    "activo": 1,
                }
            ],
        )
        periodo = self.create_periodo(cliente.name, mes="Septiembre")
        requerimiento = frappe.get_doc(
            {
                "doctype": "Requerimiento Cliente",
                "nombre_del_requerimiento": "Req Test Manual",
                "cliente": cliente.name,
                "periodo": periodo.name,
                "fecha_solicitud": "2026-09-05",
                "fecha_vencimiento": "2026-09-10",
                "canal_envio": "Correo",
                "contacto_cliente": "Manual Cliente <manual@cliente.test>",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Requerimiento Cliente", requerimiento.name)

        original_sendmail = frappe.sendmail
        calls = []

        def fake_sendmail(**kwargs):
            calls.append(kwargs)

        frappe.sendmail = fake_sendmail
        try:
            marcar_requerimiento_enviado(requerimiento.name)
            self.assertEqual(len(calls), 0)

            enviar_correo_requerimiento_manual(requerimiento.name, "envio")
            self.assertEqual(len(calls), 1)
            self.assertIn("manual@cliente.test", calls[0].get("recipients", []))
        finally:
            frappe.sendmail = original_sendmail
            frappe.db.set_single_value(
                "Configuracion Despacho Contable",
                "auto_enviar_correo_requerimiento_envio",
                previous if previous not in (None, "") else 1,
            )

        comunicaciones = frappe.get_all(
            "Communication",
            filters={"reference_doctype": "Requerimiento Cliente", "reference_name": requerimiento.name},
            pluck="name",
        )
        for name in comunicaciones:
            self.track_doc("Communication", name)
