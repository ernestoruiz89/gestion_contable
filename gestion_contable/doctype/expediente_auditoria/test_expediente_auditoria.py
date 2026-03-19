import frappe

from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestExpedienteAuditoria(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-AUDITORIA-CLIENTE")
        self.periodo = self.create_periodo(self.cliente.name, mes="Junio")
        self.servicio_auditoria = self.create_servicio("Servicio Auditoria Test", tipo_de_servicio="Auditoria", tarifa_hora=200)
        self.servicio_consultoria = self.create_servicio("Servicio Consultoria Test", tipo_de_servicio="Consultoria", tarifa_hora=120)
        self.encargo_auditoria = self.create_encargo(
            self.cliente.name,
            servicio_contable=self.servicio_auditoria.name,
            periodo_referencia=self.periodo.name,
            modalidad_honorario="Por Hora",
            tarifa_hora=200,
        )
        self.encargo_consultoria = self.create_encargo(
            self.cliente.name,
            servicio_contable=self.servicio_consultoria.name,
            periodo_referencia=self.periodo.name,
            modalidad_honorario="Por Hora",
            tarifa_hora=120,
        )

    def test_expediente_rechaza_encargo_no_auditoria(self):
        expediente = frappe.get_doc({
            "doctype": "Expediente Auditoria",
            "nombre_del_expediente": "EXP-NO-AUDITORIA",
            "encargo_contable": self.encargo_consultoria.name,
        })
        self.assertRaises(frappe.ValidationError, expediente.insert)

    def test_expediente_rechaza_cierre_sin_matriz_ni_papeles(self):
        expediente = self.create_expediente(self.encargo_auditoria.name)
        frappe.db.set_value("Expediente Auditoria", expediente.name, "estado_aprobacion", "Aprobado", update_modified=False)
        expediente = frappe.get_doc("Expediente Auditoria", expediente.name)
        expediente.estado_expediente = "Cerrada"
        expediente.resultado_revision_tecnica = "Aprobado"
        expediente.memo_cierre = "Memo de cierre preliminar"
        self.assertRaises(frappe.ValidationError, expediente.save, ignore_permissions=True)
