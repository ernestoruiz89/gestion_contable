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
            .cne-fullscreen{position:fixed!important;top:0!important;left:0!important;width:100vw!important;height:100vh!important;z-index:9999!important;margin:0!important;border-radius:0!important;display:flex;flex-direction:column;background:var(--card-bg,#fff)!important}
            .cne-fullscreen .cne-structure-wrap,.cne-fullscreen .cne-matrix-wrap{flex:1;max-height:none}
            [data-theme="dark"] .cne-shell { background: var(--bg-color); border-color: var(--border-color); }
            [data-theme="dark"] .cne-sidebar, [data-theme="dark"] .cne-card, [data-theme="dark"] .cne-rowhead { background: var(--card-bg); border-color: var(--border-color); }
            [data-theme="dark"] .cne-sidebar-head, [data-theme="dark"] .cne-card-head, [data-theme="dark"] .cne-structure-table th, [data-theme="dark"] .cne-structure-table td, [data-theme="dark"] .cne-matrix-table th, [data-theme="dark"] .cne-matrix-table td, [data-theme="dark"] .cne-note-item { border-color: var(--border-color); }
            [data-theme="dark"] .cne-sidebar-head h3, [data-theme="dark"] .cne-card-head h3, [data-theme="dark"] .cne-note-item strong, [data-theme="dark"] .cne-rowhead strong, [data-theme="dark"] .cne-matrix-table td strong { color: var(--text-color); }
            [data-theme="dark"] .cne-sidebar-head p, [data-theme="dark"] .cne-card-head p, [data-theme="dark"] .cne-note-item span, [data-theme="dark"] .cne-field label, [data-theme="dark"] .cne-structure-table th, [data-theme="dark"] .cne-matrix-table th, [data-theme="dark"] .cne-code, [data-theme="dark"] .cne-help { color: var(--text-muted); }
            [data-theme="dark"] .cne-field input, [data-theme="dark"] .cne-field select, [data-theme="dark"] .cne-field textarea, [data-theme="dark"] .cne-structure-table input, [data-theme="dark"] .cne-structure-table select, [data-theme="dark"] .cne-matrix-table input { background: var(--control-bg) !important; color: var(--text-color); border-color: var(--border-color); }
            [data-theme="dark"] .cne-btn, [data-theme="dark"] .cne-section-tab { background: var(--control-bg); color: var(--text-color); border-color: var(--border-color); }
            [data-theme="dark"] .cne-section-tab.active { background: var(--text-color); color: var(--card-bg); }
            [data-theme="dark"] .cne-structure-table th, [data-theme="dark"] .cne-matrix-table th { background: var(--control-bg) !important; text-shadow: none; }
            [data-theme="dark"] .cne-matrix-cell.computed { background: var(--control-bg) !important; border-style: dashed !important; }
            [data-theme="dark"] .cne-help code { background: var(--control-bg) !important; text-shadow: none; }
            [data-theme="dark"] .cne-empty { background: transparent; border-color: var(--border-color); color: var(--text-muted); }
            [data-theme="dark"] .cne-matrix-cell { border-color: var(--border-color); background: var(--control-bg) !important; }
            [data-theme="dark"] .cne-matrix-cell .cne-matrix-format-btn { border-right-color: var(--border-color); background: var(--card-bg); color: var(--text-color); }
            [data-theme="dark"] .cne-matrix-format-dropdown .dropdown-menu { background: var(--card-bg); border-color: var(--border-color); }
            [data-theme="dark"] .cne-matrix-format-dropdown .dropdown-item { color: var(--text-color); }
            [data-theme="dark"] .cne-matrix-format-dropdown .dropdown-item:hover { background: var(--control-bg); }
            .cne-matrix-cell{display:flex;align-items:stretch;border:1px solid #cbd5e1;border-radius:8px;background:#fff;}
            .cne-matrix-cell input.cne-matrix-input{border:none!important;border-radius:0 8px 8px 0!important;flex:1;min-width:0!important;outline:none;background:transparent!important}
            .cne-matrix-cell .cne-matrix-format-dropdown { display: flex; align-items: stretch; }
            .cne-matrix-cell .cne-matrix-format-btn{border:none;border-right:1px solid #cbd5e1;background:#f8fafc;padding:0;color:#475569;font-size:12px;cursor:pointer;outline:none;text-align:center;font-weight:700;width:32px;border-radius:8px 0 0 8px;}
            .cne-matrix-cell .cne-matrix-format-btn:hover{background:#e2e8f0}
            .cne-matrix-cell .dropdown-toggle::after{display:none!important}
            .cne-matrix-cell.computed{background:#f8fafc;border-style:dashed!important}
            .cne-matrix-format-dropdown .dropdown-menu { border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #cbd5e1; font-size: 13px; font-weight: 500; min-width: 140px; }
            .cne-matrix-format-dropdown .dropdown-item { padding: 6px 12px; }
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
                    <div class="cne-filter-panel" data-role="filters"></div><div class="cne-note-list" data-role="note-list"></div>
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

        this.$filters = this.wrapper.find('[data-role="filters"]');
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
        this.wrapper.on("change", ".cne-filter-client", (event) => this.on_inline_client_change(event));
        this.wrapper.on("change", ".cne-filter-package", (event) => this.on_inline_package_change(event));
        this.wrapper.on("change", ".cne-filter-note", (event) => this.on_inline_note_change(event));
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
        this.wrapper.on("click", ".cne-download-csv", () => this.download_current_section_csv());
        this.wrapper.on("click", ".cne-upload-csv", () => this.open_csv_picker());
        this.wrapper.on("change", ".cne-csv-input", (event) => this.handle_csv_upload(event));
        this.wrapper.on("click", ".cne-delete-column", (event) => this.delete_column(parseInt(event.currentTarget.dataset.index, 10)));
        this.wrapper.on("change", ".cne-column-field", (event) => this.update_column_field(event));
        this.wrapper.on("click", ".cne-add-row", () => this.add_row());
        this.wrapper.on("click", ".cne-delete-row", (event) => this.delete_row(parseInt(event.currentTarget.dataset.index, 10)));
        this.wrapper.on("change", ".cne-row-field", (event) => this.update_row_field(event));
        this.wrapper.on("change", ".cne-matrix-input", (event) => this.update_matrix_value(event));
        this.wrapper.on("click", ".cne-format-option", (event) => {
            event.preventDefault();
            this.update_matrix_format(event);
        });
        this.wrapper.on("click", ".cne-toggle-fullscreen", (event) => {
            const $card = $(event.currentTarget).closest(".cne-card");
            $card.toggleClass("cne-fullscreen");
            const isFull = $card.hasClass("cne-fullscreen");
            $(event.currentTarget).text(isFull ? "Contraer Pantalla" : "Expandir Pantalla");
            if (isFull) {
                $("body").css("overflow", "hidden");
            } else {
                if (!$(".cne-fullscreen").length) $("body").css("overflow", "");
            }
        });
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

    on_inline_client_change(event) {
        if (this.setting_filters) return;
        const cliente = event.currentTarget.value || null;
        this.load_bootstrap({ cliente, package_name: null, note_name: null });
    }

    on_inline_package_change(event) {
        if (this.setting_filters) return;
        const cliente = this.state.cliente || null;
        const package_name = event.currentTarget.value || null;
        this.load_bootstrap({ cliente, package_name, note_name: null });
    }

    on_inline_note_change(event) {
        if (this.setting_filters) return;
        const note_name = event.currentTarget.value || null;
        if (!note_name) {
            this.state.note = null;
            this.render_filters();
            this.render_notes();
            this.render_editor();
            return;
        }
        this.load_bootstrap({ note_name });
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
                this.render_filters();
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

    render_filters() {
        if (!this.$filters || !this.$filters.length) return;
        const currentNote = this.get_doc()?.name || "";
        this.$filters.html(`
            <div class="cne-card" style="margin:12px;">
                <div class="cne-card-head">
                    <h3>Filtros</h3>
                    <p>Carga las notas desde el cliente y el paquete sin depender de la barra superior.</p>
                </div>
                <div class="cne-grid" style="padding:16px;">
                    <div class="cne-field">
                        <label>Cliente</label>
                        <select class="cne-filter-client">
                            <option value=""></option>
                            ${(this.state.clients || []).map((row) => `<option value="${this.escape(row.value)}" ${row.value === this.state.cliente ? "selected" : ""}>${this.escape(row.label || row.value)}</option>`).join("")}
                        </select>
                    </div>
                    <div class="cne-field">
                        <label>Paquete Estados Financieros Cliente</label>
                        <select class="cne-filter-package" ${this.state.cliente ? "" : "disabled"}>
                            <option value=""></option>
                            ${(this.state.packages || []).map((row) => `<option value="${this.escape(row.value)}" ${row.value === this.state.package_name ? "selected" : ""}>${this.escape(row.label || row.value)}</option>`).join("")}
                        </select>
                    </div>
                    <div class="cne-field">
                        <label>Nota</label>
                        <select class="cne-filter-note" ${(this.state.package_name || this.state.notes.length) ? "" : "disabled"}>
                            <option value=""></option>
                            ${(this.state.notes || []).map((row) => `<option value="${this.escape(row.name)}" ${row.name === currentNote ? "selected" : ""}>${this.escape(row.label || row.name)}</option>`).join("")}
                        </select>
                    </div>
                </div>
            </div>
        `);
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
                {
                    fieldname: "contenido_inicial",
                    fieldtype: "Small Text",
                    label: __("Contenido Inicial"),
                    description: __("Si lo dejas vacio, el sistema creara un borrador inicial valido para editar la nota."),
                },
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
                        contenido_inicial: values.contenido_inicial,
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
                this.render_filters();
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
                    <p>${this.escape(doc.name)} - ${this.escape(doc.estado_aprobacion || "Borrador")}</p>
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
                ${this.escape(row.seccion_id)} - ${this.escape(row.titulo_seccion || "Seccion")}
            </button>
        `).join("");
    }

    render_section_editor(section) {
        return `
            <div class="cne-card">
                <div class="cne-card-head"><h3>Seccion ${this.escape(section.seccion_id)}</h3><p>Edita estructura, formulas y celdas desde una sola vista.</p></div>
                <div class="cne-toolbar" style="padding:12px 16px 0 16px;">
                    ${section.tipo_seccion !== "Narrativa" ? `${(this.get_columns(section.seccion_id).length > 0 && this.get_rows(section.seccion_id).length > 0) ? `<button class="cne-btn cne-download-csv">Descargar CSV</button>` : ""}<button class="cne-btn cne-upload-csv">Cargar CSV</button><input type="file" class="cne-csv-input" accept=".csv,text/csv,.txt,.tsv" style="display:none">` : ""}
                </div>
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
                <div class="cne-toolbar"><button class="cne-btn cne-add-column">Nueva Columna</button><button class="cne-btn cne-toggle-fullscreen" style="margin-left:auto;">Expandir Pantalla</button></div>
                <div class="cne-structure-wrap">
                    <table class="cne-structure-table">
                        <thead><tr><th>Codigo</th><th>Etiqueta</th><th>Grupo</th><th>Tipo</th><th>Alineacion</th><th>Entero</th><th>Auto</th><th>Formula</th><th>Orden</th><th>Total</th><th></th></tr></thead>
                        <tbody>
                            ${rows.length ? rows.map((row, index) => `
                                <tr>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="codigo_columna" data-original-code="${this.escape(row.codigo_columna || "")}" value="${this.escape(row.codigo_columna || "")}"></td>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="etiqueta" value="${this.escape(row.etiqueta || "")}"></td>
                                    <td><input class="cne-column-field" data-index="${index}" data-fieldname="grupo_columna" value="${this.escape(row.grupo_columna || "")}"></td>
                                    <td>${this.inlineSelect("cne-column-field", index, "tipo_dato", row.tipo_dato || "Moneda", ["Texto", "Numero", "Moneda", "Porcentaje"])}</td>
                                    <td>${this.inlineSelect("cne-column-field", index, "alineacion", row.alineacion || "Right", ["Left", "Center", "Right"])}</td>
                                    <td><input type="checkbox" class="cne-column-field" data-index="${index}" data-fieldname="redondear_entero" ${this.checked(row.redondear_entero)}></td>
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
                <div class="cne-toolbar"><button class="cne-btn cne-add-row">Nueva Fila</button><button class="cne-btn cne-toggle-fullscreen" style="margin-left:auto;">Expandir Pantalla</button></div>
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
                <div class="cne-card-head" style="display:flex; justify-content:space-between; align-items:center;">
                    <div><h3>Matriz Visual</h3><p>Edita celdas manuales y revisa valores calculados en tiempo real.</p></div>
                    <button class="cne-btn cne-toggle-fullscreen">Expandir Pantalla</button>
                </div>
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
            const cell = matrix[`${row.codigo_fila}::${column.codigo_columna}`] || { value: "", is_manual: false, is_computed: false, format: null, round: null };
            let value = cell.value === null || cell.value === undefined ? "" : String(cell.value);
            const format = cell.format || column.tipo_dato || "Moneda";
            const isRound = cell.round !== null && cell.round !== undefined ? cell.round : column.redondear_entero;
            if (isRound && !isNaN(cell.value) && cell.value !== "") value = String(Math.round(Number(cell.value)));
            return `<td>
                <div class="cne-matrix-cell ${cell.is_computed && !cell.is_manual ? 'computed' : ''}">
                    <div class="dropdown cne-matrix-format-dropdown">
                        <button class="cne-matrix-format-btn dropdown-toggle" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Formato">
                            ${format === 'Numero' ? '#' : format === 'Moneda' ? '$' : format === 'Porcentaje' ? '%' : 'T'}
                        </button>
                        <div class="dropdown-menu">
                            <a class="dropdown-item cne-format-option" href="#" data-format="Numero" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}"># Número</a>
                            <a class="dropdown-item cne-format-option" href="#" data-format="Moneda" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}">$ Moneda</a>
                            <a class="dropdown-item cne-format-option" href="#" data-format="Porcentaje" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}">% Porcentaje</a>
                            <a class="dropdown-item cne-format-option" href="#" data-format="Texto" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}">T Texto</a>
                            <div class="dropdown-divider"></div>
                            <a class="dropdown-item cne-format-option" href="#" data-format="ToggleRound" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}">
                                ${isRound ? '☑' : '☐'} Redondear entero
                            </a>
                        </div>
                    </div>
                    <input class="cne-matrix-input" data-row-code="${this.escape(row.codigo_fila)}" data-column-code="${this.escape(column.codigo_columna)}" value="${this.escape(value)}">
                </div>
            </td>`;
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

    open_csv_picker() {
        const input = this.wrapper.find('.cne-csv-input').get(0);
        if (input) {
            input.value = '';
            input.click();
        }
    }

    handle_csv_upload(event) {
        const file = event.currentTarget.files && event.currentTarget.files[0];
        const section = this.get_current_section();
        const doc = this.get_doc();
        if (!file || !section || !doc) return;

        const reader = new FileReader();
        reader.onload = () => {
            try {
                const parsed = this.parse_csv_table(String(reader.result || ''));
                this.apply_csv_to_section(section.seccion_id, parsed);
                this.render_editor();
                frappe.show_alert({ indicator: 'green', message: __('CSV cargado en la seccion actual') });
            } catch (error) {
                frappe.msgprint({
                    title: __('CSV invalido'),
                    indicator: 'red',
                    message: __(error.message || 'No se pudo interpretar el archivo CSV.'),
                });
            }
        };
        reader.readAsText(file, 'utf-8');
    }

    parse_csv_table(content) {
        const lines = String(content || '').replace(/^\uFEFF/, '').split(/\r?\n/).filter((line) => line.trim());
        if (lines.length < 2) {
            throw new Error(__('El archivo debe incluir una fila de encabezados y al menos una fila de datos.'));
        }
        const delimiter = this.detect_csv_delimiter(lines[0]);
        const rows = lines.map((line) => this.parse_csv_line(line, delimiter));
        const headers = rows[0].map((value) => String(value || '').trim());
        if (headers.length < 2) {
            throw new Error(__('El archivo debe tener al menos una columna de descripcion y una columna de valores.'));
        }
        return { headers, rows: rows.slice(1) };
    }

    detect_csv_delimiter(headerLine) {
        const candidates = [',', ';', '\t'];
        let best = ',';
        let bestCount = -1;
        candidates.forEach((candidate) => {
            const count = headerLine.split(candidate).length;
            if (count > bestCount) {
                best = candidate;
                bestCount = count;
            }
        });
        return best;
    }

    parse_csv_line(line, delimiter) {
        const result = [];
        let current = '';
        let inQuotes = false;
        for (let i = 0; i < line.length; i += 1) {
            const char = line[i];
            const next = line[i + 1];
            if (char === '"') {
                if (inQuotes && next === '"') {
                    current += '"';
                    i += 1;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === delimiter && !inQuotes) {
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        result.push(current.trim());
        return result;
    }

    apply_csv_to_section(sectionId, parsed) {
        const doc = this.get_doc();
        const headers = parsed.headers;
        const dataRows = parsed.rows;
        const valueHeaders = headers.slice(1);

        doc.columnas_tabulares = (doc.columnas_tabulares || []).filter((row) => row.seccion_id !== sectionId);
        doc.filas_tabulares = (doc.filas_tabulares || []).filter((row) => row.seccion_id !== sectionId);
        doc.celdas_tabulares = (doc.celdas_tabulares || []).filter((row) => row.seccion_id !== sectionId);

        valueHeaders.forEach((header, index) => {
            doc.columnas_tabulares.push({
                seccion_id: sectionId,
                codigo_columna: this.build_csv_column_code(header, index + 1),
                etiqueta: header || __('Columna {0}', [index + 1]),
                grupo_columna: '',
                tipo_dato: 'Moneda',
                alineacion: 'Right',
                calculo_automatico: 0,
                formula_columnas: '',
                orden: index + 1,
                es_total: 0,
            });
        });

        dataRows.forEach((rawRow, rowIndex) => {
            const description = String(rawRow[0] || '').trim();
            if (!description) return;
            const normalized = description.toLowerCase();
            const tipoFila = normalized.startsWith('total') ? 'Total' : normalized.startsWith('subtotal') ? 'Subtotal' : 'Detalle';
            const codigoFila = this.build_csv_row_code(description, rowIndex + 1);
            doc.filas_tabulares.push({
                seccion_id: sectionId,
                codigo_fila: codigoFila,
                descripcion: description,
                nivel: 1,
                tipo_fila: tipoFila,
                calculo_automatico: 0,
                formula_filas: '',
                orden: rowIndex + 1,
                negrita: tipoFila !== 'Detalle' ? 1 : 0,
                subrayado: tipoFila === 'Total' ? 1 : 0,
            });

            valueHeaders.forEach((header, colIndex) => {
                const rawValue = rawRow[colIndex + 1];
                if (rawValue === undefined || rawValue === null || String(rawValue).trim() === '') return;
                const numericValue = this.parse_csv_numeric_value(rawValue);
                doc.celdas_tabulares.push({
                    seccion_id: sectionId,
                    codigo_fila: codigoFila,
                    codigo_columna: this.build_csv_column_code(header, colIndex + 1),
                    valor_numero: numericValue,
                    valor_texto: numericValue === null ? String(rawValue).trim() : '',
                    formato_numero: numericValue === null ? 'Texto' : 'Moneda',
                });
            });
        });
    }

    build_csv_column_code(header, index) {
        const code = String(header || '')
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^A-Za-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .toUpperCase();
        return (code || `COL_${index}`).slice(0, 20);
    }

    build_csv_row_code(description, index) {
        const code = String(description || '')
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^A-Za-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .toUpperCase();
        return (code || `FIL_${index}`).slice(0, 20);
    }

    parse_csv_numeric_value(rawValue) {
        const cleaned = String(rawValue || '').trim();
        if (!cleaned) return null;
        const normalized = cleaned
            .replace(/C\$/gi, '')
            .replace(/US\$/gi, '')
            .replace(/\s+/g, '')
            .replace(/\(([^)]+)\)/, '-$1')
            .replace(/,/g, '');
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : null;
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
    }

    update_matrix_value(event) {
        const doc = this.get_doc();
        const section = this.get_current_section();
        if (!doc || !section) return;
        doc.celdas_tabulares = doc.celdas_tabulares || [];
        const rowCode = event.currentTarget.dataset.rowCode;
        const columnCode = event.currentTarget.dataset.columnCode;
        const raw = event.currentTarget.value;
        const index = doc.celdas_tabulares.findIndex((row) => row.seccion_id === section.seccion_id && row.codigo_fila === rowCode && row.codigo_columna === columnCode);

        let cell = index >= 0 ? doc.celdas_tabulares[index] : null;
        if (!cell) {
            if (raw === "") return;
            const colDefs = this.get_columns(section.seccion_id);
            const type = colDefs.find(c => c.codigo_columna === columnCode)?.tipo_dato || "Moneda";
            cell = { seccion_id: section.seccion_id, codigo_fila: rowCode, codigo_columna: columnCode, formato_numero: type === "Moneda" ? "Moneda" : type === "Porcentaje" ? "Porcentaje" : type === "Texto" ? "Texto" : "Numero", es_manual: 0 };
            doc.celdas_tabulares.push(cell);
        }

        if (raw === "") {
            cell.valor_texto = "";
            cell.valor_numero = null;
            cell.es_manual = 0;
        } else if (cell.formato_numero === "Texto") {
            cell.valor_texto = raw;
            cell.valor_numero = null;
            cell.es_manual = 1;
        } else {
            cell.valor_numero = this.as_float(raw);
            cell.valor_texto = "";
            cell.es_manual = 1;
        }

        const colDef = this.get_columns(section.seccion_id).find(c => c.codigo_columna === columnCode);
        const defaultFmt = colDef?.tipo_dato || "Moneda";
        if (cell.es_manual === 0 && cell.formato_numero === defaultFmt) {
            const finalIdx = doc.celdas_tabulares.indexOf(cell);
            if (finalIdx >= 0) doc.celdas_tabulares.splice(finalIdx, 1);
        }

        this.render_matrix_only();
    }

    update_matrix_format(event) {
        const doc = this.get_doc();
        const section = this.get_current_section();
        if (!doc || !section) return;
        doc.celdas_tabulares = doc.celdas_tabulares || [];
        const rowCode = event.currentTarget.dataset.rowCode;
        const columnCode = event.currentTarget.dataset.columnCode;
        const format = event.currentTarget.dataset.format;
        const index = doc.celdas_tabulares.findIndex((row) => row.seccion_id === section.seccion_id && row.codigo_fila === rowCode && row.codigo_columna === columnCode);

        let cell = index >= 0 ? doc.celdas_tabulares[index] : null;
        if (!cell) {
            const defaultFormat = this.get_columns(section.seccion_id).find(c => c.codigo_columna === columnCode)?.tipo_dato || "Moneda";
            cell = { seccion_id: section.seccion_id, codigo_fila: rowCode, codigo_columna: columnCode, valor_texto: "", valor_numero: null, formato_numero: defaultFormat, es_manual: 0, redondear_entero: 0 };
            if (format === "ToggleRound") {
                cell.redondear_entero = 1;
            } else {
                cell.formato_numero = format;
            }
            doc.celdas_tabulares.push(cell);
        } else {
            if (format === "ToggleRound") {
                cell.redondear_entero = cell.redondear_entero ? 0 : 1;
            } else {
                cell.formato_numero = format;
                if (format === "Texto" && cell.valor_numero !== null && cell.es_manual) {
                    cell.valor_texto = String(cell.valor_numero);
                    cell.valor_numero = null;
                } else if (format !== "Texto" && cell.valor_texto && cell.es_manual) {
                    cell.valor_numero = this.as_float(cell.valor_texto);
                    cell.valor_texto = "";
                }
            }
        }
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

            let formatFromExplicit = null;
            if (explicit.has(key)) {
                formatFromExplicit = explicit.get(key).formato_numero;
            }

            if (stack.has(key)) return { value: "", is_manual: false, is_computed: true, format: formatFromExplicit };
            stack.add(key);
            const row = rowsByCode[rowCode];
            const col = colsByCode[columnCode];
            let result = { value: "", is_manual: false, is_computed: false, format: formatFromExplicit };

            const isManualFromExplicit = explicit.has(key) && (explicit.get(key).es_manual === 1 || explicit.get(key).es_manual === "1");

            if (!isManualFromExplicit && row && this.truthy(row.calculo_automatico) && row.formula_filas) {
                result = { value: this.evaluate_formula(row.formula_filas, (refCode, sign) => sign * this.as_float(resolve(refCode, columnCode, stack).value)), is_manual: false, is_computed: true, format: formatFromExplicit };
            } else if (!isManualFromExplicit && col && this.truthy(col.calculo_automatico) && col.formula_columnas) {
                result = { value: this.evaluate_formula(col.formula_columnas, (refCode, sign) => sign * this.as_float(resolve(rowCode, refCode, stack).value)), is_manual: false, is_computed: true, format: formatFromExplicit };
            } else if (explicit.has(key)) {
                const cell = explicit.get(key);
                const val = cell.valor_numero !== null ? cell.valor_numero : (cell.valor_texto || "");
                result = { value: val, is_manual: isManualFromExplicit, is_computed: false, format: formatFromExplicit };
            }

            stack.delete(key);
            cache.set(key, result);
            return result;

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

    sectionHasCsvData(sectionId) {
        return this.get_columns(sectionId).length > 0 && this.get_rows(sectionId).length > 0;
    }

    download_current_section_csv() {
        const section = this.get_current_section();
        if (!section) return;
        const columns = this.get_columns(section.seccion_id);
        const rows = this.get_rows(section.seccion_id);
        if (!columns.length || !rows.length) {
            frappe.msgprint(__("La seccion actual no tiene datos suficientes para exportar CSV."));
            return;
        }
        const matrix = this.compute_matrix(section.seccion_id);
        const hasGroups = columns.some((column) => (column.grupo_columna || "").trim());
        const csvRows = [];
        if (hasGroups) {
            csvRows.push(["Concepto"].concat(columns.map((column) => (column.grupo_columna || "").trim())));
            csvRows.push([""].concat(columns.map((column) => column.etiqueta || column.codigo_columna || "")));
        } else {
            csvRows.push(["Concepto"].concat(columns.map((column) => column.etiqueta || column.codigo_columna || "")));
        }
        rows.forEach((row) => {
            const values = columns.map((column) => {
                const cell = matrix[`${row.codigo_fila}::${column.codigo_columna}`] || { value: "" };
                return cell.value === null || cell.value === undefined ? "" : String(cell.value);
            });
            csvRows.push([row.descripcion || row.codigo_fila || ""].concat(values));
        });
        const csvContent = csvRows.map((row) => row.map((value) => {
            const textValue = String(value ?? "");
            if (/[",\n;]/.test(textValue)) {
                return '"' + textValue.replace(/"/g, '""') + '"';
            }
            return textValue;
        }).join(",")).join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `${section.seccion_id || "seccion"}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
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





