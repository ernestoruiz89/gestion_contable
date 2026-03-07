import frappe

from gestion_contable.gestion_contable.doctype.papel_trabajo_auditoria.papel_trabajo_auditoria import get_documento_evidencias
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestPapelTrabajoAuditoria(GestionContableIntegrationTestCase):
    def test_papel_exige_evidencia_especifica_del_documento(self):
        cliente = self.create_cliente("TEST-PAPEL-CLIENTE", company_default=self.company)
        periodo = self.create_periodo(cliente.name, mes="Septiembre")
        encargo = self.create_encargo(
            cliente.name,
            nombre_del_encargo="Encargo Auditoria Test",
            periodo_referencia=periodo.name,
            company=self.company,
            tipo_de_servicio="Auditoria",
        )
        expediente = self.create_expediente(encargo.name)

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "papel-evidencia.pdf",
                "file_url": "/files/papel-evidencia.pdf",
                "is_private": 0,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("File", file_doc.name)

        documento = frappe.get_doc(
            {
                "doctype": "Documento Contable",
                "titulo_del_documento": "Documento Auditoria",
                "cliente": cliente.name,
                "company": self.company,
                "periodo": periodo.name,
                "encargo_contable": encargo.name,
                "tipo": "Cedula de Auditoria",
                "evidencias_documentales": [
                    {
                        "descripcion_evidencia": "Cedula evidencia",
                        "codigo_documental": "AUD-TEST-001",
                        "tipo_documental": "Cedula de Auditoria",
                        "numero_version": 2,
                        "archivo": "/files/papel-evidencia.pdf",
                        "es_principal": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Documento Contable", documento.name)

        evidencias = get_documento_evidencias(documento.name)
        self.assertEqual(len(evidencias), 1)
        self.assertEqual(evidencias[0]["file"], file_doc.name)

        papel = frappe.get_doc(
            {
                "doctype": "Papel Trabajo Auditoria",
                "expediente_auditoria": expediente.name,
                "tipo_papel": "Prueba Sustantiva",
                "titulo": "Papel con evidencia",
                "documento_contable": documento.name,
            }
        )
        self.assertRaises(frappe.ValidationError, papel.insert)

        papel = frappe.get_doc(
            {
                "doctype": "Papel Trabajo Auditoria",
                "expediente_auditoria": expediente.name,
                "tipo_papel": "Prueba Sustantiva",
                "titulo": "Papel con evidencia valida",
                "documento_contable": documento.name,
                "evidencia_documental_file": file_doc.name,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Papel Trabajo Auditoria", papel.name)

        self.assertEqual(papel.codigo_evidencia_documental, "AUD-TEST-001")
        self.assertEqual(papel.version_evidencia_documental, 2)
