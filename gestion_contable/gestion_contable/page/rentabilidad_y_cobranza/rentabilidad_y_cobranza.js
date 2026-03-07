frappe.pages["rentabilidad-y-cobranza"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Rentabilidad y Cobranza",
        single_column: true,
    });

    frappe.pages["rentabilidad-y-cobranza"].dashboard = new RentabilidadCobranza(page);
    frappe.pages["rentabilidad-y-cobranza"].dashboard.init();
};

frappe.pages["rentabilidad-y-cobranza"].on_page_show = function () {
    const dashboard = frappe.pages["rentabilidad-y-cobranza"].dashboard;
    if (dashboard) {
        dashboard.apply_route_options();
        dashboard.load_data();
    }
};

class RentabilidadCobranza {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
        this.searchTimer = null;
    }

    init() {
        this.setup_styles();
        this.render_shell();
        this.bind_events();
        this.load_filters();
        this.setup_actions();
    }

    setup_actions() {
        this.page.set_primary_action(__("Actualizar"), () => this.load_data());
    }

    setup_styles() {
        if (document.getElementById("rc-styles")) return;
        const style = document.createElement("style");
        style.id = "rc-styles";
        style.textContent = `
            .rc-shell { padding: 18px; border: 1px solid #dbe3ef; border-radius: 16px; background: linear-gradient(160deg, #f8fafc 0%, #eefaf5 45%, #fffaf2 100%); }
            .rc-hero { display:flex; justify-content:space-between; gap:16px; margin-bottom:16px; padding:18px; border-radius:14px; background:#fff; border:1px solid #dbe3ef; box-shadow:0 10px 24px rgba(15,23,42,.05); }
            .rc-hero h2 { margin:0; font-size:26px; font-weight:800; color:#0f172a; }
            .rc-hero p { margin:6px 0 0; color:#475569; font-size:13px; }
            .rc-kpis { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:12px; margin-bottom:16px; }
            .rc-kpi, .rc-box, .rc-card { background:#fff; border:1px solid #dbe3ef; border-radius:14px; box-shadow:0 8px 22px rgba(15,23,42,.04); }
            .rc-kpi { padding:14px; }
            .rc-kpi-value { font-size:24px; font-weight:800; color:#0f172a; display:block; }
            .rc-kpi-label { margin-top:6px; display:block; font-size:11px; text-transform:uppercase; font-weight:700; color:#64748b; }
            .rc-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-bottom:16px; }
            .rc-box { padding:14px; }
            .rc-box h3 { margin:0 0 10px; font-size:15px; font-weight:800; color:#0f172a; }
            .rc-table { width:100%; font-size:12px; }
            .rc-table th { text-align:left; color:#64748b; padding:0 0 6px; font-size:11px; text-transform:uppercase; }
            .rc-table td { padding:8px 0; border-top:1px solid #eef2f7; color:#1e293b; }
            .rc-list { display:flex; flex-direction:column; gap:12px; }
            .rc-card-head { display:flex; justify-content:space-between; gap:12px; padding:16px 18px 10px; }
            .rc-title { margin:0; font-size:18px; font-weight:800; color:#0f172a; cursor:pointer; }
            .rc-subtitle { margin:4px 0 0; font-size:12px; color:#64748b; }
            .rc-badges, .rc-alerts { display:flex; flex-wrap:wrap; gap:8px; }
            .rc-badge, .rc-alert { padding:6px 10px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid transparent; }
            .rc-badge.estado-cerrado, .rc-badge.estado-cancelado { background:#f8fafc; color:#334155; border-color:#cbd5e1; }
            .rc-badge.estado-en-ejecucion, .rc-badge.estado-planificado { background:#eff6ff; color:#1d4ed8; border-color:#93c5fd; }
            .rc-badge.estado-en-revision { background:#fff7ed; color:#c2410c; border-color:#fdba74; }
            .rc-badge.aprobacion-aprobado { background:#dcfce7; color:#166534; border-color:#86efac; }
            .rc-badge.aprobacion-revision-supervisor, .rc-badge.aprobacion-revision-socio { background:#eff6ff; color:#1d4ed8; border-color:#93c5fd; }
            .rc-badge.aprobacion-devuelto { background:#fef2f2; color:#b91c1c; border-color:#fca5a5; }
            .rc-alert { background:#fef2f2; color:#991b1b; border-color:#fecaca; }
            .rc-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; padding:0 18px 14px; }
            .rc-metric { padding:12px; border:1px solid #e2e8f0; border-radius:12px; background:#f8fafc; }
            .rc-metric-value { display:block; font-size:20px; font-weight:800; color:#0f172a; }
            .rc-metric-label { display:block; margin-top:5px; font-size:11px; text-transform:uppercase; font-weight:700; color:#64748b; }
            .rc-meta { display:flex; justify-content:space-between; gap:12px; padding:0 18px 16px; color:#475569; font-size:12px; }
            .rc-empty, .rc-loading { padding:32px 20px; text-align:center; color:#64748b; }
            @media (max-width: 1100px) { .rc-kpis, .rc-metrics, .rc-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
            @media (max-width: 720px) { .rc-hero, .rc-card-head, .rc-meta { flex-direction:column; } .rc-kpis, .rc-metrics, .rc-grid { grid-template-columns:1fr; } }
        `;
        document.head.appendChild(style);
    }

    render_shell() {
        this.wrapper.html(`
            <div class="rc-shell">
                <div class="rc-hero">
                    <div>
                        <h2>Rentabilidad operativa</h2>
                        <p>Vista consolidada de margen, WIP, facturacion, aging y seguimiento de cobranza por encargo, cliente y servicio.</p>
                    </div>
                </div>
                <div class="rc-kpis" data-role="summary"></div>
                <div class="rc-grid">
                    <div class="rc-box"><h3>Por Cliente</h3><div data-role="clients"></div></div>
                    <div class="rc-box"><h3>Por Servicio</h3><div data-role="services"></div></div>
                </div>
                <div class="rc-list" data-role="rows"></div>
            </div>
        `);

        this.fields = {
            cliente: this.page.add_field({ fieldtype: "Select", label: __("Cliente"), fieldname: "cliente", options: "" }),
            servicio_contable: this.page.add_field({ fieldtype: "Select", label: __("Servicio"), fieldname: "servicio_contable", options: "" }),
            estado: this.page.add_field({ fieldtype: "Select", label: __("Estado"), fieldname: "estado", options: "\nPlanificado\nEn Ejecucion\nEn Revision\nCerrado\nCancelado" }),
            tipo_de_servicio: this.page.add_field({ fieldtype: "Select", label: __("Tipo"), fieldname: "tipo_de_servicio", options: "\nContabilidad\nAuditoria\nTrabajo Especial\nConsultoria" }),
            solo_vencidos: this.page.add_field({ fieldtype: "Check", label: __("Solo Vencidos"), fieldname: "solo_vencidos" }),
            search: this.page.add_field({ fieldtype: "Data", label: __("Buscar"), fieldname: "search" }),
        };
    }

    bind_events() {
        Object.keys(this.fields).forEach((key) => {
            const field = this.fields[key];
            if (!field) return;
            const handler = key === "search"
                ? () => {
                    clearTimeout(this.searchTimer);
                    this.searchTimer = setTimeout(() => this.load_data(), 250);
                }
                : () => this.load_data();
            field.$input && field.$input.on("change input", handler);
        });
    }

    apply_route_options() {
        const options = frappe.route_options || {};
        Object.keys(this.fields).forEach((key) => {
            if (options[key] !== undefined) this.fields[key].set_value(options[key]);
        });
        frappe.route_options = null;
    }

    load_filters() {
        frappe.call({
            method: "gestion_contable.gestion_contable.page.rentabilidad_y_cobranza.rentabilidad_y_cobranza.get_filters_data",
            callback: (r) => {
                const data = r.message || {};
                this.set_select_options(this.fields.cliente, data.clientes || []);
                this.set_select_options(this.fields.servicio_contable, data.servicios || []);
                this.load_data();
            },
        });
    }

    set_select_options(field, rows) {
        const seen = new Set();
        const options = [""];
        rows.forEach((row) => {
            if (!row.value || seen.has(row.value)) return;
            seen.add(row.value);
            options.push(row.value);
        });
        field.df.options = options.join("\n");
        field.refresh();
    }

    get_filters() {
        return {
            cliente: this.fields.cliente.get_value(),
            servicio_contable: this.fields.servicio_contable.get_value(),
            estado: this.fields.estado.get_value(),
            tipo_de_servicio: this.fields.tipo_de_servicio.get_value(),
            solo_vencidos: this.fields.solo_vencidos.get_value() ? 1 : 0,
            search: this.fields.search.get_value(),
        };
    }

    load_data() {
        this.wrapper.find('[data-role="rows"]').html('<div class="rc-loading">Cargando datos...</div>');
        frappe.call({
            method: "gestion_contable.gestion_contable.page.rentabilidad_y_cobranza.rentabilidad_y_cobranza.get_dashboard",
            args: this.get_filters(),
            callback: (r) => {
                const data = r.message || {};
                this.render_summary(data.summary || {});
                this.render_aggregate(this.wrapper.find('[data-role="clients"]'), data.by_cliente || []);
                this.render_aggregate(this.wrapper.find('[data-role="services"]'), data.by_servicio || []);
                this.render_rows(data.rows || []);
            },
        });
    }

    render_summary(summary) {
        const cards = [
            ["Encargos", summary.encargos || 0, false],
            ["Facturado", summary.ingreso_facturado || 0, true],
            ["Cobrado", summary.cobrado_total || 0, true],
            ["Saldo", summary.saldo_por_cobrar || 0, true],
            ["WIP", summary.wip_monto || 0, true],
            ["Margen Facturado", summary.margen_facturado || 0, true],
        ];
        const html = cards.map(([label, value, money]) => `
            <div class="rc-kpi">
                <span class="rc-kpi-value">${money ? this.money(value) : frappe.format(value, { fieldtype: 'Int' })}</span>
                <span class="rc-kpi-label">${label}</span>
            </div>
        `).join("");
        this.wrapper.find('[data-role="summary"]').html(html);
    }

    render_aggregate(target, rows) {
        if (!rows.length) {
            target.html('<div class="rc-empty">Sin datos</div>');
            return;
        }
        const html = `
            <table class="rc-table">
                <thead><tr><th>Nombre</th><th>Facturado</th><th>Saldo</th><th>Margen</th></tr></thead>
                <tbody>
                    ${rows.map((row) => `
                        <tr>
                            <td>${frappe.utils.escape_html(row.label || row.key)}</td>
                            <td>${this.money(row.ingreso_facturado)}</td>
                            <td>${this.money(row.saldo_por_cobrar)}</td>
                            <td>${this.money(row.margen_facturado)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
        target.html(html);
    }

    render_rows(rows) {
        const target = this.wrapper.find('[data-role="rows"]');
        if (!rows.length) {
            target.html('<div class="rc-empty">No hay encargos con los filtros seleccionados.</div>');
            return;
        }
        const html = rows.map((row) => `
            <div class="rc-card">
                <div class="rc-card-head">
                    <div>
                        <h3 class="rc-title" data-name="${row.name}">${frappe.utils.escape_html(row.name)}</h3>
                        <div class="rc-subtitle">${frappe.utils.escape_html(row.cliente_label || "")} · ${frappe.utils.escape_html(row.servicio_contable || "")} · ${frappe.utils.escape_html(row.tipo_de_servicio || "")}</div>
                    </div>
                    <div class="rc-badges">
                        <span class="rc-badge estado-${frappe.scrub(row.estado || '').replace(/_/g, '-')}">${frappe.utils.escape_html(row.estado || "")}</span>
                        <span class="rc-badge aprobacion-${frappe.scrub(row.estado_aprobacion || '').replace(/_/g, '-')}">${frappe.utils.escape_html(row.estado_aprobacion || "")}</span>
                    </div>
                </div>
                <div class="rc-metrics">
                    ${this.metric("Horas", frappe.format(row.horas_registradas, { fieldtype: 'Float' }))}
                    ${this.metric("Costo", this.money(row.costo_interno_total))}
                    ${this.metric("Facturado", this.money(row.ingreso_facturado))}
                    ${this.metric("Cobrado", this.money(row.cobrado_total))}
                    ${this.metric("Saldo", this.money(row.saldo_por_cobrar))}
                    ${this.metric("WIP", this.money(row.wip_monto))}
                    ${this.metric("Margen Facturado", this.money(row.margen_facturado))}
                    ${this.metric("Cartera Vencida", this.money(row.cartera_vencida))}
                </div>
                ${row.alertas && row.alertas.length ? `<div class="rc-alerts" style="padding:0 18px 12px;">${row.alertas.map((alert) => `<span class="rc-alert">${frappe.utils.escape_html(alert)}</span>`).join("")}</div>` : ''}
                <div class="rc-meta">
                    <div>Aging: Corriente ${this.money(row.aging_current)} · 0-30 ${this.money(row.aging_0_30)} · 31-60 ${this.money(row.aging_31_60)} · 61-90 ${this.money(row.aging_61_90)} · 91+ ${this.money(row.aging_91_plus)}</div>
                    <div>Responsable: ${frappe.utils.escape_html(row.responsable || "-")} · Ultima gestion: ${row.ultima_gestion_cobranza || '-'} · Proxima: ${row.proxima_gestion_cobranza || '-'}</div>
                </div>
            </div>
        `).join("");
        target.html(html);
        target.find('.rc-title').on('click', (event) => frappe.set_route('Form', 'Encargo Contable', event.currentTarget.dataset.name));
    }

    metric(label, value) {
        return `<div class="rc-metric"><span class="rc-metric-value">${value}</span><span class="rc-metric-label">${label}</span></div>`;
    }

    money(value) {
        return format_currency(value || 0, frappe.defaults.get_default("currency"));
    }
}