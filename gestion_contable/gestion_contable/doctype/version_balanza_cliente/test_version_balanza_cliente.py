import frappe

from gestion_contable.gestion_contable.doctype.version_balanza_cliente.version_balanza_cliente import publicar_version_balanza
from gestion_contable.gestion_contable.services.balanza.importing import importar_version_balanza
from gestion_contable.gestion_contable.services.balanza.mapping import actualizar_paquete_desde_balanza
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestVersionBalanzaCliente(GestionContableIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = self.create_cliente("TEST-BALANZA-CLIENTE")
        self.periodo = self.create_periodo(self.cliente.name, mes="Diciembre")
        self.paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": self.cliente.name,
                "periodo_contable": self.periodo.name,
                "fecha_corte": "2026-12-31",
                "version": 1,
                "es_version_vigente": 1,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", self.paquete.name)

    def _crear_version_balanza(self, rol_periodo="Actual", version=1):
        doc = frappe.get_doc(
            {
                "doctype": "Version Balanza Cliente",
                "cliente": self.cliente.name,
                "company": self.company,
                "periodo_contable": self.periodo.name,
                "paquete_estados_financieros_cliente": self.paquete.name,
                "rol_periodo": rol_periodo,
                "version": version,
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Version Balanza Cliente", doc.name)
        return doc

    def _csv_actual(self):
        return "\n".join(
            [
                "cuenta,descripcion,debe_mes_actual,haber_mes_actual,debe_saldo,haber_saldo,centro_costo,periodo",
                "1101,Caja general,100,0,100,0,ADM,2026-12",
                "1201,Cuentas por cobrar,50,0,50,0,ADM,2026-12",
                "2101,Proveedores,0,150,0,150,ADM,2026-12",
            ]
        )

    def _csv_comparativo(self):
        return "\n".join(
            [
                "cuenta,descripcion,debe_mes_actual,haber_mes_actual,debe_saldo,haber_saldo,centro_costo,periodo",
                "1101,Caja general,80,0,80,0,ADM,2025-12",
                "1201,Cuentas por cobrar,40,0,40,0,ADM,2025-12",
                "2101,Proveedores,0,120,0,120,ADM,2025-12",
            ]
        )

    def test_importa_balanza_csv_y_deriva_saldo_neto(self):
        version = self._crear_version_balanza()
        result = importar_version_balanza(version.name, csv_content=self._csv_actual())

        version.reload()
        lines = frappe.get_all(
            "Linea Balanza Cliente",
            filters={"version_balanza_cliente": version.name},
            fields=["codigo_cuenta", "saldo_final", "saldo_neto"],
            order_by="idx_importacion asc",
        )

        self.assertEqual(result["total_lineas"], 3)
        self.assertEqual(int(version.total_lineas), 3)
        self.assertEqual(flt_or_zero(lines[0]["saldo_final"]), 100)
        self.assertEqual(flt_or_zero(lines[1]["saldo_neto"]), 50)
        self.assertEqual(flt_or_zero(lines[2]["saldo_neto"]), -150)
        self.assertEqual(flt_or_zero(version.total_debe_saldo), 150)
        self.assertEqual(flt_or_zero(version.total_haber_saldo), 150)
        self.assertEqual(int(version.cuadra), 1)

    def test_actualiza_paquete_desde_balanza_a_estado_y_notas(self):
        current_version = self._crear_version_balanza("Actual", 1)
        comparative_version = self._crear_version_balanza("Comparativo", 1)
        importar_version_balanza(current_version.name, csv_content=self._csv_actual())
        importar_version_balanza(comparative_version.name, csv_content=self._csv_comparativo())
        publicar_version_balanza(current_version.name)
        publicar_version_balanza(comparative_version.name)

        estado = frappe.get_doc(
            {
                "doctype": "Estado Financiero Cliente",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "tipo_estado": "Otro Estado Complementario",
                "lineas": [
                    {"descripcion": "Efectivo", "codigo_linea_estado": "EFE", "monto_actual": 1},
                    {"descripcion": "Cuentas por Cobrar", "codigo_linea_estado": "CXC", "monto_actual": 1},
                    {"descripcion": "Total Activos Operativos", "codigo_linea_estado": "TOT", "calculo_automatico": 1, "formula_lineas": "+EFE,+CXC", "monto_actual": 1},
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Estado Financiero Cliente", estado.name)

        nota = frappe.get_doc(
            {
                "doctype": "Nota Estado Financiero",
                "paquete_estados_financieros_cliente": self.paquete.name,
                "numero_nota": "4",
                "titulo": "Nota 4",
                "contenido_narrativo": "Detalle de saldos automatizados.",
                "cifras_nota": [
                    {"concepto": "Efectivo", "codigo_cifra": "EFE", "monto_actual": 0},
                    {"concepto": "Cuentas por Cobrar", "codigo_cifra": "CXC", "monto_actual": 0},
                    {"concepto": "Total", "codigo_cifra": "TOT", "calculo_automatico": 1, "formula_cifras": "+EFE,+CXC", "monto_actual": 0},
                ],
                "secciones_estructuradas": [
                    {"seccion_id": "SEC-01", "titulo_seccion": "Tabla Automatizada", "tipo_seccion": "Tabla", "orden": 1}
                ],
                "columnas_tabulares": [
                    {"seccion_id": "SEC-01", "codigo_columna": "VIG", "etiqueta": "Vigente", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 1}
                ],
                "filas_tabulares": [
                    {"seccion_id": "SEC-01", "codigo_fila": "DET", "descripcion": "Detalle", "tipo_fila": "Detalle", "orden": 1},
                    {"seccion_id": "SEC-01", "codigo_fila": "MAN", "descripcion": "Manual", "tipo_fila": "Detalle", "orden": 2},
                ],
                "celdas_tabulares": [
                    {"seccion_id": "SEC-01", "codigo_fila": "MAN", "codigo_columna": "VIG", "valor_numero": 999, "formato_numero": "Moneda", "es_manual": 1}
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Nota Estado Financiero", nota.name)

        esquema = frappe.get_doc(
            {
                "doctype": "Esquema Mapeo Contable",
                "cliente": self.cliente.name,
                "company": self.company,
                "marco_contable": self.paquete.marco_contable,
                "tipo_paquete": self.paquete.tipo_paquete,
                "version": 1,
                "es_vigente": 1,
                "reglas": [
                    {"activo": 1, "destino_tipo": "Linea Estado", "origen_version": "Actual", "selector_tipo": "Cuenta Exacta", "selector_valor": "1101", "destino_tipo_estado": "Otro Estado Complementario", "destino_codigo_linea_estado": "EFE"},
                    {"activo": 1, "destino_tipo": "Linea Estado", "origen_version": "Actual", "selector_tipo": "Cuenta Exacta", "selector_valor": "1201", "destino_tipo_estado": "Otro Estado Complementario", "destino_codigo_linea_estado": "CXC"},
                    {"activo": 1, "destino_tipo": "Linea Estado", "origen_version": "Comparativo", "selector_tipo": "Cuenta Exacta", "selector_valor": "1101", "destino_tipo_estado": "Otro Estado Complementario", "destino_codigo_linea_estado": "EFE"},
                    {"activo": 1, "destino_tipo": "Linea Estado", "origen_version": "Comparativo", "selector_tipo": "Cuenta Exacta", "selector_valor": "1201", "destino_tipo_estado": "Otro Estado Complementario", "destino_codigo_linea_estado": "CXC"},
                    {"activo": 1, "destino_tipo": "Cifra Nota", "origen_version": "Actual", "selector_tipo": "Cuenta Exacta", "selector_valor": "1101", "destino_numero_nota": "4", "destino_codigo_cifra": "EFE"},
                    {"activo": 1, "destino_tipo": "Cifra Nota", "origen_version": "Actual", "selector_tipo": "Cuenta Exacta", "selector_valor": "1201", "destino_numero_nota": "4", "destino_codigo_cifra": "CXC"},
                    {"activo": 1, "destino_tipo": "Cifra Nota", "origen_version": "Comparativo", "selector_tipo": "Cuenta Exacta", "selector_valor": "1101", "destino_numero_nota": "4", "destino_codigo_cifra": "EFE"},
                    {"activo": 1, "destino_tipo": "Cifra Nota", "origen_version": "Comparativo", "selector_tipo": "Cuenta Exacta", "selector_valor": "1201", "destino_numero_nota": "4", "destino_codigo_cifra": "CXC"},
                    {"activo": 1, "destino_tipo": "Celda Nota", "origen_version": "Actual", "selector_tipo": "Cuenta Exacta", "selector_valor": "1101", "destino_numero_nota": "4", "destino_seccion_id": "SEC-01", "destino_codigo_fila": "DET", "destino_codigo_columna": "VIG"},
                    {"activo": 1, "destino_tipo": "Celda Nota", "origen_version": "Actual", "selector_tipo": "Cuenta Exacta", "selector_valor": "1201", "destino_numero_nota": "4", "destino_seccion_id": "SEC-01", "destino_codigo_fila": "MAN", "destino_codigo_columna": "VIG"},
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Esquema Mapeo Contable", esquema.name)

        frappe.db.set_value(
            "Paquete Estados Financieros Cliente",
            self.paquete.name,
            {
                "version_balanza_actual": current_version.name,
                "version_balanza_comparativa": comparative_version.name,
                "esquema_mapeo_contable": esquema.name,
            },
            update_modified=False,
        )

        result = actualizar_paquete_desde_balanza(self.paquete.name)

        estado.reload()
        nota.reload()
        self.paquete.reload()

        lineas = {row.codigo_linea_estado: row for row in estado.lineas}
        self.assertEqual(flt_or_zero(lineas["EFE"].monto_actual), 100)
        self.assertEqual(flt_or_zero(lineas["EFE"].monto_comparativo), 80)
        self.assertEqual(flt_or_zero(lineas["CXC"].monto_actual), 50)
        self.assertEqual(flt_or_zero(lineas["CXC"].monto_comparativo), 40)
        self.assertEqual(flt_or_zero(lineas["TOT"].monto_actual), 150)
        self.assertEqual(flt_or_zero(lineas["TOT"].monto_comparativo), 120)
        self.assertEqual(lineas["TOT"].origen_dato, "Formula")

        cifras = {row.codigo_cifra: row for row in nota.cifras_nota}
        self.assertEqual(flt_or_zero(cifras["EFE"].monto_actual), 100)
        self.assertEqual(flt_or_zero(cifras["EFE"].monto_comparativo), 80)
        self.assertEqual(flt_or_zero(cifras["CXC"].monto_actual), 50)
        self.assertEqual(flt_or_zero(cifras["TOT"].monto_actual), 150)
        self.assertEqual(flt_or_zero(cifras["TOT"].monto_comparativo), 120)
        self.assertEqual(cifras["TOT"].origen_dato, "Formula")

        cells = {(row.seccion_id, row.codigo_fila, row.codigo_columna): row for row in nota.celdas_tabulares}
        self.assertEqual(flt_or_zero(cells[("SEC-01", "DET", "VIG")].valor_numero), 100)
        self.assertEqual(flt_or_zero(cells[("SEC-01", "MAN", "VIG")].valor_numero), 999)
        self.assertEqual(int(result["destinos_bloqueados_manual"]), 1)
        self.assertTrue(self.paquete.ultima_ejecucion_actualizacion_eeff)
        self.assertTrue(self.paquete.fecha_ultima_actualizacion_automatica)


def flt_or_zero(value):
    return float(value or 0)
