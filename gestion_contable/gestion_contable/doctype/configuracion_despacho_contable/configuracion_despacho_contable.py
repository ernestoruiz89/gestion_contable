# Copyright (c) 2024, ernestoruiz89 and contributors
# For license information, please see license.txt

import random
from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate
from dateutil.relativedelta import relativedelta

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company

DUMMY_TOOLS_SITE_CONFIG_KEY = "gestion_contable_enable_destructive_dummy_tools"
DUMMY_TASK_NOTE = "Tarea generada automaticamente."
DUMMY_TASK_NOTE_FILTER = "%generada autom%"


class ConfiguracionDespachoContable(Document):
    pass


EMPRESAS = [
    ("Grupo Comercial del Valle SA", "J0310000012345"),
    ("Distribuidora Industrial del Norte SA", "J0310000023456"),
    ("Textiles y Confecciones Leon SA", "J0310000034567"),
    ("Agroexportadora del Pacifico SA", "J0310000045678"),
    ("Construcciones y Proyectos Managua SA", "J0310000056789"),
    ("Alimentos y Bebidas Santa Fe SA", "J0310000067890"),
    ("Logistica Integral Chinandega SA", "J0310000078901"),
    ("Soluciones Tecnologicas Granada SA", "J0310000089012"),
    ("Inmobiliaria Residencial Masaya SA", "J0310000090123"),
    ("Farmaceutica del Centro SA", "J0310000001234"),
    ("Servicios Automotrices Esteli SA", "J0310000012346"),
    ("Importadora y Exportadora Corinto SA", "J0310000023457"),
    ("Plasticos y Empaques Matagalpa SA", "J0310000034568"),
    ("Consultoria Empresarial Jinotepe SA", "J0310000045679"),
    ("Energias Renovables del Caribe SA", "J0310000056780"),
]

USUARIOS = [
    ("ana.martinez@despacho.com", "Ana", "Martinez", "Auxiliar Contable del Despacho"),
    ("carlos.reyes@despacho.com", "Carlos", "Reyes", "Auxiliar Contable del Despacho"),
    ("laura.gonzalez@despacho.com", "Laura", "Gonzalez", "Auxiliar Contable del Despacho"),
    ("miguel.hernandez@despacho.com", "Miguel", "Hernandez", "Auxiliar Contable del Despacho"),
    ("sofia.lopez@despacho.com", "Sofia", "Lopez", "Auxiliar Contable del Despacho"),
    ("roberto.castillo@despacho.com", "Roberto", "Castillo", "Contador del Despacho"),
    ("patricia.navarro@despacho.com", "Patricia", "Navarro", "Contador del Despacho"),
]


@frappe.whitelist()
def get_dummy_tools_status():
    enabled = is_dummy_tools_enabled()
    return {
        "enabled": enabled,
        "site_config_key": DUMMY_TOOLS_SITE_CONFIG_KEY,
        "message": (
            "Herramientas dummy habilitadas solo para desarrollo."
            if enabled
            else "Herramientas dummy deshabilitadas por defecto."
        ),
    }


@frappe.whitelist()
def generar_datos_dummy():
    _ensure_dummy_tools_enabled()

    frappe.publish_realtime("msgprint", dict(message="Iniciando creacion de usuarios...", title="Progreso"))
    crear_usuarios()

    frappe.publish_realtime("msgprint", dict(message="Creando clientes...", title="Progreso"))
    crear_clientes()

    frappe.publish_realtime("msgprint", dict(message="Generando periodos contables...", title="Progreso"))
    crear_periodos_contables()

    frappe.publish_realtime(
        "msgprint",
        dict(message="Creando tareas y comunicaciones demo...", title="Progreso"),
    )
    crear_tareas_y_comunicaciones()

    frappe.db.commit()
    return True


