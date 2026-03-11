frappe.pages["creador-de-mapeo-contable"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Creador de Mapeo Contable",
        single_column: true,
    });

    frappe.pages["creador-de-mapeo-contable"].editor = new CreadorMapeoContable(page);
    frappe.pages["creador-de-mapeo-contable"].editor.init();
};

frappe.pages["creador-de-mapeo-contable"].on_page_show = function () {
    const editor = frappe.pages["creador-de-mapeo-contable"].editor;
    if (!editor) return;

    editor.apply_route_options();
    const hasRouteOptions = !!Object.keys(editor.state.route_options || {}).length;
    editor.ensure_filter_bar_visible();
    if (hasRouteOptions || !editor.bootstrapped) {
        editor.load_bootstrap();
    }
};

class CreadorMapeoContable {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
        this.state = {
            cliente: null,
            esquema_name: null,
            clients: [],
            schemes: [],
            scheme: null,
            catalogs: {},
            current_rule_id: null,
            route_options: {},
        };
        this.setting_filters = false;
        this.loading_bootstrap = false;
        this.last_bootstrap_key = null;
        this.bootstrapped = false;
        this.ruleSequence = 0;
    }

    init() {
        this.setup_styles();
        this.render_shell();
        this.ensure_filter_bar_visible();
        this.bind_events();
        this.page.set_primary_action(__("Guardar Esquema"), () => this.save_current_scheme(), "save");
        this.page.set_secondary_action(__("Nuevo Esquema"), () => this.open_create_scheme_dialog());
    }

    apply_route_options() {
        this.state.route_options = frappe.route_options || {};
        frappe.route_options = null;
    }

    setup_styles() {
        if (document.getElementById("cmc-styles")) return;
        const style = document.createElement("style");
        style.id = "cmc-styles";
        style.textContent = `
            .cmc-shell{display:grid;grid-template-columns:300px minmax(0,1fr);gap:18px;padding:18px;border:1px solid #d9e6df;border-radius:24px;background:radial-gradient(circle at top left,#fffaf1 0%,#eff8f2 48%,#f7fbff 100%)}
            .cmc-sidebar,.cmc-card{background:#fff;border:1px solid #d8e2dc;border-radius:18px;box-shadow:0 16px 36px rgba(15,23,42,.06)}
            .cmc-sidebar-head,.cmc-card-head{padding:16px 18px;border-bottom:1px solid #edf2ef}
            .cmc-sidebar-head h3,.cmc-card-head h3{margin:0;color:#122c1e;font-size:15px;font-weight:800}
            .cmc-sidebar-head p,.cmc-card-head p{margin:6px 0 0;color:#667b6f;font-size:12px}
            .cmc-sidebar-actions{padding:14px 16px;border-bottom:1px solid #edf2ef}
            .cmc-list{max-height:calc(100vh - 270px);overflow:auto}
            .cmc-list-item{padding:13px 16px;border-bottom:1px solid #eff4f1;cursor:pointer;transition:background .15s ease}
            .cmc-list-item:hover{background:#f6fbf7}.cmc-list-item.active{background:#def3e6}
            .cmc-list-item strong{display:block;color:#163622;font-size:13px}.cmc-list-item span{display:block;margin-top:5px;color:#667b6f;font-size:11px}
            .cmc-main{display:flex;flex-direction:column;gap:16px;min-width:0}
            .cmc-empty{padding:56px 26px;text-align:center;border:1px dashed #bfd1c6;border-radius:18px;background:rgba(255,255,255,.72);color:#667b6f}
            .cmc-empty strong{display:block;font-size:18px;color:#163622;margin-bottom:8px}
            .cmc-grid{display:grid;gap:12px}.cmc-grid.meta{grid-template-columns:repeat(4,minmax(0,1fr))}.cmc-grid.rule{grid-template-columns:repeat(3,minmax(0,1fr))}
            .cmc-field{display:flex;flex-direction:column;gap:6px}.cmc-field label{font-size:11px;text-transform:uppercase;font-weight:800;color:#667b6f;letter-spacing:.35px}
            .cmc-field input,.cmc-field select,.cmc-field textarea{width:100%;border:1px solid #c6d4cc;border-radius:10px;padding:9px 10px;font-size:13px;background:#fff;color:#122c1e}
            .cmc-field textarea{min-height:92px;resize:vertical}.cmc-field.inline{flex-direction:row;align-items:center;gap:10px}.cmc-field.inline label{margin:0}
            .cmc-pills{display:flex;gap:8px;flex-wrap:wrap;padding:0 18px 14px}.cmc-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;background:#edf8f1;color:#1c6a42;font-size:11px;font-weight:800;text-transform:uppercase}
            .cmc-toolbar{display:flex;gap:8px;flex-wrap:wrap;padding:0 18px 14px}.cmc-btn{border:1px solid #c6d4cc;background:#fff;color:#163622;border-radius:999px;padding:8px 13px;font-size:12px;font-weight:800;cursor:pointer}
            .cmc-btn.primary{background:#1f6f43;border-color:#1f6f43;color:#fff}.cmc-btn.danger{background:#fff1f2;border-color:#fecdd3;color:#be123c}
            .cmc-board{display:grid;grid-template-columns:320px minmax(0,1fr);gap:16px}.cmc-rule-list{max-height:calc(100vh - 420px);overflow:auto}
            .cmc-rule-item{padding:14px 16px;border-bottom:1px solid #eff4f1;cursor:pointer}.cmc-rule-item:hover{background:#f7fbf8}.cmc-rule-item.active{background:#eef8ff}
            .cmc-rule-item strong{display:block;color:#163622;font-size:13px}.cmc-rule-item span{display:block;margin-top:5px;color:#667b6f;font-size:11px}
            .cmc-rule-item .cmc-rule-tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.cmc-tag{display:inline-flex;padding:3px 8px;border-radius:999px;background:#f1f5f9;color:#334155;font-size:10px;font-weight:800;text-transform:uppercase}
            .cmc-help{padding:0 18px 16px;color:#566a60;font-size:12px}.cmc-help code{background:#f3f6f4;padding:2px 6px;border-radius:6px}
            @media (max-width:1200px){.cmc-shell,.cmc-board,.cmc-grid.meta,.cmc-grid.rule{grid-template-columns:1fr}}
        `;
        document.head.appendChild(style);
    }

    render_shell() {
        this.wrapper.html(`
            <div class="cmc-shell">
                <aside class="cmc-sidebar">
                    <div class="cmc-sidebar-head">
                        <h3>Esquemas de mapeo</h3>
                        <p>Selecciona un cliente, abre un esquema y edita sus reglas sin entrar al grid hijo.</p>
                    </div>
                    <div class="cmc-sidebar-actions">
                        <button class="cmc-btn primary cmc-create-scheme">${__("Nuevo Esquema")}</button>
                        <button class="cmc-btn cmc-view-balanza" style="margin-top: 6px; width: 100%;">${__("Ver Balanza")}</button>
                    </div>
                    <div class="cmc-list" data-role="scheme-list"></div>
                </aside>
                <section class="cmc-main">
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
        this.schemeField = this.page.add_field({
            fieldtype: "Select",
            fieldname: "esquema_name",
            label: __("Esquema"),
            options: "\n",
            change: () => this.on_scheme_change(),
        });

        this.$schemeList = this.wrapper.find('[data-role="scheme-list"]');
        this.$editor = this.wrapper.find('[data-role="editor"]');
    }

    ensure_filter_bar_visible() {
        const show = () => {
            const $pageForm = $(this.page.wrapper).find(".page-form");
            if ($pageForm.length) {
                $pageForm.removeClass("hide hidden d-none");
                $pageForm.attr("style", "display:flex !important; flex-wrap:wrap; gap:8px; align-items:flex-end; padding:12px 15px;");
            }
        };
        show();
        setTimeout(show, 0);
        setTimeout(show, 200);
    }

    bind_events() {
        this.wrapper.on("click", ".cmc-create-scheme", () => this.open_create_scheme_dialog());
        this.wrapper.on("click", ".cmc-view-balanza", () => this.view_balanza());
        this.wrapper.on("click", ".cmc-list-item", (event) => {
            const $item = $(event.currentTarget);
            const name = $item.attr("data-scheme-name");
            if (name) this.load_bootstrap({ esquema_name: name });
        });
        this.wrapper.on("change input", ".cmc-meta-field", (event) => this.update_meta_field(event));
        this.wrapper.on("click", ".cmc-open-form", () => {
            const doc = this.get_doc();
            if (doc?.name) frappe.set_route("Form", "Esquema Mapeo Contable", doc.name);
        });
        this.wrapper.on("click", ".cmc-new-rule", () => this.add_rule());
        this.wrapper.on("click", ".cmc-duplicate-rule", () => this.duplicate_current_rule());
        this.wrapper.on("click", ".cmc-delete-rule", () => this.delete_current_rule());
        this.wrapper.on("click", ".cmc-rule-item", (event) => {
            const $item = $(event.currentTarget);
            this.state.current_rule_id = $item.attr("data-rule-id") || null;
            this.render_editor();
        });
        this.wrapper.on("change input", ".cmc-rule-field", (event) => this.update_rule_field(event));
    }

    on_client_change() {
        if (this.setting_filters) return;
        this.load_bootstrap({ cliente: this.clientField.get_value() || null, esquema_name: null });
    }

    on_scheme_change() {
        if (this.setting_filters) return;
        const esquema_name = this.schemeField.get_value() || null;
        if (!esquema_name) {
            this.state.esquema_name = null;
            this.state.scheme = null;
            this.render_schemes();
            this.render_editor();
            return;
        }
        this.load_bootstrap({ esquema_name });
    }

    load_bootstrap(overrides = {}) {
        const route = this.state.route_options || {};
        const args = {
            cliente: overrides.cliente !== undefined ? overrides.cliente : (route.cliente || this.clientField.get_value() || null),
            esquema_name: overrides.esquema_name !== undefined ? overrides.esquema_name : (route.esquema_name || this.schemeField.get_value() || null),
        };
        const bootstrapKey = JSON.stringify(args);
        this.state.route_options = {};

        if (this.loading_bootstrap) return;
        if (bootstrapKey === this.last_bootstrap_key) return;

        this.loading_bootstrap = true;

        frappe.call({
            method: "gestion_contable.gestion_contable.page.creador_de_mapeo_contable.creador_de_mapeo_contable.get_mapping_editor_bootstrap",
            args,
            freeze: true,
            freeze_message: __("Cargando creador de mapeo..."),
            callback: (r) => {
                const data = r.message || {};
                this.state.cliente = data.cliente || args.cliente || null;
                this.state.esquema_name = data.esquema_name || args.esquema_name || null;
                this.state.clients = data.clients || [];
                this.state.schemes = data.schemes || [];
                this.state.catalogs = data.catalogs || {};
                this.state.scheme = this.decorate_scheme(data.scheme || null);
                this.ensure_current_rule();
                this.sync_filter_options();
                this.render_schemes();
                this.render_editor();
                this.last_bootstrap_key = bootstrapKey;
                this.bootstrapped = true;
            },
            always: () => {
                this.loading_bootstrap = false;
            },
        });
    }

    decorate_scheme(scheme) {
        if (!scheme?.doc) return null;
        const reglas = (scheme.doc.reglas || []).map((rule) => ({
            ...rule,
            __editor_id: rule.__editor_id || this.next_rule_id(),
        }));
        return {
            ...scheme,
            doc: {
                ...scheme.doc,
                reglas: this.sort_rules(reglas),
            },
        };
    }

    next_rule_id() {
        this.ruleSequence += 1;
        return `RULE-${this.ruleSequence}`;
    }

    ensure_current_rule() {
        const rules = this.get_rules();
        if (!rules.length) {
            this.state.current_rule_id = null;
            return;
        }
        if (!rules.some((row) => row.__editor_id === this.state.current_rule_id)) {
            this.state.current_rule_id = rules[0].__editor_id;
        }
    }

    sync_filter_options() {
        this.setting_filters = true;
        this.set_select_options(this.clientField, this.state.clients);
        this.set_select_options(this.schemeField, this.state.schemes);

        const client_val = this.state.cliente || "";
        const scheme_val = this.state.esquema_name || "";

        // Use synchronous setter and bypass async change trigger
        if (this.clientField.$input) this.clientField.$input.val(client_val);
        this.clientField.value = client_val;
        this.clientField.last_value = client_val;

        if (this.schemeField.$input) this.schemeField.$input.val(scheme_val);
        this.schemeField.value = scheme_val;
        this.schemeField.last_value = scheme_val;

        this.setting_filters = false;
    }

    set_select_options(field, rows) {
        field.df.options = [""].concat((rows || []).map((row) => row.value)).join("\n");
        field.refresh();
    }

    render_schemes() {
        if (!this.state.cliente) {
            this.$schemeList.html(`
                <div class="cmc-empty">
                    <strong>${__("Selecciona un cliente")}</strong>
                    ${__("El editor lista los esquemas por cliente para que trabajes sobre uno vigente o prepares una nueva version.")}
                </div>
            `);
            return;
        }

        if (!this.state.schemes.length) {
            this.$schemeList.html(`
                <div class="cmc-empty">
                    <strong>${__("No hay esquemas para este cliente")}</strong>
                    ${__("Crea el primer esquema desde el boton superior y luego agrega las reglas de mapeo.")}
                </div>
            `);
            return;
        }

        this.$schemeList.html(this.state.schemes.map((scheme) => `
            <div class="cmc-list-item ${scheme.value === this.state.esquema_name ? "active" : ""}" data-scheme-name="${this.escape(scheme.value)}">
                <strong>${this.escape(scheme.value)}</strong>
                <span>${this.escape(scheme.label || "")}</span>
            </div>
        `).join(""));
    }

    render_editor() {
        const doc = this.get_doc();
        if (!doc) {
            this.$editor.html(`
                <div class="cmc-empty">
                    <strong>${__("Abre un esquema o crea uno nuevo")}</strong>
                    ${__("El editor permite mantener reglas, origenes y destinos con una vista mas clara que el grid del doctype.")}
                </div>
            `);
            return;
        }

        const rules = this.get_rules();
        const currentRule = this.get_current_rule();
        this.$editor.html(`
            ${this.render_meta_card(doc)}
            <div class="cmc-board">
                <div class="cmc-card">
                    <div class="cmc-card-head">
                        <h3>${__("Reglas del esquema")}</h3>
                        <p>${__("Selecciona una regla para editarla o crea una nueva.")}</p>
                    </div>
                    <div class="cmc-toolbar">
                        <button class="cmc-btn primary cmc-new-rule">${__("Nueva Regla")}</button>
                        <button class="cmc-btn cmc-duplicate-rule" ${currentRule ? "" : "disabled"}>${__("Duplicar")}</button>
                        <button class="cmc-btn danger cmc-delete-rule" ${currentRule ? "" : "disabled"}>${__("Eliminar")}</button>
                    </div>
                    <div class="cmc-rule-list">
                        ${rules.length ? rules.map((rule, index) => this.render_rule_list_item(rule, index)).join("") : `
                            <div class="cmc-empty">
                                <strong>${__("Sin reglas")}</strong>
                                ${__("Agrega la primera regla y define el selector de cuentas, el destino y la operacion de agregacion.")}
                            </div>
                        `}
                    </div>
                </div>
                ${this.render_rule_editor(currentRule)}
            </div>
        `);
    }

    render_meta_card(doc) {
        return `
            <div class="cmc-card">
                <div class="cmc-card-head">
                    <h3>${this.escape(doc.nombre_esquema || doc.name)}</h3>
                    <p>${__("Cliente: {0}", [this.escape(doc.cliente || "")])}</p>
                </div>
                <div class="cmc-pills">
                    <span class="cmc-pill">${__("Version {0}", [doc.version || 1])}</span>
                    ${this.truthy(doc.es_vigente) ? `<span class="cmc-pill">${__("Vigente")}</span>` : ""}
                    ${this.truthy(doc.activo) ? `<span class="cmc-pill">${__("Activo")}</span>` : `<span class="cmc-pill">${__("Inactivo")}</span>`}
                </div>
                <div class="cmc-toolbar">
                    <button class="cmc-btn cmc-open-form">${__("Abrir Formulario")}</button>
                </div>
                <div class="cmc-grid meta" style="padding:0 18px 18px;">
                    <div class="cmc-field">
                        <label>${__("Nombre Esquema")}</label>
                        <input type="text" value="${this.escape(doc.nombre_esquema || doc.name || "")}" readonly />
                    </div>
                    <div class="cmc-field">
                        <label>${__("Compania")}</label>
                        <input class="cmc-meta-field" data-fieldname="company" type="text" value="${this.escape(doc.company || "")}" />
                    </div>
                    <div class="cmc-field">
                        <label>${__("Marco Contable")}</label>
                        <select class="cmc-meta-field" data-fieldname="marco_contable">${this.build_options(this.state.catalogs.marcos_contables, doc.marco_contable)}</select>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Tipo Paquete")}</label>
                        <select class="cmc-meta-field" data-fieldname="tipo_paquete">${this.build_options(this.state.catalogs.tipos_paquete, doc.tipo_paquete)}</select>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Version")}</label>
                        <input class="cmc-meta-field" data-fieldname="version" type="number" min="1" value="${this.escape(doc.version || 1)}" />
                    </div>
                    <div class="cmc-field inline">
                        <label>${__("Activo")}</label>
                        <input class="cmc-meta-field" data-fieldname="activo" type="checkbox" ${this.checked(doc.activo)} />
                    </div>
                    <div class="cmc-field inline">
                        <label>${__("Es Vigente")}</label>
                        <input class="cmc-meta-field" data-fieldname="es_vigente" type="checkbox" ${this.checked(doc.es_vigente)} />
                    </div>
                    <div class="cmc-field" style="grid-column:1/-1;">
                        <label>${__("Descripcion")}</label>
                        <textarea class="cmc-meta-field" data-fieldname="descripcion">${this.escape(doc.descripcion || "")}</textarea>
                    </div>
                </div>
            </div>
        `;
    }

    render_rule_list_item(rule, index) {
        return `
            <div class="cmc-rule-item ${rule.__editor_id === this.state.current_rule_id ? "active" : ""}" data-rule-id="${this.escape(rule.__editor_id)}">
                <strong>${__("Regla {0}", [index + 1])} - ${this.escape(rule.destino_tipo || __("Sin destino"))}</strong>
                <span>${this.escape(this.rule_summary(rule))}</span>
                <div class="cmc-rule-tags">
                    <span class="cmc-tag">${this.escape(rule.origen_version || "Actual")}</span>
                    <span class="cmc-tag">${this.escape(rule.selector_tipo || "Lista")}</span>
                    ${this.truthy(rule.obligatoria) ? `<span class="cmc-tag">${__("Obligatoria")}</span>` : ""}
                </div>
            </div>
        `;
    }

    render_rule_editor(rule) {
        if (!rule) {
            return `
                <div class="cmc-card">
                    <div class="cmc-card-head">
                        <h3>${__("Editor de Regla")}</h3>
                        <p>${__("Selecciona una regla desde la lista o crea una nueva.")}</p>
                    </div>
                    <div class="cmc-empty">
                        <strong>${__("No hay una regla activa")}</strong>
                        ${__("Cuando abras una regla veras su selector, su origen de balanza y el destino exacto que actualiza.")}
                    </div>
                </div>
            `;
        }

        return `
            <div class="cmc-card">
                <div class="cmc-card-head">
                    <h3>${__("Editor de Regla")}</h3>
                    <p>${this.escape(this.rule_summary(rule))}</p>
                </div>
                <div class="cmc-help">
                    ${__("Usa <code>Lista</code> para varias cuentas separadas por coma o salto de linea. Usa <code>Rango</code> en formato <code>1101-1199</code>.")}
                </div>
                <div class="cmc-grid rule" style="padding:0 18px 18px;">
                    <div class="cmc-field inline">
                        <label>${__("Activa")}</label>
                        <input class="cmc-rule-field" data-fieldname="activo" type="checkbox" ${this.checked(rule.activo)} />
                    </div>
                    <div class="cmc-field">
                        <label>${__("Orden")}</label>
                        <input class="cmc-rule-field" data-fieldname="orden_ejecucion" type="number" min="1" value="${this.escape(rule.orden_ejecucion || 1)}" />
                    </div>
                    <div class="cmc-field">
                        <label>${__("Origen Version")}</label>
                        <select class="cmc-rule-field" data-fieldname="origen_version">${this.build_options(this.state.catalogs.origen_versiones, rule.origen_version)}</select>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Destino Tipo")}</label>
                        <select class="cmc-rule-field" data-fieldname="destino_tipo">${this.build_options(this.state.catalogs.destino_tipos, rule.destino_tipo)}</select>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Selector Tipo")}</label>
                        <select class="cmc-rule-field" data-fieldname="selector_tipo">${this.build_options(this.state.catalogs.selector_tipos, rule.selector_tipo)}</select>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Operacion")}</label>
                        <select class="cmc-rule-field" data-fieldname="operacion_agregacion">${this.build_options(this.state.catalogs.operaciones_agregacion, rule.operacion_agregacion)}</select>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Signo Presentacion")}</label>
                        <select class="cmc-rule-field" data-fieldname="signo_presentacion">${this.build_options(this.state.catalogs.signos_presentacion, rule.signo_presentacion)}</select>
                    </div>
                    <div class="cmc-field inline">
                        <label>${__("Sobrescribir Manual")}</label>
                        <input class="cmc-rule-field" data-fieldname="sobrescribir_manual" type="checkbox" ${this.checked(rule.sobrescribir_manual)} />
                    </div>
                    <div class="cmc-field inline">
                        <label>${__("Obligatoria")}</label>
                        <input class="cmc-rule-field" data-fieldname="obligatoria" type="checkbox" ${this.checked(rule.obligatoria)} />
                    </div>
                    <div class="cmc-field" style="grid-column:1/-1;">
                        <label>${__("Selector Valor")}</label>
                        <textarea class="cmc-rule-field" data-fieldname="selector_valor">${this.escape(rule.selector_valor || "")}</textarea>
                    </div>
                    <div class="cmc-field">
                        <label>${__("Filtro Centro Costo")}</label>
                        <input class="cmc-rule-field" data-fieldname="filtro_centro_costo" type="text" value="${this.escape(rule.filtro_centro_costo || "")}" />
                    </div>
                    <div class="cmc-field" style="grid-column:span 2;">
                        <label>${__("Descripcion Destino")}</label>
                        <input class="cmc-rule-field" data-fieldname="destino_descripcion" type="text" value="${this.escape(rule.destino_descripcion || "")}" />
                    </div>
                    ${this.render_destination_fields(rule)}
                    <div class="cmc-field" style="grid-column:1/-1;">
                        <label>${__("Comentario")}</label>
                        <textarea class="cmc-rule-field" data-fieldname="comentario">${this.escape(rule.comentario || "")}</textarea>
                    </div>
                </div>
            </div>
        `;
    }

    render_destination_fields(rule) {
        if (rule.destino_tipo === "Cedula Sumaria") {
            return `
                <div class="cmc-field">
                    <label>${__("Codigo Sumaria")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_codigo_sumaria" type="text" value="${this.escape(rule.destino_codigo_sumaria || "")}" />
                </div>
                <div class="cmc-field">
                    <label>${__("Codigo Linea Sumaria")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_codigo_linea_sumaria" type="text" value="${this.escape(rule.destino_codigo_linea_sumaria || "")}" />
                </div>
            `;
        }
        if (rule.destino_tipo === "Linea Estado") {
            const catalog = this.state.catalogs.estados_y_rubros || {};
            const available_estados = Object.keys(catalog[rule.destino_tipo_estado] || {});

            let select_estado = `<input class="cmc-rule-field" data-fieldname="destino_codigo_estado" type="text" value="${this.escape(rule.destino_codigo_estado || "")}" />`;
            if (available_estados.length > 0) {
                select_estado = `<select class="cmc-rule-field" data-fieldname="destino_codigo_estado"><option value=""></option>${available_estados.map(st => `<option value="${this.escape(st)}" ${st === rule.destino_codigo_estado ? 'selected' : ''}>${this.escape(st)}</option>`).join('')}</select>`;
            }

            const available_lineas = rule.destino_codigo_estado ? (catalog[rule.destino_tipo_estado]?.[rule.destino_codigo_estado] || []) : [];
            let select_linea = `<input class="cmc-rule-field" data-fieldname="destino_codigo_linea_estado" type="text" value="${this.escape(rule.destino_codigo_linea_estado || "")}" />`;

            if (available_lineas.length > 0) {
                select_linea = `
                    <input list="lineas_estado_${rule.__editor_id}" class="cmc-rule-field" data-fieldname="destino_codigo_linea_estado" type="text" value="${this.escape(rule.destino_codigo_linea_estado || "")}" placeholder="Escribe o selecciona..." />
                    <datalist id="lineas_estado_${rule.__editor_id}">
                        ${available_lineas.map(ln => `<option value="${this.escape(ln.value)}">${this.escape(ln.label)}</option>`).join('')}
                    </datalist>
               `;
            }

            return `
                <div class="cmc-field">
                    <label>${__("Tipo Estado")}</label>
                    <select class="cmc-rule-field" data-fieldname="destino_tipo_estado">${this.build_options(this.state.catalogs.tipos_estado, rule.destino_tipo_estado)}</select>
                </div>
                <div class="cmc-field">
                    <label>${__("Codigo Estado")}</label>
                    ${select_estado}
                </div>
                <div class="cmc-field">
                    <label>${__("Codigo Linea Estado")}</label>
                    ${select_linea}
                </div>
            `;
        }
        if (rule.destino_tipo === "Cifra Nota") {
            return `
                <div class="cmc-field">
                    <label>${__("Numero Nota")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_numero_nota" type="text" value="${this.escape(rule.destino_numero_nota || "")}" />
                </div>
                <div class="cmc-field">
                    <label>${__("Codigo Cifra")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_codigo_cifra" type="text" value="${this.escape(rule.destino_codigo_cifra || "")}" />
                </div>
            `;
        }
        if (rule.destino_tipo === "Celda Nota") {
            return `
                <div class="cmc-field">
                    <label>${__("Numero Nota")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_numero_nota" type="text" value="${this.escape(rule.destino_numero_nota || "")}" />
                </div>
                <div class="cmc-field">
                    <label>${__("Seccion ID")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_seccion_id" type="text" value="${this.escape(rule.destino_seccion_id || "")}" />
                </div>
                <div class="cmc-field">
                    <label>${__("Codigo Fila")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_codigo_fila" type="text" value="${this.escape(rule.destino_codigo_fila || "")}" />
                </div>
                <div class="cmc-field">
                    <label>${__("Codigo Columna")}</label>
                    <input class="cmc-rule-field" data-fieldname="destino_codigo_columna" type="text" value="${this.escape(rule.destino_codigo_columna || "")}" />
                </div>
                ${rule.origen_version === "Ambas" ? `
                    <div class="cmc-field">
                        <label>${__("Seccion ID Comparativa")}</label>
                        <input class="cmc-rule-field" data-fieldname="destino_seccion_id_comparativa" type="text" value="${this.escape(rule.destino_seccion_id_comparativa || "")}" />
                    </div>
                    <div class="cmc-field">
                        <label>${__("Codigo Fila Comparativa")}</label>
                        <input class="cmc-rule-field" data-fieldname="destino_codigo_fila_comparativa" type="text" value="${this.escape(rule.destino_codigo_fila_comparativa || "")}" />
                    </div>
                    <div class="cmc-field">
                        <label>${__("Codigo Columna Comparativa")}</label>
                        <input class="cmc-rule-field" data-fieldname="destino_codigo_columna_comparativa" type="text" value="${this.escape(rule.destino_codigo_columna_comparativa || "")}" />
                    </div>
                ` : ""}
            `;
        }
        return "";
    }

    rule_summary(rule) {
        const selector = rule.selector_tipo === "Todas"
            ? __("Todas las cuentas")
            : `${rule.selector_tipo || __("Selector")} ${String(rule.selector_valor || "").trim() || __("sin valor")}`;
        return `${selector} -> ${this.destination_label(rule)}`;
    }

    destination_label(rule) {
        if (rule.destino_tipo === "Cedula Sumaria") {
            return `${__("Sumaria")} ${rule.destino_codigo_sumaria || __("sin codigo")}`;
        }
        if (rule.destino_tipo === "Linea Estado") {
            return `${rule.destino_codigo_estado || rule.destino_tipo_estado || __("Estado")} / ${rule.destino_codigo_linea_estado || __("sin linea")}`;
        }
        if (rule.destino_tipo === "Cifra Nota") {
            return `${__("Nota")} ${rule.destino_numero_nota || "?"} / ${rule.destino_codigo_cifra || __("sin cifra")}`;
        }
        if (rule.destino_tipo === "Celda Nota") {
            return `${__("Nota")} ${rule.destino_numero_nota || "?"} / ${rule.destino_seccion_id || "?"} / ${rule.destino_codigo_fila || "?"} / ${rule.destino_codigo_columna || "?"}`;
        }
        return __("Destino sin definir");
    }
    open_create_scheme_dialog() {
        const dialog = new frappe.ui.Dialog({
            title: __("Nuevo Esquema de Mapeo"),
            fields: [
                { fieldname: "cliente", fieldtype: "Select", label: __("Cliente"), options: [""].concat((this.state.clients || []).map((row) => row.value)).join("\n"), reqd: 1, default: this.state.cliente || "" },
                { fieldname: "nombre_esquema", fieldtype: "Data", label: __("Nombre Esquema") },
                { fieldname: "company", fieldtype: "Link", label: __("Compania"), options: "Company" },
                { fieldname: "marco_contable", fieldtype: "Select", label: __("Marco Contable"), options: (this.state.catalogs.marcos_contables || []).join("\n"), default: "NIIF para PYMES" },
                { fieldname: "tipo_paquete", fieldtype: "Select", label: __("Tipo Paquete"), options: (this.state.catalogs.tipos_paquete || []).join("\n"), default: "Preliminar" },
                { fieldname: "descripcion", fieldtype: "Small Text", label: __("Descripcion") },
            ],
            primary_action_label: __("Crear"),
            primary_action: (values) => {
                frappe.call({
                    method: "gestion_contable.gestion_contable.page.creador_de_mapeo_contable.creador_de_mapeo_contable.create_scheme_for_editor",
                    args: values,
                    freeze: true,
                    freeze_message: __("Creando esquema..."),
                    callback: (r) => {
                        const data = r.message || {};
                        this.state.cliente = data.cliente || values.cliente;
                        this.state.esquema_name = data.esquema_name || null;
                        this.state.clients = data.clients || [];
                        this.state.schemes = data.schemes || [];
                        this.state.catalogs = data.catalogs || this.state.catalogs;
                        this.state.scheme = this.decorate_scheme(data.scheme || null);
                        this.ensure_current_rule();
                        this.sync_filter_options();
                        this.render_schemes();
                        this.render_editor();
                        this.last_bootstrap_key = null;
                        dialog.hide();
                        frappe.show_alert({ message: __("Esquema creado correctamente."), indicator: "green" });
                    },
                });
            },
        });
        dialog.show();
    }

    save_current_scheme() {
        const doc = this.get_doc();
        if (!doc?.name) {
            frappe.msgprint(__("Primero crea o selecciona un esquema."));
            return;
        }
        frappe.call({
            method: "gestion_contable.gestion_contable.page.creador_de_mapeo_contable.creador_de_mapeo_contable.save_mapping_scheme_editor",
            args: { esquema_payload: this.build_save_payload(doc) },
            freeze: true,
            freeze_message: __("Guardando esquema de mapeo..."),
            callback: (r) => {
                const data = r.message || {};
                this.state.cliente = data.cliente || this.state.cliente;
                this.state.esquema_name = data.esquema_name || this.state.esquema_name;
                this.state.clients = data.clients || this.state.clients;
                this.state.schemes = data.schemes || this.state.schemes;
                this.state.catalogs = data.catalogs || this.state.catalogs;
                this.state.scheme = this.decorate_scheme(data.scheme || null);
                this.ensure_current_rule();
                this.sync_filter_options();
                this.render_schemes();
                this.render_editor();
                this.last_bootstrap_key = null;
                frappe.show_alert({ message: __("Esquema guardado."), indicator: "green" });
            },
        });
    }

    build_save_payload(doc) {
        return {
            ...doc,
            reglas: this.sort_rules(doc.reglas || []).map((row, index) => {
                const clean = {};
                Object.keys(row || {}).forEach((key) => {
                    if (!String(key).startsWith("__")) clean[key] = row[key];
                });
                clean.orden_ejecucion = this.as_int(clean.orden_ejecucion, index + 1);
                return clean;
            }),
        };
    }

    add_rule() {
        const doc = this.get_doc();
        if (!doc) return;
        const nextOrder = (doc.reglas || []).reduce((max, row) => Math.max(max, this.as_int(row.orden_ejecucion, 0)), 0) + 1;
        doc.reglas = doc.reglas || [];
        doc.reglas.push({
            __editor_id: this.next_rule_id(),
            activo: 1,
            orden_ejecucion: nextOrder,
            destino_tipo: "Cifra Nota",
            origen_version: "Actual",
            selector_tipo: "Lista",
            selector_valor: "",
            filtro_centro_costo: "",
            operacion_agregacion: "Saldo Neto",
            signo_presentacion: "Normal",
            sobrescribir_manual: 0,
            obligatoria: 0,
            comentario: "",
        });
        this.state.current_rule_id = doc.reglas[doc.reglas.length - 1].__editor_id;
        this.render_editor();
    }

    duplicate_current_rule() {
        const doc = this.get_doc();
        const rule = this.get_current_rule();
        if (!doc || !rule) return;
        const clone = {};
        Object.keys(rule).forEach((key) => {
            if (key !== "__editor_id") clone[key] = rule[key];
        });
        clone.__editor_id = this.next_rule_id();
        clone.orden_ejecucion = (doc.reglas || []).reduce((max, row) => Math.max(max, this.as_int(row.orden_ejecucion, 0)), 0) + 1;
        doc.reglas.push(clone);
        this.state.current_rule_id = clone.__editor_id;
        this.render_editor();
    }

    delete_current_rule() {
        const doc = this.get_doc();
        if (!doc || !this.state.current_rule_id) return;
        frappe.confirm(__("Se eliminara la regla seleccionada del esquema en memoria. Guarda el esquema para persistir el cambio."), () => {
            doc.reglas = (doc.reglas || []).filter((row) => row.__editor_id !== this.state.current_rule_id);
            this.ensure_current_rule();
            this.render_editor();
        });
    }

    update_meta_field(event) {
        const doc = this.get_doc();
        if (!doc) return;
        const fieldname = event.currentTarget.dataset.fieldname;
        if (!fieldname) return;
        let value = event.currentTarget.value;
        if (event.currentTarget.type === "checkbox") {
            value = event.currentTarget.checked ? 1 : 0;
        } else if (event.currentTarget.type === "number") {
            value = this.as_int(value, 0);
        }
        doc[fieldname] = value;
    }

    update_rule_field(event) {
        const rule = this.get_current_rule();
        if (!rule) return;
        const fieldname = event.currentTarget.dataset.fieldname;
        if (!fieldname) return;
        let value = event.currentTarget.value;
        if (event.currentTarget.type === "checkbox") {
            value = event.currentTarget.checked ? 1 : 0;
        } else if (event.currentTarget.type === "number") {
            value = this.as_int(value, 0);
        }
        rule[fieldname] = value;

        if (fieldname === "destino_tipo") {
            this.clear_destination_fields(rule);
        }
        if (fieldname === "origen_version" && value !== "Ambas") {
            rule.destino_seccion_id_comparativa = "";
            rule.destino_codigo_fila_comparativa = "";
            rule.destino_codigo_columna_comparativa = "";
        }
        if (fieldname === "selector_tipo" && value === "Todas") {
            rule.selector_valor = "";
        }
        this.render_editor();
    }

    clear_destination_fields(rule) {
        [
            "destino_codigo_sumaria",
            "destino_codigo_linea_sumaria",
            "destino_tipo_estado",
            "destino_codigo_estado",
            "destino_codigo_linea_estado",
            "destino_numero_nota",
            "destino_codigo_cifra",
            "destino_seccion_id",
            "destino_codigo_fila",
            "destino_codigo_columna",
            "destino_seccion_id_comparativa",
            "destino_codigo_fila_comparativa",
            "destino_codigo_columna_comparativa",
        ].forEach((fieldname) => {
            rule[fieldname] = "";
        });
    }

    get_doc() {
        return this.state.scheme?.doc || null;
    }

    get_rules() {
        const doc = this.get_doc();
        if (!doc) return [];
        doc.reglas = this.sort_rules(doc.reglas || []);
        return doc.reglas;
    }

    get_current_rule() {
        return this.get_rules().find((row) => row.__editor_id === this.state.current_rule_id) || null;
    }

    sort_rules(rules) {
        return [...(rules || [])].sort((a, b) => this.as_int(a.orden_ejecucion, 0) - this.as_int(b.orden_ejecucion, 0));
    }

    build_options(options, selectedValue) {
        const rows = ["<option value=''></option>"];
        (options || []).forEach((value) => {
            rows.push(`<option value="${this.escape(value)}" ${value === selectedValue ? "selected" : ""}>${this.escape(value)}</option>`);
        });
        return rows.join("");
    }

    checked(value) {
        return this.truthy(value) ? "checked" : "";
    }

    truthy(value) {
        return this.as_int(value, 0) === 1;
    }

    as_int(value, fallback = 0) {
        const parsed = parseInt(value, 10);
        return Number.isNaN(parsed) ? fallback : parsed;
    }

    view_balanza() {
        if (!this.state.cliente) {
            frappe.msgprint(__("Por favor, selecciona un cliente para ver su balanza."));
            return;
        }

        frappe.call({
            method: "gestion_contable.gestion_contable.page.creador_de_mapeo_contable.creador_de_mapeo_contable.get_balanza_para_mapeo",
            args: {
                cliente: this.state.cliente,
                company: this.get_doc()?.company || null
            },
            freeze: true,
            freeze_message: __("Cargando balanza..."),
            callback: (r) => {
                const balanza = r.message || [];
                if (!balanza.length) {
                    frappe.msgprint(__("No se encontro una version de balanza vigente/publicada para este cliente."));
                    return;
                }

                const dialog = new frappe.ui.Dialog({
                    title: __("Balanza de Comprobacion"),
                    size: 'extra-large',
                    fields: [
                        {
                            fieldname: "filtro",
                            fieldtype: "Data",
                            label: __("Filtrar Cuentas"),
                            placeholder: __("Escribe cuenta o nombre...")
                        },
                        {
                            fieldname: "balanza_html",
                            fieldtype: "HTML",
                        }
                    ],
                });

                const render_html = (filtro) => {
                    const lowered = (filtro || "").toLowerCase();
                    const html = `
                        <div style="max-height: 50vh; overflow-y: auto;">
                            <table class="table table-bordered table-sm cmc-balanza-table">
                                <thead>
                                    <tr>
                                        <th style="width: 25%;">Cuenta</th>
                                        <th>Nombre</th>
                                        <th style="text-align: right; width: 25%;">Saldo Final</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${balanza.filter(r => (r.cuenta || "").toLowerCase().includes(lowered) || (r.nombre || "").toLowerCase().includes(lowered)).map(line => `
                                        <tr>
                                            <td style="font-family: monospace;">${line.cuenta}</td>
                                            <td>${line.nombre}</td>
                                            <td style="text-align: right;">${format_currency(line.saldo)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                    dialog.fields_dict.balanza_html.$wrapper.html(html);
                };

                render_html("");
                dialog.get_field("filtro").$input.on("input", (e) => {
                    render_html(e.target.value);
                });

                dialog.show();
            }
        });
    }

    escape(str) {
        return frappe.utils.escape_html(String(str ?? ""));
    }
}
