import csv
import io
import json
import unicodedata

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, now_datetime

from gestion_contable.gestion_contable.utils.security import ensure_supervisor

REQUIRED_HEADERS = (
    "cuenta",
    "descripcion",
    "debe_mes_actual",
    "haber_mes_actual",
    "debe_saldo",
    "haber_saldo",
    "centro_costo",
    "periodo",
)

HEADER_ALIASES = {
    "cuenta": "cuenta",
    "codigo_cuenta": "cuenta",
    "codigo": "cuenta",
    "descripcion": "descripcion",
    "descripcion_cuenta": "descripcion",
    "debe_mes_actual": "debe_mes_actual",
    "debe_mes": "debe_mes_actual",
    "debe_actual": "debe_mes_actual",
    "haber_mes_actual": "haber_mes_actual",
    "haber_mes": "haber_mes_actual",
    "haber_actual": "haber_mes_actual",
    "debe_saldo": "debe_saldo",
    "saldo_debe": "debe_saldo",
    "haber_saldo": "haber_saldo",
    "saldo_haber": "haber_saldo",
    "centro_costo": "centro_costo",
    "centro_de_costo": "centro_costo",
    "cost_center": "centro_costo",
    "periodo": "periodo",
    "period": "periodo",
}


def _normalize_header(value):
    text = unicodedata.normalize("NFKD", cstr(value or "")).encode("ascii", "ignore").decode("ascii")
    text = "".join(char if char.isalnum() else "_" for char in text.lower())
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _detect_delimiter(content):
    header_line = next((line for line in cstr(content or "").splitlines() if line.strip()), "")
    candidates = [",", ";", "\t"]
    best = ","
    best_count = -1
    for candidate in candidates:
        count = header_line.count(candidate)
        if count > best_count:
            best = candidate
            best_count = count
    return best


def _decode_content(raw_content):
    if raw_content is None:
        return ""
    if isinstance(raw_content, str):
        return raw_content
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw_content.decode(encoding)
        except Exception:
            continue
    return raw_content.decode("utf-8", "ignore")


def _parse_numeric_value(value, row_no, label, errors):
    text = cstr(value or "").strip()
    if not text:
        return 0.0

    normalized = text.replace(" ", "").replace("$", "")
    is_negative_parentheses = normalized.startswith("(") and normalized.endswith(")")
    if is_negative_parentheses:
        normalized = normalized[1:-1]

    if normalized.count(",") and normalized.count("."):
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif normalized.count(","):
        if normalized.count(",") == 1:
            normalized = normalized.replace(",", ".")
        else:
            normalized = normalized.replace(",", "")

    try:
        amount = float(normalized)
    except (TypeError, ValueError):
        errors.append(_("Fila {0}: el valor de {1} debe ser numerico. Valor recibido: {2}.").format(row_no, label, cstr(value)))
        return 0.0

    return -amount if is_negative_parentheses else amount


def _throw_import_errors(errors):
    if not errors:
        return
    preview = errors[:20]
    message = "<br>".join(preview)
    if len(errors) > 20:
        message += "<br>" + _("...y {0} errores adicionales.").format(len(errors) - 20)
    frappe.throw(
        _("La importacion de la balanza contiene errores y no puede procesarse:<br>{0}").format(message),
        title=_("CSV Invalido"),
    )


def _resolve_file_document(file_reference):
    if not file_reference or not frappe.db.exists("DocType", "File"):
        return None
    if frappe.db.exists("File", file_reference):
        return frappe.get_doc("File", file_reference)
    file_rows = frappe.get_all(
        "File",
        filters={"file_url": file_reference},
        fields=["name"],
        order_by="creation desc",
        limit_page_length=1,
    )
    if not file_rows:
        return None
    return frappe.get_doc("File", file_rows[0].name)


def _get_version_source_file(version_doc):
    if version_doc.archivo_fuente:
        return _resolve_file_document(version_doc.archivo_fuente)

    if not version_doc.documento_contable_fuente or not frappe.db.exists("Documento Contable", version_doc.documento_contable_fuente):
        return None

    documento = frappe.get_doc("Documento Contable", version_doc.documento_contable_fuente)
    for row in documento.evidencias_documentales or []:
        if row.archivo_file and frappe.db.exists("File", row.archivo_file):
            return frappe.get_doc("File", row.archivo_file)
        if row.archivo:
            file_doc = _resolve_file_document(row.archivo)
            if file_doc:
                return file_doc

    if documento.archivo_adjunto:
        return _resolve_file_document(documento.archivo_adjunto)
    return None


