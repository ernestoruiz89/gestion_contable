import frappe

from gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente import (
    duplicar_paquete_estados_financieros,
    emitir_paquete_estados_financieros,
)
from gestion_contable.gestion_contable.utils.estados_financieros import get_package_column_labels
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestPaqueteEstadosFinancierosCliente(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-EEFF-CLIENTE")
        self.periodo = self.create_periodo(self.cliente.name, mes="Agosto")

    def _crear_paquete(self, **extra_fields):
        payload = {
            "doctype": "Paquete Estados Financieros Cliente",
            "cliente": self.cliente.name,
            "periodo_contable": self.periodo.name,
            "fecha_corte": "2026-08-31",
            "marco_contable": "NIIF para PYMES",
            "tipo_paquete": "Preliminar",
            "version": 1,
            "es_version_vigente": 1,
        }
        payload.update(extra_fields)
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", doc.name)
        return doc

    def _crear_estado(self, paquete_name, tipo_estado, metodo_flujo_efectivo=None):
        payload = {
            "doctype": "Estado Financiero Cliente",
            "paquete_estados_financieros_cliente": paquete_name,
            "tipo_estado": tipo_estado,
            "lineas": [
                {
                    "descripcion": "Rubro principal",
                    "monto_actual": 100,
                    "monto_comparativo": 90,
                }
            ],
        }
        if metodo_flujo_efectivo:
            payload["metodo_flujo_efectivo"] = metodo_flujo_efectivo
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", doc.name)
        return doc

    def test_paquete_emitido_requiere_estados_base_aprobados(self):
        paquete = self._crear_paquete()
        frappe.db.set_value("Paquete Estados Financieros Cliente", paquete.name, "estado_aprobacion", "Aprobado", update_modified=False)

        self.assertRaises(frappe.ValidationError, emitir_paquete_estados_financieros, paquete.name)

        required = [
            "Estado de Situacion Financiera",
            "Estado de Resultados",
            "Estado de Cambios en el Patrimonio",
            "Estado de Flujos de Efectivo",
        ]
        for tipo_estado in required:
            estado = self._crear_estado(paquete.name, tipo_estado, metodo_flujo_efectivo="Indirecto" if tipo_estado == "Estado de Flujos de Efectivo" else None)
            frappe.db.set_value("Estado Financiero Cliente", estado.name, "estado_aprobacion", "Aprobado", update_modified=False)

        emitted = emitir_paquete_estados_financieros(paquete.name)
        self.assertEqual(emitted["estado_preparacion"], "Emitido")

    def test_no_permite_dos_versiones_vigentes_mismo_scope(self):
        self._crear_paquete(version=1)
        another = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-08-31",
                "marco_contable": "NIIF para PYMES",
                "tipo_paquete": "Preliminar",
                "version": 2,
                "es_version_vigente": 1,
            }
        )
        self.assertRaises(frappe.ValidationError, another.insert, ignore_permissions=True)

    def test_etiquetas_columnas_usan_mes_ano_y_permiten_override(self):
        paquete = self._crear_paquete(fecha_corte="2026-08-31", fecha_corte_comparativa="2025-08-31")

        labels = get_package_column_labels(paquete)
        self.assertEqual(labels["actual"], "Agosto 2026")
        self.assertEqual(labels["comparativo"], "Agosto 2025")

        paquete.etiqueta_columna_actual = "Junio 2025"
        paquete.etiqueta_columna_comparativa = "Junio 2024"
        paquete.save(ignore_permissions=True)

        labels = get_package_column_labels(paquete.name)
        self.assertEqual(labels["actual"], "Junio 2025")
        self.assertEqual(labels["comparativo"], "Junio 2024")

    def _crear_nota(self, paquete_name, numero_nota="1"):
        payload = {
            "doctype": "Nota Estado Financiero",
            "paquete_estados_financieros_cliente": paquete_name,
            "numero_nota": numero_nota,
            "titulo": f"Nota {numero_nota}",
            "contenido_narrativo": "Contenido de prueba",
            "cifras_nota": [
                {
                    "concepto": "Saldo",
                    "monto_actual": 100,
                    "monto_comparativo": 90,
                }
            ],
        }
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Nota Estado Financiero", doc.name)
        return doc

    def test_duplicar_paquete_copia_estados_y_notas_en_borrador(self):
        paquete = self._crear_paquete(estado_preparacion="Emitido", estado_aprobacion="Aprobado")
        estado = self._crear_estado(paquete.name, "Estado de Situacion Financiera")
        nota = self._crear_nota(paquete.name, numero_nota="1")
        frappe.db.set_value("Paquete Estados Financieros Cliente", paquete.name, {
            "dictamen_de_auditoria": "DICTAMEN-DEMO",
            "informe_final_auditoria": "INFORME-DEMO",
            "fecha_emision": "2026-08-31",
        }, update_modified=False)

        nuevo_periodo = self.create_periodo(self.cliente.name, mes="Septiembre")
        duplicated = duplicar_paquete_estados_financieros(
            paquete.name,
            nuevo_periodo.name,
            "2026-09-30",
            version=1,
            es_version_vigente=0,
        )

        duplicated_package = frappe.get_doc("Paquete Estados Financieros Cliente", duplicated["name"])
        self.track_doc("Paquete Estados Financieros Cliente", duplicated_package.name)

        duplicated_states = frappe.get_all(
            "Estado Financiero Cliente",
            filters={"paquete_estados_financieros_cliente": duplicated_package.name},
            pluck="name",
        )
        duplicated_notes = frappe.get_all(
            "Nota Estado Financiero",
            filters={"paquete_estados_financieros_cliente": duplicated_package.name},
            pluck="name",
        )
        for name in duplicated_states:
            self.track_doc("Estado Financiero Cliente", name)
        for name in duplicated_notes:
            self.track_doc("Nota Estado Financiero", name)

        self.assertEqual(duplicated_package.estado_preparacion, "Borrador")
        self.assertEqual(duplicated_package.estado_aprobacion, "Borrador")
        self.assertEqual(duplicated_package.periodo_contable, nuevo_periodo.name)
        self.assertFalse(duplicated_package.dictamen_de_auditoria)
        self.assertFalse(duplicated_package.informe_final_auditoria)
        self.assertEqual(len(duplicated_states), 1)
        self.assertEqual(len(duplicated_notes), 1)
        self.assertEqual(frappe.db.get_value("Estado Financiero Cliente", duplicated_states[0], "estado_aprobacion"), "Borrador")
        self.assertEqual(frappe.db.get_value("Nota Estado Financiero", duplicated_notes[0], "estado_aprobacion"), "Borrador")
        self.assertEqual(duplicated["copied_states"], 1)
        self.assertEqual(duplicated["copied_notes"], 1)
