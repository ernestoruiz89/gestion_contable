import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, getdate, nowdate

from gestion_contable.gestion_contable.doctype.cliente_contable.cliente_contable import get_cliente_defaults
from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import validate_periodo_operativo
from gestion_contable.gestion_contable.services.encargos import planning as planning_service
from gestion_contable.gestion_contable.services.encargos.constants import (
    ESTADOS_CONTRATO_VALIDOS,
    MODALIDADES_FIJO,
    MODALIDADES_HORAS,
)
from gestion_contable.gestion_contable.utils.governance import ESTADO_APROBACION_APROBADO


def validar_cliente_activo(doc):
    if not doc.cliente:
        return
    estado = frappe.db.get_value("Cliente Contable", doc.cliente, "estado")
    if estado != "Activo":
        frappe.throw(
            _("No se puede crear un encargo para el cliente <b>{0}</b> porque su estado es <b>{1}</b>.").format(doc.cliente, estado),
            title=_("Cliente Inactivo"),
        )


def obtener_servicio(doc):
    if not doc.servicio_contable:
        return None
    servicio = frappe.db.get_value(
        "Servicio Contable",
        doc.servicio_contable,
        ["name", "activo", "tipo_de_servicio", "company", "moneda", "item_horas", "item_honorario_fijo", "tarifa_hora", "honorario_fijo", "costo_interno_hora", "plantilla_encargo_contable"],
        as_dict=True,
    )
    if not servicio:
        frappe.throw(_("El servicio contable <b>{0}</b> no existe.").format(doc.servicio_contable), title=_("Servicio Invalido"))
    if not cint(servicio.activo):
        frappe.throw(_("El servicio contable <b>{0}</b> esta inactivo.").format(doc.servicio_contable), title=_("Servicio Inactivo"))
    return servicio


def obtener_contrato_comercial(doc):
    if not doc.contrato_comercial:
        return None
    contrato = frappe.db.get_value(
        "Contrato Comercial",
        doc.contrato_comercial,
        ["name", "cliente", "customer", "company", "moneda", "estado_aprobacion", "estado_comercial", "fecha_inicio", "fecha_fin"],
        as_dict=True,
    )
    if not contrato:
        frappe.throw(_("El contrato comercial <b>{0}</b> no existe.").format(doc.contrato_comercial), title=_("Contrato Invalido"))
    return contrato


def obtener_plantilla_doc(doc, plantilla_name=None):
    plantilla_name = plantilla_name or doc.plantilla_encargo_contable
    if not plantilla_name and doc.servicio_contable:
        plantilla_name = frappe.db.get_value("Servicio Contable", doc.servicio_contable, "plantilla_encargo_contable")
        if plantilla_name and not doc.plantilla_encargo_contable:
            doc.plantilla_encargo_contable = plantilla_name
    if not plantilla_name:
        return None
    if not frappe.db.exists("Plantilla Encargo Contable", plantilla_name):
        frappe.throw(_("La plantilla de encargo <b>{0}</b> no existe.").format(plantilla_name), title=_("Plantilla Invalida"))
    return frappe.get_doc("Plantilla Encargo Contable", plantilla_name)


def sincronizar_desde_cliente(doc):
    if not doc.cliente:
        return
    defaults = get_cliente_defaults(doc.cliente)
    if defaults.company_default and not doc.company:
        doc.company = defaults.company_default
    if defaults.moneda_preferida and not doc.moneda:
        doc.moneda = defaults.moneda_preferida
    if defaults.responsable_operativo_default and not doc.responsable:
        doc.responsable = defaults.responsable_operativo_default


