import hashlib
import io
import re
from html import unescape

import frappe
from frappe import _
from frappe.utils import cint, cstr, now_datetime

REPORT_TITLE = "Informe Completo de EEFF Auditados"


def export_audited_financial_package_to_word(package_name):
    package = frappe.get_doc("Paquete Estados Financieros Cliente", package_name)
    if not package.dictamen_de_auditoria:
        frappe.throw(
            _("El paquete debe tener un Dictamen de Auditoria vinculado para exportarse a Word."),
            title=_("Dictamen Requerido"),
        )

    dictamen = frappe.get_doc("Informe Final Auditoria", package.dictamen_de_auditoria)
    if dictamen.tipo_de_informe != "Dictamen de Auditoria":
        frappe.throw(
            _("El documento vinculado en Dictamen de Auditoria no corresponde a un dictamen valido."),
            title=_("Dictamen Invalido"),
        )

    document = _build_audited_package_document(package, dictamen)
    stream = io.BytesIO()
    document.save(stream)
    content = stream.getvalue()
    stream.close()

    from frappe.utils.file_manager import save_file

    file_name = _build_word_export_filename(package.name)
    file_doc = save_file(file_name, content, "Paquete Estados Financieros Cliente", package.name, is_private=1)
    version_info = _register_package_document_version(
        package.name,
        tipo_documento="Word Revision Cliente",
        file_doc=file_doc,
        content_hash=hashlib.sha256(content).hexdigest(),
        estado_documento="Generado",
        observaciones="Documento Word generado para revision del cliente.",
    )
    return {
        "file_name": file_doc.file_name,
        "file_url": file_doc.file_url,
        "file_id": file_doc.name,
        "version_documento": version_info["version_documento"],
        "tipo_documento": version_info["tipo_documento"],
    }


def _build_audited_package_document(package, dictamen):
    try:
        from docx import Document
        from docx.enum.section import WD_SECTION
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt
    except ImportError:
        frappe.throw(
            _("No esta instalada la dependencia opcional python-docx. Instala la dependencia en el sitio con <b>bench pip install python-docx</b> para habilitar la exportacion Word."),
            title=_("Dependencia Faltante"),
        )

    document = Document()
    _configure_document(document, package, dictamen, WD_ALIGN_PARAGRAPH, OxmlElement, qn, Cm, Pt)

    document.add_paragraph(REPORT_TITLE, style="Title")
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph(style="Subtitle")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(package.razon_social_reportante or package.cliente or "Cliente")

    badge = document.add_paragraph()
    badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    badge_run = badge.add_run("Documento formal de revision y entrega al cliente")
    badge_run.italic = True

    document.add_paragraph()
    cover_table = document.add_table(rows=4, cols=2)
    cover_table.style = "Table Grid"
    cover_pairs = [
        ("Cliente", package.cliente or "-"),
        ("Razon social reportante", package.razon_social_reportante or "-"),
        ("Identificacion fiscal", package.identificacion_fiscal_reportante or "-"),
        ("Periodo", package.periodo_contable or "-"),
        ("Fecha de corte", cstr(package.fecha_corte or "-")),
        ("Fecha de emision", cstr(package.fecha_emision or "-")),
        ("Marco contable", package.marco_contable or "-"),
        ("Version", cstr(package.version or "-")),
    ]
    for index, pair in enumerate(cover_pairs):
        row = cover_table.rows[index // 2]
        cell = row.cells[index % 2]
        _fill_label_value_cell(cell, pair[0], pair[1])

    summary = document.add_paragraph()
    summary.add_run(
        "Se presenta el juego completo de estados financieros auditados, sus notas y el dictamen de auditoria independiente para revision del cliente."
    )

    document.add_page_break()
    toc_heading = document.add_paragraph("Indice", style="Heading 1")
    toc_heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
    toc_paragraph = document.add_paragraph()
    _append_field(toc_paragraph, 'TOC \\o "1-3" \\h \\z \\u', "Actualice la tabla de contenido al abrir el documento en Word.", OxmlElement, qn)
    document.add_paragraph("Nota: si Word no actualiza el indice automaticamente, use Actualizar campo.")
    document.add_page_break()

    _add_dictamen_section(document, dictamen)
    document.add_page_break()
    _add_estados_section(document, package)
    document.add_page_break()
    _add_notas_section(document, package)
    document.add_page_break()
    _add_delivery_section(document, package, dictamen)

    return document


def _configure_document(document, package, dictamen, WD_ALIGN_PARAGRAPH, OxmlElement, qn, Cm, Pt):
    styles = document.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10.5)
    styles["Title"].font.name = "Calibri"
    styles["Title"].font.size = Pt(22)
    styles["Heading 1"].font.name = "Calibri"
    styles["Heading 1"].font.size = Pt(16)
    styles["Heading 2"].font.name = "Calibri"
    styles["Heading 2"].font.size = Pt(13)
    styles["Heading 3"].font.name = "Calibri"
    styles["Heading 3"].font.size = Pt(11)

    for section in document.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.3)
        section.right_margin = Cm(2.0)
        section.header_distance = Cm(1.1)
        section.footer_distance = Cm(1.2)

        header = section.header
        header_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header_para.text = f"{package.razon_social_reportante or package.cliente or '-'} | {REPORT_TITLE}"
        if header_para.runs:
            header_para.runs[0].font.size = Pt(9)

        footer = section.footer
        footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.add_run(f"{package.periodo_contable or '-'} | ")
        _append_field(footer_para, "PAGE", "1", OxmlElement, qn)
        footer_para.add_run(" de ")
        _append_field(footer_para, "NUMPAGES", "1", OxmlElement, qn)
        footer_para.add_run(f" | Generado {now_datetime().strftime('%Y-%m-%d %H:%M')}")
        for run in footer_para.runs:
            run.font.size = Pt(8.5)


