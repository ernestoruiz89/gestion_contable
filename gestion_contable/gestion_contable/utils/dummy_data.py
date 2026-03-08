from __future__ import annotations

import hashlib
import json
import random
from contextlib import contextmanager
from datetime import date
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, now_datetime, nowdate
from frappe.utils.file_manager import save_file

from gestion_contable.gestion_contable.doctype.encargo_contable.encargo_contable import (
    crear_payment_entry_encargo as crear_payment_entry_encargo_api,
    generar_factura_venta as generar_factura_encargo,
)
from gestion_contable.gestion_contable.doctype.informe_final_auditoria.informe_final_auditoria import (
    TIPO_DICTAMEN_AUDITORIA,
    TIPO_INFORME_FINAL_GENERAL,
    emitir_informe_final_auditoria,
    generar_informe_final_desde_expediente,
)
from gestion_contable.gestion_contable.doctype.paquete_estados_financieros_cliente.paquete_estados_financieros_cliente import (
    emitir_paquete_estados_financieros,
)
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company
from gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente import (
    cerrar_requerimiento_cliente,
    marcar_requerimiento_enviado,
)
from gestion_contable.gestion_contable.portal.cliente import (
    registrar_carga_entregable_portal,
    registrar_mensaje_portal,
)

DEMO_PREFIX = "GC DEMO"
DEMO_USER_DOMAIN = "dummy.gc.local"
PORTAL_PASSWORD = "Revision2026!"
DEMO_FILE_PREFIX = "gc-demo"
MONTH_SPAN = 3
RANDOM_SEED = 20260307

INTERNAL_USERS = {
    "socio": {"email": f"socio@{DEMO_USER_DOMAIN}", "first_name": "Sofia", "last_name": "Quiroz", "roles": ["Socio del Despacho"]},
    "supervisor_1": {"email": f"supervisor.1@{DEMO_USER_DOMAIN}", "first_name": "Marco", "last_name": "Silva", "roles": ["Supervisor del Despacho"]},
    "supervisor_2": {"email": f"supervisor.2@{DEMO_USER_DOMAIN}", "first_name": "Paula", "last_name": "Mendez", "roles": ["Supervisor del Despacho"]},
    "contador_1": {"email": f"contador.1@{DEMO_USER_DOMAIN}", "first_name": "Luis", "last_name": "Rojas", "roles": ["Contador del Despacho"]},
    "contador_2": {"email": f"contador.2@{DEMO_USER_DOMAIN}", "first_name": "Marta", "last_name": "Vega", "roles": ["Contador del Despacho"]},
    "aux_1": {"email": f"auxiliar.1@{DEMO_USER_DOMAIN}", "first_name": "Ana", "last_name": "Lopez", "roles": ["Auxiliar Contable del Despacho"]},
    "aux_2": {"email": f"auxiliar.2@{DEMO_USER_DOMAIN}", "first_name": "Jorge", "last_name": "Perez", "roles": ["Auxiliar Contable del Despacho"]},
    "aux_3": {"email": f"auxiliar.3@{DEMO_USER_DOMAIN}", "first_name": "Carla", "last_name": "Duarte", "roles": ["Auxiliar Contable del Despacho"]},
    "aux_4": {"email": f"auxiliar.4@{DEMO_USER_DOMAIN}", "first_name": "Kevin", "last_name": "Mora", "roles": ["Auxiliar Contable del Despacho"]},
}

CLIENT_DEFINITIONS = [
    {"code": "C01", "customer": f"{DEMO_PREFIX} Comercial Delta SA", "tax_id": "J0310001010001", "segment": "contabilidad"},
    {"code": "C02", "customer": f"{DEMO_PREFIX} Servicios Integrales Norte SA", "tax_id": "J0310001010002", "segment": "contabilidad"},
    {"code": "C03", "customer": f"{DEMO_PREFIX} Agroindustria Pacifica SA", "tax_id": "J0310001010003", "segment": "contabilidad"},
    {"code": "C04", "customer": f"{DEMO_PREFIX} Distribuciones Urbanas SA", "tax_id": "J0310001010004", "segment": "contabilidad"},
    {"code": "C05", "customer": f"{DEMO_PREFIX} Logistica Caribe SA", "tax_id": "J0310001010005", "segment": "contabilidad"},
    {"code": "C06", "customer": f"{DEMO_PREFIX} Manufactura Centro SA", "tax_id": "J0310001010006", "segment": "contabilidad"},
    {"code": "C07", "customer": f"{DEMO_PREFIX} Tecnologia Comercial SA", "tax_id": "J0310001010007", "segment": "contabilidad"},
    {"code": "A01", "customer": f"{DEMO_PREFIX} Auditada Horizonte SA", "tax_id": "J0310001010008", "segment": "auditoria_completa"},
    {"code": "A02", "customer": f"{DEMO_PREFIX} Auditada Gran Via SA", "tax_id": "J0310001010009", "segment": "auditoria_completa"},
    {"code": "A03", "customer": f"{DEMO_PREFIX} Revision Industrial SA", "tax_id": "J0310001010010", "segment": "auditoria_proceso"},
]

SPANISH_MONTHS = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


TASK_TYPE_ALIASES = {
    "Cierre mensual": "Cierre Contable",
    "Cierre Mensual": "Cierre Contable",
    "Cierre contable": "Cierre Contable",
    "Auditoria": "Auditoría",
    "Declaracion DGI": "Declaración DGI",
    "Consultoria": "Consultoría",
}


SERVICE_CATALOG = {
    "Contabilidad": {"service_name": f"{DEMO_PREFIX} - Contabilidad Mensual", "hours_item": "GC-DEMO-HRS-CONT", "fixed_item": "GC-DEMO-FIX-CONT", "tarifa_hora": 35, "honorario_fijo": 850, "costo_interno_hora": 14},
    "Auditoria": {"service_name": f"{DEMO_PREFIX} - Auditoria Financiera", "hours_item": "GC-DEMO-HRS-AUD", "fixed_item": "GC-DEMO-FIX-AUD", "tarifa_hora": 55, "honorario_fijo": 5200, "costo_interno_hora": 22},
    "Trabajo Especial": {"service_name": f"{DEMO_PREFIX} - Trabajo Especial", "hours_item": "GC-DEMO-HRS-ESP", "fixed_item": "GC-DEMO-FIX-ESP", "tarifa_hora": 48, "honorario_fijo": 1800, "costo_interno_hora": 18},
    "Consultoria": {"service_name": f"{DEMO_PREFIX} - Consultoria Financiera", "hours_item": "GC-DEMO-HRS-CON", "fixed_item": "GC-DEMO-FIX-CON", "tarifa_hora": 60, "honorario_fijo": 2400, "costo_interno_hora": 25},
}


def generate_demo_dataset(status_callback=None):
    random.seed(RANDOM_SEED)
    clear_demo_dataset(status_callback=status_callback, commit=False)
    ctx = _load_context()
    _status(status_callback, "Creando catalogos base demo...")
    ctx["services"] = _ensure_service_catalog(ctx)
    _status(status_callback, "Creando usuarios internos demo...")
    ctx["internal_users"] = _ensure_internal_users()
    _status(status_callback, "Creando clientes demo...")
    ctx["clients"] = _ensure_demo_clients(ctx)
    _status(status_callback, "Creando periodos de los ultimos 3 meses...")
    ctx["periods"] = _ensure_demo_periods(ctx)
    _status(status_callback, "Sembrando operaciones de contabilidad...")
    _seed_accounting_clients(ctx)
    _status(status_callback, "Sembrando auditorias completas con portal y EEFF...")
    _seed_complete_audits(ctx)
    _status(status_callback, "Sembrando auditoria en proceso...")
    _seed_in_progress_audit(ctx)
    frappe.db.commit()
    return {
        "ok": True,
        "clients": len(ctx["clients"]),
        "periods": len(ctx["periods"]),
        "services": list(ctx["services"].keys()),
        "message": "Dataset demo realista generado.",
    }


def clear_demo_dataset(status_callback=None, commit=True):
    random.seed(RANDOM_SEED)
    _status(status_callback, "Limpiando dataset demo anterior...")
    cliente_names = _get_demo_client_names()
    customer_names = _get_demo_customer_names()
    _delete_demo_financial_flows(cliente_names)
    _delete_demo_operational_docs(cliente_names)
    _delete_demo_audit_and_eeff(cliente_names)
    _delete_demo_commercial_and_periods(cliente_names)
    _delete_demo_customers(cliente_names, customer_names)
    _delete_demo_users()
    _delete_demo_files()
    if commit:
        frappe.db.commit()
    return {"ok": True, "message": "Dataset demo limpiado."}


