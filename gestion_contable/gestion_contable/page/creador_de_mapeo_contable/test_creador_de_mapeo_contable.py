import frappe

from gestion_contable.gestion_contable.page.creador_de_mapeo_contable.creador_de_mapeo_contable import (
    create_scheme_for_editor,
    get_mapping_editor_bootstrap,
    save_mapping_scheme_editor,
)
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestCreadorDeMapeoContable(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-CREADOR-MAPEO")
        self.esquema = frappe.get_doc(
            {
                "doctype": "Esquema Mapeo Contable",
                "cliente": self.cliente.name,
                "company": self.company,
                "marco_contable": "NIIF para PYMES",
                "tipo_paquete": "Preliminar",
                "version": 1,
                "activo": 1,
                "es_vigente": 0,
                "descripcion": "Esquema base",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Esquema Mapeo Contable", self.esquema.name)

    def test_bootstrap_lista_clientes_y_catalogos(self):
        data = get_mapping_editor_bootstrap()
        self.assertTrue(any(row["value"] == self.cliente.name for row in data["clients"]))
        self.assertIn("Cifra Nota", data["catalogs"]["destino_tipos"])
        self.assertIsNone(data["scheme"])

    def test_bootstrap_carga_esquema(self):
        data = get_mapping_editor_bootstrap(esquema_name=self.esquema.name)
        self.assertEqual(data["cliente"], self.cliente.name)
        self.assertEqual(data["scheme"]["doc"]["name"], self.esquema.name)
        self.assertTrue(any(row["value"] == self.esquema.name for row in data["schemes"]))

    def test_create_scheme_for_editor_crea_nueva_version(self):
        response = create_scheme_for_editor(
            cliente=self.cliente.name,
            company=self.company,
            marco_contable="NIIF para PYMES",
            tipo_paquete="Preliminar",
            descripcion="Nueva version",
        )
        created_name = response["scheme"]["doc"]["name"]
        self.track_doc("Esquema Mapeo Contable", created_name)
        created_doc = frappe.get_doc("Esquema Mapeo Contable", created_name)
        self.assertEqual(created_doc.version, 2)
        self.assertEqual(created_doc.descripcion, "Nueva version")

    def test_save_scheme_editor_actualiza_reglas(self):
        payload = {
            "name": self.esquema.name,
            "cliente": self.cliente.name,
            "company": self.company,
            "marco_contable": "NIIF para PYMES",
            "tipo_paquete": "Preliminar",
            "version": 1,
            "activo": 1,
            "es_vigente": 0,
            "descripcion": "Actualizado desde page",
            "reglas": [
                {
                    "activo": 1,
                    "orden_ejecucion": 1,
                    "destino_tipo": "Cifra Nota",
                    "origen_version": "Ambas",
                    "selector_tipo": "Lista",
                    "selector_valor": "1101\n1102",
                    "operacion_agregacion": "Saldo Neto",
                    "signo_presentacion": "Normal",
                    "destino_numero_nota": "4",
                    "destino_codigo_cifra": "EFECTIVO",
                    "sobrescribir_manual": 0,
                    "obligatoria": 1,
                }
            ],
        }

        response = save_mapping_scheme_editor(payload)
        self.assertEqual(response["scheme"]["doc"]["descripcion"], "Actualizado desde page")

        esquema = frappe.get_doc("Esquema Mapeo Contable", self.esquema.name)
        self.assertEqual(esquema.descripcion, "Actualizado desde page")
        self.assertEqual(len(esquema.reglas), 1)
        self.assertEqual(esquema.reglas[0].destino_codigo_cifra, "EFECTIVO")
        self.assertEqual(esquema.reglas[0].origen_version, "Ambas")
