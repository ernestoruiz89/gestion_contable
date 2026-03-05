# Copyright (c) 2024, ernestoruiz89 and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import random
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class ConfiguracionDespachoContable(Document):
	pass

# ── Catálogos de nombres realistas (Nicaragua) ──────────────────

EMPRESAS = [
	("Grupo Comercial del Valle SA", "J0310000012345"),
	("Distribuidora Industrial del Norte SA", "J0310000023456"),
	("Textiles y Confecciones León SA", "J0310000034567"),
	("Agroexportadora del Pacífico SA", "J0310000045678"),
	("Construcciones y Proyectos Managua SA", "J0310000056789"),
	("Alimentos y Bebidas Santa Fe SA", "J0310000067890"),
	("Logística Integral Chinandega SA", "J0310000078901"),
	("Soluciones Tecnológicas Granada SA", "J0310000089012"),
	("Inmobiliaria Residencial Masaya SA", "J0310000090123"),
	("Farmacéutica del Centro SA", "J0310000001234"),
	("Servicios Automotrices Estelí SA", "J0310000012346"),
	("Importadora y Exportadora Corinto SA", "J0310000023457"),
	("Plásticos y Empaques Matagalpa SA", "J0310000034568"),
	("Consultoría Empresarial Jinotepe SA", "J0310000045679"),
	("Energías Renovables del Caribe SA", "J0310000056780"),
]

USUARIOS = [
	# (email, first_name, last_name, rol)
	("ana.martinez@despacho.com", "Ana", "Martínez", "Auxiliar Contable del Despacho"),
	("carlos.reyes@despacho.com", "Carlos", "Reyes", "Auxiliar Contable del Despacho"),
	("laura.gonzalez@despacho.com", "Laura", "González", "Auxiliar Contable del Despacho"),
	("miguel.hernandez@despacho.com", "Miguel", "Hernández", "Auxiliar Contable del Despacho"),
	("sofia.lopez@despacho.com", "Sofía", "López", "Auxiliar Contable del Despacho"),
	("roberto.castillo@despacho.com", "Roberto", "Castillo", "Contador del Despacho"),
	("patricia.navarro@despacho.com", "Patricia", "Navarro", "Contador del Despacho"),
]

# ── Generación ──────────────────────────────────────────────────

@frappe.whitelist()
def generar_datos_dummy():
	if frappe.session.user != "Administrator":
		frappe.throw("Solo el usuario Administrator puede ejecutar esta acción.")

	frappe.publish_realtime("msgprint", dict(message="Iniciando creación de usuarios...", title="Progreso"))
	crear_usuarios()

	frappe.publish_realtime("msgprint", dict(message="Creando clientes...", title="Progreso"))
	crear_clientes()

	frappe.publish_realtime("msgprint", dict(message="Generando periodos contables...", title="Progreso"))
	crear_periodos_contables()

	frappe.publish_realtime("msgprint", dict(message="Creando tareas y comunicaciones (puede tardar un momento)...", title="Progreso"))
	crear_tareas_y_comunicaciones()

	frappe.db.commit()
	return True

# ── Limpieza ────────────────────────────────────────────────────

