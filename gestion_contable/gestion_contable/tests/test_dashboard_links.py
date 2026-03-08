import json
from pathlib import Path


def test_dashboard_links_reference_real_fields():
    root = Path(__file__).resolve().parents[2]
    doctype_root = root / "doctype"
    custom_field_path = root.parent / "fixtures" / "custom_field.json"

    schemas = {}
    for json_file in doctype_root.glob("*/*.json"):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        if data.get("doctype") != "DocType":
            continue
        schemas[data["name"]] = {
            field.get("fieldname")
            for field in data.get("fields", [])
            if field.get("fieldname")
        }

    for row in json.loads(custom_field_path.read_text(encoding="utf-8")):
        dt = row.get("dt")
        fieldname = row.get("fieldname")
        if dt and fieldname:
            schemas.setdefault(dt, set()).add(fieldname)

    invalid = []
    for json_file in doctype_root.glob("*/*.json"):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        if data.get("doctype") != "DocType":
            continue
        src = data["name"]
        for link in data.get("links", []):
            target = link.get("link_doctype")
            field = link.get("link_fieldname")
            if not target or not field:
                continue
            if target not in schemas:
                continue
            if field not in schemas[target]:
                invalid.append(f"{src} -> {target}.{field}")

    assert not invalid, "Invalid dashboard links: " + ", ".join(sorted(invalid))