def _append_field(paragraph, instruction, placeholder, OxmlElement, qn):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def _add_dictamen_section(document, dictamen):
    opinion_standard = "NIA 700" if dictamen.tipo_opinion == "Favorable" else "NIA 705"
    document.add_paragraph("Dictamen de Auditoria", style="Heading 1")
    meta = document.add_paragraph()
    meta.add_run(f"Tipo de opinion: {dictamen.tipo_opinion or '-'}")
    meta.add_run(f" | Destinatario: {dictamen.destinatario or '-'}")
    meta.add_run(f" | Fecha: {dictamen.fecha_informe or '-'}")

    _add_rich_section(document, f"Opinion del Auditor ({opinion_standard})", dictamen.opinion_o_conclusion)
    _add_rich_section(document, f"Fundamento de la Opinion ({opinion_standard})", dictamen.fundamento_opinion)

    if dictamen.tipo_opinion in ("Con Salvedades", "Adversa", "Abstencion"):
        _add_rich_section(document, "Asunto que Origina la Modificacion (NIA 705)", dictamen.asunto_que_origina_modificacion)
        modified_title = "Fundamento de la Abstencion (NIA 705)" if dictamen.tipo_opinion == "Abstencion" else "Fundamento de la Opinion Modificada (NIA 705)"
        _add_rich_section(document, modified_title, dictamen.fundamento_salvedad)

    if dictamen.parrafo_enfasis:
        _add_rich_section(document, "Parrafo de Enfasis (NIA 706)", dictamen.parrafo_enfasis)
    if dictamen.parrafo_otros_asuntos:
        _add_rich_section(document, "Parrafo de Otros Asuntos (NIA 706)", dictamen.parrafo_otros_asuntos)

    _add_rich_section(document, "Responsabilidades de la Administracion", dictamen.responsabilidades_administracion)
    _add_rich_section(document, "Responsabilidades del Auditor", dictamen.responsabilidades_auditor)
    _add_rich_section(document, "Conclusion Final", dictamen.conclusion_final)

    sign = document.add_paragraph()
    sign.add_run(dictamen.firmado_por or "-").bold = True
    if dictamen.cargo_firmante:
        sign.add_run(f"\n{dictamen.cargo_firmante}")


