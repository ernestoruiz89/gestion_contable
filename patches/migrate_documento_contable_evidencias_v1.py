import frappe


def execute():
    if not frappe.db.exists("DocType", "Documento Contable") or not frappe.db.exists("DocType", "Evidencia Documental"):
        return

    documentos = frappe.get_all(
        "Documento Contable",
        filters={"archivo_adjunto": ["is", "set"]},
        fields=["name", "archivo_adjunto", "tipo", "titulo_del_documento"],
        limit_page_length=0,
    )

    for row in documentos:
        doc = frappe.get_doc("Documento Contable", row.name)
        if doc.evidencias_documentales:
            continue

        doc.append(
            "evidencias_documentales",
            {
                "descripcion_evidencia": row.titulo_del_documento or row.name,
                "tipo_documental": row.tipo or "Otro",
                "origen_documental": "Otro",
                "confidencialidad": "Confidencial",
                "politica_retencion": "Sin Definir",
                "numero_version": 1,
                "es_version_vigente": 1,
                "es_principal": 1,
                "archivo": row.archivo_adjunto,
            },
        )
        doc.flags.ignore_governance_validation = True
        doc.save(ignore_permissions=True)
