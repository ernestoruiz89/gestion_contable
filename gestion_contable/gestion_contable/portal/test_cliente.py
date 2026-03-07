import frappe

from gestion_contable.gestion_contable.portal.cliente import get_portal_cliente_for_user, get_portal_dashboard_context
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestPortalCliente(GestionContableIntegrationTestCase):
    def test_usuario_portal_resuelve_cliente_y_dashboard(self):
        portal_user = self.create_user("portal_cliente@test.local", "Portal", "Cliente", role="Contador del Despacho")
        cliente = self.create_cliente(
            "TEST-PORTAL-CLIENTE",
            company_default=self.company,
            portal_habilitado=1,
            usuario_portal_principal=portal_user.name,
            correo_electronico=portal_user.name,
        )
        self.create_periodo(cliente.name, mes="Octubre")

        frappe.set_user(portal_user.name)
        resolved = get_portal_cliente_for_user()
        dashboard = get_portal_dashboard_context()

        self.assertEqual(resolved.name, cliente.name)
        self.assertEqual(dashboard["cliente"].name, cliente.name)
        self.assertIn("summary", dashboard)
