frappe.pages["panel-de-tareas"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Panel de Tareas",
        single_column: true,
    });

    page.main.html(`
		<div class="panel-tareas-container">
			<div class="filters-row"></div>
			<div class="stats-row"></div>
			<div class="kanban-board"></div>
		</div>
	`);

    const panelTareas = new PanelDeTareas(page);
    panelTareas.init();
};

class PanelDeTareas {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
        this.filters = {};
        this.statuses = ["Pendiente", "En Proceso", "En Revisión", "Completada"];
        this.status_colors = {
            Pendiente: { bg: "#fff3e0", border: "#ff9800", text: "#e65100", badge: "#ff9800" },
            "En Proceso": { bg: "#e3f2fd", border: "#2196f3", text: "#0d47a1", badge: "#2196f3" },
            "En Revisión": { bg: "#f3e5f5", border: "#9c27b0", text: "#4a148c", badge: "#9c27b0" },
            Completada: { bg: "#e8f5e9", border: "#4caf50", text: "#1b5e20", badge: "#4caf50" },
        };
    }

    init() {
        this.setup_styles();
        this.setup_filters();
        this.load_data();
    }

    setup_styles() {
        if (document.getElementById("panel-tareas-styles")) return;

        const style = document.createElement("style");
        style.id = "panel-tareas-styles";
        style.textContent = `
			.panel-tareas-container {
				padding: 15px;
				max-width: 100%;
			}

			.filters-row {
				display: flex;
				gap: 12px;
				margin-bottom: 20px;
				flex-wrap: wrap;
				align-items: flex-end;
			}

			.filter-group {
				display: flex;
				flex-direction: column;
				gap: 4px;
			}

			.filter-group label {
				font-size: 11px;
				font-weight: 600;
				color: var(--text-muted);
				text-transform: uppercase;
				letter-spacing: 0.5px;
			}

			.filter-group select,
			.filter-group input {
				padding: 6px 10px;
				border: 1px solid var(--border-color);
				border-radius: 6px;
				font-size: 13px;
				min-width: 160px;
				background: var(--control-bg);
				color: var(--text-color);
			}

			.stats-row {
				display: flex;
				gap: 12px;
				margin-bottom: 20px;
				flex-wrap: wrap;
			}

			.stat-card {
				flex: 1;
				min-width: 140px;
				padding: 16px 20px;
				border-radius: 10px;
				text-align: center;
				border-left: 4px solid;
				background: var(--card-bg);
				box-shadow: var(--shadow-sm);
			}

			.stat-card .stat-number {
				font-size: 28px;
				font-weight: 700;
				line-height: 1.2;
			}

			.stat-card .stat-label {
				font-size: 12px;
				font-weight: 600;
				text-transform: uppercase;
				letter-spacing: 0.5px;
				margin-top: 4px;
				color: var(--text-muted);
			}

			.kanban-board {
				display: grid;
				grid-template-columns: repeat(4, 1fr);
				gap: 16px;
				min-height: 400px;
			}

			.kanban-column {
				background: var(--subtle-bg, var(--bg-color));
				border-radius: 10px;
				padding: 0;
				display: flex;
				flex-direction: column;
				min-height: 300px;
			}

			.kanban-column-header {
				padding: 14px 16px;
				border-radius: 10px 10px 0 0;
				display: flex;
				justify-content: space-between;
				align-items: center;
				font-weight: 700;
				font-size: 13px;
				text-transform: uppercase;
				letter-spacing: 0.5px;
			}

			.kanban-column-header .count-badge {
				font-size: 12px;
				font-weight: 700;
				padding: 2px 10px;
				border-radius: 12px;
				color: white;
			}

			.kanban-column-body {
				padding: 10px;
				flex: 1;
				overflow-y: auto;
				display: flex;
				flex-direction: column;
				gap: 8px;
			}

			.task-card {
				background: var(--card-bg);
				border-radius: 8px;
				padding: 12px 14px;
				box-shadow: var(--shadow-sm);
				cursor: pointer;
				transition: box-shadow 0.2s, transform 0.15s;
				border: 1px solid var(--border-color);
			}

			.task-card:hover {
				box-shadow: var(--shadow-base);
				transform: translateY(-1px);
			}

			.task-card .task-title {
				font-weight: 600;
				font-size: 13px;
				color: var(--text-color);
				margin-bottom: 8px;
				line-height: 1.4;
			}

			.task-card .task-meta {
				display: flex;
				flex-direction: column;
				gap: 4px;
			}

			.task-card .task-meta-row {
				display: flex;
				align-items: center;
				gap: 6px;
				font-size: 11.5px;
				color: var(--text-muted);
			}

			.task-card .task-meta-row .meta-icon {
				width: 14px;
				text-align: center;
				color: var(--text-light);
			}

			.task-card .task-tipo {
				display: inline-block;
				font-size: 10px;
				font-weight: 600;
				padding: 2px 8px;
				border-radius: 4px;
				background: var(--subtle-fg, var(--bg-color));
				color: var(--text-muted);
				margin-bottom: 6px;
				text-transform: uppercase;
				letter-spacing: 0.3px;
			}

			.task-card .task-vencimiento {
				font-weight: 600;
			}

			.task-card .task-vencimiento.vencida {
				color: var(--red-500, #e53935);
			}

			.task-card .task-vencimiento.proxima {
				color: var(--orange-500, #ff9800);
			}

			.kanban-empty {
				text-align: center;
				padding: 30px 10px;
				color: var(--text-muted);
				font-size: 12px;
				font-style: italic;
			}

			.avatar-small {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 20px;
				height: 20px;
				border-radius: 50%;
				background: var(--primary);
				color: white;
				font-size: 10px;
				font-weight: 700;
			}

			@media (max-width: 1200px) {
				.kanban-board {
					grid-template-columns: repeat(2, 1fr);
				}
			}

			@media (max-width: 768px) {
				.kanban-board {
					grid-template-columns: 1fr;
				}
			}
		`;
        document.head.appendChild(style);
    }

    setup_filters() {
        const filtersRow = this.wrapper.find(".filters-row");
        filtersRow.html(`
			<div class="filter-group">
				<label>Empresa</label>
				<select class="filter-empresa">
					<option value="">Todas</option>
				</select>
			</div>
			<div class="filter-group">
				<label>Cliente</label>
				<select class="filter-cliente">
					<option value="">Todos</option>
				</select>
			</div>
			<div class="filter-group">
				<label>Periodo</label>
				<select class="filter-periodo">
					<option value="">Todos</option>
				</select>
			</div>
			<div class="filter-group">
				<label>Tipo de Tarea</label>
				<select class="filter-tipo">
					<option value="">Todos</option>
				</select>
			</div>
			<div class="filter-group">
				<label>Asignado a</label>
				<select class="filter-asignado">
					<option value="">Todos</option>
				</select>
			</div>
		`);

        // Load filter options
        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Company", fields: ["name"], limit_page_length: 0, order_by: "name asc" },
            callback: (r) => {
                r.message.forEach((c) => {
                    filtersRow.find(".filter-empresa").append(`<option value="${c.name}">${c.name}</option>`);
                });
            },
        });

        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Cliente Contable", fields: ["name"], limit_page_length: 0, order_by: "name asc" },
            callback: (r) => {
                r.message.forEach((c) => {
                    filtersRow.find(".filter-cliente").append(`<option value="${c.name}">${c.name}</option>`);
                });
            },
        });

        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Periodo Contable", fields: ["name"], limit_page_length: 0, order_by: "name asc" },
            callback: (r) => {
                r.message.forEach((p) => {
                    filtersRow.find(".filter-periodo").append(`<option value="${p.name}">${p.name}</option>`);
                });
            },
        });

        const tipos = [
            "Impuestos", "Nómina", "Cierre Contable", "Auditoría",
            "Conciliación Bancaria", "Declaración Anual", "Dictamen Fiscal",
            "Estados Financieros", "Facturación", "Atención a Requerimiento",
            "Trámite Fiscal", "Consultoría", "Otro",
        ];
        tipos.forEach((t) => {
            filtersRow.find(".filter-tipo").append(`<option value="${t}">${t}</option>`);
        });

        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "User", fields: ["name", "full_name"], filters: { enabled: 1, user_type: "System User" }, limit_page_length: 0 },
            callback: (r) => {
                r.message.forEach((u) => {
                    const label = u.full_name || u.name;
                    filtersRow.find(".filter-asignado").append(`<option value="${u.name}">${label}</option>`);
                });
            },
        });

        // Bind filter change events
        filtersRow.find("select").on("change", () => this.load_data());
    }

    get_filters() {
        const filters = {};
        const cliente = this.wrapper.find(".filter-cliente").val();
        const periodo = this.wrapper.find(".filter-periodo").val();
        const tipo = this.wrapper.find(".filter-tipo").val();
        const asignado = this.wrapper.find(".filter-asignado").val();

        if (cliente) filters.cliente = cliente;
        if (periodo) filters.periodo = periodo;
        if (tipo) filters.tipo_de_tarea = tipo;
        if (asignado) filters.asignado_a = asignado;

        return filters;
    }

    load_data() {
        const filters = this.get_filters();
        const empresa = this.wrapper.find(".filter-empresa").val();

        if (empresa) {
            // First get clients belonging to this company, then filter tasks
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Cliente Contable",
                    fields: ["name"],
                    filters: [["Cliente Contable", "customer", "in",
                        frappe.call({
                            method: "frappe.client.get_list",
                            args: { doctype: "Customer", filters: { company: empresa }, fields: ["name"], limit_page_length: 0 },
                            async: false,
                        }).message?.map(c => c.name) || []
                    ]],
                    limit_page_length: 0,
                },
                callback: (r) => {
                    const clienteNames = (r.message || []).map(c => c.name);
                    if (clienteNames.length > 0) {
                        filters.cliente = ["in", clienteNames];
                    } else {
                        // No clients for this company — show empty
                        this.render([]);
                        return;
                    }
                    this.fetch_tasks(filters);
                },
            });
        } else {
            this.fetch_tasks(filters);
        }
    }

    fetch_tasks(filters) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Tarea Contable",
                fields: ["name", "titulo", "cliente", "periodo", "tipo_de_tarea", "estado", "fecha_de_vencimiento", "asignado_a"],
                filters: filters,
                limit_page_length: 0,
                order_by: "fecha_de_vencimiento asc",
            },
            callback: (r) => {
                this.render(r.message || []);
            },
        });
    }

    render(tasks) {
        this.render_stats(tasks);
        this.render_kanban(tasks);
    }

    render_stats(tasks) {
        const statsRow = this.wrapper.find(".stats-row");
        const counts = {};
        this.statuses.forEach((s) => (counts[s] = 0));
        tasks.forEach((t) => {
            if (counts[t.estado] !== undefined) counts[t.estado]++;
        });

        let html = "";
        this.statuses.forEach((status) => {
            const colors = this.status_colors[status];
            html += `
				<div class="stat-card" style="border-left-color: ${colors.border};">
					<div class="stat-number" style="color: ${colors.badge};">${counts[status]}</div>
					<div class="stat-label">${status}</div>
				</div>
			`;
        });
        statsRow.html(html);
    }

    render_kanban(tasks) {
        const board = this.wrapper.find(".kanban-board");
        const grouped = {};
        this.statuses.forEach((s) => (grouped[s] = []));
        tasks.forEach((t) => {
            if (grouped[t.estado]) grouped[t.estado].push(t);
        });

        let html = "";
        this.statuses.forEach((status) => {
            const colors = this.status_colors[status];
            const items = grouped[status];

            html += `
				<div class="kanban-column">
					<div class="kanban-column-header" style="background: ${colors.bg}; color: ${colors.text};">
						<span>${status}</span>
						<span class="count-badge" style="background: ${colors.badge};">${items.length}</span>
					</div>
					<div class="kanban-column-body">
			`;

            if (items.length === 0) {
                html += `<div class="kanban-empty">Sin tareas</div>`;
            } else {
                items.forEach((task) => {
                    html += this.render_task_card(task);
                });
            }

            html += `</div></div>`;
        });

        board.html(html);

        // Bind click to open task
        board.find(".task-card").on("click", function () {
            const name = $(this).data("name");
            frappe.set_route("Form", "Tarea Contable", name);
        });
    }

    render_task_card(task) {
        const today = frappe.datetime.get_today();
        let vencClass = "";
        if (task.estado !== "Completada" && task.fecha_de_vencimiento) {
            if (task.fecha_de_vencimiento < today) {
                vencClass = "vencida";
            } else {
                const diff = frappe.datetime.get_diff(task.fecha_de_vencimiento, today);
                if (diff <= 3) vencClass = "proxima";
            }
        }

        const fechaFormatted = task.fecha_de_vencimiento
            ? frappe.datetime.str_to_user(task.fecha_de_vencimiento)
            : "—";

        const asignadoLabel = task.asignado_a
            ? frappe.utils.get_abbr(task.asignado_a)
            : "—";

        const asignadoName = task.asignado_a || "Sin asignar";

        const tipoHtml = task.tipo_de_tarea
            ? `<span class="task-tipo">${task.tipo_de_tarea}</span>`
            : "";

        return `
			<div class="task-card" data-name="${task.name}">
				${tipoHtml}
				<div class="task-title">${task.titulo}</div>
				<div class="task-meta">
					<div class="task-meta-row">
						<span class="meta-icon">👤</span>
						<span>${frappe.utils.escape_html(task.cliente || "—")}</span>
					</div>
					<div class="task-meta-row">
						<span class="meta-icon">📅</span>
						<span class="task-vencimiento ${vencClass}">${fechaFormatted}</span>
					</div>
					<div class="task-meta-row">
						<span class="meta-icon">📋</span>
						<span>${frappe.utils.escape_html(task.periodo || "—")}</span>
					</div>
					<div class="task-meta-row">
						${task.asignado_a ? `<span class="avatar-small">${asignadoLabel}</span>` : '<span class="meta-icon">—</span>'}
						<span>${frappe.utils.escape_html(asignadoName)}</span>
					</div>
				</div>
			</div>
		`;
    }
}