def sincronizar_desde_servicio(doc):
    servicio = obtener_servicio(doc)
    if not servicio:
        return
    if not doc.tipo_de_servicio:
        doc.tipo_de_servicio = servicio.tipo_de_servicio
    elif servicio.tipo_de_servicio and doc.tipo_de_servicio != servicio.tipo_de_servicio:
        frappe.throw(_("El tipo de servicio del encargo no coincide con el servicio contable seleccionado."), title=_("Inconsistencia de Servicio"))
    if not doc.company and servicio.company:
        doc.company = servicio.company
    if not doc.moneda and servicio.moneda:
        doc.moneda = servicio.moneda
    if flt(doc.tarifa_hora) <= 0 and flt(servicio.tarifa_hora) > 0:
        doc.tarifa_hora = flt(servicio.tarifa_hora)
    if flt(doc.honorario_fijo) <= 0 and flt(servicio.honorario_fijo) > 0:
        doc.honorario_fijo = flt(servicio.honorario_fijo)
    if flt(doc.costo_interno_hora) <= 0 and flt(servicio.costo_interno_hora) > 0:
        doc.costo_interno_hora = flt(servicio.costo_interno_hora)
    if servicio.plantilla_encargo_contable and not doc.plantilla_encargo_contable:
        doc.plantilla_encargo_contable = servicio.plantilla_encargo_contable


def sincronizar_desde_contrato(doc):
    contrato = obtener_contrato_comercial(doc)
    if not contrato:
        return
    if doc.cliente and contrato.cliente and doc.cliente != contrato.cliente:
        frappe.throw(_("El cliente del encargo no coincide con el contrato comercial vinculado."), title=_("Contrato Inconsistente"))
    if contrato.cliente and not doc.cliente:
        doc.cliente = contrato.cliente
    if contrato.company and not doc.company:
        doc.company = contrato.company
    if contrato.moneda and not doc.moneda:
        doc.moneda = contrato.moneda
    if contrato.fecha_inicio and not doc.fecha_de_inicio:
        doc.fecha_de_inicio = contrato.fecha_inicio
    if contrato.fecha_fin and not doc.fecha_fin_estimada:
        doc.fecha_fin_estimada = contrato.fecha_fin
    alcance = obtener_alcance_contractual(doc, fecha=doc.fecha_de_inicio)
    if alcance:
        doc.modalidad_honorario = alcance.modalidad_tarifa or doc.modalidad_honorario
        if flt(doc.tarifa_hora) <= 0 and flt(alcance.tarifa_hora) > 0:
            doc.tarifa_hora = flt(alcance.tarifa_hora)
        if flt(doc.honorario_fijo) <= 0 and flt(alcance.honorario_fijo) > 0:
            doc.honorario_fijo = flt(alcance.honorario_fijo)


def sincronizar_desde_plantilla(doc):
    plantilla = obtener_plantilla_doc(doc)
    if not plantilla:
        return
    if plantilla.tipo_de_servicio and not doc.tipo_de_servicio:
        doc.tipo_de_servicio = plantilla.tipo_de_servicio
    if plantilla.modalidad_honorario_sugerida and (doc.is_new() or not doc.modalidad_honorario):
        doc.modalidad_honorario = plantilla.modalidad_honorario_sugerida
    if flt(doc.presupuesto_horas) <= 0 and flt(plantilla.presupuesto_horas_sugerido) > 0:
        doc.presupuesto_horas = flt(plantilla.presupuesto_horas_sugerido)
    if flt(doc.presupuesto_monto) <= 0 and flt(plantilla.presupuesto_monto_sugerido) > 0:
        doc.presupuesto_monto = flt(plantilla.presupuesto_monto_sugerido)
    if not doc.fecha_fin_estimada and doc.fecha_de_inicio and cint(plantilla.duracion_dias_sugerida) > 0:
        doc.fecha_fin_estimada = add_to_date(doc.fecha_de_inicio, days=max(cint(plantilla.duracion_dias_sugerida) - 1, 0), as_string=True)
    if doc.is_new() and not doc.hitos:
        planning_service.construir_hitos_desde_plantilla(doc, plantilla, replace=True)


