frappe.pages["salida-a-produccion"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Salida a Produccion",
        single_column: true,
    });

    frappe.pages["salida-a-produccion"].dashboard = new SalidaProduccion(page);
    frappe.pages["salida-a-produccion"].dashboard.init();
};

frappe.pages["salida-a-produccion"].on_page_show = function () {
    const dashboard = frappe.pages["salida-a-produccion"].dashboard;
    if (dashboard) {
        dashboard.load_data();
    }
};

class SalidaProduccion {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
    }

    init() {
        this.setup_styles();
        this.page.set_primary_action("Actualizar", () => this.load_data(), "refresh");
        this.render_shell();
        this.load_data();
    }

    setup_styles() {
        if (document.getElementById("gc-release-styles")) return;
        const style = document.createElement("style");
        style.id = "gc-release-styles";
        style.textContent = `
            .gc-release-shell { padding: 18px; border: 1px solid #dbe3ef; border-radius: 16px; background: linear-gradient(160deg, #f8fafc 0%, #eef6ff 45%, #fffaf0 100%); }
            .gc-release-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:16px; }
            .gc-release-kpi, .gc-release-box { background:#fff; border:1px solid #dbe3ef; border-radius:14px; box-shadow:0 10px 24px rgba(15,23,42,.04); }
            .gc-release-kpi { padding:14px; }
            .gc-release-value { font-size:26px; font-weight:800; color:#0f172a; display:block; }
            .gc-release-label { display:block; margin-top:6px; font-size:11px; text-transform:uppercase; font-weight:700; color:#64748b; }
            .gc-release-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-bottom:16px; }
            .gc-release-box { padding:16px; }
            .gc-release-box h3 { margin:0 0 12px; font-size:16px; font-weight:800; color:#0f172a; }
            .gc-release-group { margin-bottom:14px; padding:14px; border:1px solid #e2e8f0; border-radius:12px; background:#f8fafc; }
            .gc-release-group h4 { margin:0 0 8px; font-size:14px; font-weight:800; }
            .gc-release-item { display:flex; justify-content:space-between; gap:12px; padding:8px 0; border-top:1px solid #e2e8f0; font-size:12px; }
            .gc-release-item:first-child { border-top:0; padding-top:0; }
            .gc-release-badge { padding:4px 10px; border-radius:999px; font-size:11px; font-weight:800; text-transform:uppercase; }
            .gc-release-badge.pass { background:#dcfce7; color:#166534; }
            .gc-release-badge.warn { background:#fff7ed; color:#c2410c; }
            .gc-release-badge.fail { background:#fef2f2; color:#b91c1c; }
            .gc-release-check { margin-bottom:14px; padding:14px; border:1px solid #e2e8f0; border-radius:12px; background:#fff; }
            .gc-release-check h4 { margin:0 0 8px; font-size:14px; font-weight:800; }
            .gc-release-check label { display:flex; gap:10px; align-items:flex-start; }
            .gc-release-check input { margin-top:3px; }
            .gc-release-check strong { display:block; margin-bottom:4px; color:#0f172a; }
            .gc-release-check p { margin:0; color:#475569; font-size:12px; }
            .gc-release-list { margin:0; padding-left:18px; color:#334155; font-size:12px; }
            .gc-release-empty, .gc-release-loading { padding:28px; text-align:center; color:#64748b; }
            @media (max-width: 980px) { .gc-release-kpis, .gc-release-grid { grid-template-columns:1fr; } }
        `;
        document.head.appendChild(style);
    }

    render_shell() {
        this.wrapper.html(`
            <div class="gc-release-shell">
                <div class="gc-release-kpis" data-role="summary"></div>
                <div class="gc-release-grid">
                    <div class="gc-release-box"><h3>Revision de Migraciones</h3><div data-role="groups"></div></div>
                    <div class="gc-release-box"><h3>Comandos Base</h3><div data-role="commands"></div><h3 style="margin-top:16px;">Notas</h3><div data-role="notes"></div></div>
                </div>
                <div class="gc-release-box"><h3>Checklist UAT</h3><div data-role="uat"></div></div>
            </div>
        `);
    }

    load_data() {
        this.wrapper.find('[data-role="groups"]').html('<div class="gc-release-loading">Cargando revision...</div>');
        frappe.call({
            method: "gestion_contable.gestion_contable.page.salida_a_produccion.salida_a_produccion.get_release_readiness",
            callback: (r) => this.render(r.message || {}),
        });
    }

    render(data) {
        this.render_summary(data.summary || {});
        this.render_groups(data.groups || []);
        this.render_commands(data.commands || []);
        this.render_notes(data.notes || []);
        this.render_uat(data.uat_sections || []);
    }

    render_summary(summary) {
        const cards = [
            ["Checks", summary.total || 0],
            ["OK", summary.pass || 0],
            ["Warnings", summary.warn || 0],
            ["Fails", summary.fail || 0],
        ];
        this.wrapper.find('[data-role="summary"]').html(cards.map(([label, value]) => `
            <div class="gc-release-kpi">
                <span class="gc-release-value">${value}</span>
                <span class="gc-release-label">${label}</span>
            </div>
        `).join(""));
    }

    render_groups(groups) {
        if (!groups.length) {
            this.wrapper.find('[data-role="groups"]').html('<div class="gc-release-empty">Sin checks.</div>');
            return;
        }
        const html = groups.map((group) => `
            <div class="gc-release-group">
                <h4>${frappe.utils.escape_html(group.title || "Grupo")}</h4>
                ${group.items.map((item) => `
                    <div class="gc-release-item">
                        <div>
                            <strong>${frappe.utils.escape_html(item.kind || "Check")}: ${frappe.utils.escape_html(item.name || "")}</strong><br>
                            <span>${frappe.utils.escape_html(item.message || "")}</span>
                        </div>
                        <span class="gc-release-badge ${item.status}">${item.status}</span>
                    </div>
                `).join("")}
            </div>
        `).join("");
        this.wrapper.find('[data-role="groups"]').html(html);
    }

    render_commands(commands) {
        this.wrapper.find('[data-role="commands"]').html(`<ol class="gc-release-list">${commands.map((item) => `<li><code>${frappe.utils.escape_html(item)}</code></li>`).join("")}</ol>`);
    }

    render_notes(notes) {
        this.wrapper.find('[data-role="notes"]').html(`<ul class="gc-release-list">${notes.map((item) => `<li>${frappe.utils.escape_html(item)}</li>`).join("")}</ul>`);
    }

    render_uat(sections) {
        if (!sections.length) {
            this.wrapper.find('[data-role="uat"]').html('<div class="gc-release-empty">Sin checklist UAT.</div>');
            return;
        }
        const html = sections.map((section) => `
            <div class="gc-release-group">
                <h4>${frappe.utils.escape_html(section.title || "Seccion")}</h4>
                ${(section.items || []).map((item) => `
                    <div class="gc-release-check">
                        <label>
                            <input type="checkbox" data-uat-id="${frappe.utils.escape_html(item.id || "")}">
                            <span>
                                <strong>${frappe.utils.escape_html(item.title || "Caso")}</strong>
                                <p><b>Pasos:</b> ${frappe.utils.escape_html(item.steps || "")}</p>
                                <p><b>Resultado esperado:</b> ${frappe.utils.escape_html(item.expected || "")}</p>
                            </span>
                        </label>
                    </div>
                `).join("")}
            </div>
        `).join("");
        this.wrapper.find('[data-role="uat"]').html(html);
    }
}