def parse_balanza_csv(content):
    content = _decode_content(content)
    delimiter = _detect_delimiter(content)
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    if not reader.fieldnames:
        frappe.throw(_("El archivo CSV de balanza no contiene encabezados."), title=_("CSV Invalido"))

    header_map = {}
    for fieldname in reader.fieldnames:
        canonical = HEADER_ALIASES.get(_normalize_header(fieldname))
        if canonical:
            header_map[fieldname] = canonical

    missing = [header for header in REQUIRED_HEADERS if header not in header_map.values()]
    if missing:
        frappe.throw(
            _("El archivo CSV no contiene todas las columnas requeridas. Faltan: <b>{0}</b>.").format(", ".join(missing)),
            title=_("CSV Incompleto"),
        )

    rows = []
    errors = []
    for row_no, raw_row in enumerate(reader, start=2):
        if not any(cstr(value or "").strip() for value in (raw_row or {}).values()):
            continue

        mapped = {}
        for original_key, value in (raw_row or {}).items():
            canonical = header_map.get(original_key)
            if canonical:
                mapped[canonical] = value

        codigo_cuenta = cstr(mapped.get("cuenta") or "").strip()
        descripcion = cstr(mapped.get("descripcion") or "").strip()
        periodo_linea = cstr(mapped.get("periodo") or "").strip()
        row_errors = []
        if not codigo_cuenta:
            row_errors.append(_("Fila {0}: falta el valor de cuenta.").format(row_no))
        if not descripcion:
            row_errors.append(_("Fila {0}: falta la descripcion de la cuenta.").format(row_no))
        if not periodo_linea:
            row_errors.append(_("Fila {0}: falta el periodo de la linea.").format(row_no))

        debe_mes_actual = _parse_numeric_value(mapped.get("debe_mes_actual"), row_no, _("Debe Mes Actual"), row_errors)
        haber_mes_actual = _parse_numeric_value(mapped.get("haber_mes_actual"), row_no, _("Haber Mes Actual"), row_errors)
        debe_saldo = _parse_numeric_value(mapped.get("debe_saldo"), row_no, _("Debe Saldo"), row_errors)
        haber_saldo = _parse_numeric_value(mapped.get("haber_saldo"), row_no, _("Haber Saldo"), row_errors)
        if row_errors:
            errors.extend(row_errors)
            continue

        saldo_final = debe_saldo - haber_saldo
        rows.append(
            {
                "row_no": row_no,
                "codigo_cuenta": codigo_cuenta,
                "descripcion_cuenta": descripcion,
                "centro_costo": cstr(mapped.get("centro_costo") or "").strip(),
                "periodo_linea": periodo_linea,
                "debe_mes_actual": debe_mes_actual,
                "haber_mes_actual": haber_mes_actual,
                "debe_saldo": debe_saldo,
                "haber_saldo": haber_saldo,
                "saldo_final": saldo_final,
                "saldo_neto": saldo_final,
                "origen_linea": "Importada",
                "linea_fuente_externa": json.dumps(mapped, ensure_ascii=True),
            }
        )

    _throw_import_errors(errors)
    if not rows:
        frappe.throw(_("El archivo CSV no contiene filas validas para importar."), title=_("CSV Vacio"))
    return rows


def sync_version_summary(version_name):
    totals = frappe.db.sql(
        """
        SELECT
            COUNT(name) AS total_lineas,
            COALESCE(SUM(debe_mes_actual), 0) AS total_debe_mes_actual,
            COALESCE(SUM(haber_mes_actual), 0) AS total_haber_mes_actual,
            COALESCE(SUM(debe_saldo), 0) AS total_debe_saldo,
            COALESCE(SUM(haber_saldo), 0) AS total_haber_saldo,
            COALESCE(SUM(saldo_neto), 0) AS saldo_neto
        FROM `tabLinea Balanza Cliente`
        WHERE version_balanza_cliente = %s
        """,
        (version_name,),
        as_dict=True,
    )
    totals = totals[0] if totals else {}
    summary = {
        "total_lineas": cint(totals.get("total_lineas") or 0),
        "total_debe_mes_actual": flt(totals.get("total_debe_mes_actual")),
        "total_haber_mes_actual": flt(totals.get("total_haber_mes_actual")),
        "total_debe_saldo": flt(totals.get("total_debe_saldo")),
        "total_haber_saldo": flt(totals.get("total_haber_saldo")),
        "saldo_neto": flt(totals.get("saldo_neto")),
    }
    summary["cuadra"] = int(abs(summary["saldo_neto"]) <= 0.01)
    if frappe.db.exists("Version Balanza Cliente", version_name):
        frappe.db.set_value("Version Balanza Cliente", version_name, summary, update_modified=False)
    return summary


def importar_version_balanza(version_name, *, csv_content=None, replace=True):
    if not frappe.db.exists("Version Balanza Cliente", version_name):
        frappe.throw(_("La version de balanza indicada no existe."), title=_("Version Invalida"))

    version_doc = frappe.get_doc("Version Balanza Cliente", version_name)
    if csv_content is None:
        file_doc = _get_version_source_file(version_doc)
        if not file_doc:
            frappe.throw(_("Debes adjuntar un archivo fuente o vincular un Documento Contable con evidencia valida."), title=_("Archivo Requerido"))
        csv_content = file_doc.get_content()
        version_doc.archivo_fuente = file_doc.file_url or version_doc.archivo_fuente
        version_doc.archivo_fuente_file = file_doc.name
        version_doc.hash_fuente_sha256 = getattr(file_doc, "content_hash", None) or version_doc.hash_fuente_sha256

    rows = parse_balanza_csv(csv_content)

    if replace:
        for name in frappe.get_all("Linea Balanza Cliente", filters={"version_balanza_cliente": version_name}, pluck="name", limit_page_length=20000):
            frappe.delete_doc("Linea Balanza Cliente", name, ignore_permissions=True, force=True)

    for index, row in enumerate(rows, start=1):
        payload = dict(row)
        payload.update(
            {
                "doctype": "Linea Balanza Cliente",
                "version_balanza_cliente": version_name,
                "idx_importacion": index,
            }
        )
        frappe.get_doc(payload).insert(ignore_permissions=True)

    summary = sync_version_summary(version_name)
    version_updates = {
        "estado_version": "Importada",
        "ultima_importacion": now_datetime(),
        "archivo_fuente_file": version_doc.archivo_fuente_file,
        "hash_fuente_sha256": version_doc.hash_fuente_sha256,
    }
    frappe.db.set_value("Version Balanza Cliente", version_name, version_updates, update_modified=False)
    return {"version_balanza_cliente": version_name, **summary}


@frappe.whitelist()
def importar_version_balanza_csv(version_name, csv_content=None, replace=1):
    ensure_supervisor(_("Solo Supervisor del Despacho, Socio del Despacho, Contador del Despacho o System Manager pueden importar balanzas."))
    return importar_version_balanza(version_name, csv_content=csv_content, replace=cint(replace))