def obtener_alcance_contractual(doc, fecha=None):
    if not doc.contrato_comercial or not doc.servicio_contable:
        return None
    fecha = getdate(fecha or doc.fecha_de_inicio or nowdate())
    lineas = frappe.get_all(
        "Alcance Contrato Comercial",
        filters={"parent": doc.contrato_comercial, "parenttype": "Contrato Comercial", "parentfield": "alcances", "servicio_contable": doc.servicio_contable, "activa": 1},
        fields=["name", "periodicidad", "modalidad_tarifa", "horas_incluidas", "tarifa_hora", "honorario_fijo", "fecha_inicio", "fecha_fin", "sla_respuesta_horas", "sla_entrega_dias"],
        order_by="idx asc",
        limit_page_length=50,
    )
    for linea in lineas:
        desde = getdate(linea.fecha_inicio) if linea.fecha_inicio else None
        hasta = getdate(linea.fecha_fin) if linea.fecha_fin else None
        if desde and fecha < desde:
            continue
        if hasta and fecha > hasta:
            continue
        return linea
    return None


def validar_periodo_referencia(doc):
    if not doc.periodo_referencia:
        return
    validate_periodo_operativo(
        doc.periodo_referencia,
        cliente=doc.cliente,
        company=doc.company,
        allow_closed=True,
        label=_("el encargo"),
    )


def validar_contrato_comercial(doc):
    contrato = obtener_contrato_comercial(doc)
    if not contrato:
        return
    if contrato.estado_aprobacion != ESTADO_APROBACION_APROBADO:
        frappe.throw(_("El contrato comercial debe estar aprobado antes de vincularlo a un encargo."), title=_("Contrato No Aprobado"))
    if contrato.estado_comercial not in ESTADOS_CONTRATO_VALIDOS:
        frappe.throw(_("El contrato comercial debe estar en estado Aprobado o Vigente para usarse en un encargo."), title=_("Contrato No Vigente"))
    if not doc.servicio_contable:
        frappe.throw(_("Debes seleccionar un servicio contable para validar el alcance contractual del encargo."), title=_("Servicio Requerido"))
    fecha_inicio = getdate(doc.fecha_de_inicio or nowdate())
    if contrato.fecha_inicio and fecha_inicio < getdate(contrato.fecha_inicio):
        frappe.throw(_("La fecha de inicio del encargo no puede ser anterior al inicio del contrato comercial."), title=_("Fuera de Vigencia"))
    if contrato.fecha_fin and fecha_inicio > getdate(contrato.fecha_fin):
        frappe.throw(_("La fecha de inicio del encargo no puede ser posterior al fin del contrato comercial."), title=_("Fuera de Vigencia"))
    if doc.fecha_fin_estimada and contrato.fecha_fin and getdate(doc.fecha_fin_estimada) > getdate(contrato.fecha_fin):
        frappe.throw(_("La fecha fin estimada del encargo excede la vigencia del contrato comercial."), title=_("Fuera de Vigencia"))
    alcance = obtener_alcance_contractual(doc, fecha=fecha_inicio)
    if not alcance:
        frappe.throw(_("El servicio <b>{0}</b> no esta cubierto por el contrato comercial seleccionado.").format(doc.servicio_contable), title=_("Fuera de Alcance"))


def validar_plantilla_encargo(doc):
    plantilla = obtener_plantilla_doc(doc)
    if not plantilla:
        return
    if not cint(plantilla.activa):
        frappe.throw(_("La plantilla de encargo seleccionada debe estar activa."), title=_("Plantilla Inactiva"))
    if doc.tipo_de_servicio and plantilla.tipo_de_servicio and doc.tipo_de_servicio != plantilla.tipo_de_servicio:
        frappe.throw(_("El tipo de servicio del encargo no coincide con la plantilla seleccionada."), title=_("Plantilla Inconsistente"))
    if doc.servicio_contable and plantilla.servicio_contable and doc.servicio_contable != plantilla.servicio_contable:
        frappe.throw(_("La plantilla seleccionada corresponde a otro servicio contable especifico."), title=_("Plantilla Inconsistente"))


