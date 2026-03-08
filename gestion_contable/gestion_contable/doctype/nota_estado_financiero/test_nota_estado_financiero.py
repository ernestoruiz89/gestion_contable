import frappe

from gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente import emitir_paquete_estados_financieros
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase
from gestion_contable.gestion_contable.utils.estados_financieros import sync_package_summary


class TestNotaEstadoFinanciero(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-NOTA-EEFF")
        self.periodo = self.create_periodo(self.cliente.name, mes="Octubre")
        self.paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-10-31",
                "version": 1,
                "es_version_vigente": 1,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", self.paquete.name)

    def _crear_estado(self, tipo_estado, requiere_nota=False, numero_nota=None):
        line = {
            "descripcion": f"Linea {tipo_estado}",
            "monto_actual": 100,
            "monto_comparativo": 90,
        }
        if requiere_nota:
            line["requiere_nota"] = 1
            line["numero_nota_referencial"] = numero_nota

        payload = {
            "doctype": "Estado Financiero Cliente",
            "paquete_estados_financieros_cliente": self.paquete.name,
            "tipo_estado": tipo_estado,
            "lineas": [line],
        }
        if tipo_estado == "Estado de Flujos de Efectivo":
            payload["metodo_flujo_efectivo"] = "Indirecto"
        estado = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", estado.name)
        return estado

    def _crear_nota(self, numero_nota, **extra_fields):
        payload = {
            "doctype": "Nota Estado Financiero",
            "paquete_estados_financieros_cliente": self.paquete.name,
            "numero_nota": numero_nota,
            "titulo": f"Nota {numero_nota}",
            "contenido_narrativo": "Contenido de prueba",
        }
        payload.update(extra_fields)
        nota = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Nota Estado Financiero", nota.name)
        return nota

    def test_paquete_emitido_exige_notas_requeridas_aprobadas(self):
        frappe.db.set_value("Paquete Estados Financieros Cliente", self.paquete.name, "estado_aprobacion", "Aprobado", update_modified=False)

        required_states = [
            ("Estado de Situacion Financiera", True, "1"),
            ("Estado de Resultados", False, None),
            ("Estado de Cambios en el Patrimonio", False, None),
            ("Estado de Flujos de Efectivo", False, None),
        ]
        for tipo_estado, requiere_nota, numero_nota in required_states:
            estado = self._crear_estado(tipo_estado, requiere_nota=requiere_nota, numero_nota=numero_nota)
            frappe.db.set_value("Estado Financiero Cliente", estado.name, "estado_aprobacion", "Aprobado", update_modified=False)

        self.assertRaises(frappe.ValidationError, emitir_paquete_estados_financieros, self.paquete.name)

        nota = self._crear_nota("1")
        sync_package_summary(self.paquete.name)
        self.assertRaises(frappe.ValidationError, emitir_paquete_estados_financieros, self.paquete.name)

        frappe.db.set_value("Nota Estado Financiero", nota.name, "estado_aprobacion", "Aprobado", update_modified=False)
        sync_package_summary(self.paquete.name)
        emitted = emitir_paquete_estados_financieros(self.paquete.name)
        self.assertEqual(emitted["estado_preparacion"], "Emitido")

        paquete = frappe.get_doc("Paquete Estados Financieros Cliente", self.paquete.name)
        self.assertEqual(int(paquete.total_notas), 1)
        self.assertEqual(int(paquete.notas_aprobadas), 1)
        self.assertEqual(int(paquete.notas_requeridas_pendientes), 0)

    def test_no_permite_numero_de_nota_duplicado(self):
        self._crear_nota("2")
        duplicate = frappe.get_doc(
            {
                "doctype": "Nota Estado Financiero",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "numero_nota": "2",
                "titulo": "Nota duplicada",
                "contenido_narrativo": "Contenido",
            }
        )
        self.assertRaises(frappe.ValidationError, duplicate.insert, ignore_permissions=True)


    def test_nota_sincroniza_referencias_cruzadas(self):
        estado = self._crear_estado("Estado de Situacion Financiera", requiere_nota=True, numero_nota="3")
        nota = self._crear_nota("3")

        self.assertEqual(int(nota.total_referencias), 1)
        referencia = nota.referencias_cruzadas[0]
        self.assertEqual(referencia.estado_financiero_cliente, estado.name)
        self.assertEqual(referencia.descripcion_linea_estado, "Linea Estado de Situacion Financiera")

        estado.lineas[0].descripcion = "Caja y Bancos"
        estado.save(ignore_permissions=True)
        nota.reload()

        self.assertEqual(int(nota.total_referencias), 1)
        self.assertEqual(nota.referencias_cruzadas[0].descripcion_linea_estado, "Caja y Bancos")