def _load_context():
    company = get_default_company() or frappe.db.get_value("Company", {}, "name")
    if not company:
        frappe.throw(_("No existe una Company configurada. Crea o define una compa??a antes de generar la data demo."), title=_("Compania Requerida"))
    currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
    customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
    territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
    item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
    stock_uom = frappe.db.get_value("UOM", {}, "name") or "Nos"
    month_starts = []
    base_month = getdate(nowdate()).replace(day=1)
    for offset in range(MONTH_SPAN - 1, -1, -1):
        month_starts.append(getdate(add_months(base_month, -offset)))
    return {
        "company": company,
        "currency": currency,
        "customer_group": customer_group,
        "territory": territory,
        "item_group": item_group,
        "stock_uom": stock_uom,
        "month_starts": month_starts,
    }


def _ensure_service_catalog(ctx):
    services = {}
    for service_type, data in SERVICE_CATALOG.items():
        hours_item = _ensure_item(data["hours_item"], f"{data['service_name']} - Horas", ctx, is_stock=False)
        fixed_item = _ensure_item(data["fixed_item"], f"{data['service_name']} - Honorario", ctx, is_stock=False)
        payload = {
            "nombre_del_servicio": data["service_name"],
            "tipo_de_servicio": service_type,
            "item_horas": hours_item,
            "item_honorario_fijo": fixed_item,
            "company": ctx["company"],
            "moneda": ctx["currency"],
            "tarifa_hora": data["tarifa_hora"],
            "honorario_fijo": data["honorario_fijo"],
            "costo_interno_hora": data["costo_interno_hora"],
            "descripcion": f"Servicio demo para {service_type.lower()}.",
        }
        if frappe.db.exists("Servicio Contable", data["service_name"]):
            frappe.db.set_value("Servicio Contable", data["service_name"], payload, update_modified=False)
        else:
            frappe.get_doc({"doctype": "Servicio Contable", **payload}).insert(ignore_permissions=True)
        services[service_type] = data["service_name"]
    return services


def _ensure_internal_users():
    result = {}
    for key, data in INTERNAL_USERS.items():
        result[key] = _ensure_user(
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            roles=data["roles"],
            user_type="System User",
            new_password=None,
        )
    return result


def _ensure_demo_clients(ctx):
    clients = {}
    for idx, seed in enumerate(CLIENT_DEFINITIONS, start=1):
        customer_name = seed["customer"]
        portal_email = f"portal.{seed['code'].lower()}@{DEMO_USER_DOMAIN}"
        if not frappe.db.exists("Customer", customer_name):
            frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "customer_group": ctx["customer_group"],
                    "customer_type": "Company",
                    "territory": ctx["territory"],
                    "tax_id": seed["tax_id"],
                }
            ).insert(ignore_permissions=True)
        portal_user = None
        contactos_funcionales = [
            {"nombre_contacto": f"Contacto {seed['code']}", "contacto_rol": "Contabilidad", "email_contacto": f"contabilidad.{seed['code'].lower()}@cliente.demo", "telefono_contacto": f"505-22{idx:02d}100{idx}", "es_principal": 1, "recibe_requerimientos": 1, "activo": 1},
            {"nombre_contacto": f"Cobranza {seed['code']}", "contacto_rol": "Cobranza", "email_contacto": f"cobranza.{seed['code'].lower()}@cliente.demo", "telefono_contacto": f"505-22{idx:02d}200{idx}", "recibe_cobranza": 1, "activo": 1},
        ]
        portal_enabled = seed["segment"] != "contabilidad"
        if portal_enabled:
            portal_user = _ensure_user(
                email=portal_email,
                first_name="Cliente",
                last_name=seed["code"],
                roles=[],
                user_type="Website User",
                new_password=PORTAL_PASSWORD,
            )
            contactos_funcionales.append({"nombre_contacto": f"Portal {seed['code']}", "contacto_rol": "Portal", "email_contacto": portal_email, "telefono_contacto": f"505-22{idx:02d}300{idx}", "recibe_requerimientos": 1, "activo": 1})
        if not frappe.db.exists("Cliente Contable", customer_name):
            frappe.get_doc(
                {
                    "doctype": "Cliente Contable",
                    "customer": customer_name,
                    "estado": "Activo",
                    "frecuencia_de_cierre": "Mensual",
                    "company_default": ctx["company"],
                    "regimen_fiscal": "General",
                    "clasificacion_riesgo": "Medio" if seed["segment"] == "contabilidad" else "Alto",
                    "moneda_preferida": ctx["currency"],
                    "ejecutivo_comercial_default": INTERNAL_USERS["contador_1"]["email"],
                    "responsable_operativo_default": INTERNAL_USERS["supervisor_1"]["email"],
                    "responsable_cobranza_interno": INTERNAL_USERS["contador_2"]["email"],
                    "sla_respuesta_horas_default": 8,
                    "sla_entrega_dias_default": 5,
                    "canal_envio_preferido": "Portal" if portal_enabled else "Correo",
                    "telefono": f"505-22{idx:02d}000{idx}",
                    "correo_electronico": f"gerencia.{seed['code'].lower()}@cliente.demo",
                    "contacto_facturacion": f"Facturacion {seed['code']}",
                    "email_facturacion": f"facturacion.{seed['code'].lower()}@cliente.demo",
                    "contacto_cobranza": f"Cobranza {seed['code']}",
                    "email_cobranza": f"cobranza.{seed['code'].lower()}@cliente.demo",
                    "contactos_funcionales": contactos_funcionales,
                    "termino_pago_dias": 15,
                    "dias_gracia_cobranza": 3,
                    "politica_retencion_documental": "Auditoria" if portal_enabled else "Fiscal",
                    "clasificacion_confidencialidad_default": "Confidencial",
                    "portal_habilitado": 1 if portal_enabled else 0,
                    "permite_carga_documentos": 1 if portal_enabled else 0,
                    "recordatorios_automaticos_portal": 1 if portal_enabled else 0,
                    "usuario_portal_principal": portal_user if portal_enabled else None,
                }
            ).insert(ignore_permissions=True)
        clients[seed["code"]] = {"name": customer_name, "segment": seed["segment"], "portal_user": portal_user, "portal_password": PORTAL_PASSWORD if portal_user else None}
    return clients


def _ensure_demo_periods(ctx):
    periods = {}
    for client_code, client in ctx["clients"].items():
        for month_start in ctx["month_starts"]:
            period_name = _ensure_period(client["name"], ctx["company"], month_start)
            periods[(client_code, month_start.strftime("%Y-%m"))] = period_name
    return periods