def _add_estados_section(document, package):
    document.add_paragraph("Estados Financieros", style="Heading 1")
    estados = frappe.get_all(
        "Estado Financiero Cliente",
        filters={"paquete_estados_financieros_cliente": package.name},
        fields=["name", "tipo_estado", "titulo_formal", "subtitulo", "orden_presentacion"],
        order_by="orden_presentacion asc, creation asc",
        limit_page_length=100,
    )
    if not estados:
        document.add_paragraph("No hay estados financieros registrados para este paquete.")
        return

    for estado in estados:
        estado_doc = frappe.get_doc("Estado Financiero Cliente", estado.name)
        document.add_paragraph(estado_doc.titulo_formal or estado_doc.tipo_estado, style="Heading 2")
        if estado_doc.subtitulo:
            document.add_paragraph(estado_doc.subtitulo)
        table = document.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        headers = ["Descripcion", "Monto Actual", "Monto Comparativo", "Nota"]
        for index, title in enumerate(headers):
            table.rows[0].cells[index].text = title
        for linea in estado_doc.lineas:
            row = table.add_row().cells
            descripcion = ("    " * max((linea.nivel or 1) - 1, 0)) + (linea.descripcion or "-")
            row[0].text = descripcion
            row[1].text = _fmt_number(linea.monto_actual)
            row[2].text = _fmt_number(linea.monto_comparativo)
            row[3].text = cstr(linea.numero_nota_referencial or "-")
        document.add_paragraph()


def _add_notas_section(document, package):
    document.add_paragraph("Notas a los Estados Financieros", style="Heading 1")
    notas = frappe.get_all(
        "Nota Estado Financiero",
        filters={"paquete_estados_financieros_cliente": package.name},
        fields=["name", "numero_nota", "titulo", "orden_presentacion", "estado_aprobacion", "total_referencias"],
        order_by="orden_presentacion asc, creation asc",
        limit_page_length=300,
    )
    if not notas:
        document.add_paragraph("No hay notas registradas para este paquete.")
        return

    for nota in notas:
        nota_doc = frappe.get_doc("Nota Estado Financiero", nota.name)
        document.add_paragraph(f"Nota {nota_doc.numero_nota}. {nota_doc.titulo or 'Sin titulo'}", style="Heading 2")
        meta = document.add_paragraph()
        meta.add_run(f"Categoria: {nota_doc.categoria_nota or '-'}")
        meta.add_run(f" | Estado: {nota_doc.estado_aprobacion or '-'}")
        meta.add_run(f" | Referencias: {nota_doc.total_referencias or 0}")

        if nota_doc.referencias_cruzadas:
            document.add_paragraph("Referencias cruzadas", style="Heading 3")
            for ref in nota_doc.referencias_cruzadas:
                parts = [ref.tipo_estado or "Estado"]
                if ref.codigo_rubro:
                    parts.append(ref.codigo_rubro)
                if ref.descripcion_linea_estado:
                    parts.append(ref.descripcion_linea_estado)
                document.add_paragraph(" | ".join(parts), style="List Bullet")

        if nota_doc.politica_contable:
            _add_rich_section(document, "Politica contable", nota_doc.politica_contable, level=3)
        if nota_doc.contenido_narrativo:
            _add_rich_section(document, "Contenido narrativo", nota_doc.contenido_narrativo, level=3)

        if nota_doc.cifras_nota:
            document.add_paragraph("Cifras de la nota", style="Heading 3")
            table = document.add_table(rows=1, cols=5)
            table.style = "Table Grid"
            headers = ["Concepto", "Subconcepto", "Monto Actual", "Monto Comparativo", "Comentario"]
            for index, title in enumerate(headers):
                table.rows[0].cells[index].text = title
            for cifra in nota_doc.cifras_nota:
                row = table.add_row().cells
                row[0].text = cstr(cifra.concepto or "-")
                row[1].text = cstr(cifra.subconcepto or "-")
                row[2].text = _fmt_number(cifra.monto_actual)
                row[3].text = _fmt_number(cifra.monto_comparativo)
                row[4].text = cstr(cifra.comentario or "-")
        document.add_paragraph()


