frappe.pages["creador-de-notas-eeff"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Creador de Notas EEFF",
        single_column: true,
    });

    frappe.pages["creador-de-notas-eeff"].editor = new CreadorNotasEEFF(page);
    frappe.pages["creador-de-notas-eeff"].editor.init();
};

frappe.pages["creador-de-notas-eeff"].on_page_show = function () {
    const editor = frappe.pages["creador-de-notas-eeff"].editor;
    if (!editor) return;

    editor.apply_route_options();
    const hasRouteOptions = !!Object.keys(editor.state.route_options || {}).length;
    editor.ensure_filter_bar_visible();
    if (hasRouteOptions || !editor.bootstrapped) {
        editor.load_bootstrap();
    }
};

class CreadorNotasEEFF {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
        this.state = {
            cliente: null,
            package_name: null,
            clients: [],
            packages: [],
            notes: [],
            note: null,
            current_section_id: null,
            route_options: {},
        };
        this.setting_filters = false;
        this.loading_bootstrap = false;
        this.last_bootstrap_key = null;
        this.bootstrapped = false;
    }

    init() {
        this.setup_styles();
        this.render_shell();
        this.ensure_filter_bar_visible();
        this.bind_events();
        this.page.set_primary_action(__("Guardar Nota"), () => this.save_current_note(), "save");
        this.page.set_secondary_action(__("Nueva Nota"), () => this.open_create_note_dialog());
    }

    apply_route_options() {
        this.state.route_options = frappe.route_options || {};
        frappe.route_options = null;
    }

    setup_styles() {
        if (document.getElementById("cne-styles")) return;
        const style = document.createElement("style");
        style.id = "cne-styles";
        style.textContent = `
            .cne-shell{display:grid;grid-template-columns:280px minmax(0,1fr);gap:16px;padding:18px;border:1px solid #dbe3ef;border-radius:18px;background:linear-gradient(160deg,#f8fafc 0%,#eef6ff 52%,#fffdf6 100%)}
            .cne-sidebar,.cne-card{background:#fff;border:1px solid #dbe3ef;border-radius:16px;box-shadow:0 12px 28px rgba(15,23,42,.05)}
            .cne-sidebar{overflow:hidden}.cne-sidebar-head,.cne-card-head{padding:14px 16px;border-bottom:1px solid #eef2f7}
            .cne-sidebar-head h3,.cne-card-head h3{margin:0;font-size:15px;font-weight:800;color:#0f172a}.cne-sidebar-head p,.cne-card-head p{margin:6px 0 0;color:#64748b;font-size:12px}
            .cne-note-list{max-height:calc(100vh - 260px);overflow:auto}.cne-note-item{padding:12px 16px;border-bottom:1px solid #f1f5f9;cursor:pointer}.cne-note-item:hover{background:#f8fafc}.cne-note-item.active{background:#e0f2fe}
            .cne-note-item strong{display:block;color:#0f172a;font-size:13px}.cne-note-item span{display:block;margin-top:4px;color:#64748b;font-size:11px}
            .cne-main{display:flex;flex-direction:column;gap:14px;min-width:0}.cne-empty{padding:50px 24px;text-align:center;color:#64748b;border:1px dashed #cbd5e1;border-radius:16px;background:rgba(255,255,255,.75)}
            .cne-grid{display:grid;gap:12px}.cne-grid.note{grid-template-columns:repeat(2,minmax(0,1fr))}.cne-field{display:flex;flex-direction:column;gap:6px}.cne-field label{font-size:11px;text-transform:uppercase;font-weight:700;color:#64748b;letter-spacing:.4px}
            .cne-field input,.cne-field select,.cne-field textarea{width:100%;border:1px solid #cbd5e1;border-radius:10px;padding:9px 10px;font-size:13px;background:#fff}.cne-field textarea{min-height:90px;resize:vertical}
            .cne-note-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:0 16px 16px}.cne-kpi{padding:12px;border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc}.cne-kpi strong{display:block;font-size:18px;color:#0f172a}.cne-kpi span{display:block;margin-top:4px;color:#64748b;font-size:11px;text-transform:uppercase;font-weight:700}
            .cne-toolbar,.cne-sections{display:flex;gap:8px;flex-wrap:wrap;padding:0 16px 12px}.cne-sections{padding-bottom:16px}.cne-btn{border:1px solid #cbd5e1;background:#fff;color:#0f172a;border-radius:999px;padding:7px 12px;font-size:12px;font-weight:700;cursor:pointer}.cne-btn.primary{background:#0f766e;border-color:#0f766e;color:#fff}.cne-btn.danger{background:#fff1f2;border-color:#fecdd3;color:#be123c}
            .cne-section-tab{border:1px solid #cbd5e1;border-radius:999px;padding:8px 12px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#334155}.cne-section-tab.active{background:#0f172a;border-color:#0f172a;color:#fff}
            .cne-layout-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.cne-structure-wrap,.cne-matrix-wrap{overflow:auto;padding:0 16px 16px}.cne-structure-table,.cne-matrix-table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}
            .cne-structure-table th,.cne-structure-table td,.cne-matrix-table th,.cne-matrix-table td{padding:8px;border-bottom:1px solid #eef2f7;vertical-align:top}.cne-structure-table th,.cne-matrix-table th{background:#f8fafc;color:#475569;font-size:11px;text-transform:uppercase;font-weight:800}
            .cne-structure-table input,.cne-structure-table select,.cne-matrix-table input{width:100%;border:1px solid #cbd5e1;border-radius:8px;padding:6px 8px;font-size:12px;background:#fff}.cne-delete-link{color:#be123c;cursor:pointer;font-weight:700}.cne-pill{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;font-size:10px;font-weight:800;background:#eef2ff;color:#3730a3;text-transform:uppercase}.cne-rowhead{min-width:220px;background:#fff}.cne-code{display:block;color:#64748b;font-size:11px;margin-top:3px}.cne-matrix-input.computed{background:#f8fafc;border-style:dashed}.cne-help{padding:0 16px 16px;color:#475569;font-size:12px}.cne-help code{background:#f1f5f9;padding:2px 5px;border-radius:6px}
            @media (max-width:1100px){.cne-shell{grid-template-columns:1fr}.cne-grid.note,.cne-layout-two,.cne-note-meta{grid-template-columns:1fr}}
        `;
        document.head.appendChild(style);
    }

    render_shell() {
        this.wrapper.html(`
            <div class="cne-shell">
                <aside class="cne-sidebar">
                    <div class="cne-sidebar-head">
                        <h3>Notas del paquete</h3>
                        <p>La page edita la nota, pero el doctype sigue siendo la fuente de verdad.</p>
                    </div>
                    <div class="cne-note-list" data-role="note-list"></div>
                </aside>
                <section class="cne-main">
                    <div data-role="editor"></div>
                </section>
            </div>
        `);

        this.clientField = this.page.add_field({
            fieldtype: "Select",
            fieldname: "cliente",
            label: __("Cliente"),
            options: "\n",
            change: () => this.on_client_change(),
        });
        this.packageField = this.page.add_field({
            fieldtype: "Select",
            fieldname: "package_name",
            label: __("Paquete"),
            options: "\n",
            change: () => this.on_package_change(),
        });
        this.noteField = this.page.add_field({
            fieldtype: "Select",
            fieldname: "note_name",
            label: __("Nota"),
            options: "\n",
            change: () => this.on_note_change(),
        });

        this.$noteList = this.wrapper.find('[data-role="note-list"]');
        this.$editor = this.wrapper.find('[data-role="editor"]');
    }

    ensure_filter_bar_visible() {
        const show = () => {
            const $pageForm = $(this.page.wrapper).find('.page-form');
            if ($pageForm.length) {
                $pageForm.removeClass('hide hidden d-none');
                $pageForm.attr('style', 'display: flex !important; flex-wrap: wrap; gap: 8px; align-items: flex-end; padding: 12px 15px;');
            }
        };
        show();
        setTimeout(show, 0);
        setTimeout(show, 200);
    }

    bind_events() {
        this.wrapper.on("click", ".cne-note-item", (event) => {
            const name = event.currentTarget.dataset.noteName;
            if (name) this.load_bootstrap({ note_name: name });
        });
        this.wrapper.on("change input", ".cne-note-field", (event) => {
            const doc = this.get_doc();
            if (!doc) return;
            doc[event.currentTarget.dataset.fieldname] = event.currentTarget.value;
        });
        this.wrapper.on("click", ".cne-open-form", () => {
            const doc = this.get_doc();
            if (doc?.name) frappe.set_route("Form", "Nota Estado Financiero", doc.name);
        });
        this.wrapper.on("click", ".cne-add-section", () => this.add_section());
        this.wrapper.on("click", ".cne-delete-section", () => this.delete_current_section());
        this.wrapper.on("click", ".cne-section-tab", (event) => {
            this.state.current_section_id = event.currentTarget.dataset.sectionId;
            this.render_editor();
        });
        this.wrapper.on("change", ".cne-section-field", (event) => this.update_section_field(event));
        this.wrapper.on("click", ".cne-add-column", () => this.add_column());
        this.wrapper.on("click", ".cne-delete-column", (event) => this.delete_column(parseInt(event.currentTarget.dataset.index, 10)));
        this.wrapper.on("change", ".cne-column-field", (event) => this.update_column_field(event));
        this.wrapper.on("click", ".cne-add-row", () => this.add_row());
        this.wrapper.on("click", ".cne-delete-row", (event) => this.delete_row(parseInt(event.currentTarget.dataset.index, 10)));
        this.wrapper.on("change", ".cne-row-field", (event) => this.update_row_field(event));
        this.wrapper.on("change", ".cne-matrix-input", (event) => this.update_matrix_cell(event));
    }

    on_client_change() {
        if (this.setting_filters) return;
        this.load_bootstrap({ cliente: this.clientField.get_value() || null, package_name: null, note_name: null });
    }

    on_package_change() {
        if (this.setting_filters) return;
        this.load_bootstrap({ cliente: this.clientField.get_value() || null, package_name: this.packageField.get_value() || null, note_name: null });
    }

    on_note_change() {
        if (this.setting_filters) return;
        const noteName = this.noteField.get_value();
        if (!noteName) {
            this.state.note = null;
            this.render_editor();
            return;
        }
        this.load_bootstrap({ note_name: noteName });
    }

    load_bootstrap(overrides = {}) {
        const route = this.state.route_options || {};
        const args = {
            cliente: overrides.cliente !== undefined ? overrides.cliente : (route.cliente || this.clientField.get_value() || null),
            package_name: overrides.package_name !== undefined ? overrides.package_name : (route.package_name || this.packageField.get_value() || null),
            note_name: overrides.note_name !== undefined ? overrides.note_name : (route.note_name || this.noteField.get_value() || null),
        };
        const bootstrapKey = JSON.stringify(args);
        this.state.route_options = {};

        if (this.loading_bootstrap) return;
        if (bootstrapKey === this.last_bootstrap_key) return;
        this.loading_bootstrap = true;

        frappe.call({
            method: "gestion_contable.gestion_contable.page.creador_de_notas_eeff.creador_de_notas_eeff.get_editor_bootstrap",
            args,
            freeze: true,
            freeze_message: __("Cargando creador de notas..."),
            callback: (r) => {
                const data = r.message || {};
                this.state.cliente = data.cliente || args.cliente || null;
                this.state.package_name = data.package_name || args.package_name || null;
                this.state.clients = data.clients || [];
                this.state.packages = data.packages || [];
                this.state.notes = data.notes || [];
                this.state.note = data.note || null;
                this.ensure_current_section();
                this.sync_filter_options();
                this.render_notes();
                this.render_editor();
                this.last_bootstrap_key = bootstrapKey;
                this.bootstrapped = true;
            },
            always: () => {
                this.loading_bootstrap = false;
            },
        });
    }

    sync_filter_options() {
        this.setting_filters = true;
        this.set_select_options(this.clientField, (this.state.clients || []).map((row) => ({ value: row.value, label: row.label })), this.state.cliente);
        this.set_select_options(this.packageField, this.state.packages.map((row) => ({ value: row.value, label: row.label })), this.state.package_name);
        this.set_select_options(this.noteField, this.state.notes.map((row) => ({ value: row.name, label: row.label })), this.get_doc()?.name || "");
        this.setting_filters = false;
    }

    set_select_options(field, rows, selectedValue) {
        field.df.options = [""].concat((rows || []).map((row) => row.value)).join("\n");
        field.refresh();
        const safeValue = selectedValue || "";
        field.value = safeValue;
        field.last_value = safeValue;
        if (field.$input) {
            field.$input.val(safeValue);
        }
    }

    open_create_note_dialog() {
        const packageName = this.packageField.get_value();
        if (!packageName) {
            frappe.msgprint(__("Selecciona un paquete antes de crear una nota."));
            return;
        }
        const dialog = new frappe.ui.Dialog({
            title: __("Nueva Nota EEFF"),
            fields: [
                { fieldname: "numero_nota", fieldtype: "Data", label: __("Numero Nota"), reqd: 1 },
                { fieldname: "titulo", fieldtype: "Data", label: __("Titulo"), reqd: 1 },
                { fieldname: "categoria_nota", fieldtype: "Select", label: __("Categoria"), options: "Base de Preparacion\nPoliticas Contables\nEfectivo\nCuentas por Cobrar\nInventarios\nPropiedad Planta y Equipo\nPasivos\nPatrimonio\nIngresos\nGastos\nImpuestos\nPartes Relacionadas\nContingencias\nHechos Posteriores\nOtra", default: "Otra" },
            ],
            primary_action_label: __("Crear"),
            primary_action: (values) => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.page.creador_de_notas_eeff.creador_de_notas_eeff.create_note_for_editor",
                    args: {
                        package_name: packageName,
                        numero_nota: values.numero_nota,
                        titulo: values.titulo,
                        categoria_nota: values.categoria_nota,
                    },
                    freeze: true,
                    callback: (r) => {
                        const data = r.message || {};
                        this.state.cliente = data.cliente || this.state.cliente;
                        this.state.package_name = data.package_name || packageName;
                        this.state.clients = data.clients || this.state.clients || [];
                        this.state.packages = data.packages || this.state.packages || [];
                        this.state.notes = data.notes || [];
                        this.state.note = data.note || null;
                        this.ensure_current_section();
                        this.sync_filter_options();
                        this.render_notes();
                        this.render_editor();
                        dialog.hide();
                    },
                });
            },
        });
        dialog.show();
    }

    save_current_note() {
        const doc = this.get_doc();
        if (!doc?.name) {
            frappe.msgprint(__("No hay una nota seleccionada."));
            return;
        }
        frappe.call({
            method: "gestion_contable.gestion_contable.page.creador_de_notas_eeff.creador_de_notas_eeff.save_note_editor",
            args: { note_payload: JSON.stringify(doc) },
            freeze: true,
            freeze_message: __("Guardando nota..."),
            callback: (r) => {
                const data = r.message || {};
                this.state.cliente = data.cliente || this.state.cliente;
                this.state.package_name = data.package_name || this.state.package_name;
                this.state.clients = data.clients || this.state.clients || [];
                this.state.packages = data.packages || this.state.packages || [];
                this.state.notes = data.notes || [];
                this.state.note = data.note || null;
                this.ensure_current_section();
                this.sync_filter_options();
                this.render_notes();
                this.render_editor();
                frappe.show_alert({ indicator: "green", message: __("Nota guardada") });
            },
            always: () => {
                this.loading_bootstrap = false;
            },
        });
    }

    render_notes() {
        if (!this.state.notes.length) {
            this.$noteList.html('<div class="cne-empty">No hay notas para el paquete activo.</div>');
            return;
        }
        const currentName = this.get_doc()?.name;
        this.$noteList.html(this.state.notes.map((note) => `
            <div class="cne-note-item ${note.name === currentName ? "active" : ""}" data-note-name="${frappe.utils.escape_html(note.name)}">
                <strong>${frappe.utils.escape_html(note.label || note.name)}</strong>
                <span>${frappe.utils.escape_html(note.categoria_nota || "")}</span>
            </div>
        `).join(""));
    }

    render_editor() {
        const doc = this.get_doc();
        if (!doc) {
            const hasClient = !!this.state.cliente;
            const emptyMessage = !hasClient ? 'Selecciona primero un cliente para cargar sus paquetes y notas.' : 'Selecciona un paquete y una nota para editarla desde esta vista.';
            this.$editor.html(`<div class="cne-empty">${emptyMessage}<br>El doctype sigue siendo el respaldo y la fuente de verdad.</div>`);
            return;
        }
        this.ensure_current_section();
        const section = this.get_current_section();
        this.$editor.html(`
            <div class="cne-card">
                <div class="cne-card-head">
                    <h3>Nota ${this.escape(doc.numero_nota || "")}</h3>
                    <p>${this.escape(doc.name)} · ${this.escape(doc.estado_aprobacion || "Borrador")}</p>
                </div>
                <div class="cne-grid note" style="padding:16px;">
                    ${this.noteInput("numero_nota", "Numero Nota", doc.numero_nota || "")}
                    ${this.noteInput("titulo", "Titulo", doc.titulo || "")}
                    ${this.noteSelect("categoria_nota", "Categoria", doc.categoria_nota || "Otra", ["Base de Preparacion", "Politicas Contables", "Efectivo", "Cuentas por Cobrar", "Inventarios", "Propiedad Planta y Equipo", "Pasivos", "Patrimonio", "Ingresos", "Gastos", "Impuestos", "Partes Relacionadas", "Contingencias", "Hechos Posteriores", "Otra"])}
                    ${this.noteInput("orden_presentacion", "Orden Presentacion", doc.orden_presentacion || "", "number")}
                    ${this.noteTextarea("politica_contable", "Politica Contable", doc.politica_contable || "")}
                    ${this.noteTextarea("contenido_narrativo", "Contenido Narrativo", doc.contenido_narrativo || "")}
                    ${this.noteTextarea("observaciones_preparacion", "Observaciones Preparacion", doc.observaciones_preparacion || "")}
                </div>
                <div class="cne-note-meta">
                    <div class="cne-kpi"><strong>${this.escape(doc.cliente || "-")}</strong><span>Cliente</span></div>
                    <div class="cne-kpi"><strong>${this.escape(doc.periodo_contable || "-")}</strong><span>Periodo</span></div>
                    <div class="cne-kpi"><strong>${doc.total_referencias || 0}</strong><span>Referencias</span></div>
                    <div class="cne-kpi"><strong>${(doc.secciones_estructuradas || []).length}</strong><span>Secciones</span></div>
                </div>
                <div class="cne-toolbar"><button class="cne-btn primary cne-open-form">Abrir Formulario Base</button></div>
            </div>
            <div class="cne-card">
                <div class="cne-card-head"><h3>Secciones</h3><p>Selecciona una seccion y construye su estructura tabular.</p></div>
                <div class="cne-toolbar">
                    <button class="cne-btn primary cne-add-section">Nueva Seccion</button>
                    ${section ? '<button class="cne-btn danger cne-delete-section">Eliminar Seccion Actual</button>' : ''}
                </div>
                <div class="cne-sections">${this.render_section_tabs()}</div>
            </div>
            ${section ? this.render_section_editor(section) : '<div class="cne-empty">La nota no tiene secciones todavia.</div>'}
        `);
    }

    render_section_tabs() {
        return this.get_sections().map((row) => `
            <button class="cne-section-tab ${row.seccion_id === this.state.current_section_id ? "active" : ""}" data-section-id="${this.escape(row.seccion_id)}">
                ${this.escape(row.seccion_id)} · ${this.escape(row.titulo_seccion || "Seccion")}
            </button>
        `).join("");
    }

    render_section_editor(section) {
        return `
            <div class="cne-card">
                <div class="cne-card-head"><h3>Seccion ${this.escape(section.seccion_id)}</h3><p>Edita estructura, formulas y celdas desde una sola vista.</p></div>
                <div class="cne-grid note" style="padding:16px;">
                    ${this.sectionInput("seccion_id", "ID Seccion", section.seccion_id || "", "text", section.seccion_id || "")}
                    ${this.sectionInput("titulo_seccion", "Titulo Seccion", section.titulo_seccion || "")}
                    ${this.sectionSelect("tipo_seccion", "Tipo Seccion", section.tipo_seccion || "Narrativa", ["Narrativa", "Tabla", "Texto y Tabla"])}
                    ${this.sectionInput("orden", "Orden", section.orden || "", "number")}
                    ${this.sectionTextarea("contenido_narrativo", "Contenido Narrativo", section.contenido_narrativo || "")}
                </div>
                <div class="cne-layout-two">
                    ${this.render_columns_editor(section.seccion_id)}
                    ${this.render_rows_editor(section.seccion_id)}
                </div>
                ${this.render_matrix(section.seccion_id)}
                <div class="cne-help">Las celdas manuales sobrescriben los calculos. Para formulas usa codigos con <code>+</code> y <code>-</code>, por ejemplo <code>+COM,+CONS,-PROV</code>. Si una celda queda vacia, vuelve a mostrarse el valor calculado.</div>
            </div>
        `;
    }

    render_columns_editor(sectionId) {
        const rows = this.get_columns(sectionId);
        return `
            <div class="cne-card">
                <div class="cne-card-head"><h3>Columnas</h3><p>Codigo, etiqueta, grupo, tipo y formula por columna.</p></div>
                <div class="cne-toolbar"><button class="cne-btn cne-add-column">Nueva Columna</button></div>
                <div class="cne-structure-wrap">
                    <table class="cne-structure-table">
                        <thead><tr><th>Codigo</th><th>Etiqueta</th><th>Grupo</th><th>Tipo</th><th>Alineacion</th><th>Auto</th><th>Formula</th><th>Orden</th><th>Total</th><th></th></tr></thead>
                        <tbody>
                            ${rows.length ? rows.map((row, index) => `
                                <tr>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="codigo_columna" data-original-code="${this.escape(row.codigo_columna || "")}" value="${this.escape(row.codigo_columna || "")}"></td>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="etiqueta" value="${this.escape(row.etiqueta || "")}"></td>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="grupo_columna" value="${this.escape(row.grupo_columna || "")}"></td>
                                    <td>${this.inlineSelect("cne-column-field", index, "tipo_dato", row.tipo_dato || "Moneda", ["Texto", "Numero", "Moneda", "Porcentaje"])}</td>
                                    <td>${this.inlineSelect("cne-column-field", index, "alineacion", row.alineacion || "Right", ["Left", "Center", "Right"])}</td>
                                    <td><input type="checkbox" class="cne-column-field" data-index="${index}" data-fieldname="calculo_automatico" ${this.checked(row.calculo_automatico)}></td>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="formula_columnas" value="${this.escape(row.formula_columnas || "")}"></td>
                                    <td><input type="number" class="cne-column-field" data-index="${index}" data-fieldname="orden" value="${this.escape(String(row.orden || index + 1))}"></td>
                                    <td><input type="checkbox" class="cne-column-field" data-index="${index}" data-fieldname="es_total" ${this.checked(row.es_total)}></td>
                                    <td><span class="cne-delete-link cne-delete-column" data-index="${index}">Eliminar</span></td>
                                </tr>
                            `).join("") : '<tr><td colspan="10">Sin columnas.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    render_rows_editor(sectionId) {
        const rows = this.get_rows(sectionId);
        return `
            <div class="cne-card">
                <div class="cne-card-head"><h3>Filas</h3><p>Codigo, nivel, tipo y formula por fila.</p></div>
                <div class="cne-toolbar"><button class="cne-btn cne-add-row">Nueva Fila</button></div>
                <div class="cne-structure-wrap">
                    <table class="cne-structure-table">
                        <thead><tr><th>Codigo</th><th>Descripcion</th><th>Nivel</th><th>Tipo</th><th>Auto</th><th>Formula</th><th>Orden</th><th>Negrita</th><th>Subrayado</th><th></th></tr></thead>
                        <tbody>
                            ${rows.length ? rows.map((row, index) => `
                                <tr>
                                    <td><input class="cne-row-field" data-index="${index}" data-fieldname="codigo_fila" data-original-code="${this.escape(row.codigo_fila || "")}" value="${this.escape(row.codigo_fila || "")}"></td>
                                    <td><input class="cne-row-field" data-index="${index}" data-fieldname="descripcion" value="${this.escape(row.descripcion || "")}"></td>
                                    <td><input type="number" class="cne-row-field" data-index="${index}" data-fieldname="nivel" value="${this.escape(String(row.nivel || 1))}"></td>
                                    <td>${this.inlineSelect("cne-row-field", index, "tipo_fila", row.tipo_fila || "Detalle", ["Detalle", "Subtotal", "Total", "Comentario"])}</td>
                                    <td><input type="checkbox" class="cne-row-field" data-index="${index}" data-fieldname="calculo_automatico" ${this.checked(row.calculo_automatico)}></td>
                                    <td><input class="cne-row-field" data-index="${index}" data-fieldname="formula_filas" value="${this.escape(row.formula_filas || "")}"></td>
                                    <td><input type="number" class="cne-row-field" data-index="${index}" data-fieldname="orden" value="${this.escape(String(row.orden || index + 1))}"></td>
                                    <td><input type="checkbox" class="cne-row-field" data-index="${index}" data-fieldname="negrita" ${this.checked(row.negrita)}></td>
                                    <td><input type="checkbox" class="cne-row-field" data-index="${index}" data-fieldname="subrayado" ${this.checked(row.subrayado)}></td>
                                    <td><span class="cne-delete-link cne-delete-row" data-index="${index}">Eliminar</span></td>
                                </tr>
                            `).join("") : '<tr><td colspan="10">Sin filas.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    render_matrix(sectionId) {
        const rows = this.get_rows(sectionId);
        const columns = this.get_columns(sectionId);
        const columnGroups = this.build_column_groups(columns);
        const hasColumnGroups = columnGroups.length > 0;
        const matrix = this.compute_matrix(sectionId);
        return `
            <div class="cne-card">
                <div class="cne-card-head"><h3>Matriz Visual</h3><p>Edita celdas manuales y revisa valores calculados en tiempo real.</p></div>
                <div class="cne-matrix-wrap">
                    ${rows.length && columns.length ? `
                        <table class="cne-matrix-table">
                            <thead>
                                ${hasColumnGroups ? `
                                    <tr>
                                        <th class="cne-rowhead" rowspan="2">Fila / Columna</th>
                                        ${columnGroups.map((group) => {
                                            if (group.standalone) {
                                                const column = group.columns[0];
                                                return `
                                                    <th rowspan="2">
                                                        <div>${this.escape(column.etiqueta || column.codigo_columna)}</div>
                                                        <span class="cne-code">${this.escape(column.codigo_columna)}</span>
                                                        ${this.truthy(column.calculo_automatico) ? '<span class="cne-pill">fx columna</span>' : ''}
                                                    </th>
                                                `;
                                            }
                                            return `<th colspan="${group.span}">${this.escape(group.label)}</th>`;
                                        }).join("")}
                                    </tr>
                                    <tr>
                                        ${columnGroups.map((group) => {
                                            if (group.standalone) return "";
                                            return group.columns.map((column) => `
                                                <th>
                                                    <div>${this.escape(column.etiqueta || column.codigo_columna)}</div>
                                                    <span class="cne-code">${this.escape(column.codigo_columna)}</span>
                                                    ${this.truthy(column.calculo_automatico) ? '<span class="cne-pill">fx columna</span>' : ''}
                                                </th>
                                            `).join("");
                                        }).join("")}
                                    </tr>
                                ` : `
                                    <tr>
                                        <th class="cne-rowhead">Fila / Columna</th>
                                        ${columns.map((column) => `
                                            <th>
                                                <div>${this.escape(column.etiqueta || column.codigo_columna)}</div>
                                                <span class="cne-code">${this.escape(column.codigo_columna)}</span>
                                                ${this.truthy(column.calculo_automatico) ? '<span class="cne-pill">fx columna</span>' : ''}
                                            </th>
                                        `).join("")}
                                    </tr>
                                `}
                            </thead>
                            <tbody>
                                ${rows.map((row) => `
                                    <tr>
                                        <td class="cne-rowhead">
                                            <strong>${this.escape(row.descripcion || row.codigo_fila)}</strong>
                                            <span class="cne-code">${this.escape(row.codigo_fila)}</span>
                                            ${this.truthy(row.calculo_automatico) ? '<span class="cne-pill">fx fila</span>' : ''}
                                        </td>
                                        ${columns.map((column) => {
            const cell = matrix[`${row.codigo_fila}::${column.codigo_columna}`] || { value: "", is_manual: false, is_computed: false };
            const value = cell.value === null || cell.value === undefined ? "" : String(cell.value);
            return `<td><input class="cne-matrix-input ${cell.is_computed && !cell.is_manual ? "computed" : ""}" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}" data-type="${this.escape(column.tipo_dato || "Numero")}" value="${this.escape(value)}"></td>`;
        }).join("")}
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    ` : '<div class="cne-empty">Define al menos una fila y una columna para usar la matriz.</div>'}
                </div>
            </div>
        `;
    }

    noteInput(fieldname, label, value, type = "text") {
        return `<div class="cne-field"><label>${label}</label><input type="${type}" class="cne-note-field" data-fieldname="${fieldname}" value="${this.escape(String(value ?? ""))}"></div>`;
    }

    noteTextarea(fieldname, label, value) {
        return `<div class="cne-field"><label>${label}</label><textarea class="cne-note-field" data-fieldname="${fieldname}">${this.escape(String(value ?? ""))}</textarea></div>`;
    }

    noteSelect(fieldname, label, value, options) {
        return `<div class="cne-field"><label>${label}</label><select class="cne-note-field" data-fieldname="${fieldname}">${options.map((option) => `<option value="${this.escape(option)}" ${option === value ? "selected" : ""}>${this.escape(option)}</option>`).join("")}</select></div>`;
    }

    sectionInput(fieldname, label, value, type = "text", originalValue = "") {
        return `<div class="cne-field"><label>${label}</label><input type="${type}" class="cne-section-field" data-fieldname="${fieldname}" data-original-value="${this.escape(String(originalValue || value || ""))}" value="${this.escape(String(value ?? ""))}"></div>`;
    }

    sectionTextarea(fieldname, label, value) {
        return `<div class="cne-field"><label>${label}</label><textarea class="cne-section-field" data-fieldname="${fieldname}">${this.escape(String(value ?? ""))}</textarea></div>`;
    }

    sectionSelect(fieldname, label, value, options) {
        return `<div class="cne-field"><label>${label}</label><select class="cne-section-field" data-fieldname="${fieldname}">${options.map((option) => `<option value="${this.escape(option)}" ${option === value ? "selected" : ""}>${this.escape(option)}</option>`).join("")}</select></div>`;
    }

    inlineSelect(cssClass, index, fieldname, value, options) {
        return `<select class="${cssClass}" data-index="${index}" data-fieldname="${fieldname}">${options.map((option) => `<option value="${this.escape(option)}" ${option === value ? "selected" : ""}>${this.escape(option)}</option>`).join("")}</select>`;
    }

    get_doc() { return this.state.note && this.state.note.doc ? this.state.note.doc : null; }
    get_sections() { return (this.get_doc()?.secciones_estructuradas || []).slice().sort((a, b) => this.as_int(a.orden) - this.as_int(b.orden)); }
    get_current_section() { return (this.get_doc()?.secciones_estructuradas || []).find((row) => row.seccion_id === this.state.current_section_id) || null; }
    get_columns(sectionId) { return (this.get_doc()?.columnas_tabulares || []).filter((row) => row.seccion_id === sectionId).sort((a, b) => this.as_int(a.orden) - this.as_int(b.orden)); }
    get_rows(sectionId) { return (this.get_doc()?.filas_tabulares || []).filter((row) => row.seccion_id === sectionId).sort((a, b) => this.as_int(a.orden) - this.as_int(b.orden)); }
    get_cells(sectionId) { return (this.get_doc()?.celdas_tabulares || []).filter((row) => row.seccion_id === sectionId); } ensure_current_section() {
        const sections = this.get_sections();
        if (!sections.length) { this.state.current_section_id = null; return; }
        if (!sections.find((row) => row.seccion_id === this.state.current_section_id)) {
            this.state.current_section_id = sections[0].seccion_id;
        }
    }

    update_section_field(event) {
        const section = this.get_current_section();
        if (!section) return;
        const fieldname = event.currentTarget.dataset.fieldname;
        const value = event.currentTarget.value;
        if (fieldname === "orden") {
            section.orden = this.as_int(value, 0);
        } else if (fieldname === "seccion_id") {
            const previous = event.currentTarget.dataset.originalValue || section.seccion_id;
            section.seccion_id = (value || "").trim().toUpperCase();
            if (previous && previous !== section.seccion_id) {
                this.rename_section(previous, section.seccion_id);
                event.currentTarget.dataset.originalValue = section.seccion_id;
                this.state.current_section_id = section.seccion_id;
            }
        } else {
            section[fieldname] = value;
        }
        this.render_editor();
    }

    add_section() {
        const doc = this.get_doc();
        if (!doc) return;
        const next = (doc.secciones_estructuradas || []).length + 1;
        const sectionId = `SEC-${String(next).padStart(2, "0")}`;
        doc.secciones_estructuradas = doc.secciones_estructuradas || [];
        doc.secciones_estructuradas.push({ seccion_id: sectionId, titulo_seccion: `Seccion ${next}`, tipo_seccion: "Tabla", orden: next, contenido_narrativo: "" });
        this.state.current_section_id = sectionId;
        this.render_editor();
    }

    delete_current_section() {
        const doc = this.get_doc();
        const section = this.get_current_section();
        if (!doc || !section) return;
        frappe.confirm(__("Se eliminara la seccion actual y toda su estructura. Continuar?"), () => {
            doc.secciones_estructuradas = (doc.secciones_estructuradas || []).filter((row) => row.seccion_id !== section.seccion_id);
            doc.columnas_tabulares = (doc.columnas_tabulares || []).filter((row) => row.seccion_id !== section.seccion_id);
            doc.filas_tabulares = (doc.filas_tabulares || []).filter((row) => row.seccion_id !== section.seccion_id);
            doc.celdas_tabulares = (doc.celdas_tabulares || []).filter((row) => row.seccion_id !== section.seccion_id);
            this.ensure_current_section();
            this.render_editor();
        });
    }

    rename_section(previousId, newId) {
        const doc = this.get_doc();
        ["columnas_tabulares", "filas_tabulares", "celdas_tabulares"].forEach((fieldname) => {
            (doc[fieldname] || []).forEach((row) => {
                if (row.seccion_id === previousId) row.seccion_id = newId;
            });
        });
    }

    add_column() {
        const doc = this.get_doc();
        const section = this.get_current_section();
        if (!doc || !section) return;
        const next = this.get_columns(section.seccion_id).length + 1;
        doc.columnas_tabulares = doc.columnas_tabulares || [];
        doc.columnas_tabulares.push({ seccion_id: section.seccion_id, codigo_columna: `COL${next}`, etiqueta: `Columna ${next}`, grupo_columna: "", tipo_dato: "Moneda", alineacion: "Right", calculo_automatico: 0, formula_columnas: "", orden: next, es_total: 0 });
        this.render_editor();
    }

    delete_column(index) {
        const section = this.get_current_section();
        const column = this.get_columns(section.seccion_id)[index];
        if (!column) return;
        const doc = this.get_doc();
        doc.columnas_tabulares = (doc.columnas_tabulares || []).filter((row) => !(row.seccion_id === section.seccion_id && row.codigo_columna === column.codigo_columna));
        doc.celdas_tabulares = (doc.celdas_tabulares || []).filter((row) => !(row.seccion_id === section.seccion_id && row.codigo_columna === column.codigo_columna));
        this.render_editor();
    }

    update_column_field(event) {
        const section = this.get_current_section();
        const column = this.get_columns(section.seccion_id)[parseInt(event.currentTarget.dataset.index, 10)];
        if (!column) return;
        const fieldname = event.currentTarget.dataset.fieldname;
        const value = event.currentTarget.type === "checkbox" ? (event.currentTarget.checked ? 1 : 0) : event.currentTarget.value;
        if (fieldname === "codigo_columna") {
            const previous = event.currentTarget.dataset.originalCode || column.codigo_columna;
            column.codigo_columna = (value || "").trim().toUpperCase();
            if (previous && previous !== column.codigo_columna) {
                (this.get_doc().celdas_tabulares || []).forEach((row) => {
                    if (row.seccion_id === section.seccion_id && row.codigo_columna === previous) row.codigo_columna = column.codigo_columna;
                });
                event.currentTarget.dataset.originalCode = column.codigo_columna;
            }
        } else if (fieldname === "orden") {
            column.orden = this.as_int(value, 0);
        } else if (fieldname === "formula_columnas") {
            column.formula_columnas = (value || "").trim().toUpperCase();
            if (column.formula_columnas) column.calculo_automatico = 1;
        } else {
            column[fieldname] = value;
        }
        this.render_matrix_only();
    }

    add_row() {
        const doc = this.get_doc();
        const section = this.get_current_section();
        if (!doc || !section) return;
        const next = this.get_rows(section.seccion_id).length + 1;
        doc.filas_tabulares = doc.filas_tabulares || [];
        doc.filas_tabulares.push({ seccion_id: section.seccion_id, codigo_fila: `FIL${next}`, descripcion: `Fila ${next}`, nivel: 1, tipo_fila: "Detalle", calculo_automatico: 0, formula_filas: "", orden: next, negrita: 0, subrayado: 0 });
        this.render_editor();
    }

    delete_row(index) {
        const section = this.get_current_section();
        const row = this.get_rows(section.seccion_id)[index];
        if (!row) return;
        const doc = this.get_doc();
        doc.filas_tabulares = (doc.filas_tabulares || []).filter((item) => !(item.seccion_id === section.seccion_id && item.codigo_fila === row.codigo_fila));
        doc.celdas_tabulares = (doc.celdas_tabulares || []).filter((item) => !(item.seccion_id === section.seccion_id && item.codigo_fila === row.codigo_fila));
        this.render_editor();
    }

    update_row_field(event) {
        const section = this.get_current_section();
        const row = this.get_rows(section.seccion_id)[parseInt(event.currentTarget.dataset.index, 10)];
        if (!row) return;
        const fieldname = event.currentTarget.dataset.fieldname;
        const value = event.currentTarget.type === "checkbox" ? (event.currentTarget.checked ? 1 : 0) : event.currentTarget.value;
        if (fieldname === "codigo_fila") {
            const previous = event.currentTarget.dataset.originalCode || row.codigo_fila;
            row.codigo_fila = (value || "").trim().toUpperCase();
            if (previous && previous !== row.codigo_fila) {
                (this.get_doc().celdas_tabulares || []).forEach((cell) => {
                    if (cell.seccion_id === section.seccion_id && cell.codigo_fila === previous) cell.codigo_fila = row.codigo_fila;
                });
                event.currentTarget.dataset.originalCode = row.codigo_fila;
            }
        } else if (fieldname === "nivel" || fieldname === "orden") {
            row[fieldname] = this.as_int(value, 0);
        } else if (fieldname === "formula_filas") {
            row.formula_filas = (value || "").trim().toUpperCase();
            if (row.formula_filas) row.calculo_automatico = 1;
        } else {
            row[fieldname] = value;
        }
        this.render_matrix_only();
    } update_matrix_cell(event) {
        const doc = this.get_doc();
        const section = this.get_current_section();
        if (!doc || !section) return;
        doc.celdas_tabulares = doc.celdas_tabulares || [];
        const rowCode = event.currentTarget.dataset.rowCode;
        const columnCode = event.currentTarget.dataset.columnCode;
        const type = event.currentTarget.dataset.type || "Numero";
        const raw = event.currentTarget.value;
        const index = doc.celdas_tabulares.findIndex((row) => row.seccion_id === section.seccion_id && row.codigo_fila === rowCode && row.codigo_columna === columnCode);
        if (raw === "") {
            if (index >= 0) doc.celdas_tabulares.splice(index, 1);
            this.render_matrix_only();
            return;
        }
        const cell = index >= 0 ? doc.celdas_tabulares[index] : { seccion_id: section.seccion_id, codigo_fila: rowCode, codigo_columna: columnCode, formato_numero: type === "Moneda" ? "Moneda" : type === "Porcentaje" ? "Porcentaje" : "Numero" };
        if (type === "Texto") {
            cell.valor_texto = raw;
            cell.valor_numero = null;
        } else {
            cell.valor_numero = this.as_float(raw);
            cell.valor_texto = "";
        }
        if (index < 0) doc.celdas_tabulares.push(cell);
        this.render_matrix_only();
    }

    compute_matrix(sectionId) {
        const rows = this.get_rows(sectionId);
        const columns = this.get_columns(sectionId);
        const explicit = new Map(this.get_cells(sectionId).map((cell) => [`${cell.codigo_fila}::${cell.codigo_columna}`, cell]));
        const rowsByCode = Object.fromEntries(rows.map((row) => [row.codigo_fila, row]));
        const colsByCode = Object.fromEntries(columns.map((column) => [column.codigo_columna, column]));
        const cache = new Map();

        const resolve = (rowCode, columnCode, stack = new Set()) => {
            const key = `${rowCode}::${columnCode}`;
            if (cache.has(key)) return cache.get(key);
            if (explicit.has(key)) {
                const cell = explicit.get(key);
                const result = { value: cell.valor_numero ?? cell.valor_texto ?? "", is_manual: true, is_computed: false };
                cache.set(key, result);
                return result;
            }
            if (stack.has(key)) return { value: "", is_manual: false, is_computed: true };
            stack.add(key);
            const row = rowsByCode[rowCode];
            const col = colsByCode[columnCode];
            let result = { value: "", is_manual: false, is_computed: false };
            if (row && this.truthy(row.calculo_automatico) && row.formula_filas) {
                result = { value: this.evaluate_formula(row.formula_filas, (refCode, sign) => sign * this.as_float(resolve(refCode, columnCode, stack).value)), is_manual: false, is_computed: true };
            } else if (col && this.truthy(col.calculo_automatico) && col.formula_columnas) {
                result = { value: this.evaluate_formula(col.formula_columnas, (refCode, sign) => sign * this.as_float(resolve(rowCode, refCode, stack).value)), is_manual: false, is_computed: true };
            }
            stack.delete(key);
            cache.set(key, result);
            return result;
        };

        const matrix = {};
        rows.forEach((row) => columns.forEach((column) => {
            matrix[`${row.codigo_fila}::${column.codigo_columna}`] = resolve(row.codigo_fila, column.codigo_columna);
        }));
        return matrix;
    }

    evaluate_formula(formula, resolver) {
        return (formula || "")
            .split(/[\n,;]+/)
            .map((token) => token.trim())
            .filter(Boolean)
            .reduce((sum, token) => {
                const sign = token.startsWith("-") ? -1 : 1;
                const code = token.replace(/^[+-]/, "").trim().toUpperCase();
                if (!code) return sum;
                return sum + resolver(code, sign);
            }, 0);
    }

    build_column_groups(columns) {
        if (!columns.some((column) => (column.grupo_columna || "").trim())) {
            return [];
        }
        const groups = [];
        let currentGroup = null;
        columns.forEach((column) => {
            const groupLabel = (column.grupo_columna || "").trim();
            if (!groupLabel) {
                groups.push({ label: "", span: 1, standalone: true, columns: [column] });
                currentGroup = null;
                return;
            }
            if (currentGroup && !currentGroup.standalone && currentGroup.label === groupLabel) {
                currentGroup.columns.push(column);
                currentGroup.span += 1;
                return;
            }
            currentGroup = { label: groupLabel, span: 1, standalone: false, columns: [column] };
            groups.push(currentGroup);
        });
        return groups;
    }

    render_matrix_only() {
        const section = this.get_current_section();
        if (!section) return;
        const newWrap = $(this.render_matrix(section.seccion_id)).find(".cne-matrix-wrap").html();
        this.wrapper.find(".cne-matrix-wrap").html(newWrap);
    }

    checked(value) { return this.truthy(value) ? "checked" : ""; }
    truthy(value) { return this.as_int(value, 0) === 1; }
    as_int(value, fallback = 0) { const parsed = parseInt(value, 10); return Number.isNaN(parsed) ? fallback : parsed; }
    as_float(value) { if (value === null || value === undefined || value === "") return 0; const parsed = parseFloat(String(value).replace(/,/g, "")); return Number.isNaN(parsed) ? 0 : parsed; }
    escape(value) { return frappe.utils.escape_html(String(value ?? "")); }
}