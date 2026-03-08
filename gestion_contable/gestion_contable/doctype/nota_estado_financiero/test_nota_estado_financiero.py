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
        common_ref = {"requiere_nota": 1, "numero_nota_referencial": numero_nota} if requiere_nota else {}
        if tipo_estado == "Estado de Situacion Financiera":
            lineas = [
                {"descripcion": "Total Activo", "naturaleza": "Activo", "es_total": 1, "monto_actual": 100, "monto_comparativo": 90, **common_ref},
                {"descripcion": "Total Pasivo", "naturaleza": "Pasivo", "es_total": 1, "monto_actual": 60, "monto_comparativo": 50},
                {"descripcion": "Total Patrimonio", "naturaleza": "Patrimonio", "es_total": 1, "monto_actual": 40, "monto_comparativo": 40},
            ]
        elif tipo_estado == "Estado de Resultados":
            lineas = [
                {"descripcion": "Total Ingresos", "naturaleza": "Ingreso", "es_total": 1, "monto_actual": 500, "monto_comparativo": 450, **common_ref},
                {"descripcion": "Total Gastos", "naturaleza": "Gasto", "es_total": 1, "monto_actual": 300, "monto_comparativo": 280},
                {"descripcion": "Resultado Final", "naturaleza": "Otro", "es_resultado_final": 1, "monto_actual": 200, "monto_comparativo": 170},
            ]
        elif tipo_estado == "Estado de Flujos de Efectivo":
            lineas = [
                {"descripcion": "Efectivo Inicial", "naturaleza": "Activo", "es_efectivo_inicial": 1, "monto_actual": 100, "monto_comparativo": 80, **common_ref},
                {"descripcion": "Variacion Neta", "naturaleza": "Otro", "es_variacion_neta_efectivo": 1, "monto_actual": 50, "monto_comparativo": 20},
                {"descripcion": "Efectivo Final", "naturaleza": "Activo", "es_efectivo_final": 1, "monto_actual": 150, "monto_comparativo": 100},
            ]
        else:
            lineas = [
                {"descripcion": "Capital Aportado", "naturaleza": "Patrimonio", "monto_actual": 250, "monto_comparativo": 230, **common_ref},
                {"descripcion": "Resultado Acumulado", "naturaleza": "Patrimonio", "monto_actual": 120, "monto_comparativo": 100},
            ]

        payload = {
            "doctype": "Estado Financiero Cliente",
            "paquete_estados_financieros_cliente": self.paquete.name,
            "tipo_estado": tipo_estado,
            "lineas": lineas,
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
        self.assertEqual(referencia.descripcion_linea_estado, "Total Activo")

        estado.lineas[0].descripcion = "Caja y Bancos"
        estado.save(ignore_permissions=True)
        nota.reload()

        self.assertEqual(int(nota.total_referencias), 1)
        self.assertEqual(nota.referencias_cruzadas[0].descripcion_linea_estado, "Caja y Bancos")

    def test_nota_permite_tabla_estructurada_compleja(self):
        nota = self._crear_nota(
            "8",
            contenido_narrativo="Resumen de cartera.",
            secciones_estructuradas=[
                {
                    "seccion_id": "SEC-01",
                    "titulo_seccion": "Cartera de creditos, neto",
                    "tipo_seccion": "Tabla",
                    "orden": 1,
                }
            ],
            columnas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_columna": "VIG", "etiqueta": "Vigentes", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 1},
                {"seccion_id": "SEC-01", "codigo_columna": "VENC", "etiqueta": "Vencidos", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 2},
                {"seccion_id": "SEC-01", "codigo_columna": "TOT", "etiqueta": "Total", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 3},
            ],
            filas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "descripcion": "Creditos comerciales", "nivel": 1, "tipo_fila": "Detalle", "orden": 1},
                {"seccion_id": "SEC-01", "codigo_fila": "SUB", "descripcion": "Subtotal", "nivel": 1, "tipo_fila": "Subtotal", "orden": 2, "negrita": 1},
            ],
            celdas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VIG", "valor_numero": 72755643, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VENC", "valor_numero": 241688, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "TOT", "valor_numero": 73621817, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "SUB", "codigo_columna": "VIG", "valor_numero": 1953933684, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "SUB", "codigo_columna": "VENC", "valor_numero": 29549491, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "SUB", "codigo_columna": "TOT", "valor_numero": 2008803061, "formato_numero": "Moneda"},
            ],
        )

        sections = nota.get_structured_sections()
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["titulo_seccion"], "Cartera de creditos, neto")
        self.assertEqual(len(sections[0]["columnas"]), 3)
        self.assertEqual(len(sections[0]["filas"]), 2)

    def test_nota_calcula_subtotales_y_totales_por_formula(self):
        nota = self._crear_nota(
            "9",
            contenido_narrativo="Resumen de cartera con formulas.",
            secciones_estructuradas=[
                {
                    "seccion_id": "SEC-01",
                    "titulo_seccion": "Cartera por categoria",
                    "tipo_seccion": "Tabla",
                    "orden": 1,
                }
            ],
            columnas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_columna": "VIG", "etiqueta": "Vigentes", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 1},
                {"seccion_id": "SEC-01", "codigo_columna": "VENC", "etiqueta": "Vencidos", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 2},
                {"seccion_id": "SEC-01", "codigo_columna": "TOT", "etiqueta": "Total", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 3, "calculo_automatico": 1, "formula_columnas": "+VIG,+VENC"},
            ],
            filas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "descripcion": "Creditos comerciales", "nivel": 1, "tipo_fila": "Detalle", "orden": 1},
                {"seccion_id": "SEC-01", "codigo_fila": "CONS", "descripcion": "Creditos de consumo", "nivel": 1, "tipo_fila": "Detalle", "orden": 2},
                {"seccion_id": "SEC-01", "codigo_fila": "PROV", "descripcion": "Provision", "nivel": 1, "tipo_fila": "Detalle", "orden": 3},
                {"seccion_id": "SEC-01", "codigo_fila": "SUB", "descripcion": "Subtotal", "nivel": 1, "tipo_fila": "Subtotal", "orden": 4, "negrita": 1, "calculo_automatico": 1, "formula_filas": "+COM,+CONS,-PROV"},
            ],
            celdas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VIG", "valor_numero": 100, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VENC", "valor_numero": 20, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "CONS", "codigo_columna": "VIG", "valor_numero": 50, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "CONS", "codigo_columna": "VENC", "valor_numero": 10, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "PROV", "codigo_columna": "VIG", "valor_numero": 5, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "PROV", "codigo_columna": "VENC", "valor_numero": 2, "formato_numero": "Moneda"},
            ],
        )

        sections = nota.get_structured_sections()
        rows = {row["codigo_fila"]: row for row in sections[0]["filas"]}
        columns = [column.codigo_columna for column in sections[0]["columnas"]]

        def value(row_code, column_code):
            idx = columns.index(column_code)
            return rows[row_code]["celdas"][idx]["valor_numero"]

        self.assertEqual(value("COM", "TOT"), 120)
        self.assertEqual(value("CONS", "TOT"), 60)
        self.assertEqual(value("PROV", "TOT"), 7)
        self.assertEqual(value("SUB", "VIG"), 145)
        self.assertEqual(value("SUB", "VENC"), 28)
        self.assertEqual(value("SUB", "TOT"), 173)


    def test_nota_agrupa_columnas_por_grupo_columna(self):
        nota = self._crear_nota(
            "10",
            contenido_narrativo="Resumen comparativo por anio.",
            secciones_estructuradas=[
                {
                    "seccion_id": "SEC-01",
                    "titulo_seccion": "Cartera de creditos",
                    "tipo_seccion": "Tabla",
                    "orden": 1,
                }
            ],
            columnas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_columna": "VIG_2023", "etiqueta": "Vigentes", "grupo_columna": "31 diciembre 2023", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 1},
                {"seccion_id": "SEC-01", "codigo_columna": "VENC_2023", "etiqueta": "Vencidos", "grupo_columna": "31 diciembre 2023", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 2},
                {"seccion_id": "SEC-01", "codigo_columna": "TOT_2023", "etiqueta": "Total", "grupo_columna": "31 diciembre 2023", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 3},
                {"seccion_id": "SEC-01", "codigo_columna": "VIG_2022", "etiqueta": "Vigentes", "grupo_columna": "31 diciembre 2022", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 4},
                {"seccion_id": "SEC-01", "codigo_columna": "VENC_2022", "etiqueta": "Vencidos", "grupo_columna": "31 diciembre 2022", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 5},
                {"seccion_id": "SEC-01", "codigo_columna": "TOT_2022", "etiqueta": "Total", "grupo_columna": "31 diciembre 2022", "tipo_dato": "Moneda", "alineacion": "Right", "orden": 6},
            ],
            filas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "descripcion": "Creditos comerciales", "nivel": 1, "tipo_fila": "Detalle", "orden": 1},
            ],
            celdas_tabulares=[
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VIG_2023", "valor_numero": 100, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VENC_2023", "valor_numero": 20, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "TOT_2023", "valor_numero": 120, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VIG_2022", "valor_numero": 80, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "VENC_2022", "valor_numero": 15, "formato_numero": "Moneda"},
                {"seccion_id": "SEC-01", "codigo_fila": "COM", "codigo_columna": "TOT_2022", "valor_numero": 95, "formato_numero": "Moneda"},
            ],
        )

        sections = nota.get_structured_sections()
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["tiene_grupos_columnas"], 1)
        self.assertEqual(len(sections[0]["grupos_columnas"]), 2)
        self.assertEqual(sections[0]["grupos_columnas"][0]["label"], "31 diciembre 2023")
        self.assertEqual(sections[0]["grupos_columnas"][0]["span"], 3)
        self.assertEqual(sections[0]["grupos_columnas"][1]["label"], "31 diciembre 2022")
        self.assertEqual(sections[0]["grupos_columnas"][1]["span"], 3)