def _seed_accounting_clients(ctx):
    month_keys = [month.strftime("%Y-%m") for month in ctx["month_starts"]]
    oldest_key = month_keys[0]
    middle_key = month_keys[1]
    current_key = month_keys[2]
    accounting_clients = [code for code, info in ctx["clients"].items() if info["segment"] == "contabilidad"]
    for index, client_code in enumerate(accounting_clients, start=1):
        client_name = ctx["clients"][client_code]["name"]
        fee = 700 + (index * 55)
        contract_name = _create_contract(
            client=client_name,
            service_name=ctx["services"]["Contabilidad"],
            company=ctx["company"],
            currency=ctx["currency"],
            manager_email=ctx["internal_users"]["contador_1"],
            operational_email=ctx["internal_users"]["supervisor_1"],
            start_date=ctx["month_starts"][0],
            end_date=add_days(ctx["month_starts"][2], 90),
            modalidad="Fijo",
            tarifa_hora=0,
            honorario_fijo=fee,
            periodicidad="Mensual",
            tag=client_code,
        )
        for month_start in ctx["month_starts"]:
            period_key = month_start.strftime("%Y-%m")
            period_name = ctx["periods"][(client_code, period_key)]
            month_label = month_start.strftime("%m/%Y")
            encargo_name = _create_encargo(
                cliente=client_name,
                contract_name=contract_name,
                service_name=ctx["services"]["Contabilidad"],
                periodo_name=period_name,
                company=ctx["company"],
                currency=ctx["currency"],
                start_date=month_start,
                end_date=add_days(add_months(month_start, 1), -1),
                modalidad="Fijo",
                tarifa_hora=0,
                honorario_fijo=fee,
                responsable=ctx["internal_users"]["contador_1"],
                estado="En Ejecucion" if period_key == current_key else "En Revision",
                description=f"Ciclo contable mensual demo {month_label}.",
                tag=f"{client_code}-{period_key}",
            )
            cierre_status = "Completed" if period_key != current_key else "Working"
            impuestos_status = "Pending Review" if period_key == middle_key else cierre_status
            task_cierre = _create_task(
                subject=f"{DEMO_PREFIX} Cierre contable {month_label}",
                cliente=client_name,
                company=ctx["company"],
                periodo=period_name,
                encargo_name=encargo_name,
                status=cierre_status,
                assigned_to=ctx["internal_users"]["aux_1" if index % 2 else "aux_2"],
                due_date=add_days(add_months(month_start, 1), 3),
                tipo_de_tarea="Cierre mensual" if _task_has_field("tipo_de_tarea") else None,
                description=f"{DEMO_PREFIX} Preparar conciliaciones y papeles de cierre para {month_label}.",
            )
            _create_task(
                subject=f"{DEMO_PREFIX} Declaraciones fiscales {month_label}",
                cliente=client_name,
                company=ctx["company"],
                periodo=period_name,
                encargo_name=encargo_name,
                status=impuestos_status,
                assigned_to=ctx["internal_users"]["aux_3" if index % 2 else "aux_4"],
                due_date=add_days(add_months(month_start, 1), 6),
                tipo_de_tarea="Impuestos" if _task_has_field("tipo_de_tarea") else None,
                description=f"{DEMO_PREFIX} Declaraciones y soportes fiscales de {month_label}.",
            )
            _create_internal_document(
                titulo=f"{DEMO_PREFIX} Balance de comprobacion {month_label}",
                cliente=client_name,
                company=ctx["company"],
                periodo=period_name,
                encargo_name=encargo_name,
                task_name=task_cierre,
                tipo="Estado de Cuenta",
                file_name=f"{DEMO_FILE_PREFIX}-{client_code.lower()}-balance-{period_key}.txt",
                content=_txt_payload(f"Balance demo {client_code} {month_label}", ["Activo 100", "Pasivo 40", "Patrimonio 60"]),
                prepared_by=ctx["internal_users"]["aux_1"],
            )
            _create_internal_document(
                titulo=f"{DEMO_PREFIX} Declaracion IVA {month_label}",
                cliente=client_name,
                company=ctx["company"],
                periodo=period_name,
                encargo_name=encargo_name,
                tipo="Declaracion",
                file_name=f"{DEMO_FILE_PREFIX}-{client_code.lower()}-iva-{period_key}.txt",
                content=_txt_payload(f"Declaracion demo {client_code} {month_label}", ["IVA debito 45", "IVA credito 28", "Pago neto 17"]),
                prepared_by=ctx["internal_users"]["aux_3"],
            )
            if period_key == current_key:
                continue
            invoice_name = _safe_generate_invoice(encargo_name, posting_date=add_days(add_months(month_start, 1), -2), due_date=add_days(add_months(month_start, 1), 15))
            if not invoice_name:
                continue
            if period_key == oldest_key:
                _safe_register_payment(encargo_name, invoice_name, paid_amount=None, posting_date=add_days(add_months(month_start, 1), 7), submit=1)
                continue
            partial_amount = None
            if index <= 3:
                total = flt(frappe.db.get_value("Sales Invoice", invoice_name, "grand_total") or 0)
                partial_amount = round(total * 0.55, 2) if total else None
                _safe_register_payment(encargo_name, invoice_name, paid_amount=partial_amount, posting_date=add_days(add_months(month_start, 1), 20), submit=1)
            _create_cobranza(invoice_name, estado="Compromiso de Pago" if index <= 3 else "Contactado", proxima_gestion=add_days(nowdate(), 5 + index), comentario=f"Seguimiento demo por saldo pendiente de {client_name}.")


def _insert_demo_doc(doc, *, target_estado_aprobacion=None):
    if hasattr(doc, "meta") and doc.meta.has_field("estado_aprobacion"):
        target_estado_aprobacion = target_estado_aprobacion or doc.get("estado_aprobacion")
        if target_estado_aprobacion and target_estado_aprobacion != "Borrador":
            doc.estado_aprobacion = "Borrador"
    doc.flags.ignore_governance_validation = True
    doc.insert(ignore_permissions=True)
    if target_estado_aprobacion and target_estado_aprobacion != "Borrador":
        frappe.db.set_value(doc.doctype, doc.name, "estado_aprobacion", target_estado_aprobacion, update_modified=False)
        doc.reload()
    return doc


def _create_contract(client, service_name, company, currency, manager_email, operational_email, start_date, end_date, modalidad, tarifa_hora, honorario_fijo, periodicidad, tag):
    contract_name = f"{DEMO_PREFIX} Contrato {tag}"
    if frappe.db.exists("Contrato Comercial", contract_name):
        return contract_name
    doc = frappe.get_doc(
        {
            "doctype": "Contrato Comercial",
            "nombre_del_contrato": contract_name,
            "cliente": client,
            "customer": client,
            "company": company,
            "moneda": currency,
            "ejecutivo_comercial": manager_email,
            "responsable_operativo": operational_email,
            "sla_respuesta_horas": 8,
            "sla_entrega_dias": 5,
            "fecha_inicio": start_date,
            "fecha_fin": end_date,
            "estado_aprobacion": "Aprobado",
            "alcances": [{"servicio_contable": service_name, "descripcion": f"Alcance demo {tag}", "activa": 1, "periodicidad": periodicidad, "modalidad_tarifa": modalidad, "tarifa_hora": tarifa_hora, "honorario_fijo": honorario_fijo, "horas_incluidas": 0, "fecha_inicio": start_date, "fecha_fin": end_date}],
        }
    )
    target_estado = doc.estado_aprobacion
    _insert_demo_doc(doc, target_estado_aprobacion=target_estado)
    doc.reload()
    doc.sincronizar_estado_comercial()
    frappe.db.set_value(
        "Contrato Comercial",
        doc.name,
        {"estado_aprobacion": target_estado, "estado_comercial": doc.estado_comercial},
        update_modified=False,
    )
    doc.reload()
    doc.sincronizar_tarifas_desde_alcances()
    return doc.name