def obtener_tarifa_cliente_servicio(doc, fecha=None):
    if not doc.cliente or not doc.servicio_contable:
        return None
    if not frappe.db.exists("DocType", "Tarifa Cliente Servicio"):
        return None
    fecha = getdate(fecha or doc.fecha_de_inicio or nowdate())
    tarifas = frappe.get_all(
        "Tarifa Cliente Servicio",
        filters={"cliente": doc.cliente, "servicio_contable": doc.servicio_contable, "activa": 1},
        fields=["name", "vigencia_desde", "vigencia_hasta", "tarifa_hora", "honorario_fijo", "contrato_comercial"],
        order_by="vigencia_desde desc, modified desc",
        limit_page_length=100,
    )
    generica = None
    for tarifa in tarifas:
        desde = getdate(tarifa.vigencia_desde) if tarifa.vigencia_desde else None
        hasta = getdate(tarifa.vigencia_hasta) if tarifa.vigencia_hasta else None
        if desde and fecha < desde:
            continue
        if hasta and fecha > hasta:
            continue
        if doc.contrato_comercial:
            if tarifa.contrato_comercial == doc.contrato_comercial:
                return tarifa
            if tarifa.contrato_comercial:
                continue
            if not generica:
                generica = tarifa
            continue
        if tarifa.contrato_comercial:
            continue
        return tarifa
    return generica


def resolver_tarifas(doc, fecha=None):
    tarifa_hora = flt(doc.tarifa_hora)
    honorario_fijo = flt(doc.honorario_fijo)
    fuente = _("Encargo")
    alcance = obtener_alcance_contractual(doc, fecha=fecha)
    if alcance:
        if tarifa_hora <= 0 and flt(alcance.tarifa_hora) > 0:
            tarifa_hora = flt(alcance.tarifa_hora)
        if honorario_fijo <= 0 and flt(alcance.honorario_fijo) > 0:
            honorario_fijo = flt(alcance.honorario_fijo)
        if tarifa_hora > 0 or honorario_fijo > 0:
            fuente = _("Contrato Comercial")

    servicio = obtener_servicio(doc)
    if servicio:
        if tarifa_hora <= 0 and flt(servicio.tarifa_hora) > 0:
            tarifa_hora = flt(servicio.tarifa_hora)
            fuente = _("Servicio")
        if honorario_fijo <= 0 and flt(servicio.honorario_fijo) > 0:
            honorario_fijo = flt(servicio.honorario_fijo)
            fuente = _("Servicio")

    tarifa_cliente = obtener_tarifa_cliente_servicio(doc, fecha=fecha)
    if tarifa_cliente:
        if flt(tarifa_cliente.tarifa_hora) > 0:
            tarifa_hora = flt(tarifa_cliente.tarifa_hora)
        if flt(tarifa_cliente.honorario_fijo) > 0:
            honorario_fijo = flt(tarifa_cliente.honorario_fijo)
        fuente = _("Tarifa Contractual") if tarifa_cliente.contrato_comercial else _("Tarifa Cliente/Servicio")
    return tarifa_hora, honorario_fijo, fuente


def validar_tarifas(doc):
    doc.modalidad_honorario = doc.modalidad_honorario or "Por Hora"
    if flt(doc.costo_interno_hora) < 0:
        frappe.throw(_("El costo interno por hora no puede ser negativo."), title=_("Costo Invalido"))
    if not doc.servicio_contable and flt(doc.tarifa_hora) <= 0 and flt(doc.honorario_fijo) <= 0:
        return
    tarifa_hora, honorario_fijo, _ = resolver_tarifas(doc)
    if doc.modalidad_honorario in MODALIDADES_HORAS and tarifa_hora <= 0:
        frappe.throw(_("Debes definir una tarifa por hora para la modalidad seleccionada."), title=_("Tarifa Incompleta"))
    if doc.modalidad_honorario in MODALIDADES_FIJO and honorario_fijo <= 0:
        frappe.throw(_("Debes definir un honorario fijo para la modalidad seleccionada."), title=_("Tarifa Incompleta"))
