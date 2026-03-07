import frappe


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
    if communication_medium:
        payload["communication_medium"] = communication_medium

    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name
