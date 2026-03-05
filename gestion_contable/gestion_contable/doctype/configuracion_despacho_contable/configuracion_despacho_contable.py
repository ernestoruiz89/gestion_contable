# Copyright (c) 2024, ernestoruiz89 and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import random
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class ConfiguracionDespachoContable(Document):
	pass

@frappe.whitelist()
def generar_datos_dummy():
	if frappe.session.user != "Administrator":
		frappe.throw("Solo el usuario Administrator puede ejecutar esta acción.")
	
	frappe.publish_realtime("msgprint", dict(message="Iniciando creación de usuarios...", title="Progreso"))
	crear_usuarios_dummy()
	
	frappe.publish_realtime("msgprint", dict(message="Creando clientes...", title="Progreso"))
	crear_clientes_dummy()
	
	frappe.publish_realtime("msgprint", dict(message="Generando periodos contables...", title="Progreso"))
	crear_periodos_contables()
	
	frappe.publish_realtime("msgprint", dict(message="Creando tareas y comunicaciones (puede tardar un momento)...", title="Progreso"))
	crear_tareas_y_comunicaciones()
	
	frappe.db.commit()
	return True

def crear_usuarios_dummy():
	# 5 Auxiliares y 2 Contadores
	roles = {
		"Auxiliar Contable del Despacho": 5,
		"Contador del Despacho": 2
	}
	
	for rol, cantidad in roles.items():
		for i in range(1, cantidad + 1):
			email = f"{rol.split()[0].lower()}dummy{i}@despacho.com"
			if not frappe.db.exists("User", email):
				user = frappe.get_doc({
					"doctype": "User",
					"email": email,
					"first_name": f"{rol.split()[0]} {i}",
					"send_welcome_email": 0,
					"roles": [{"role": rol}]
				})
				user.insert(ignore_permissions=True)

def crear_clientes_dummy():
	# 15 Clientes
	for i in range(1, 16):
		customer_name = f"Cliente Dummy {i} SA de CV"
		
		# Crear Customer base si no existe
		if not frappe.db.exists("Customer", customer_name):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_group": "Commercial",  # Standard Frappe group
				"customer_type": "Company",
				"territory": "All Territories",
				"tax_id": f"DUMMY{1000+i}XXX"
			})
			customer.insert(ignore_permissions=True)
		
		# Crear Cliente Contable
		if not frappe.db.exists("Cliente Contable", {"customer": customer_name}):
			cliente_contable = frappe.get_doc({
				"doctype": "Cliente Contable",
				"customer": customer_name,
				"estado": "Activo",
				"frecuencia_de_cierre": "Mensual",
				"telefono": f"555000{i:04d}",
				"correo_electronico": f"contacto@cliente{i}.com"
			})
			cliente_contable.insert(ignore_permissions=True)

def crear_periodos_contables():
	# 24 meses hacia atrás
	hoy = date.today()
	# Ir al primer dia del mes actual
	mes_actual = hoy.replace(day=1)
	
	meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
	
	for i in range(24):
		mes_target = mes_actual - relativedelta(months=i)
		nombre_periodo = f"{meses_es[mes_target.month - 1]} {mes_target.year}"
		
		# Calcular ultimo dia del mes
		siguiente_mes = mes_target + relativedelta(months=1)
		ultimo_dia = siguiente_mes - relativedelta(days=1)
		
		if not frappe.db.exists("Periodo Contable", nombre_periodo):
			estado = "Abierto" if i == 0 else "Cerrado"
			periodo = frappe.get_doc({
				"doctype": "Periodo Contable",
				"nombre_del_periodo": nombre_periodo,
				"estado": estado,
				"fecha_de_inicio": mes_target,
				"fecha_de_fin": ultimo_dia
			})
			periodo.insert(ignore_permissions=True)

def crear_tareas_y_comunicaciones():
	clientes = frappe.get_all("Cliente Contable", pluck="name")
	periodos = frappe.get_all("Periodo Contable", fields=["name", "estado", "fecha_de_inicio"])
	auxiliares = frappe.get_all("User", filters={"name": ("like", "auxiliar%@despacho.com")}, pluck="name")
	
	tipos_tarea = ["Impuestos", "Nómina", "Cierre Contable", "Facturación", "Conciliación Bancaria", "Consultoría"]
	
	for cliente in clientes:
		for periodo in periodos:
			# 4 a 10 tareas por cliente por periodo
			num_tareas = random.randint(4, 10)
			
			for i in range(num_tareas):
				tipo = random.choice(tipos_tarea)
				titulo = f"{tipo} - {cliente} - {periodo.name} - {i}" # Added suffix i to minimize collisions
				
				# Si ya existe, saltar
				if frappe.db.exists("Tarea Contable", {"titulo": titulo}):
					continue
				
				# Estado de la tarea depende del estado del periodo
				if periodo.estado == "Cerrado":
					estado_tarea = "Completada"
				else:
					estado_tarea = random.choice(["Pendiente", "En Proceso", "En Revisión"])
					
				asignado = random.choice(auxiliares) if auxiliares else None
				
				# Fecha de vencimiento a mitades/fines de ese mes
				dias_vencimiento = random.randint(15, 28)
				
				# Safe parsing: Make sure it's a date before relativedelta addition
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
					"notas": f"Tarea generada automáticamente para pruebas de carga."
				})
				tarea.flags.ignore_validate = True
				tarea.insert(ignore_permissions=True)
				
				# Crear algunas comunicaciones
				if random.random() > 0.6:  # 40% de chance de tener comunicación
					mensaje = random.choice([
						"He revisado los documentos, todo parece en orden.",
						"Falta la factura de papelería, por favor solicitar al cliente.",
						"El pago de impuestos ya fue procesado.",
						"Conciliación terminada con cero diferencias."
					])
					comunicacion = frappe.get_doc({
						"doctype": "Communication",
						"communication_type": "Comment",
						"communication_medium": "System",
						"comment_type": "Comment",
						"reference_doctype": "Tarea Contable",
						"reference_name": tarea.name,
						"content": f"<p>{mensaje}</p>",
						"sender": asignado if asignado else "Administrator"
					})
					comunicacion.insert(ignore_permissions=True)
