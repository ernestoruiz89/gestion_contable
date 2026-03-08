# Copyright (c) 2024, ernestoruiz89 and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from gestion_contable.gestion_contable.utils.dummy_data import clear_demo_dataset, generate_demo_dataset

DUMMY_TOOLS_SITE_CONFIG_KEY = "gestion_contable_enable_destructive_dummy_tools"


class ConfiguracionDespachoContable(Document):
    pass


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
    result = generate_demo_dataset(status_callback=_publish_dummy_progress)
    frappe.db.commit()
    return result


@frappe.whitelist()
def limpiar_datos_dummy():
    _ensure_dummy_tools_enabled()
    result = clear_demo_dataset(status_callback=_publish_dummy_progress, commit=False)
    frappe.db.commit()
    return result


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


def _publish_dummy_progress(message):
    frappe.publish_realtime("msgprint", {"message": message, "title": "Data Demo"})
