import frappe

from gestion_contable.gestion_contable.page.creador_de_notas_eeff.creador_de_notas_eeff import (
    create_note_for_editor,
    get_editor_bootstrap,
    save_note_editor,
)
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestCreadorDeNotasEEFF(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-CREADOR-EEFF")
        self.periodo = self.create_periodo(self.cliente.name, mes="Noviembre")
        self.paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-11-30",
                "version": 1,
                "es_version_vigente": 1,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", self.paquete.name)
        self.nota = frappe.get_doc(
            {
                "doctype": "Nota Estado Financiero",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "numero_nota": "1",
                "titulo": "Nota inicial",
                "contenido_narrativo": "Contenido base",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Nota Estado Financiero", self.nota.name)

    def test_bootstrap_solo_lista_clientes_sin_contexto(self):
        data = get_editor_bootstrap()
        self.assertIsNone(data["cliente"])
        self.assertEqual(data["packages"], [])
        self.assertEqual(data["notes"], [])
        self.assertTrue(any(row["value"] == self.cliente.name for row in data["clients"]))

    def test_bootstrap_filtra_paquetes_por_cliente(self):
        otro_cliente = self.create_cliente("TEST-CREADOR-EEFF-OTRO")
        otro_periodo = self.create_periodo(otro_cliente.name, mes="Diciembre")
        otro_paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": otro_cliente.name,
                "periodo_contable": otro_periodo.name,
                "fecha_corte": "2026-12-31",
                "version": 1,
                "es_version_vigente": 1,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", otro_paquete.name)

        data = get_editor_bootstrap(cliente=self.cliente.name)
        self.assertEqual(data["cliente"], self.cliente.name)
        self.assertEqual([row["value"] for row in data["packages"]], [self.paquete.name])

    def test_bootstrap_carga_nota_y_paquete(self):
        data = get_editor_bootstrap(note_name=self.nota.name)
        self.assertEqual(data["package_name"], self.paquete.name)
        self.assertEqual(data["cliente"], self.cliente.name)
        self.assertEqual(data["note"]["doc"]["name"], self.nota.name)
        self.assertTrue(any(row["name"] == self.nota.name for row in data["notes"]))

    def test_save_editor_actualiza_tablas_estructuradas(self):
        payload = {
            "name": self.nota.name,
            "paquete_estados_financieros_cliente": self.paquete.name,
            "numero_nota": "1",
            "titulo": "Nota cartera",
            "categoria_nota": "Cuentas por Cobrar",
            "orden_presentacion": 8,
            "politica_contable": "Politica actualizada",
            "contenido_narrativo": "Texto actualizado",
            "observaciones_preparacion": "Obs",
            "secciones_estructuradas": [
                {
                    "seccion_id": "SEC-01",
                    "titulo_seccion": "Cartera",
                    "tipo_seccion": "Tabla",
                    "orden": 1,
                    "contenido_narrativo": "Resumen",
                }
            ],
            "columnas_tabulares": [
                {
                    "seccion_id": "SEC-01",
                    "codigo_columna": "VIG",
                    "etiqueta": "Vigentes",
                    "tipo_dato": "Moneda",
                    "alineacion": "Right",
                    "orden": 1,
                },
                {
                    "seccion_id": "SEC-01",
                    "codigo_columna": "TOT",
                    "etiqueta": "Total",
                    "tipo_dato": "Moneda",
                    "alineacion": "Right",
                    "orden": 2,
                    "calculo_automatico": 1,
                    "formula_columnas": "+VIG",
                },
            ],
            "filas_tabulares": [
                {
                    "seccion_id": "SEC-01",
                    "codigo_fila": "COM",
                    "descripcion": "Creditos comerciales",
                    "nivel": 1,
                    "tipo_fila": "Detalle",
                    "orden": 1,
                }
            ],
            "celdas_tabulares": [
                {
                    "seccion_id": "SEC-01",
                    "codigo_fila": "COM",
                    "codigo_columna": "VIG",
                    "valor_numero": 1250,
                    "formato_numero": "Moneda",
                }
            ],
        }

        response = save_note_editor(payload)
        self.assertEqual(response["note"]["doc"]["titulo"], "Nota cartera")

        nota = frappe.get_doc("Nota Estado Financiero", self.nota.name)
        self.assertEqual(nota.titulo, "Nota cartera")
        self.assertEqual(len(nota.secciones_estructuradas), 1)
        self.assertEqual(len(nota.columnas_tabulares), 2)
        self.assertEqual(len(nota.filas_tabulares), 1)
        self.assertEqual(len(nota.celdas_tabulares), 1)

    def test_create_note_for_editor_crea_nota_en_paquete(self):
        response = create_note_for_editor(self.paquete.name, "2", "Nota nueva", "Otra")
        created_name = response["note"]["doc"]["name"]
        self.track_doc("Nota Estado Financiero", created_name)
        self.assertTrue(frappe.db.exists("Nota Estado Financiero", created_name))