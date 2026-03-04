app_name = "gestion_contable"
app_title = "Gestión Contable"
app_publisher = "Despacho"
app_description = "Aplicación completa para la gestión de clientes, periodos y tareas contables."
app_email = "contacto@despacho.com"
app_license = "mit"

# Fixtures
# ----------
fixtures = [
    {
        "doctype": "Role",
        "filters": [["name", "in", ["Contador del Despacho", "Auxiliar Contable del Despacho"]]]
    }
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/gestion_contable/css/gestion_contable.css"
# app_include_js = "/assets/gestion_contable/js/gestion_contable.js"

# include js, css files in header of web template
# web_include_css = "/assets/gestion_contable/css/gestion_contable.css"
# web_include_js = "/assets/gestion_contable/js/gestion_contable.js"