@frappe.whitelist()
def limpiar_datos_dummy():
    _ensure_dummy_tools_enabled()

    clientes_dummy = obtener_clientes_dummy()

    frappe.publish_realtime("msgprint", dict(message="Eliminando comunicaciones demo...", title="Limpieza"))
    tareas_demo = frappe.get_all(
        "Task",
        filters={
            "cliente": ["in", clientes_dummy or [""]],
            "description": ["like", DUMMY_TASK_NOTE_FILTER],
        },
        pluck="name",
    )
    for tarea_name in tareas_demo:
        comms = frappe.get_all(
            "Communication",
            filters={"reference_doctype": "Task", "reference_name": tarea_name},
            pluck="name",
        )
        for comm in comms:
            frappe.delete_doc("Communication", comm, ignore_permissions=True, force=True)

    frappe.publish_realtime("msgprint", dict(message="Eliminando tareas demo...", title="Limpieza"))
    for tarea_name in tareas_demo:
        frappe.delete_doc("Task", tarea_name, ignore_permissions=True, force=True)

    frappe.publish_realtime("msgprint", dict(message="Eliminando periodos demo...", title="Limpieza"))
    periodos = frappe.get_all(
        "Periodo Contable",
        filters={"cliente": ["in", clientes_dummy or [""]]},
        pluck="name",
    )
    for periodo in periodos:
        frappe.delete_doc("Periodo Contable", periodo, ignore_permissions=True, force=True)

    frappe.publish_realtime("msgprint", dict(message="Eliminando clientes contables demo...", title="Limpieza"))
    for empresa, _ in EMPRESAS:
        cliente_name = frappe.db.get_value("Cliente Contable", {"customer": empresa}, "name")
        if cliente_name:
            frappe.delete_doc("Cliente Contable", cliente_name, ignore_permissions=True, force=True)

    frappe.publish_realtime("msgprint", dict(message="Eliminando customers demo...", title="Limpieza"))
    for empresa, _ in EMPRESAS:
        if frappe.db.exists("Customer", empresa):
            frappe.delete_doc("Customer", empresa, ignore_permissions=True, force=True)

    frappe.publish_realtime("msgprint", dict(message="Eliminando usuarios demo...", title="Limpieza"))
    for email, _, _, _ in USUARIOS:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, ignore_permissions=True, force=True)

    frappe.db.commit()
    return True


def is_dummy_tools_enabled():
    return bool(cint(frappe.conf.get(DUMMY_TOOLS_SITE_CONFIG_KEY) or 0))


def _ensure_dummy_tools_enabled():
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Solo el usuario Administrator puede ejecutar estas utilidades dummy."),
            frappe.PermissionError,
        )

    if is_dummy_tools_enabled():
        return

    frappe.throw(
        _(
            "Las utilidades dummy estan deshabilitadas. "
            "Para habilitarlas temporalmente define <code>{0}: 1</code> en <code>site_config.json</code> y recarga el sitio."
        ).format(DUMMY_TOOLS_SITE_CONFIG_KEY),
        frappe.PermissionError,
    )


def obtener_clientes_dummy():
    customers_dummy = [empresa for empresa, _ in EMPRESAS]
    if not customers_dummy:
        return []
    return frappe.get_all(
        "Cliente Contable",
        filters={"customer": ["in", customers_dummy]},
        pluck="name",
    )


def crear_usuarios():
    for email, first_name, last_name, rol in USUARIOS:
        if frappe.db.exists("User", email):
            continue
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "send_welcome_email": 0,
                "roles": [{"role": rol}],
            }
        )
        user.insert(ignore_permissions=True)


def crear_clientes():
    dominios = [
        "grupovalle.com.ni",
        "disinorte.com.ni",
        "textilesleon.com.ni",
        "agropacifico.com.ni",
        "cpmanagua.com.ni",
        "santafe-alimentos.com.ni",
        "logichinandega.com.ni",
        "soltecgranada.com.ni",
        "inmomasaya.com.ni",
        "farmacentro.com.ni",
        "serviautosteli.com.ni",
        "imexcorinto.com.ni",
        "plastmatagalpa.com.ni",
        "cejinotepe.com.ni",
        "enercaribe.com.ni",
    ]
    telefonos = [
        "22701234",
        "23151234",
        "23111234",
        "25631234",
        "22701235",
        "22981234",
        "23411234",
        "25521234",
        "25221234",
        "22551234",
        "27131234",
        "23421234",
        "27721234",
        "24121234",
        "28721234",
    ]
    customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
    territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"

    for idx, (empresa, ruc) in enumerate(EMPRESAS):
        if not frappe.db.exists("Customer", empresa):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": empresa,
                    "customer_group": customer_group,
                    "customer_type": "Company",
                    "territory": territory,
                    "tax_id": ruc,
                }
            )
            customer.insert(ignore_permissions=True)

        if not frappe.db.exists("Cliente Contable", {"customer": empresa}):
            cliente_contable = frappe.get_doc(
                {
                    "doctype": "Cliente Contable",
                    "customer": empresa,
                    "estado": "Activo",
                    "frecuencia_de_cierre": "Mensual",
                    "telefono": telefonos[idx],
                    "correo_electronico": f"contabilidad@{dominios[idx]}",
                }
            )
            cliente_contable.insert(ignore_permissions=True)


def crear_periodos_contables():
    hoy = date.today()
    mes_actual = hoy.replace(day=1)
    company = get_default_company()
    if not company:
        frappe.throw("Configura una Company por defecto antes de generar periodos contables demo.")

    meses_es = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    clientes = obtener_clientes_dummy()

    for cliente in clientes:
        for i in range(24):
            mes_target = mes_actual - relativedelta(months=i)
            estado = "Abierto" if i == 0 else "Cerrado"
            filtros = {
                "cliente": cliente,
                "company": company,
                "anio": mes_target.year,
                "mes": meses_es[mes_target.month - 1],
            }

            if frappe.db.exists("Periodo Contable", filtros):
                continue

            periodo = frappe.get_doc(
                {
                    "doctype": "Periodo Contable",
                    "cliente": cliente,
                    "company": company,
                    "anio": mes_target.year,
                    "mes": meses_es[mes_target.month - 1],
                    "estado": estado,
                }
            )
            periodo.insert(ignore_permissions=True)


