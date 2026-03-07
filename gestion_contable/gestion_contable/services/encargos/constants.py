ESTADOS_CERRADOS = ("Cerrado", "Cancelado")
ESTADOS_CONTRATO_VALIDOS = ("Aprobado", "Vigente")
MODALIDADES_HORAS = ("Por Hora", "Mixto")
MODALIDADES_FIJO = ("Fijo", "Mixto")
AVANCE_ESTADO_SIN_HITOS = {
    "Planificado": 0,
    "En Ejecucion": 50,
    "En Revision": 85,
    "Cerrado": 100,
    "Cancelado": 0,
}
ENCARGO_CONTENT_FIELDS = (
    "nombre_del_encargo", "cliente", "contrato_comercial", "plantilla_encargo_contable", "project", "servicio_contable", "tipo_de_servicio", "estado",
    "fecha_de_inicio", "fecha_fin_estimada", "periodo_referencia", "responsable", "company", "moneda", "modalidad_honorario",
    "tarifa_hora", "honorario_fijo", "costo_interno_hora", "presupuesto_horas", "presupuesto_monto", "descripcion", "hitos",
)
ENCARGO_CREATE_ROLES = (
    "System Manager",
    "Contador del Despacho",
    "Supervisor del Despacho",
    "Socio del Despacho",
)
