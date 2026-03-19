import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.setup.email_templates import ensure_standard_email_templates
from gestion_contable.gestion_contable.utils.emailing import EMAIL_TEMPLATE_DEFAULTS


class TestEmailTemplatesSetup(IntegrationTestCase):
    def test_ensure_standard_email_templates_crea_sugeridos_y_configuracion(self):
        if not frappe.db.exists("DocType", "Email Template"):
            self.skipTest("Email Template no esta disponible en este sitio")

        ensure_standard_email_templates()

        for config_fieldname, definition in EMAIL_TEMPLATE_DEFAULTS.items():
            self.assertTrue(frappe.db.exists("Email Template", definition["name"]))
            self.assertEqual(
                frappe.db.get_single_value("Configuracion Despacho Contable", config_fieldname),
                definition["name"],
            )

        for fieldname in (
            "auto_enviar_correo_requerimiento_envio",
            "auto_enviar_recordatorio_requerimiento",
            "auto_enviar_aviso_vencido_requerimiento",
            "auto_enviar_correo_cobranza",
        ):
            self.assertEqual(int(frappe.db.get_single_value("Configuracion Despacho Contable", fieldname) or 0), 1)