@frappe.whitelist()
def limpiar_datos_dummy():
	if frappe.session.user != "Administrator":
		frappe.throw("Solo el usuario Administrator puede ejecutar esta acción.")

	# 1. Eliminar comunicaciones vinculadas a tareas generadas
	frappe.publish_realtime("msgprint", dict(message="Eliminando comunicaciones...", title="Limpieza"))
	tareas_demo = frappe.get_all("Tarea Contable",
		filters={"notas": ("like", "%generada automáticamente%")},
		pluck="name"
	)
	for tarea_name in tareas_demo:
		comms = frappe.get_all("Communication",
			filters={"reference_doctype": "Tarea Contable", "reference_name": tarea_name},
			pluck="name"
		)
		for comm in comms:
			frappe.delete_doc("Communication", comm, ignore_permissions=True, force=True)

	# 2. Eliminar tareas
	frappe.publish_realtime("msgprint", dict(message="Eliminando tareas...", title="Limpieza"))
	for tarea_name in tareas_demo:
		frappe.delete_doc("Tarea Contable", tarea_name, ignore_permissions=True, force=True)

	# 3. Eliminar periodos contables
	frappe.publish_realtime("msgprint", dict(message="Eliminando periodos...", title="Limpieza"))
	periodos = frappe.get_all("Periodo Contable", pluck="name")
	for periodo in periodos:
		frappe.delete_doc("Periodo Contable", periodo, ignore_permissions=True, force=True)

	# 4. Eliminar clientes contables
	frappe.publish_realtime("msgprint", dict(message="Eliminando clientes contables...", title="Limpieza"))
	for empresa, _ in EMPRESAS:
		if frappe.db.exists("Cliente Contable", {"customer": empresa}):
			doc_name = frappe.db.get_value("Cliente Contable", {"customer": empresa})
			frappe.delete_doc("Cliente Contable", doc_name, ignore_permissions=True, force=True)

	# 5. Eliminar customers
	frappe.publish_realtime("msgprint", dict(message="Eliminando customers...", title="Limpieza"))
	for empresa, _ in EMPRESAS:
		if frappe.db.exists("Customer", empresa):
			frappe.delete_doc("Customer", empresa, ignore_permissions=True, force=True)

	# 6. Eliminar usuarios
	frappe.publish_realtime("msgprint", dict(message="Eliminando usuarios...", title="Limpieza"))
	for email, _, _, _ in USUARIOS:
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, ignore_permissions=True, force=True)

	frappe.db.commit()
	return True

# ── Funciones auxiliares ────────────────────────────────────────

def crear_usuarios():
	for email, first_name, last_name, rol in USUARIOS:
		if not frappe.db.exists("User", email):
			user = frappe.get_doc({
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"send_welcome_email": 0,
				"roles": [{"role": rol}]
			})
			user.insert(ignore_permissions=True)

def crear_clientes():
	dominios = [
		"grupovalle.com.ni", "disinorte.com.ni", "textilesleon.com.ni", "agropacifico.com.ni",
		"cpmanagua.com.ni", "santafe-alimentos.com.ni", "logichinandega.com.ni", "soltecgranada.com.ni",
		"inmomasaya.com.ni", "farmacentro.com.ni", "serviautosteli.com.ni", "imexcorinto.com.ni",
		"plastmatagalpa.com.ni", "cejinotepe.com.ni", "enercaribe.com.ni",
	]
	telefonos = [
		"22701234", "23151234", "23111234", "25631234", "22701235",
		"22981234", "23411234", "25521234", "25221234", "22551234",
		"27131234", "23421234", "27721234", "24121234", "28721234",
	]

	for idx, (empresa, ruc) in enumerate(EMPRESAS):
		# Crear Customer base si no existe
		if not frappe.db.exists("Customer", empresa):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": empresa,
				"customer_group": "Commercial",
				"customer_type": "Company",
				"territory": "All Territories",
				"tax_id": ruc
			})
			customer.insert(ignore_permissions=True)

		# Crear Cliente Contable
		if not frappe.db.exists("Cliente Contable", {"customer": empresa}):
			cliente_contable = frappe.get_doc({
				"doctype": "Cliente Contable",
				"customer": empresa,
				"estado": "Activo",
				"frecuencia_de_cierre": "Mensual",
				"telefono": telefonos[idx],
				"correo_electronico": f"contabilidad@{dominios[idx]}"
			})
			cliente_contable.insert(ignore_permissions=True)

def crear_periodos_contables():
	hoy = date.today()
	mes_actual = hoy.replace(day=1)

	meses_es = [
		"Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
		"Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
	]

	for i in range(24):
		mes_target = mes_actual - relativedelta(months=i)
		nombre_periodo = f"{meses_es[mes_target.month - 1]} {mes_target.year}"

		if not frappe.db.exists("Periodo Contable", nombre_periodo):
			estado = "Abierto" if i == 0 else "Cerrado"
			periodo = frappe.get_doc({
				"doctype": "Periodo Contable",
				"anio": mes_target.year,
				"mes": meses_es[mes_target.month - 1],
				"estado": estado,
			})
			periodo.insert(ignore_permissions=True)

