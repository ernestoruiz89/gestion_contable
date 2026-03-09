import frappe

def execute():
    try:
        frappe.db.sql("""
            UPDATE `tabCelda Tabla Nota Estado Financiero`
            SET es_manual = 1
            WHERE valor_texto IS NOT NULL AND valor_texto != ''
               OR (valor_numero IS NOT NULL AND valor_numero != 0.0)
        """)
        
        frappe.db.sql("""
            UPDATE `tabCelda Tabla Nota Estado Financiero`
            SET es_manual = 1
            WHERE valor_numero = 0.0 AND valor_texto = ''
        """)
        
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(title="Error migrando es_manual en Celdas Tabulares", message=str(e))