def _add_delivery_section(document, package, dictamen):
    document.add_paragraph("Constancia de Entrega", style="Heading 1")
    paragraph = document.add_paragraph()
    paragraph.add_run("Se deja constancia de la entrega formal del presente informe completo de estados financieros auditados, incluyendo dictamen, estados financieros y notas, para revision del cliente.")

    table = document.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    _fill_label_value_cell(table.rows[0].cells[0], "Documento", package.name)
    _fill_label_value_cell(table.rows[0].cells[1], "Fecha de entrega", cstr(package.fecha_emision or "-"))
    _fill_label_value_cell(table.rows[1].cells[0], "Destinatario", dictamen.destinatario or "-")
    _fill_label_value_cell(table.rows[1].cells[1], "Dictamen", package.dictamen_de_auditoria or "-")

    document.add_paragraph()
    sign_table = document.add_table(rows=2, cols=3)
    sign_table.style = "Table Grid"
    labels = [
        dictamen.firmado_por or "____________________________",
        dictamen.revisado_por or "____________________________",
        dictamen.destinatario or "____________________________",
    ]
    roles = [
        dictamen.cargo_firmante or "Responsable de emision",
        "Revisor interno",
        "Recibido por el cliente",
    ]
    for index in range(3):
        sign_table.rows[0].cells[index].text = "\n\n\n"
        sign_table.rows[1].cells[index].text = f"{labels[index]}\n{roles[index]}"


def _fill_label_value_cell(cell, label, value):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.add_run(f"{label}\n").bold = True
    paragraph.add_run(cstr(value or "-"))


def _add_rich_section(document, heading, raw_value, level=2):
    document.add_paragraph(heading, style=f"Heading {level}")
    text = _html_to_text(raw_value)
    if not text:
        document.add_paragraph("Sin contenido.")
        return
    for block in [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]:
        document.add_paragraph(block)


def _html_to_text(value):
    text = cstr(value or "")
    if not text.strip():
        return ""
    replacements = (
        (r"<br\s*/?>", "\n"),
        (r"</p>", "\n\n"),
        (r"</div>", "\n"),
        (r"</li>", "\n"),
        (r"<li[^>]*>", "• "),
        (r"</h[1-6]>", "\n"),
    )
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fmt_number(value):
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return cstr(value)


def _build_word_export_filename(package_name):
    safe_name = _sanitize_filename(package_name)
    base_name = f"{REPORT_TITLE} - {safe_name}" if safe_name else REPORT_TITLE
    max_base_length = 135 - len(".docx")
    base_name = base_name[:max_base_length].rstrip(" -_")
    return f"{base_name}.docx"


def _sanitize_filename(value):
    filename = re.sub(r'[\\/:*?"<>|]+', '-', cstr(value or REPORT_TITLE)).strip()
    return filename or REPORT_TITLE


def _register_package_document_version(package_name, tipo_documento, file_doc, content_hash=None, estado_documento="Generado", observaciones=None):
    package = frappe.get_doc("Paquete Estados Financieros Cliente", package_name)
    rows = list(package.get("versiones_documento_eeff") or [])
    current_versions = [cint(row.version_documento) for row in rows if row.tipo_documento == tipo_documento]
    next_version = max(current_versions or [0]) + 1

    for row in rows:
        if row.tipo_documento == tipo_documento and cint(row.es_version_vigente):
            row.es_version_vigente = 0
            if row.estado_documento == "Generado":
                row.estado_documento = "Reemplazado"

    package.append("versiones_documento_eeff", {
        "tipo_documento": tipo_documento,
        "version_documento": next_version,
        "estado_documento": estado_documento,
        "es_version_vigente": 1,
        "fecha_generacion": now_datetime(),
        "generado_por": frappe.session.user,
        "archivo_file": file_doc.name,
        "nombre_archivo": file_doc.file_name,
        "archivo_url": file_doc.file_url,
        "hash_sha256": content_hash,
        "observaciones": observaciones,
    })
    package.save(ignore_permissions=True)
    return {
        "tipo_documento": tipo_documento,
        "version_documento": next_version,
    }