def crear_tareas_y_comunicaciones():
	clientes = frappe.get_all("Cliente Contable", pluck="name")
	periodos = frappe.get_all("Periodo Contable", fields=["name", "estado", "fecha_de_inicio"])
	auxiliares = [u[0] for u in USUARIOS if u[3] == "Auxiliar Contable del Despacho"]

	tipos_tarea = [
		"Impuestos", "Nómina", "Cierre Contable",
		"Facturación", "Conciliación Bancaria", "Consultoría"
	]

	titulos_tarea = {
		"Impuestos": [
			"Declaración mensual IR",
			"Anticipo IR mensual",
			"Declaración de IVA",
			"Retenciones en la fuente",
			"Pago del IMI (Impuesto Municipal)",
		],
		"Nómina": [
			"Cálculo de nómina quincenal",
			"Aportes patronales INSS",
			"Provisión de décimo tercer mes",
			"Liquidaciones finales de personal",
		],
		"Cierre Contable": [
			"Póliza de cierre mensual",
			"Depreciación de activos fijos",
			"Ajustes de cierre del periodo",
			"Balanza de comprobación",
		],
		"Facturación": [
			"Revisión de facturas emitidas",
			"Control de secuencia de facturas DGI",
			"Conciliación de ventas vs facturación",
		],
		"Conciliación Bancaria": [
			"Conciliación cuenta córdobas",
			"Conciliación cuenta dólares",
			"Identificación de partidas en tránsito",
		],
		"Consultoría": [
			"Asesoría en planeación tributaria",
			"Revisión de contratos laborales",
			"Preparación para auditoría DGI",
		],
	}

	mensajes_comunicacion = [
		"He revisado los documentos, todo parece en orden.",
		"Falta la factura de insumos, por favor solicitar al cliente.",
		"El pago de impuestos ante la DGI ya fue procesado.",
		"Conciliación terminada con cero diferencias.",
		"Se envió el requerimiento al cliente por correo.",
		"El cliente confirmó la recepción de la documentación.",
		"Pendiente revisar las pólizas de cierre.",
		"Se detectó una diferencia en la conciliación, verificar con el banco.",
		"La DGI ya acusó recibo de la declaración mensual.",
		"El cliente solicita reunión para revisar estados financieros.",
	]

	for cliente in clientes:
		for periodo in periodos:
			num_tareas = random.randint(4, 10)

			for i in range(num_tareas):
				tipo = random.choice(tipos_tarea)
				titulo_base = random.choice(titulos_tarea[tipo])
				titulo = f"{titulo_base} - {cliente} - {periodo.name} - {i}"

				if frappe.db.exists("Tarea Contable", {"titulo": titulo}):
					continue

				if periodo.estado == "Cerrado":
					estado_tarea = "Completada"
				else:
					estado_tarea = random.choice(["Pendiente", "En Proceso", "En Revisión"])

				asignado = random.choice(auxiliares) if auxiliares else None

				dias_vencimiento = random.randint(15, 28)
				fecha_inicio_date = periodo.fecha_de_inicio
				if isinstance(fecha_inicio_date, str):
					from frappe.utils import getdate
					fecha_inicio_date = getdate(fecha_inicio_date)
				fecha_vencimiento = fecha_inicio_date + relativedelta(days=dias_vencimiento)

				tarea = frappe.get_doc({
					"doctype": "Tarea Contable",
					"titulo": titulo,
					"cliente": cliente,
					"periodo": periodo.name,
					"tipo_de_tarea": tipo,
					"estado": estado_tarea,
					"fecha_de_vencimiento": fecha_vencimiento,
					"asignado_a": asignado,
					"notas": "Tarea generada automáticamente."
				})
				tarea.flags.ignore_validate = True
				tarea.insert(ignore_permissions=True)

				# Crear comunicación aleatoria
				if random.random() > 0.6:
					mensaje = random.choice(mensajes_comunicacion)
					comunicacion = frappe.get_doc({
						"doctype": "Communication",
						"communication_type": "Communication",
						"communication_medium": "Other",
						"comment_type": "Comment",
						"subject": f"Nota: {titulo_base}",
						"reference_doctype": "Tarea Contable",
						"reference_name": tarea.name,
						"content": f"<p>{mensaje}</p>",
						"sender": asignado if asignado else "Administrator"
					})
					comunicacion.flags.ignore_validate = True
					comunicacion.insert(ignore_permissions=True)
