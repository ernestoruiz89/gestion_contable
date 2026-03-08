# Copyright (c) 2026, Despacho and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class VersionDocumentoEEFF(Document):
    pass


# Backward-compatible alias in case Frappe resolves the acronym as title-case.
class VersionDocumentoEeff(VersionDocumentoEEFF):
    pass