def _create_encargo(cliente, contract_name, service_name, periodo_name, company, currency, start_date, end_date, modalidad, tarifa_hora, honorario_fijo, responsable, estado, description, tag):
    existing = frappe.db.get_value("Encargo Contable", {"cliente": cliente, "periodo_referencia": periodo_name, "servicio_contable": service_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc(
        {
            "doctype": "Encargo Contable",
            "cliente": cliente,
            "contrato_comercial": contract_name,
            "servicio_contable": service_name,
            "estado": estado,
            "estado_aprobacion": "Aprobado",
            "fecha_de_inicio": start_date,
            "fecha_fin_estimada": end_date,
            "periodo_referencia": periodo_name,
            "responsable": responsable,
            "company": company,
            "moneda": currency,
            "modalidad_honorario": modalidad,
            "tarifa_hora": tarifa_hora,
            "honorario_fijo": honorario_fijo,
            "costo_interno_hora": max(flt(honorario_fijo) * 0.25, 10) if modalidad == "Fijo" else max(flt(tarifa_hora) * 0.4, 10),
            "descripcion": description,
            "nombre_del_encargo": f"{DEMO_PREFIX} Encargo {tag}",
        }
    )
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _normalize_task_type(tipo_de_tarea):
    if not tipo_de_tarea:
        return None
    return TASK_TYPE_ALIASES.get(tipo_de_tarea, tipo_de_tarea)


def _create_task(subject, cliente, company, periodo, encargo_name, status, assigned_to, due_date, description, tipo_de_tarea=None):
    task = frappe.get_doc({"doctype": "Task", "subject": subject, "status": status, "cliente": cliente, "company": company, "periodo": periodo, "encargo_contable": encargo_name, "exp_end_date": due_date, "description": description})
    if tipo_de_tarea and _task_has_field("tipo_de_tarea"):
        task.tipo_de_tarea = _normalize_task_type(tipo_de_tarea)
    task.flags.ignore_governance_validation = True
    task.insert(ignore_permissions=True)
    frappe.db.set_value("Task", task.name, "_assign", json.dumps([assigned_to]), update_modified=False)
    return task.name


def _resolve_demo_document_title(titulo, cliente, periodo, encargo_name=None, task_name=None, entregable_name=None):
    filters = {
        "titulo_del_documento": titulo,
        "cliente": cliente,
        "periodo": periodo,
    }
    if encargo_name:
        filters["encargo_contable"] = encargo_name
    if task_name:
        filters["task"] = task_name
    if entregable_name:
        filters["entregable_cliente"] = entregable_name
    existing = frappe.db.get_value("Documento Contable", filters, "name")
    if existing:
        return existing, titulo

    if not frappe.db.exists("Documento Contable", titulo):
        return None, titulo

    suffix_parts = []
    if periodo:
        suffix_parts.append(periodo)
    if task_name:
        suffix_parts.append(task_name)
    elif encargo_name:
        suffix_parts.append(encargo_name[-12:])
    elif entregable_name:
        suffix_parts.append(entregable_name[-12:])
    else:
        suffix_parts.append(cliente[:24])

    suffix = " | ".join(part for part in suffix_parts if part)
    unique_title = f"{titulo} | {suffix}" if suffix else f"{titulo} | demo"
    if len(unique_title) > 140:
        max_title_len = max(24, 140 - len(suffix) - 3)
        unique_title = f"{titulo[:max_title_len].rstrip()} | {suffix}"
    return None, unique_title[:140]


def _create_internal_document(titulo, cliente, company, periodo, encargo_name=None, task_name=None, entregable_name=None, tipo="Otro", file_name=None, content=b"", prepared_by=None):
    existing_name, resolved_title = _resolve_demo_document_title(
        titulo,
        cliente,
        periodo,
        encargo_name=encargo_name,
        task_name=task_name,
        entregable_name=entregable_name,
    )
    if existing_name:
        return existing_name

    file_doc = save_file(file_name or f"{DEMO_FILE_PREFIX}-documento.txt", content, "Task", task_name or encargo_name or cliente, is_private=1)
    doc = frappe.get_doc({"doctype": "Documento Contable", "titulo_del_documento": resolved_title, "cliente": cliente, "company": company, "periodo": periodo, "encargo_contable": encargo_name, "task": task_name, "entregable_cliente": entregable_name, "tipo": tipo, "archivo_adjunto": file_doc.file_url, "preparado_por": prepared_by})
    doc.flags.ignore_governance_validation = True
    doc.insert(ignore_permissions=True)
    frappe.db.set_value("File", file_doc.name, {"attached_to_doctype": "Documento Contable", "attached_to_name": doc.name}, update_modified=False)
    return doc.name


def _safe_generate_invoice(encargo_name, posting_date, due_date):
    try:
        result = generar_factura_encargo(encargo_name, posting_date=posting_date, due_date=due_date, incluir_horas=0, incluir_honorario_fijo=1, submit=1)
        return result.get("sales_invoice")
    except Exception:
        frappe.log_error(title=f"{DEMO_PREFIX} invoice seed failed", message=frappe.get_traceback())
        return None


def _safe_register_payment(encargo_name, invoice_name, paid_amount, posting_date, submit):
    try:
        result = crear_payment_entry_encargo_api(encargo_name, invoice_name, posting_date=posting_date, paid_amount=paid_amount, reference_no=f"{DEMO_PREFIX[:7]}-{invoice_name[-6:]}", reference_date=posting_date, submit=submit)
        return result.get("payment_entry")
    except Exception:
        frappe.log_error(title=f"{DEMO_PREFIX} payment seed failed", message=frappe.get_traceback())
        return None


def _create_cobranza(invoice_name, estado, proxima_gestion, comentario):
    if frappe.db.exists("Seguimiento Cobranza", {"sales_invoice": invoice_name, "estado_seguimiento": estado, "comentarios": comentario}):
        return
    doc = frappe.get_doc({"doctype": "Seguimiento Cobranza", "sales_invoice": invoice_name, "estado_seguimiento": estado, "canal": "Llamada", "comentarios": comentario, "proxima_gestion": proxima_gestion})
    doc.insert(ignore_permissions=True)

def _seed_complete_audits(ctx):
    complete_codes = [code for code, info in ctx["clients"].items() if info["segment"] == "auditoria_completa"]
    for index, client_code in enumerate(complete_codes, start=1):
        opinion = "Favorable" if index == 1 else "Con Salvedades"
        _seed_closed_audit_case(ctx, client_code, opinion)


def _seed_in_progress_audit(ctx):
    client_code = next(code for code, info in ctx["clients"].items() if info["segment"] == "auditoria_proceso")
    client_name = ctx["clients"][client_code]["name"]
    period_name = ctx["periods"][(client_code, ctx["month_starts"][2].strftime("%Y-%m"))]
    contract_name = _create_contract(
        client=client_name,
        service_name=ctx["services"]["Auditoria"],
        company=ctx["company"],
        currency=ctx["currency"],
        manager_email=ctx["internal_users"]["contador_2"],
        operational_email=ctx["internal_users"]["supervisor_2"],
        start_date=add_days(ctx["month_starts"][0], 3),
        end_date=add_days(ctx["month_starts"][2], 95),
        modalidad="Fijo",
        tarifa_hora=0,
        honorario_fijo=4300,
        periodicidad="Por Evento",
        tag=client_code,
    )
    encargo_name = _create_encargo(
        cliente=client_name,
        contract_name=contract_name,
        service_name=ctx["services"]["Auditoria"],
        periodo_name=period_name,
        company=ctx["company"],
        currency=ctx["currency"],
        start_date=add_days(ctx["month_starts"][0], 5),
        end_date=add_days(ctx["month_starts"][2], 55),
        modalidad="Fijo",
        tarifa_hora=0,
        honorario_fijo=4300,
        responsable=ctx["internal_users"]["supervisor_2"],
        estado="En Ejecucion",
        description=f"{DEMO_PREFIX} Auditoria financiera en proceso.",
        tag=f"{client_code}-AUD-PROC",
    )
    task_name = _create_task(
        subject=f"{DEMO_PREFIX} Planeacion auditoria {client_code}",
        cliente=client_name,
        company=ctx["company"],
        periodo=period_name,
        encargo_name=encargo_name,
        status="Working",
        assigned_to=ctx["internal_users"]["aux_4"],
        due_date=add_days(nowdate(), 7),
        description=f"{DEMO_PREFIX} Planeacion y obtencion inicial de evidencia para {client_code}.",
    )
    req_name, deliverables = _create_portal_request(
        client_name=client_name,
        period_name=period_name,
        encargo_name=encargo_name,
        titulo=f"{DEMO_PREFIX} Requerimiento auditoria en proceso {client_code}",
        descripcion="Solicitud inicial de balanza, auxiliares y borrador de EEFF.",
        due_date=add_days(nowdate(), 4),
        deliverable_specs=[
            {"tipo": "Balanza mensual", "descripcion": "Balanza de comprobacion del periodo", "obligatorio": 1},
            {"tipo": "Borrador EEFF", "descripcion": "Estados financieros preliminares", "obligatorio": 1},
        ],
    )
    uploaded = _portal_upload(
        client_code,
        deliverables[0],
        f"{DEMO_FILE_PREFIX}-{client_code.lower()}-balanza-proceso.txt",
        _txt_payload(f"Balanza preliminar {client_code}", ["Activo 420000", "Pasivo 170000", "Patrimonio 250000"]),
        titulo_documento=f"{DEMO_PREFIX} Balanza preliminar {client_code}",
        tipo_documental="Estado de Cuenta",
    )
    expediente_name = _create_expediente(encargo_name, ctx["internal_users"]["socio"], ctx["internal_users"]["supervisor_2"], estado_expediente="Ejecucion")
    riesgo_name = _create_riesgo(expediente_name, area="Ingresos", riesgo="Reconocimiento anticipado de ingresos.", control="Revision de cortes y facturacion.", estado="En Ejecucion", riesgo_inherente="Alto", riesgo_residual="Medio")
    _create_papel(
        expediente_name=expediente_name,
        riesgo_name=riesgo_name,
        task_name=task_name,
        documento_name=uploaded["documento_contable"],
        tipo_papel="Prueba Sustantiva",
        titulo=f"{DEMO_PREFIX} Analitica de ingresos {client_code}",
        estado_papel="En Revision",
        prepared_by=ctx["internal_users"]["aux_4"],
        reviewed_by=ctx["internal_users"]["supervisor_2"],
        conclusion="Pendiente completar pruebas de corte.",
    )
    _create_hallazgo(
        expediente_name=expediente_name,
        riesgo_name=riesgo_name,
        titulo=f"{DEMO_PREFIX} Diferencia en corte de ingresos {client_code}",
        severidad="Alta",
        estado="En Seguimiento",
        condicion="Se identificaron facturas del mes siguiente reconocidas en el periodo auditado.",
        respuesta="Administracion revisando el soporte y posible ajuste.",
    )
    _seed_eeff_package(ctx, client_code, encargo_name, expediente_name, period_name, audited=False, opinion=None)
    invoice_name = _safe_generate_invoice(encargo_name, posting_date=nowdate(), due_date=add_days(nowdate(), 20))
    if invoice_name:
        _create_cobranza(invoice_name, estado="Contactado", proxima_gestion=add_days(nowdate(), 7), comentario=f"Seguimiento inicial de honorarios de auditoria en proceso para {client_name}.")
    _with_requirements_message(client_code, req_name, "Adjuntamos la balanza preliminar. El borrador de EEFF se cargara en la siguiente entrega.")


def _seed_closed_audit_case(ctx, client_code, opinion):
    client_name = ctx["clients"][client_code]["name"]
    period_name = ctx["periods"][(client_code, ctx["month_starts"][1].strftime("%Y-%m"))]
    contract_name = _create_contract(
        client=client_name,
        service_name=ctx["services"]["Auditoria"],
        company=ctx["company"],
        currency=ctx["currency"],
        manager_email=ctx["internal_users"]["contador_2"],
        operational_email=ctx["internal_users"]["supervisor_1"],
        start_date=add_days(ctx["month_starts"][0], 1),
        end_date=add_days(ctx["month_starts"][2], 60),
        modalidad="Fijo",
        tarifa_hora=0,
        honorario_fijo=5200 if opinion == "Favorable" else 5800,
        periodicidad="Por Evento",
        tag=client_code,
    )
    encargo_name = _create_encargo(
        cliente=client_name,
        contract_name=contract_name,
        service_name=ctx["services"]["Auditoria"],
        periodo_name=period_name,
        company=ctx["company"],
        currency=ctx["currency"],
        start_date=add_days(ctx["month_starts"][0], 2),
        end_date=add_days(ctx["month_starts"][2], 25),
        modalidad="Fijo",
        tarifa_hora=0,
        honorario_fijo=5200 if opinion == "Favorable" else 5800,
        responsable=ctx["internal_users"]["supervisor_1"],
        estado="En Revision",
        description=f"{DEMO_PREFIX} Auditoria completa {opinion.lower()}.",
        tag=f"{client_code}-AUD-COMP",
    )
    req_name, deliverables = _create_portal_request(
        client_name=client_name,
        period_name=period_name,
        encargo_name=encargo_name,
        titulo=f"{DEMO_PREFIX} Requerimiento evidencia auditoria {client_code}",
        descripcion="Solicitud de soporte final para auditoria y revision de EEFF auditados.",
        due_date=add_days(nowdate(), -10),
        deliverable_specs=[
            {"tipo": "Balanza final", "descripcion": "Balanza de cierre del periodo", "obligatorio": 1},
            {"tipo": "Auxiliar cartera", "descripcion": "Auxiliar de cuentas por cobrar", "obligatorio": 1},
            {"tipo": "Comentarios Word EEFF", "descripcion": "Word con comentarios del cliente", "obligatorio": 1},
        ],
    )
    upload_1 = _portal_upload(client_code, deliverables[0], f"{DEMO_FILE_PREFIX}-{client_code.lower()}-balanza-final.txt", _txt_payload(f"Balanza final {client_code}", ["Activo 500000", "Pasivo 200000", "Patrimonio 300000"]), titulo_documento=f"{DEMO_PREFIX} Balanza final {client_code}", tipo_documental="Estado de Cuenta")
    upload_2 = _portal_upload(client_code, deliverables[1], f"{DEMO_FILE_PREFIX}-{client_code.lower()}-auxiliar-cartera.txt", _txt_payload(f"Auxiliar cartera {client_code}", ["Cliente A 40000", "Cliente B 25000", "Total 65000"]), titulo_documento=f"{DEMO_PREFIX} Auxiliar cartera {client_code}", tipo_documental="Correspondencia")
    expediente_name = _create_expediente(encargo_name, ctx["internal_users"]["socio"], ctx["internal_users"]["supervisor_1"], estado_expediente="Planeacion")
    riesgo_name = _create_riesgo(expediente_name, area="Cuentas por cobrar", riesgo="Sobrevaloracion de cuentas por cobrar.", control="Conciliacion de auxiliares y confirmaciones.", estado="Planeado", riesgo_inherente="Medio", riesgo_residual="Bajo")
    paper_name = _create_papel(
        expediente_name=expediente_name,
        riesgo_name=riesgo_name,
        task_name=None,
        documento_name=upload_2["documento_contable"],
        tipo_papel="Cedula Analitica",
        titulo=f"{DEMO_PREFIX} Cedula cartera {client_code}",
        estado_papel="Cerrado",
        prepared_by=ctx["internal_users"]["aux_2"],
        reviewed_by=ctx["internal_users"]["supervisor_1"],
        conclusion="La cartera fue conciliada con auxiliares y soporte documental.",
    )
    _update_riesgo_validado(riesgo_name, paper_name)
    _create_hallazgo(
        expediente_name=expediente_name,
        riesgo_name=riesgo_name,
        titulo=f"{DEMO_PREFIX} Ajuste de clasificacion cartera {client_code}",
        severidad="Media",
        estado="Cerrado",
        condicion="Se reclasifico una porcion de cartera a largo plazo para mejor revelacion.",
        respuesta="Administracion acepto y registro el ajuste propuesto.",
        papel_name=paper_name,
    )
    _close_expediente(expediente_name)
    general_report, dictamen = _create_and_emit_audit_reports(expediente_name, opinion)
    package_name, version_name = _seed_eeff_package(ctx, client_code, encargo_name, expediente_name, period_name, audited=True, opinion=opinion, general_report=general_report, dictamen_name=dictamen, review_requirement=req_name, review_deliverable=deliverables[2])
    reviewed = _portal_upload(client_code, deliverables[2], f"{DEMO_FILE_PREFIX}-{client_code.lower()}-revision-word.txt", _txt_payload(f"Comentarios cliente {client_code}", ["Pagina 3: ajustar redaccion de nota 2", "Pagina 8: confirmar fecha del dictamen"]), titulo_documento=f"{DEMO_PREFIX} Comentarios Word {client_code}", tipo_documental="Correspondencia", version_documento_name=version_name)
    _append_client_approved_word_version(package_name, req_name, deliverables[2], reviewed["documento_contable"])
    emitir_paquete_estados_financieros(package_name)
    _validate_entregable(deliverables[0])
    _validate_entregable(deliverables[1])
    _validate_entregable(deliverables[2])
    cerrar_requerimiento_cliente(req_name)
    _archive_expediente(expediente_name, general_report)
    invoice_name = _safe_generate_invoice(encargo_name, posting_date=add_days(nowdate(), -20), due_date=add_days(nowdate(), -5))
    if invoice_name:
        if opinion == "Favorable":
            _safe_register_payment(encargo_name, invoice_name, paid_amount=None, posting_date=add_days(nowdate(), -3), submit=1)
        else:
            total = flt(frappe.db.get_value("Sales Invoice", invoice_name, "grand_total") or 0)
            _safe_register_payment(encargo_name, invoice_name, paid_amount=round(total * 0.6, 2) if total else None, posting_date=add_days(nowdate(), -4), submit=1)
            _create_cobranza(invoice_name, estado="Compromiso de Pago", proxima_gestion=add_days(nowdate(), 4), comentario=f"Cliente revisa saldo final de auditoria {client_name}.")
    _with_requirements_message(client_code, req_name, "Adjuntamos observaciones al Word de EEFF auditados y confirmamos recepcion de la version ajustada.")

def _create_expediente(encargo_name, socio_email, supervisor_email, estado_expediente="Planeacion"):
    existing = frappe.db.get_value("Expediente Auditoria", {"encargo_contable": encargo_name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "Expediente Auditoria", "encargo_contable": encargo_name, "socio_a_cargo": socio_email, "supervisor_a_cargo": supervisor_email, "base_normativa": "NIA", "estado_expediente": estado_expediente, "objetivo_auditoria": "Emitir conclusion sobre la razonabilidad de los EEFF del cliente.", "alcance_auditoria": "Revision integral de saldos, revelaciones y controles relevantes.", "materialidad_monetaria": 25000, "enfoque_auditoria": "Enfoque combinado de controles y sustantivo.", "estrategia_muestreo": "Muestreo dirigido por riesgo.", "memorando_planeacion": f"{DEMO_PREFIX} Planeacion inicial del expediente."})
    _insert_demo_doc(doc)
    return doc.name


def _create_riesgo(expediente_name, area, riesgo, control, estado, riesgo_inherente, riesgo_residual):
    doc = frappe.get_doc({"doctype": "Riesgo Control Auditoria", "expediente_auditoria": expediente_name, "area_auditoria": area, "proceso": area, "afirmacion": "Existencia", "riesgo": riesgo, "control_clave": control, "tipo_control": "Detectivo", "frecuencia_control": "Mensual", "riesgo_inherente": riesgo_inherente, "riesgo_residual": riesgo_residual, "respuesta_auditoria": "Mixto", "procedimiento_planificado": "Pruebas de detalle y conciliacion.", "estado_evaluacion": estado, "estado_aprobacion": "Aprobado"})
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _update_riesgo_validado(riesgo_name, papel_name):
    frappe.db.set_value(
        "Riesgo Control Auditoria",
        riesgo_name,
        {
            "estado_evaluacion": "Validado",
            "papel_trabajo_principal": papel_name,
            "estado_aprobacion": "Aprobado",
        },
        update_modified=False,
    )


def _create_papel(expediente_name, riesgo_name, task_name, documento_name, tipo_papel, titulo, estado_papel, prepared_by, reviewed_by, conclusion):
    documento = frappe.get_doc("Documento Contable", documento_name)
    evidence_file = documento.evidencias_documentales[0].archivo_file if documento.evidencias_documentales else None
    doc = frappe.get_doc({"doctype": "Papel Trabajo Auditoria", "expediente_auditoria": expediente_name, "tipo_papel": tipo_papel, "titulo": titulo, "riesgo_control_auditoria": riesgo_name, "documento_contable": documento_name, "evidencia_documental_file": evidence_file, "task": task_name, "objetivo_prueba": "Documentar evidencia y conclusion de auditoria.", "procedimiento_ejecutado": "Revision de soporte, conciliacion y validacion de consistencia.", "resultado": "Sin diferencias materiales pendientes." if estado_papel in ("Aprobado", "Cerrado") else "Procedimiento en curso.", "conclusion": conclusion, "preparado_por": prepared_by, "revisado_por": reviewed_by, "estado_papel": estado_papel, "estado_aprobacion": "Aprobado"})
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _create_hallazgo(expediente_name, riesgo_name, titulo, severidad, estado, condicion, respuesta, papel_name=None):
    doc = frappe.get_doc({"doctype": "Hallazgo Auditoria", "expediente_auditoria": expediente_name, "riesgo_control_auditoria": riesgo_name, "papel_trabajo_auditoria": papel_name, "titulo_hallazgo": titulo, "severidad": severidad, "estado_hallazgo": estado, "criterio": "Politicas contables, NIA y manuales internos del cliente.", "condicion": condicion, "causa": "Proceso de cierre con evidencia limitada.", "efecto": "Puede afectar revelacion o presentacion.", "recomendacion": "Ajustar la presentacion y fortalecer el control del cierre.", "respuesta_administracion": respuesta, "responsable_plan_accion": "Gerencia Financiera", "fecha_compromiso": add_days(nowdate(), 10), "estado_aprobacion": "Aprobado"})
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _close_expediente(expediente_name):
    frappe.db.set_value(
        "Expediente Auditoria",
        expediente_name,
        {
            "estado_aprobacion": "Aprobado",
            "resultado_revision_tecnica": "Aprobado",
            "comentarios_revision_tecnica": "Revision tecnica completada en seed demo.",
            "estado_expediente": "Cerrada",
            "memo_cierre": f"{DEMO_PREFIX} Memo de cierre con evidencia suficiente y documentacion final revisada.",
            "cerrado_por": frappe.session.user,
            "fecha_cierre": now_datetime(),
        },
        update_modified=False,
    )


def _archive_expediente(expediente_name, report_name):
    frappe.db.set_value(
        "Expediente Auditoria",
        expediente_name,
        {"informe_final_auditoria": report_name, "estado_expediente": "Archivada"},
        update_modified=False,
    )


def _create_and_emit_audit_reports(expediente_name, opinion):
    general_name = generar_informe_final_desde_expediente(expediente_name, TIPO_INFORME_FINAL_GENERAL, 1)["name"]
    dictamen_name = generar_informe_final_desde_expediente(expediente_name, TIPO_DICTAMEN_AUDITORIA, 0)["name"]
    frappe.db.set_value(
        "Informe Final Auditoria",
        general_name,
        {"estado_aprobacion": "Aprobado", "estado_emision": "Emitido"},
        update_modified=False,
    )
    updates = {"tipo_opinion": opinion, "estado_aprobacion": "Aprobado"}
    if opinion != "Favorable":
        updates["asunto_que_origina_modificacion"] = "Persisten diferencias materiales no corregidas en cuentas del periodo."
        updates["fundamento_salvedad"] = "La administracion decidio no registrar un ajuste material recomendado por la firma."
    frappe.db.set_value("Informe Final Auditoria", dictamen_name, updates, update_modified=False)
    emitir_informe_final_auditoria(dictamen_name)
    return general_name, dictamen_name


def _seed_eeff_package(ctx, client_code, encargo_name, expediente_name, period_name, audited, opinion, general_report=None, dictamen_name=None, review_requirement=None, review_deliverable=None):
    client_name = ctx["clients"][client_code]["name"]
    package = frappe.get_doc({"doctype": "Paquete Estados Financieros Cliente", "cliente": client_name, "encargo_contable": encargo_name, "expediente_auditoria": expediente_name, "periodo_contable": period_name, "fecha_corte": add_days(add_months(ctx["month_starts"][1], 1), -1), "marco_contable": "NIIF para PYMES", "tipo_paquete": "Auditado" if audited else "Para Auditoria", "version": 1, "es_version_vigente": 1, "estado_preparacion": "Aprobado para Emision" if audited else "En Revision", "estado_aprobacion": "Aprobado" if audited else "Borrador", "informe_final_auditoria": general_report, "dictamen_de_auditoria": dictamen_name, "observaciones_generales": f"{DEMO_PREFIX} Paquete EEFF {client_code}."})
    _insert_demo_doc(package, target_estado_aprobacion=package.estado_aprobacion)
    _create_financial_state(package.name, "Estado de Situacion Financiera", [{"codigo_rubro": "ACT-01", "descripcion": "Efectivo y bancos", "nivel": 2, "naturaleza": "Activo", "monto_actual": 120000, "monto_comparativo": 110000, "requiere_nota": 1, "numero_nota_referencial": "1"}, {"codigo_rubro": "ACT-02", "descripcion": "Cuentas por cobrar", "nivel": 2, "naturaleza": "Activo", "monto_actual": 80000, "monto_comparativo": 76000, "requiere_nota": 1, "numero_nota_referencial": "2"}, {"codigo_rubro": "ACT-03", "descripcion": "Propiedad planta y equipo", "nivel": 2, "naturaleza": "Activo", "monto_actual": 300000, "monto_comparativo": 295000, "requiere_nota": 1, "numero_nota_referencial": "3"}, {"codigo_rubro": "ACT-T", "descripcion": "Total activo", "nivel": 1, "naturaleza": "Activo", "es_total": 1, "monto_actual": 500000, "monto_comparativo": 481000}, {"codigo_rubro": "PAS-01", "descripcion": "Pasivos corrientes", "nivel": 2, "naturaleza": "Pasivo", "monto_actual": 140000, "monto_comparativo": 130000, "requiere_nota": 1, "numero_nota_referencial": "4"}, {"codigo_rubro": "PAS-02", "descripcion": "Obligaciones a largo plazo", "nivel": 2, "naturaleza": "Pasivo", "monto_actual": 60000, "monto_comparativo": 64000, "requiere_nota": 1, "numero_nota_referencial": "5"}, {"codigo_rubro": "PAS-T", "descripcion": "Total pasivo", "nivel": 1, "naturaleza": "Pasivo", "es_total": 1, "monto_actual": 200000, "monto_comparativo": 194000}, {"codigo_rubro": "PAT-01", "descripcion": "Capital social", "nivel": 2, "naturaleza": "Patrimonio", "monto_actual": 250000, "monto_comparativo": 250000, "requiere_nota": 1, "numero_nota_referencial": "6"}, {"codigo_rubro": "PAT-02", "descripcion": "Resultados acumulados", "nivel": 2, "naturaleza": "Patrimonio", "monto_actual": 50000, "monto_comparativo": 37000, "requiere_nota": 1, "numero_nota_referencial": "7"}, {"codigo_rubro": "PAT-T", "descripcion": "Total patrimonio", "nivel": 1, "naturaleza": "Patrimonio", "es_total": 1, "monto_actual": 300000, "monto_comparativo": 287000}], approved=audited)
    _create_financial_state(package.name, "Estado de Resultados", [{"codigo_rubro": "ING-T", "descripcion": "Total ingresos", "nivel": 1, "naturaleza": "Ingreso", "es_total": 1, "monto_actual": 420000, "monto_comparativo": 390000, "requiere_nota": 1, "numero_nota_referencial": "8"}, {"codigo_rubro": "GAS-T", "descripcion": "Total gastos", "nivel": 1, "naturaleza": "Gasto", "es_total": 1, "monto_actual": 355000, "monto_comparativo": 339000, "requiere_nota": 1, "numero_nota_referencial": "9"}, {"codigo_rubro": "RES-N", "descripcion": "Utilidad neta", "nivel": 1, "es_resultado_final": 1, "monto_actual": 65000, "monto_comparativo": 51000}], approved=audited)
    _create_financial_state(package.name, "Estado de Cambios en el Patrimonio", [{"codigo_rubro": "PAT-INI", "descripcion": "Patrimonio inicial", "nivel": 1, "monto_actual": 287000, "monto_comparativo": 260000}, {"codigo_rubro": "PAT-RES", "descripcion": "Resultado del periodo", "nivel": 1, "monto_actual": 65000, "monto_comparativo": 51000, "requiere_nota": 1, "numero_nota_referencial": "7"}, {"codigo_rubro": "PAT-FIN", "descripcion": "Patrimonio final", "nivel": 1, "monto_actual": 300000, "monto_comparativo": 287000, "es_total": 1}], approved=audited)
    _create_financial_state(package.name, "Estado de Flujos de Efectivo", [{"codigo_rubro": "EFE-INI", "descripcion": "Efectivo inicial", "nivel": 1, "monto_actual": 110000, "monto_comparativo": 90000, "es_efectivo_inicial": 1}, {"codigo_rubro": "EFE-VAR", "descripcion": "Variacion neta del efectivo", "nivel": 1, "monto_actual": 10000, "monto_comparativo": 20000, "es_variacion_neta_efectivo": 1}, {"codigo_rubro": "EFE-FIN", "descripcion": "Efectivo final", "nivel": 1, "monto_actual": 120000, "monto_comparativo": 110000, "es_efectivo_final": 1}], approved=audited)
    for number, title, category in [("1", "Efectivo y bancos", "Efectivo"), ("2", "Cuentas por cobrar", "Cuentas por Cobrar"), ("3", "Propiedad planta y equipo", "Propiedad Planta y Equipo"), ("4", "Pasivos corrientes", "Pasivos"), ("5", "Obligaciones a largo plazo", "Pasivos"), ("6", "Capital social", "Patrimonio"), ("7", "Resultados acumulados", "Patrimonio"), ("8", "Ingresos operativos", "Ingresos"), ("9", "Gastos operativos", "Gastos")]:
        _create_note(package.name, number, title, category, approved=audited)
    _create_adjustment(package.name, expediente_name, encargo_name, client_name, period_name, material=(opinion != "Favorable"), registrado=(opinion == "Favorable"))
    version_name = None
    if audited and review_requirement and review_deliverable:
        version_name = _append_word_version(package.name, review_requirement, review_deliverable)
        frappe.get_doc("Paquete Estados Financieros Cliente", package.name).save(ignore_permissions=True)
    else:
        frappe.get_doc("Paquete Estados Financieros Cliente", package.name).save(ignore_permissions=True)
    return package.name, version_name

def _create_financial_state(package_name, state_type, lines, approved):
    doc = frappe.get_doc({"doctype": "Estado Financiero Cliente", "paquete_estados_financieros_cliente": package_name, "tipo_estado": state_type, "estado_aprobacion": "Aprobado" if approved else "Borrador", "lineas": lines})
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _create_note(package_name, number, title, category, approved):
    doc = frappe.get_doc({"doctype": "Nota Estado Financiero", "paquete_estados_financieros_cliente": package_name, "numero_nota": number, "titulo": title, "categoria_nota": category, "orden_presentacion": cint(number), "estado_aprobacion": "Aprobado" if approved else "Borrador", "politica_contable": f"Politica contable demo para {title.lower()}.", "contenido_narrativo": f"{DEMO_PREFIX} Nota {number}: detalle narrativo de {title.lower()}.", "cifras_nota": [{"concepto": title, "monto_actual": 1000 + (cint(number) * 100), "monto_comparativo": 900 + (cint(number) * 80)}]})
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _create_adjustment(package_name, expediente_name, encargo_name, client_name, period_name, material, registrado):
    state_name = frappe.db.get_value("Estado Financiero Cliente", {"paquete_estados_financieros_cliente": package_name, "tipo_estado": "Estado de Situacion Financiera"}, "name")
    doc = frappe.get_doc({"doctype": "Ajuste Estados Financieros Cliente", "paquete_estados_financieros_cliente": package_name, "estado_financiero_cliente": state_name, "fecha_ajuste": nowdate(), "tipo_ajuste": "Auditoria", "origen_ajuste": "Auditoria", "estado_ajuste": "Registrado" if registrado else "No Registrado", "material": 1 if material else 0, "generalizado": 0, "impacta_dictamen": 1 if material and not registrado else 0, "impacta_informe_final": 1, "aceptado_por_cliente": 1 if registrado else 0, "registrado_en_version_final": 1 if registrado else 0, "descripcion": f"{DEMO_PREFIX} Ajuste de auditoria para {client_name}.", "justificacion": "Regularizacion de presentacion y revelacion.", "estado_aprobacion": "Aprobado", "lineas_ajuste": [{"estado_financiero_cliente": state_name, "codigo_rubro": "ACT-02", "descripcion_linea": "Cuentas por cobrar", "monto_previo": 80000, "monto_ajuste": -500 if registrado else -25000, "afecta_resultado": 1, "numero_nota_referencial": "2"}]})
    _insert_demo_doc(doc, target_estado_aprobacion=doc.estado_aprobacion)
    return doc.name


def _append_word_version(package_name, requerimiento_name, entregable_name):
    package = frappe.get_doc("Paquete Estados Financieros Cliente", package_name)
    file_doc = save_file(f"{DEMO_FILE_PREFIX}-{package.name.lower().replace(' ', '-')}-v1.txt", _txt_payload(f"Word revision {package.name}", ["Version 1 para revision del cliente."]), "Paquete Estados Financieros Cliente", package.name, is_private=1)
    package.append("versiones_documento_eeff", {"tipo_documento": "Word Revision Cliente", "version_documento": 1, "estado_documento": "Enviado a Cliente", "es_version_vigente": 1, "archivo_file": file_doc.name, "archivo_url": file_doc.file_url, "nombre_archivo": file_doc.file_name, "hash_sha256": _hash_bytes(_read_file_bytes(file_doc)), "requerimiento_cliente": requerimiento_name, "entregable_cliente": entregable_name, "fecha_generacion": now_datetime(), "fecha_envio_cliente": now_datetime(), "generado_por": frappe.session.user})
    package.flags.ignore_governance_validation = True
    package.save(ignore_permissions=True)
    return package.versiones_documento_eeff[-1].name


def _append_client_approved_word_version(package_name, requerimiento_name, entregable_name, documento_revision_cliente):
    package = frappe.get_doc("Paquete Estados Financieros Cliente", package_name)
    previous_rows = [row for row in package.versiones_documento_eeff if row.tipo_documento == "Word Revision Cliente" and row.estado_documento != "Reemplazado"]
    for row in previous_rows:
        row.estado_documento = "Reemplazado" if row.estado_documento == "Generado" else row.estado_documento
        row.es_version_vigente = 0
    file_doc = save_file(f"{DEMO_FILE_PREFIX}-{package.name.lower().replace(' ', '-')}-v2.txt", _txt_payload(f"Word aprobado {package.name}", ["Version 2 aprobada por cliente."]), "Paquete Estados Financieros Cliente", package.name, is_private=1)
    package.append("versiones_documento_eeff", {"tipo_documento": "Word Revision Cliente", "version_documento": 2, "estado_documento": "Aprobado por Cliente", "es_version_vigente": 1, "archivo_file": file_doc.name, "archivo_url": file_doc.file_url, "nombre_archivo": file_doc.file_name, "hash_sha256": _hash_bytes(_read_file_bytes(file_doc)), "requerimiento_cliente": requerimiento_name, "entregable_cliente": entregable_name, "documento_revision_cliente": documento_revision_cliente, "fecha_generacion": now_datetime(), "fecha_envio_cliente": now_datetime(), "fecha_revision_cliente": now_datetime(), "generado_por": frappe.session.user})
    package.flags.ignore_governance_validation = True
    package.save(ignore_permissions=True)


def _create_portal_request(client_name, period_name, encargo_name, titulo, descripcion, due_date, deliverable_specs):
    req = frappe.get_doc({"doctype": "Requerimiento Cliente", "nombre_del_requerimiento": titulo, "cliente": client_name, "company": frappe.db.get_value("Cliente Contable", client_name, "company_default"), "encargo_contable": encargo_name, "periodo": period_name, "prioridad": "Alta", "canal_envio": "Portal", "fecha_solicitud": add_days(due_date, -5), "fecha_vencimiento": due_date, "descripcion": descripcion, "instrucciones_cliente": "Adjuntar archivo txt o Word con informacion solicitada."})
    req.flags.ignore_governance_validation = True
    req.insert(ignore_permissions=True)
    entregables = []
    for spec in deliverable_specs:
        entregable = frappe.get_doc({"doctype": "Entregable Cliente", "requerimiento_cliente": req.name, "tipo_entregable": spec["tipo"], "descripcion": spec["descripcion"], "obligatorio": spec.get("obligatorio", 1), "fecha_compromiso": due_date})
        entregable.flags.ignore_governance_validation = True
        entregable.insert(ignore_permissions=True)
        entregables.append(entregable.name)
    marcar_requerimiento_enviado(req.name)
    return req.name, entregables


def _portal_upload(client_code, entregable_name, file_name, content, titulo_documento, tipo_documental, version_documento_name=None):
    user = ctx_client = None
    for code, info in CLIENT_DEFINITIONS_MAP().items():
        if code == client_code:
            ctx_client = info
            break
    user = frappe.db.get_value("Cliente Contable", ctx_client["customer"], "usuario_portal_principal") if ctx_client else None
    with _acting_as(user):
        return registrar_carga_entregable_portal(entregable_name, file_name=file_name, content=content, titulo_documento=titulo_documento, tipo_documental=tipo_documental, observaciones="Carga demo desde portal.", version_documento_name=version_documento_name)


def _with_requirements_message(client_code, requerimiento_name, mensaje):
    user = frappe.db.get_value("Cliente Contable", CLIENT_DEFINITIONS_MAP()[client_code]["customer"], "usuario_portal_principal")
    with _acting_as(user):
        registrar_mensaje_portal(requerimiento_name, mensaje)


def _validate_entregable(entregable_name):
    entregable = frappe.get_doc("Entregable Cliente", entregable_name)
    entregable.flags.ignore_governance_validation = True
    entregable.estado_entregable = "Validado"
    entregable.save(ignore_permissions=True)


def _ensure_item(item_code, item_name, ctx, is_stock=False):
    if frappe.db.exists("Item", item_code):
        return item_code
    frappe.get_doc({"doctype": "Item", "item_code": item_code, "item_name": item_name, "item_group": ctx["item_group"], "stock_uom": ctx["stock_uom"], "is_stock_item": 1 if is_stock else 0, "is_sales_item": 1, "is_service_item": 0 if is_stock else 1, "include_item_in_manufacturing": 0}).insert(ignore_permissions=True)
    return item_code


def _ensure_user(email, first_name, last_name, roles, user_type, new_password):
    if not frappe.db.exists("User", email):
        user = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name, "last_name": last_name, "send_welcome_email": 0, "user_type": user_type, "new_password": new_password})
        for role in roles:
            user.append("roles", {"role": role})
        user.insert(ignore_permissions=True)
    else:
        user = frappe.get_doc("User", email)
        existing_roles = {row.role for row in user.roles}
        for role in roles:
            if role not in existing_roles:
                user.append("roles", {"role": role})
        if user_type and getattr(user, "user_type", None) != user_type:
            user.user_type = user_type
        if new_password:
            user.new_password = new_password
        user.save(ignore_permissions=True)
    return email


