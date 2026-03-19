from frappe.utils import flt


def calcular_porcentaje(valor, base):
    base = flt(base)
    if base == 0:
        return 0
    return flt((flt(valor) / base) * 100)


def normalizar_texto(value):
    return (value or "").strip().lower()
