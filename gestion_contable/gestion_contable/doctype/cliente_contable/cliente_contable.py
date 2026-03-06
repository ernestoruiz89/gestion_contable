from frappe.model.document import Document

from gestion_contable.gestion_contable.utils.security import ensure_manager


class ClienteContable(Document):
    def validate(self):
        ensure_manager()

    def on_trash(self):
        ensure_manager()