def _month_name_es(month_number):
    month_name = SPANISH_MONTHS.get(int(month_number or 0))
    if not month_name:
        frappe.throw(_("Mes invalido para data demo: {0}").format(month_number), title=_("Mes Invalido"))
    return month_name


def _ensure_period(cliente, company, month_start):
    month_name = _month_name_es(month_start.month)
    existing = frappe.db.get_value("Periodo Contable", {"cliente": cliente, "company": company, "mes": month_name, "anio": month_start.year}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "Periodo Contable", "cliente": cliente, "company": company, "mes": month_name, "anio": month_start.year, "estado": "Abierto"})
    doc.insert(ignore_permissions=True)
    return doc.name


def _task_has_field(fieldname):
    return frappe.get_meta("Task").has_field(fieldname)


def CLIENT_DEFINITIONS_MAP():
    return {row["code"]: row for row in CLIENT_DEFINITIONS}


def _status(callback, message):
    if callback:
        callback(message)


def _txt_payload(title, lines):
    body = "\n".join([title, "", *lines, "", f"Generado: {now_datetime()}"])
    return body.encode("utf-8")


def _hash_bytes(content):
    return hashlib.sha256(content).hexdigest()


def _read_file_bytes(file_doc):
    file_path = file_doc.get_full_path() if hasattr(file_doc, "get_full_path") else None
    if file_path:
        with open(file_path, "rb") as handle:
            return handle.read()
    return b""


