import frappe


VALID_COMMUNICATION_MEDIA = {
    "Email",
    "Chat",
    "Phone",
    "SMS",
    "Event",
    "Meeting",
    "Visit",
    "Other",
}

COMMUNICATION_MEDIA_ALIASES = {
    "Correo": "Email",
    "Correo electr?nico": "Email",
    "Email": "Email",
    "Portal": "Other",
    "Telefono": "Phone",
    "Tel?fono": "Phone",
    "Llamada": "Phone",
    "Phone": "Phone",
    "Reunion": "Meeting",
    "Reuni?n": "Meeting",
    "Meeting": "Meeting",
    "Visita": "Visit",
    "Visit": "Visit",
    "Evento": "Event",
    "Event": "Event",
    "WhatsApp": "Chat",
    "Otro": "Other",
    "Other": "Other",
}


def _normalize_communication_medium(communication_medium):
    if not communication_medium:
        return None
    normalized = COMMUNICATION_MEDIA_ALIASES.get(communication_medium, communication_medium)
    if normalized not in VALID_COMMUNICATION_MEDIA:
        return None
    return normalized


def log_linked_communication(
    reference_doctype,
    reference_name,
    *,
    subject,
    content,
    recipients=None,
    sender=None,
    sender_full_name=None,
    communication_medium=None,
):
    if not subject and not content:
        return None
    if not frappe.db.exists("DocType", "Communication"):
        return None

    payload = {
        "doctype": "Communication",
        "communication_type": "Communication",
        "sent_or_received": "Sent",
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "subject": (subject or "").strip(),
        "content": (content or "").strip(),
        "sender": sender or frappe.session.user,
        "sender_full_name": sender_full_name or frappe.utils.get_fullname(frappe.session.user),
        "recipients": recipients or None,
    }
    normalized_medium = _normalize_communication_medium(communication_medium)
    if normalized_medium:
        payload["communication_medium"] = normalized_medium

    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name
