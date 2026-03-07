frappe.pages["seguimiento-de-auditoria"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Seguimiento de Auditoria",
        single_column: true,
    });

    frappe.pages["seguimiento-de-auditoria"].dashboard = new SeguimientoAuditoria(page);
    frappe.pages["seguimiento-de-auditoria"].dashboard.init();
};

frappe.pages["seguimiento-de-auditoria"].on_page_show = function () {
    const dashboard = frappe.pages["seguimiento-de-auditoria"].dashboard;
    if (dashboard) {
        dashboard.apply_route_options();
        dashboard.load_data();
    }
};

class SeguimientoAuditoria {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
        this.rows = [];
        this.searchTimer = null;
    }

    init() {
        this.setup_styles();
        this.setup_actions();
        this.render_shell();
        this.bind_events();
        this.load_clients();
    }

    setup_styles() {
        if (document.getElementById("sa-styles")) return;

        const style = document.createElement("style");
        style.id = "sa-styles";
        style.textContent = `
            .sa-shell {
                padding: 18px;
                border: 1px solid #d9e2ec;
                border-radius: 16px;
                background:
                    radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 28%),
                    radial-gradient(circle at right, rgba(245, 158, 11, 0.10), transparent 24%),
                    linear-gradient(160deg, #f8fafc 0%, #eef6ff 45%, #fffaf0 100%);
            }

            .sa-hero {
                display: flex;
                justify-content: space-between;
                gap: 18px;
                align-items: flex-start;
                margin-bottom: 16px;
                padding: 18px;
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.25);
                background: rgba(255, 255, 255, 0.82);
                box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
            }

            .sa-hero h2 {
                margin: 0;
                font-size: 26px;
                font-weight: 800;
                color: #0f172a;
                letter-spacing: 0.2px;
            }

            .sa-hero p {
                margin: 6px 0 0;
                font-size: 13px;
                color: #475569;
                max-width: 720px;
            }

            .sa-kpis {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
                margin-bottom: 16px;
            }

            .sa-kpi {
                background: #fff;
                border: 1px solid #dbe3ef;
                border-radius: 14px;
                padding: 14px;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
            }

            .sa-kpi-value {
                display: block;
                font-size: 28px;
                line-height: 1;
                font-weight: 800;
                color: #0f172a;
            }

            .sa-kpi-label {
                display: block;
                margin-top: 6px;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.6px;
                font-weight: 700;
                color: #64748b;
            }

            .sa-kpi-note {
                display: block;
                margin-top: 4px;
                font-size: 12px;
                color: #475569;
            }

            .sa-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .sa-card {
                border: 1px solid #dbe3ef;
                border-radius: 16px;
                background: rgba(255, 255, 255, 0.92);
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
                overflow: hidden;
            }

            .sa-card-head {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                align-items: flex-start;
                padding: 16px 18px 10px;
            }

            .sa-card-title {
                margin: 0;
                font-size: 18px;
                font-weight: 800;
                color: #0f172a;
                cursor: pointer;
            }

            .sa-card-subtitle {
                margin: 4px 0 0;
                font-size: 12px;
                color: #64748b;
            }

            .sa-badges {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                justify-content: flex-end;
            }

            .sa-badge {
                padding: 6px 10px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.4px;
                text-transform: uppercase;
                border: 1px solid transparent;
            }

            .sa-badge.estado-planeacion { background: #fff7ed; color: #9a3412; border-color: #fdba74; }
            .sa-badge.estado-ejecucion { background: #eff6ff; color: #1d4ed8; border-color: #93c5fd; }
            .sa-badge.estado-revision-tecnica { background: #faf5ff; color: #7e22ce; border-color: #d8b4fe; }
            .sa-badge.estado-cerrada { background: #ecfdf5; color: #047857; border-color: #86efac; }
            .sa-badge.estado-archivada, .sa-badge.estado-cancelada { background: #f8fafc; color: #334155; border-color: #cbd5e1; }
            .sa-badge.aprobacion-aprobado { background: #dcfce7; color: #166534; border-color: #86efac; }
            .sa-badge.aprobacion-devuelto { background: #fef2f2; color: #b91c1c; border-color: #fca5a5; }
            .sa-badge.aprobacion-revision-supervisor, .sa-badge.aprobacion-revision-socio { background: #eff6ff; color: #1d4ed8; border-color: #93c5fd; }
            .sa-badge.tecnica-aprobado { background: #dcfce7; color: #166534; border-color: #86efac; }
            .sa-badge.tecnica-observado { background: #fff7ed; color: #c2410c; border-color: #fdba74; }
            .sa-badge.alerta { background: #fef2f2; color: #b91c1c; border-color: #fca5a5; }

            .sa-metrics {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 10px;
                padding: 0 18px 14px;
            }

            .sa-metric {
                border: 1px solid #e2e8f0;
                background: #f8fafc;
                border-radius: 12px;
                padding: 12px;
            }

            .sa-metric-value {
                display: block;
                font-size: 24px;
                font-weight: 800;
                line-height: 1;
                color: #0f172a;
            }

            .sa-metric-label {
                display: block;
                margin-top: 5px;
                font-size: 11px;
                text-transform: uppercase;
                font-weight: 700;
                letter-spacing: 0.5px;
                color: #64748b;
            }

            .sa-meta {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                align-items: center;
                padding: 0 18px 16px;
                color: #475569;
                font-size: 12px;
            }

            .sa-alerts {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                padding: 0 18px 16px;
            }

            .sa-alert-chip {
                padding: 6px 10px;
                border-radius: 999px;
                background: #fef2f2;
                color: #991b1b;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid #fecaca;
            }

            .sa-empty {
                padding: 42px 24px;
                text-align: center;
                border: 1px dashed #cbd5e1;
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.74);
                color: #64748b;
            }

            .sa-loading {
                padding: 36px 24px;
                text-align: center;
                color: #64748b;
                font-weight: 700;
            }

            @media (max-width: 1100px) {
                .sa-kpis,
                .sa-metrics {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }

            @media (max-width: 768px) {
                .sa-hero,
                .sa-card-head,
                .sa-meta {
                    flex-direction: column;
                    align-items: stretch;
                }

                .sa-kpis,
                .sa-metrics {
                    grid-template-columns: 1fr;
                }

                .sa-badges {
                    justify-content: flex-start;
                }
            }
        `;
        document.head.appendChild(style);
    }

    setup_actions() {
        this.page.set_primary_action("Actualizar", () => this.load_data(), "refresh");
    }

    render_shell() {
        this.clienteField = this.page.add_field({
            label: "Cliente",
            fieldname: "cliente",
            fieldtype: "Select",
            options: "\n",
            change: () => this.load_data(),
        });

        this.estadoField = this.page.add_field({
            label: "Estado",
            fieldname: "estado",
            fieldtype: "Select",
            options: "\nPlaneacion\nEjecucion\nRevision Tecnica\nCerrada\nArchivada\nCancelada",
            change: () => this.load_data(),
        });

        this.searchField = this.page.add_field({
            label: "Buscar",
            fieldname: "search",
            fieldtype: "Data",
            placeholder: "Expediente, cliente, periodo...",
        });

        this.wrapper.html(`
            <div class="sa-shell">
                <div class="sa-hero">
                    <div>
                        <h2>Seguimiento de Auditoria</h2>
                        <p>Vista operativa del avance de expedientes, papeles de trabajo, revision tecnica y hallazgos. Filtra por cliente para revisar la situacion completa de una auditoria.</p>
                    </div>
                </div>
                <div class="sa-kpis" data-kpis></div>
                <div class="sa-list" data-list></div>
            </div>
        `);
    }

    bind_events() {
        const input = this.searchField && (this.searchField.$input || this.searchField.input);
        if (input) {
            input.on("input", () => {
                clearTimeout(this.searchTimer);
                this.searchTimer = setTimeout(() => this.load_data(), 220);
            });
        }
    }

    apply_route_options() {
        if (!frappe.route_options) return;
        const ro = frappe.route_options;
        if (ro.cliente && this.clienteField) {
            this.clienteField.set_value(ro.cliente);
        }
        if (ro.estado && this.estadoField) {
            this.estadoField.set_value(ro.estado);
        }
        frappe.route_options = null;
    }

    load_clients() {
        frappe.call({
            method: "gestion_contable.gestion_contable.page.seguimiento_de_auditoria.seguimiento_de_auditoria.get_audit_clients",
            callback: (r) => {
                if (r.exc || !r.message || !this.clienteField) return;
                const options = [""];
                (r.message || []).forEach((item) => {
                    options.push(item.value);
                });
                this.clienteField.df.options = options.join("\n");
                this.clienteField.refresh();
            },
        });
    }

    get_filters() {
        return {
            cliente: this.clienteField ? this.clienteField.get_value() : "",
            estado: this.estadoField ? this.estadoField.get_value() : "",
            search: this.searchField ? this.searchField.get_value() : "",
        };
    }

    load_data() {
        this.render_loading();
        frappe.call({
            method: "gestion_contable.gestion_contable.page.seguimiento_de_auditoria.seguimiento_de_auditoria.get_audit_dashboard",
            args: this.get_filters(),
            callback: (r) => {
                if (r.exc) {
                    this.render_error();
                    return;
                }
                const message = r.message || { summary: {}, rows: [] };
                this.rows = message.rows || [];
                this.render_summary(message.summary || {});
                this.render_rows(this.rows);
            },
        });
    }

    render_loading() {
        this.wrapper.find("[data-kpis]").html(this.build_loading_kpis());
        this.wrapper.find("[data-list]").html('<div class="sa-loading">Cargando seguimiento de auditoria...</div>');
    }

    render_error() {
        this.wrapper.find("[data-list]").html('<div class="sa-empty">No fue posible cargar la informacion de auditoria.</div>');
    }

    render_summary(summary) {
        const kpis = [
            { value: summary.total || 0, label: "Expedientes", note: `${summary.planeacion || 0} en planeacion / ${summary.ejecucion || 0} en ejecucion` },
            { value: summary.revision_tecnica || 0, label: "Revision Tecnica", note: `${summary.papeles_pendientes || 0} papeles pendientes` },
            { value: summary.hallazgos_abiertos || 0, label: "Hallazgos Abiertos", note: `${summary.riesgos_altos || 0} riesgos altos` },
            { value: summary.vencidos || 0, label: "Vencidos", note: `${summary.cerrados || 0} expedientes cerrados` },
        ];

        const html = kpis.map((item) => `
            <div class="sa-kpi">
                <span class="sa-kpi-value">${item.value}</span>
                <span class="sa-kpi-label">${frappe.utils.escape_html(item.label)}</span>
                <span class="sa-kpi-note">${frappe.utils.escape_html(item.note)}</span>
            </div>
        `).join("");

        this.wrapper.find("[data-kpis]").html(html);
    }

    render_rows(rows) {
        if (!rows.length) {
            this.wrapper.find("[data-list]").html('<div class="sa-empty">No hay expedientes de auditoria con los filtros seleccionados.</div>');
            return;
        }

        const html = rows.map((row) => this.build_card(row)).join("");
        const list = this.wrapper.find("[data-list]");
        list.html(html);

        list.find("[data-open-expediente]").on("click", (e) => {
            const name = $(e.currentTarget).data("open-expediente");
            frappe.set_route("Form", "Expediente Auditoria", name);
        });
    }

    build_card(row) {
        const estadoClass = this.slug(row.estado_expediente);
        const aprobacionClass = this.slug(row.estado_aprobacion);
        const tecnicaClass = this.slug(row.resultado_revision_tecnica || "Pendiente");
        const badges = [
            `<span class="sa-badge estado-${estadoClass}">${frappe.utils.escape_html(row.estado_expediente || "Sin Estado")}</span>`,
            `<span class="sa-badge aprobacion-${aprobacionClass}">${frappe.utils.escape_html(row.estado_aprobacion || "Sin Aprobacion")}</span>`,
        ];

        if (row.resultado_revision_tecnica && row.resultado_revision_tecnica !== "Pendiente") {
            badges.push(`<span class="sa-badge tecnica-${tecnicaClass}">${frappe.utils.escape_html(row.resultado_revision_tecnica)}</span>`);
        }
        if (row.overdue) {
            badges.push('<span class="sa-badge alerta">Vencido</span>');
        }

        const alerts = (row.alertas || []).map((alerta) => `<span class="sa-alert-chip">${frappe.utils.escape_html(alerta)}</span>`).join("");

        return `
            <div class="sa-card">
                <div class="sa-card-head">
                    <div>
                        <h3 class="sa-card-title" data-open-expediente="${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(row.name)}</h3>
                        <p class="sa-card-subtitle">${frappe.utils.escape_html(row.cliente_label || row.cliente || "Sin cliente")} | Periodo ${frappe.utils.escape_html(row.periodo || "N/D")} | Encargo ${frappe.utils.escape_html(row.encargo_contable || "N/D")}</p>
                    </div>
                    <div class="sa-badges">${badges.join("")}</div>
                </div>
                <div class="sa-metrics">
                    <div class="sa-metric">
                        <span class="sa-metric-value">${row.riesgos_altos}/${row.total_riesgos}</span>
                        <span class="sa-metric-label">Riesgos altos / total</span>
                    </div>
                    <div class="sa-metric">
                        <span class="sa-metric-value">${row.papeles_aprobados}/${row.total_papeles}</span>
                        <span class="sa-metric-label">Papeles aprobados / total</span>
                    </div>
                    <div class="sa-metric">
                        <span class="sa-metric-value">${row.papeles_pendientes_revision}</span>
                        <span class="sa-metric-label">Papeles pendientes</span>
                    </div>
                    <div class="sa-metric">
                        <span class="sa-metric-value">${row.hallazgos_abiertos}/${row.total_hallazgos}</span>
                        <span class="sa-metric-label">Hallazgos abiertos / total</span>
                    </div>
                </div>
                ${alerts ? `<div class="sa-alerts">${alerts}</div>` : ""}
                <div class="sa-meta">
                    <div>
                        <strong>Supervisor:</strong> ${frappe.utils.escape_html(row.supervisor_a_cargo || "N/D")}<br>
                        <strong>Socio:</strong> ${frappe.utils.escape_html(row.socio_a_cargo || "N/D")}
                    </div>
                    <div>
                        <strong>Inicio:</strong> ${this.format_date(row.fecha_inicio_planeada)}<br>
                        <strong>Fin:</strong> ${this.format_date(row.fecha_fin_planeada)}
                    </div>
                    <div>
                        <strong>Envio revision:</strong> ${this.format_datetime(row.fecha_envio_revision_tecnica)}
                    </div>
                </div>
            </div>
        `;
    }

    build_loading_kpis() {
        return [1, 2, 3, 4].map(() => `
            <div class="sa-kpi">
                <span class="sa-kpi-value">...</span>
                <span class="sa-kpi-label">Cargando</span>
                <span class="sa-kpi-note">Procesando datos</span>
            </div>
        `).join("");
    }

    slug(value) {
        return (value || "sin-estado")
            .toString()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "");
    }

    format_date(value) {
        return value ? frappe.datetime.str_to_user(value) : "N/D";
    }

    format_datetime(value) {
        return value ? frappe.datetime.str_to_user(value) : "N/D";
    }
}