def _get_demo_customer_names():
    return frappe.get_all("Customer", filters={"name": ["like", f"{DEMO_PREFIX}%"]}, pluck="name")


def _get_demo_client_names():
    return frappe.get_all("Cliente Contable", filters={"name": ["like", f"{DEMO_PREFIX}%"]}, pluck="name")


def _delete_demo_financial_flows(cliente_names):
    for name in frappe.get_all("Seguimiento Cobranza", filters={"cliente_contable": ["in", cliente_names or [""]]}, pluck="name"):
        _force_delete("Seguimiento Cobranza", name)
    invoices = frappe.get_all("Sales Invoice", filters={"customer": ["like", f"{DEMO_PREFIX}%"]}, pluck="name")
    for name in frappe.get_all("Payment Entry Reference", filters={"reference_name": ["in", invoices or [""]]}, pluck="parent"):
        _force_delete("Payment Entry", name)
    for name in invoices:
        _force_delete("Sales Invoice", name)


def _delete_demo_operational_docs(cliente_names):
    for doctype, fieldname in (("Documento Contable", "cliente"), ("Entregable Cliente", "cliente"), ("Requerimiento Cliente", "cliente"), ("Task", "cliente")):
        if not frappe.db.exists("DocType", doctype):
            continue
        for name in frappe.get_all(doctype, filters={fieldname: ["in", cliente_names or [""]]}, pluck="name"):
            _delete_linked_artifacts(doctype, name)
            _force_delete(doctype, name)


