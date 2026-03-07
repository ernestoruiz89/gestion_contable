from gestion_contable.gestion_contable.setup.email_templates import ensure_standard_email_templates
from gestion_contable.gestion_contable.setup.workflows import ensure_native_workflows


def after_install():
    ensure_native_workflows()
    ensure_standard_email_templates()


def after_migrate():
    ensure_native_workflows()
    ensure_standard_email_templates()
