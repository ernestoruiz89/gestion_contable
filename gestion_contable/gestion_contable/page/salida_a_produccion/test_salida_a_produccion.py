from gestion_contable.gestion_contable.page.salida_a_produccion.salida_a_produccion import get_release_readiness
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestSalidaProduccion(GestionContableIntegrationTestCase):
    def test_readiness_publica_checks_de_release_y_eeff(self):
        payload = get_release_readiness()
        checks = {(item["kind"], item["name"]) for group in payload["groups"] for item in group["items"]}

        self.assertIn(("DocType", "Informe Final Auditoria"), checks)
        self.assertIn(("DocType", "Paquete Estados Financieros Cliente"), checks)
        self.assertIn(("Print Format", "Informe Completo de EEFF Auditados"), checks)
        self.assertIn(("Patch", "gestion_contable.gestion_contable.patches.reload_panel_de_gestion_workspace_v5"), checks)
        self.assertTrue(any(group["title"] == "Dependencias Opcionales" for group in payload["groups"]))
        self.assertTrue(any(section["title"] == "Estados Financieros del Cliente" for section in payload["uat_sections"]))
