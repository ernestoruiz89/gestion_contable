import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, getdate, nowdate

from gestion_contable.gestion_contable.services.encargos.common import normalizar_texto
from gestion_contable.gestion_contable.services.encargos.constants import (
    AVANCE_ESTADO_SIN_HITOS,
    MODALIDADES_FIJO,
    MODALIDADES_HORAS,
)


def construir_hitos_desde_plantilla(doc, plantilla, replace=False):
    if replace:
        doc.set("hitos", [])

    existentes = {normalizar_texto(row.titulo) for row in doc.hitos or [] if row.titulo}
    fecha_inicio = getdate(doc.fecha_de_inicio or nowdate())
    creados = 0
    for row in sorted(plantilla.hitos or [], key=lambda h: (cint(h.orden) or 0, cint(h.idx) or 0)):
        titulo_key = normalizar_texto(row.titulo)
        if not replace and titulo_key in existentes:
            continue
        fecha_planificada = add_to_date(fecha_inicio, days=cint(row.dias_desde_inicio), as_string=True)
        fecha_limite = add_to_date(fecha_planificada, days=max(cint(row.duracion_dias) - 1, 0), as_string=True)
        doc.append("hitos", {
            "orden": cint(row.orden) or ((row.idx or 0) + 1),
            "titulo": row.titulo,
            "descripcion": row.descripcion,
            "estado": "Pendiente",
            "fecha_planificada": fecha_planificada,
            "fecha_limite": fecha_limite,
            "porcentaje_avance": 0,
            "peso_porcentaje": flt(row.peso_porcentaje),
            "obligatorio": cint(row.obligatorio),
            "horas_planificadas": flt(row.horas_planificadas),
            "monto_planificado": flt(row.monto_planificado),
        })
        creados += 1
        existentes.add(titulo_key)
    return creados


def validar_hitos(doc):
    titulos = set()
    for index, row in enumerate(doc.hitos or [], start=1):
        if not row.titulo:
            frappe.throw(_("Cada hito del encargo debe tener titulo."))
        clave = normalizar_texto(row.titulo)
        if clave in titulos:
            frappe.throw(_("No puedes repetir hitos en el mismo encargo: <b>{0}</b>.").format(row.titulo), title=_("Hito Duplicado"))
        titulos.add(clave)
        row.orden = cint(row.orden) or index
        row.estado = row.estado or "Pendiente"
        row.porcentaje_avance = max(0, min(flt(row.porcentaje_avance), 100))
        row.peso_porcentaje = max(flt(row.peso_porcentaje), 0)
        row.horas_planificadas = flt(row.horas_planificadas)
        row.monto_planificado = flt(row.monto_planificado)
        if row.fecha_planificada and row.fecha_limite and getdate(row.fecha_planificada) > getdate(row.fecha_limite):
            frappe.throw(_("Un hito tiene fecha planificada posterior a su fecha limite."), title=_("Hito Invalido"))
        if row.fecha_cumplimiento:
            row.estado = "Completado"
            row.porcentaje_avance = 100
        elif row.estado == "Completado":
            row.porcentaje_avance = 100
            row.fecha_cumplimiento = row.fecha_cumplimiento or nowdate()
        elif row.estado == "Pendiente" and flt(row.porcentaje_avance) > 0:
            row.estado = "En Proceso"


def actualizar_indicadores_planeacion(doc):
    total_horas_hitos = flt(sum(flt(row.horas_planificadas) for row in doc.hitos or []))
    total_monto_hitos = flt(sum(flt(row.monto_planificado) for row in doc.hitos or []))
    if flt(doc.presupuesto_horas) <= 0 and total_horas_hitos > 0:
        doc.presupuesto_horas = total_horas_hitos
    if flt(doc.presupuesto_monto) <= 0 and total_monto_hitos > 0:
        doc.presupuesto_monto = total_monto_hitos
    if flt(doc.presupuesto_monto) <= 0:
        estimado = calcular_presupuesto_monto_estimado(doc)
        if estimado > 0:
            doc.presupuesto_monto = estimado

    doc.hitos_totales = len(doc.hitos or [])
    doc.hitos_completados = len([row for row in doc.hitos or [] if row.estado == "Completado"])
    hoy = getdate(nowdate())
    doc.hitos_vencidos = len([
        row for row in doc.hitos or []
        if row.estado not in ("Completado", "Cancelado") and row.fecha_limite and getdate(row.fecha_limite) < hoy
    ])
    doc.avance_hitos_pct = calcular_avance_hitos(doc)

    presupuesto_horas = flt(doc.presupuesto_horas)
    doc.consumo_horas_pct = flt((doc.horas_registradas / presupuesto_horas) * 100) if presupuesto_horas > 0 else 0
    doc.desviacion_horas = flt(doc.horas_registradas - presupuesto_horas) if presupuesto_horas > 0 else 0
    doc.desviacion_horas_pct = flt((doc.desviacion_horas / presupuesto_horas) * 100) if presupuesto_horas > 0 else 0

    doc.monto_real_ejecutado = calcular_monto_real_ejecutado(doc)
    presupuesto_monto = flt(doc.presupuesto_monto)
    doc.consumo_monto_pct = flt((doc.monto_real_ejecutado / presupuesto_monto) * 100) if presupuesto_monto > 0 else 0
    doc.desviacion_monto = flt(doc.monto_real_ejecutado - presupuesto_monto) if presupuesto_monto > 0 else 0
    doc.desviacion_monto_pct = flt((doc.desviacion_monto / presupuesto_monto) * 100) if presupuesto_monto > 0 else 0


def calcular_avance_hitos(doc):
    hitos = [row for row in doc.hitos or [] if row.estado != "Cancelado"]
    if not hitos:
        return flt(AVANCE_ESTADO_SIN_HITOS.get(doc.estado or "Planificado", 0))

    total_peso = flt(sum(flt(row.peso_porcentaje) for row in hitos if flt(row.peso_porcentaje) > 0))
    if total_peso > 0:
        return flt(sum(flt(row.peso_porcentaje) * flt(row.porcentaje_avance) for row in hitos) / total_peso)

    return flt(sum(flt(row.porcentaje_avance) for row in hitos) / len(hitos))


def calcular_presupuesto_monto_estimado(doc):
    tarifa_hora, honorario_fijo, _ = doc.resolver_tarifas()
    total = 0
    if doc.modalidad_honorario in MODALIDADES_HORAS and flt(doc.presupuesto_horas) > 0:
        total += flt(doc.presupuesto_horas) * flt(tarifa_hora)
    if doc.modalidad_honorario in MODALIDADES_FIJO:
        total += flt(honorario_fijo)
    return flt(total)


def calcular_monto_real_ejecutado(doc):
    tarifa_hora, honorario_fijo, _ = doc.resolver_tarifas()
    monto = 0
    if doc.modalidad_honorario in MODALIDADES_HORAS:
        monto += flt(doc.horas_registradas) * flt(tarifa_hora)

    if doc.modalidad_honorario in MODALIDADES_FIJO and flt(honorario_fijo) > 0:
        avance = flt(doc.avance_hitos_pct) / 100
        if doc.hitos_totales <= 0:
            avance = flt(AVANCE_ESTADO_SIN_HITOS.get(doc.estado or "Planificado", 0)) / 100
        monto += flt(honorario_fijo) * avance
    return flt(monto)