def _delete_demo_audit_and_eeff(cliente_names):
    package_names = frappe.get_all(
        "Paquete Estados Financieros Cliente",
        filters={"cliente": ["in", cliente_names or [""]]},
        pluck="name",
    ) if frappe.db.exists("DocType", "Paquete Estados Financieros Cliente") else []

    if package_names:
        for doctype in ("Ajuste Estados Financieros Cliente", "Nota Estado Financiero", "Estado Financiero Cliente"):
            if not frappe.db.exists("DocType", doctype):
                continue
            for name in frappe.get_all(
                doctype,
                filters={"paquete_estados_financieros_cliente": ["in", package_names]},
                pluck="name",
            ):
                _delete_linked_artifacts(doctype, name)
                _force_delete(doctype, name)

    for doctype in ("Informe Final Auditoria", "Hallazgo Auditoria", "Papel Trabajo Auditoria", "Riesgo Control Auditoria", "Expediente Auditoria"):
        if not frappe.db.exists("DocType", doctype):
            continue
        for name in frappe.get_all(doctype, filters={"cliente": ["in", cliente_names or [""]]}, pluck="name"):
            _delete_linked_artifacts(doctype, name)
            _force_delete(doctype, name)

    for package_name in package_names:
        _delete_linked_artifacts("Paquete Estados Financieros Cliente", package_name)
        _force_delete("Paquete Estados Financieros Cliente", package_name)


