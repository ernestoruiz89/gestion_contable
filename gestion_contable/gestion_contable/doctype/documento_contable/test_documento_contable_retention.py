import frappe

from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestDocumentoContableRetention(GestionContableIntegrationTestCase):
    def test_documento_bloquea_eliminacion_si_retencion_esta_activa(self):
        cliente = self.create_cliente(
            "TEST-DOC-RETENCION",
            company_default=self.company,
            politica_retencion_documental="Fiscal",
        )
        periodo = self.create_periodo(cliente.name, mes="Agosto")
        documento = frappe.get_doc(
            {
                "doctype": "Documento Contable",
                "titulo_del_documento": "Documento con Retencion",
                "cliente": cliente.name,
                "company": self.company,
                "periodo": periodo.name,
                "tipo": "Factura",
                "evidencias_documentales": [
                    {
                        "descripcion_evidencia": "Factura fiscal",
                        "tipo_documental": "Factura",
                        "politica_retencion": "Fiscal",
                        "archivo": "/files/test-retencion.pdf",
                        "es_principal": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Documento Contable", documento.name)

        self.assertRaises(
            frappe.ValidationError,
            frappe.delete_doc,
            "Documento Contable",
            documento.name,
            ignore_permissions=True,
            force=True,
        )