def crear_tareas_y_comunicaciones():
    clientes = obtener_clientes_dummy()
    periodos = frappe.get_all(
        "Periodo Contable",
        filters={"cliente": ["in", clientes or [""]]},
        fields=["name", "cliente", "company", "estado", "fecha_de_inicio"],
    )
    auxiliares = [user[0] for user in USUARIOS if user[3] == "Auxiliar Contable del Despacho"]

    tipos_tarea = [
        "Impuestos",
        "Nomina",
        "Cierre Contable",
        "Facturacion",
        "Conciliacion Bancaria",
        "Consultoria",
    ]

    titulos_tarea = {
        "Impuestos": [
            "Declaracion mensual IR",
            "Anticipo IR mensual",
            "Declaracion de IVA",
            "Retenciones en la fuente",
            "Pago del IMI",
        ],
        "Nomina": [
            "Calculo de nomina quincenal",
            "Aportes patronales INSS",
            "Provision de decimo tercer mes",
            "Liquidaciones finales de personal",
        ],
        "Cierre Contable": [
            "Poliza de cierre mensual",
            "Depreciacion de activos fijos",
            "Ajustes de cierre del periodo",
            "Balanza de comprobacion",
        ],
        "Facturacion": [
            "Revision de facturas emitidas",
            "Control de secuencia de facturas DGI",
            "Conciliacion de ventas vs facturacion",
        ],
        "Conciliacion Bancaria": [
            "Conciliacion cuenta cordobas",
            "Conciliacion cuenta dolares",
            "Identificacion de partidas en transito",
        ],
        "Consultoria": [
            "Asesoria en planeacion tributaria",
            "Revision de contratos laborales",
            "Preparacion para auditoria DGI",
        ],
    }

    mensajes_comunicacion = [
        "He revisado los documentos, todo parece en orden.",
        "Falta la factura de insumos, por favor solicitar al cliente.",
        "El pago de impuestos ante la DGI ya fue procesado.",
        "Conciliacion terminada con cero diferencias.",
        "Se envio el requerimiento al cliente por correo.",
        "El cliente confirmo la recepcion de la documentacion.",
        "Pendiente revisar las polizas de cierre.",
        "Se detecto una diferencia en la conciliacion, verificar con el banco.",
        "La DGI ya acuso recibo de la declaracion mensual.",
        "El cliente solicita reunion para revisar estados financieros.",
    ]

    for cliente in clientes:
        periodos_cliente = [periodo for periodo in periodos if periodo.cliente == cliente]
        for periodo in periodos_cliente:
            num_tareas = random.randint(3, 7)
            tipos_asignados = random.sample(tipos_tarea, min(num_tareas, len(tipos_tarea)))

            for tipo in tipos_asignados:
                titulo_base = random.choice(titulos_tarea[tipo])
                titulo = f"{titulo_base} - {cliente} - {periodo.name}"
                expected_name = f"{tipo} - {cliente} - {periodo.name}"
                if frappe.db.exists("Task", {"subject": titulo}):
                    continue

                if periodo.estado == "Cerrado":
                    estado_tarea = "Completed"
                else:
                    estado_tarea = random.choice(["Open", "Working", "Pending Review"])

                asignado = random.choice(auxiliares) if auxiliares else None
                fecha_inicio_date = periodo.fecha_de_inicio
                if isinstance(fecha_inicio_date, str):
                    fecha_inicio_date = getdate(fecha_inicio_date)
                fecha_vencimiento = fecha_inicio_date + relativedelta(days=random.randint(15, 28))

                tarea = frappe.get_doc(
                    {
                        "doctype": "Task",
                        "subject": titulo,
                        "cliente": cliente,
                        "periodo": periodo.name,
                        "tipo_de_tarea": tipo,
                        "status": estado_tarea,
                        "exp_end_date": fecha_vencimiento,
                        "description": DUMMY_TASK_NOTE,
                    }
                )
                if asignado:
                    tarea.append("assignees", {"user": asignado})
                tarea.flags.ignore_validate = True
                tarea.insert(ignore_permissions=True)

                if random.random() > 0.6:
                    mensaje = random.choice(mensajes_comunicacion)
                    comunicacion = frappe.get_doc(
                        {
                            "doctype": "Communication",
                            "communication_type": "Communication",
                            "communication_medium": "Other",
                            "comment_type": "Comment",
                            "subject": f"Nota: {titulo_base}",
                            "reference_doctype": "Task",
                            "reference_name": tarea.name,
                            "content": f"<p>{mensaje}</p>",
                            "sender": asignado if asignado else "Administrator",
                        }
                    )
                    comunicacion.flags.ignore_validate = True
                    comunicacion.insert(ignore_permissions=True)