def _delete_demo_commercial_and_periods(cliente_names):
    for doctype, fieldname in (("Encargo Contable", "cliente"), ("Contrato Comercial", "cliente"), ("Tarifa Cliente Servicio", "cliente"), ("Periodo Contable", "cliente"), ("Project", "customer")):
        if not frappe.db.exists("DocType", doctype):
            continue
        values = _get_demo_customer_names() if doctype == "Project" else cliente_names
        filter_field = "customer" if doctype == "Project" else fieldname
        for name in frappe.get_all(doctype, filters={filter_field: ["in", values or [""]]}, pluck="name"):
            _force_delete(doctype, name)


def _delete_demo_customers(cliente_names, customer_names):
    for name in cliente_names:
        _force_delete("Cliente Contable", name)
    for name in customer_names:
        _force_delete("Customer", name)
    for service in SERVICE_CATALOG.values():
        _force_delete("Servicio Contable", service["service_name"])
        _force_delete("Item", service["hours_item"])
        _force_delete("Item", service["fixed_item"])


def _delete_demo_users():
    for email in frappe.get_all("User", filters={"email": ["like", f"%@{DEMO_USER_DOMAIN}"]}, pluck="name"):
        _force_delete("User", email)


def _delete_demo_files():
    for name in frappe.get_all("File", filters={"file_name": ["like", f"{DEMO_FILE_PREFIX}%"]}, pluck="name"):
        _force_delete("File", name)


def _delete_linked_artifacts(doctype, name):
    for comm in frappe.get_all("Communication", filters={"reference_doctype": doctype, "reference_name": name}, pluck="name"):
        _force_delete("Communication", comm)
    for todo in frappe.get_all("ToDo", filters={"reference_type": doctype, "reference_name": name}, pluck="name"):
        _force_delete("ToDo", todo)
    for comment in frappe.get_all("Comment", filters={"reference_doctype": doctype, "reference_name": name}, pluck="name"):
        _force_delete("Comment", comment)
    for file_name in frappe.get_all("File", filters={"attached_to_doctype": doctype, "attached_to_name": name}, pluck="name"):
        _force_delete("File", file_name)


def _force_delete(doctype, name):
    if name and frappe.db.exists(doctype, name):
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)


@contextmanager
def _acting_as(user):
    previous_user = frappe.session.user
    if user:
        frappe.set_user(user)
    try:
        yield
    finally:
        frappe.set_user(previous_user)
