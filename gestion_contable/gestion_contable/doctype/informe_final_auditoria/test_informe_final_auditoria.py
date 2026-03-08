import frappe

from gestion_contable.gestion_contable.doctype.informe_final_auditoria.informe_final_auditoria import (
    TIPO_CARTA_GERENCIA,
    TIPO_DICTAMEN_AUDITORIA,
    emitir_informe_final_auditoria,
    generar_informe_final_desde_expediente,
)
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestInformeFinalAuditoria(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-INFORME-FINAL")
        self.periodo = self.create_periodo(self.cliente.name, mes="Julio")
        self.servicio = self.create_servicio("Servicio Auditoria Final", tipo_de_servicio="Auditoria", tarifa_hora=220)
        self.encargo = self.create_encargo(
            self.cliente.name,
            servicio_contable=self.servicio.name,
            periodo_referencia=self.periodo.name,
            modalidad_honorario="Por Hora",
            tarifa_hora=220,
        )
        self.expediente = self.create_expediente(self.encargo.name)

    def _crear_hallazgo(self):
        hallazgo = frappe.get_doc(
            {
                "doctype": "Hallazgo Auditoria",
                "expediente_auditoria": self.expediente.name,
                "titulo_hallazgo": "Control de ingresos incompleto",
                "severidad": "Alta",
                "condicion": "Se identificaron diferencias en la conciliacion.",
                "recomendacion": "Formalizar conciliaciones y evidencia de revision.",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Hallazgo Auditoria", hallazgo.name)
        return hallazgo

    def _cerrar_expediente_para_informe(self):
        frappe.db.set_value(
            "Expediente Auditoria",
            self.expediente.name,
            {
                "estado_expediente": "Cerrada",
                "estado_aprobacion": "Aprobado",
                "resultado_revision_tecnica": "Aprobado",
                "memo_cierre": "Memo de cierre validado para pruebas.",
            },
            update_modified=False,
        )
        return frappe.get_doc("Expediente Auditoria", self.expediente.name)

    def test_genera_informe_final_desde_expediente_cerrado(self):
        hallazgo = self._crear_hallazgo()
        expediente = self._cerrar_expediente_para_informe()

        result = generar_informe_final_desde_expediente(expediente.name)
        self.track_doc("Informe Final Auditoria", result["name"])
        informe = frappe.get_doc("Informe Final Auditoria", result["name"])

        self.assertEqual(informe.expediente_auditoria, expediente.name)
        self.assertEqual(informe.tipo_de_informe, "Informe Final General")
        self.assertEqual(informe.formato_impresion_sugerido, "Informe Final Auditoria - General")
        self.assertEqual(informe.es_informe_principal, 1)
        self.assertIn(hallazgo.titulo_hallazgo, informe.principales_hallazgos or "")
        self.assertEqual(frappe.db.get_value("Expediente Auditoria", expediente.name, "informe_final_auditoria"), informe.name)

    def test_emitir_informe_requiere_aprobacion_propia(self):
        expediente = self._cerrar_expediente_para_informe()
        result = generar_informe_final_desde_expediente(expediente.name)
        self.track_doc("Informe Final Auditoria", result["name"])

        self.assertRaises(frappe.ValidationError, emitir_informe_final_auditoria, result["name"])
        frappe.db.set_value("Informe Final Auditoria", result["name"], "estado_aprobacion", "Aprobado", update_modified=False)
        emitted = emitir_informe_final_auditoria(result["name"])
        self.assertEqual(emitted["estado_emision"], "Emitido")

    def test_permite_informe_adicional_no_principal(self):
        self._crear_hallazgo()
        expediente = self._cerrar_expediente_para_informe()
        principal = generar_informe_final_desde_expediente(expediente.name)
        self.track_doc("Informe Final Auditoria", principal["name"])

        carta = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": expediente.name,
                "tipo_de_informe": TIPO_CARTA_GERENCIA,
                "es_informe_principal": 0,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Informe Final Auditoria", carta.name)

        self.assertEqual(carta.formato_impresion_sugerido, "Carta a la Gerencia - Auditoria")
        self.assertEqual(frappe.db.get_value("Expediente Auditoria", expediente.name, "informe_final_auditoria"), principal["name"])

    def test_no_permite_dos_informes_principales_activos(self):
        self._cerrar_expediente_para_informe()
        principal = generar_informe_final_desde_expediente(self.expediente.name)
        self.track_doc("Informe Final Auditoria", principal["name"])

        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "es_informe_principal": 1,
            }
        )
        self.assertRaises(frappe.ValidationError, dictamen.insert, ignore_permissions=True)

    def test_dictamen_rechaza_opinion_favorable_con_hallazgos_abiertos(self):
        self._crear_hallazgo()
        self._cerrar_expediente_para_informe()

        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Favorable",
                "es_informe_principal": 0,
            }
        )
        self.assertRaises(frappe.ValidationError, dictamen.insert, ignore_permissions=True)

    def test_emitir_dictamen_con_salvedades_requiere_asunto_y_fundamento(self):
        self._crear_hallazgo()
        self._cerrar_expediente_para_informe()

        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Con Salvedades",
                "es_informe_principal": 0,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Informe Final Auditoria", dictamen.name)
        frappe.db.set_value("Informe Final Auditoria", dictamen.name, "estado_aprobacion", "Aprobado", update_modified=False)

        self.assertRaises(frappe.ValidationError, emitir_informe_final_auditoria, dictamen.name)

        frappe.db.set_value(
            "Informe Final Auditoria",
            dictamen.name,
            {
                "asunto_que_origina_modificacion": "Diferencias materiales en la conciliacion de ingresos.",
                "fundamento_salvedad": "<p>La evidencia disponible demuestra un efecto material pero no generalizado sobre la informacion auditada.</p>",
            },
            update_modified=False,
        )
        emitted = emitir_informe_final_auditoria(dictamen.name)
        self.assertEqual(emitted["estado_emision"], "Emitido")

    def test_dictamen_rechaza_tipo_opinion_no_valido_nia(self):
        self._cerrar_expediente_para_informe()
        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Conclusiones y Recomendaciones",
                "es_informe_principal": 0,
            }
        )
        self.assertRaises(frappe.ValidationError, dictamen.insert, ignore_permissions=True)

    def test_dictamen_favorable_sugiere_base_normativa_nia_700(self):
        self._cerrar_expediente_para_informe()
        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Favorable",
                "es_informe_principal": 0,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Informe Final Auditoria", dictamen.name)
        self.assertEqual(dictamen.base_normativa, "NIA 700")
        self.assertIn("NIA 700", dictamen.fundamento_opinion or "")

    def test_dictamen_modificado_sugiere_base_normativa_nia_705(self):
        self._crear_hallazgo()
        self._cerrar_expediente_para_informe()
        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Con Salvedades",
                "es_informe_principal": 0,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Informe Final Auditoria", dictamen.name)
        self.assertEqual(dictamen.base_normativa, "NIA 705")
        self.assertIn("NIA 705", dictamen.fundamento_opinion or "")

    def test_emitir_dictamen_con_parrafo_enfasis_requiere_nia_706(self):
        self._cerrar_expediente_para_informe()
        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Favorable",
                "es_informe_principal": 0,
                "parrafo_enfasis": "<p>Sin modificar nuestra opinion, llamamos la atencion sobre la nota X.</p>",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Informe Final Auditoria", dictamen.name)
        frappe.db.set_value("Informe Final Auditoria", dictamen.name, "estado_aprobacion", "Aprobado", update_modified=False)

        self.assertRaises(frappe.ValidationError, emitir_informe_final_auditoria, dictamen.name)

        frappe.db.set_value(
            "Informe Final Auditoria",
            dictamen.name,
            "base_normativa",
            "NIA 700 / NIA 706",
            update_modified=False,
        )
        emitted = emitir_informe_final_auditoria(dictamen.name)
        self.assertEqual(emitted["estado_emision"], "Emitido")

    def test_dictamen_abstencion_normaliza_flags_nia(self):
        self._crear_hallazgo()
        self._cerrar_expediente_para_informe()
        dictamen = frappe.get_doc(
            {
                "doctype": "Informe Final Auditoria",
                "expediente_auditoria": self.expediente.name,
                "tipo_de_informe": TIPO_DICTAMEN_AUDITORIA,
                "tipo_opinion": "Abstencion",
                "es_informe_principal": 0,
                "efecto_generalizado": 0,
                "limitacion_alcance_material": 0,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Informe Final Auditoria", dictamen.name)
        self.assertEqual(int(dictamen.efecto_generalizado), 1)
        self.assertEqual(int(dictamen.limitacion_alcance_material), 1)
