frappe.pages["panel-de-tareas"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Panel de Tareas",
		single_column: true,
	});

	frappe.pages["panel-de-tareas"].panel = new PanelDeTareas(page);
	frappe.pages["panel-de-tareas"].panel.init();
};

frappe.pages["panel-de-tareas"].on_page_show = function (wrapper) {
	const panel = frappe.pages["panel-de-tareas"].panel;
	if (panel) {
		panel.apply_route_options();
		panel.load_data();
	}
};

class PanelDeTareas {
	constructor(page) {
		this.page = page;
		this.wrapper = page.main;
		this.statuses = ["Pendiente", "En Proceso", "En Revisión", "Completada"];
		this.canMoveCards = this.has_any_role(["Contador del Despacho", "System Manager"]);
		this.draggedTask = null;
		this.blockCardClickUntil = 0;
		this.statusMeta = {
			Pendiente: { border: "#f59e0b", chip: "#fef3c7", text: "#92400e" },
			"En Proceso": { border: "#3b82f6", chip: "#dbeafe", text: "#1e3a8a" },
			"En Revisión": { border: "#a855f7", chip: "#f3e8ff", text: "#6b21a8" },
			Completada: { border: "#10b981", chip: "#d1fae5", text: "#065f46" },
		};
	}

	has_any_role(roles) {
		const userRoles = frappe.user_roles || [];
		return roles.some((role) => userRoles.includes(role));
	}

	init() {
		this.setup_styles();
		this.render_shell();
		this.setup_filters();
		this.setup_actions();
	}

	apply_route_options() {
		if (frappe.route_options) {
			const ro = frappe.route_options;
			if (ro.asignado_a) {
				// Prevent empty options or overriding sync issues
				if (this.wrapper.find(`.filter-asignado option[value="${ro.asignado_a}"]`).length === 0) {
					this.wrapper.find(".filter-asignado").append(`<option value="${ro.asignado_a}">${ro.asignado_a}</option>`);
				}
				this.wrapper.find(".filter-asignado").val(ro.asignado_a);
			}
			if (ro.estado) {
				this.wrapper.find(".filter-estado").val(ro.estado);
			}
			if (ro.vencimiento) {
				let v = ro.vencimiento.toLowerCase();
				this.wrapper.find(".filter-vencimiento").val(v);
			}
			this.sync_kpi_highlight();
			frappe.route_options = null; // consume
		}
	}

	setup_styles() {
		if (document.getElementById("panel-tareas-v3-styles")) return;

		const style = document.createElement("style");
		style.id = "panel-tareas-v3-styles";
		style.textContent = `
			:root {
				--pt-bg-soft: linear-gradient(140deg, #f8fafc 0%, #eef2ff 55%, #ecfeff 100%);
				--pt-card: #ffffff;
				--pt-border: #dbe3ef;
				--pt-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
			}

			.panel-tareas-shell {
				background: var(--pt-bg-soft);
				border: 1px solid var(--pt-border);
				border-radius: 16px;
				padding: 18px;
			}

			.panel-tareas-hero {
				display: grid;
				grid-template-columns: 1.2fr .8fr;
				gap: 14px;
				margin-bottom: 14px;
			}

			.panel-tareas-title {
				background: rgba(255, 255, 255, 0.74);
				border: 1px solid var(--pt-border);
				border-radius: 14px;
				padding: 16px;
				box-shadow: var(--pt-shadow);
				display: flex;
				justify-content: space-between;
				align-items: flex-start;
			}

			.panel-tareas-title h2 {
				margin: 0;
				font-size: 24px;
				font-weight: 800;
				letter-spacing: .2px;
				color: #1f2937;
			}

			.panel-tareas-title p {
				margin: 6px 0 0;
				font-size: 13px;
				color: #475569;
			}

			.pt-btn-nueva-tarea {
				background: linear-gradient(135deg, #3b82f6, #2563eb);
				color: #fff;
				border: none;
				border-radius: 10px;
				padding: 9px 18px;
				font-size: 13px;
				font-weight: 700;
				cursor: pointer;
				white-space: nowrap;
				transition: transform .12s ease, box-shadow .12s ease;
				box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
			}

			.pt-btn-nueva-tarea:hover {
				transform: translateY(-1px);
				box-shadow: 0 6px 18px rgba(37, 99, 235, 0.4);
			}

			.pt-move-note {
				margin: 8px 0 0;
				font-size: 12px;
				font-weight: 700;
				color: #065f46;
			}

			.panel-tareas-kpis {
				display: grid;
				grid-template-columns: repeat(2, 1fr);
				gap: 10px;
			}

			.pt-kpi {
				background: var(--pt-card);
				border: 1px solid var(--pt-border);
				border-radius: 12px;
				padding: 10px 12px;
				box-shadow: var(--pt-shadow);
			}

			.pt-kpi .v {
				display: block;
				font-size: 24px;
				font-weight: 800;
				line-height: 1;
				color: #0f172a;
			}

			.pt-kpi .l {
				display: block;
				margin-top: 4px;
				font-size: 11px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: .5px;
				color: #64748b;
			}

			.panel-tareas-filters {
				display: grid;
				grid-template-columns: repeat(7, minmax(120px, 1fr));
				gap: 10px;
				margin-bottom: 14px;
			}

			.pt-field {
				display: flex;
				flex-direction: column;
				gap: 4px;
			}

			.pt-field label {
				font-size: 11px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: .5px;
				color: #64748b;
			}

			.pt-field select,
			.pt-field input,
			.pt-reset {
				height: 36px;
				border-radius: 10px;
				border: 1px solid var(--pt-border);
				padding: 0 10px;
				font-size: 13px;
				background: #fff;
			}

			.pt-reset {
				cursor: pointer;
				font-weight: 700;
				color: #0f172a;
				background: #f8fafc;
			}

			.panel-tareas-stats {
				display: grid;
				grid-template-columns: repeat(4, minmax(150px, 1fr));
				gap: 10px;
				margin-bottom: 14px;
			}

			.pt-stat {
				background: var(--pt-card);
				border-radius: 12px;
				padding: 12px;
				border: 1px solid var(--pt-border);
				border-left: 4px solid;
				box-shadow: var(--pt-shadow);
			}

			.pt-stat .n {
				font-size: 30px;
				font-weight: 800;
				line-height: 1;
			}

			.pt-stat .t {
				margin-top: 4px;
				font-size: 12px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: .4px;
				color: #64748b;
			}

			.panel-tareas-board {
				display: grid;
				grid-template-columns: repeat(4, minmax(0, 1fr));
				gap: 12px;
			}

			.pt-col {
				background: #f8fafc;
				border: 1px solid var(--pt-border);
				border-radius: 12px;
				min-height: 360px;
				overflow: hidden;
			}

			.pt-col-h {
				display: flex;
				justify-content: space-between;
				align-items: center;
				padding: 10px 12px;
				border-bottom: 1px solid var(--pt-border);
				font-size: 12px;
				font-weight: 800;
				text-transform: uppercase;
				letter-spacing: .5px;
			}

			.pt-count {
				padding: 2px 8px;
				border-radius: 999px;
				font-size: 11px;
				font-weight: 800;
			}

			.pt-col-b {
				padding: 10px;
				display: flex;
				flex-direction: column;
				gap: 8px;
				max-height: 75vh;
				overflow-y: auto;
			}

			.pt-col-b.pt-dropzone {
				transition: background-color .12s ease;
			}

			.pt-col-b.pt-dropzone.pt-drop-active {
				background: #e2e8f0;
			}

			.pt-task {
				display: flex;
				align-items: stretch;
				background: #fff;
				border: 1px solid var(--pt-border);
				border-radius: 10px;
				box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
				transition: transform .15s ease, box-shadow .15s ease;
				flex-shrink: 0;
			}

			.pt-task:hover {
				transform: translateY(-1px);
				box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
			}

			.pt-task-content {
				flex: 1;
				padding: 10px;
				cursor: pointer;
				min-width: 0;
			}


			.pt-task-kind {
				display: inline-flex;
				padding: 2px 7px;
				border-radius: 6px;
				font-size: 10px;
				font-weight: 700;
				text-transform: uppercase;
				background: #eef2ff;
				color: #4338ca;
				margin-bottom: 6px;
			}

			.pt-task-head {
				display: flex;
				justify-content: space-between;
				align-items: flex-start;
				gap: 8px;
			}

			.pt-task-title {
				font-size: 13px;
				font-weight: 700;
				color: #111827;
				line-height: 1.35;
				margin-bottom: 7px;
			}

			.pt-drag-handle {
				display: flex;
				align-items: center;
				justify-content: center;
				width: 28px;
				min-width: 28px;
				background: #f8fafc;
				border-left: 1px solid var(--pt-border);
				cursor: grab;
				transition: background .12s ease;
				flex-shrink: 0;
			}

			.pt-drag-handle:hover {
				background: #e2e8f0;
			}

			.pt-drag-handle:active {
				cursor: grabbing;
				background: #cbd5e1;
			}

			.pt-drag-dots {
				display: grid;
				grid-template-columns: repeat(2, 5px);
				gap: 3px;
			}

			.pt-drag-dots span {
				width: 5px;
				height: 5px;
				border-radius: 50%;
				background: #94a3b8;
			}

			.pt-task.pt-dragging {
				opacity: 0.45;
			}

			.pt-task-meta {
				display: grid;
				gap: 4px;
			}

			.pt-task-meta-row {
				font-size: 11px;
				color: #64748b;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			.pt-task-meta-row strong {
				color: #334155;
			}

			.pt-due-danger {
				color: #b91c1c;
				font-weight: 700;
			}

			.pt-due-warn {
				color: #b45309;
				font-weight: 700;
			}

			.pt-modal-body {
				padding: 0;
			}

			.pt-modal-field {
				padding: 10px 0;
				border-bottom: 1px solid #f1f5f9;
			}

			.pt-modal-field:last-child {
				border-bottom: none;
			}

			.pt-modal-label {
				font-size: 11px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: .4px;
				color: #64748b;
				margin-bottom: 4px;
			}

			.pt-modal-value {
				font-size: 14px;
				color: #1e293b;
				font-weight: 500;
			}

			.pt-modal-value.pt-due-danger {
				color: #b91c1c;
				font-weight: 700;
			}

			.pt-modal-value.pt-due-warn {
				color: #b45309;
				font-weight: 700;
			}

			.pt-modal-notas {
				background: #f8fafc;
				border-radius: 8px;
				padding: 10px;
				font-size: 13px;
				color: #475569;
				min-height: 40px;
				white-space: pre-wrap;
			}

			.pt-modal-edit-field select,
			.pt-modal-edit-field input,
			.pt-modal-edit-field textarea {
				width: 100%;
				border-radius: 8px;
				border: 1px solid var(--pt-border);
				padding: 8px 10px;
				font-size: 13px;
				background: #fff;
			}

			.pt-modal-edit-field textarea {
				min-height: 70px;
				resize: vertical;
			}

			.pt-empty {
				padding: 26px 10px;
				text-align: center;
				font-size: 12px;
				color: #94a3b8;
				font-style: italic;
			}

			.pt-kpi[data-filter] {
				cursor: pointer;
				transition: transform .12s ease, box-shadow .12s ease;
			}

			.pt-kpi[data-filter]:hover {
				transform: translateY(-1px);
				box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
			}

			.pt-kpi[data-filter].pt-kpi-active {
				outline: 2px solid #3b82f6;
				outline-offset: -2px;
			}

			@media (max-width: 1200px) {
				.panel-tareas-filters {
					grid-template-columns: repeat(4, minmax(120px, 1fr));
				}

				.panel-tareas-board {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}
			}

			@media (max-width: 900px) {
				.panel-tareas-hero {
					grid-template-columns: 1fr;
				}

				.panel-tareas-kpis {
					grid-template-columns: repeat(4, minmax(0, 1fr));
				}

				.panel-tareas-stats {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}
			}

			@media (max-width: 640px) {
				.panel-tareas-filters {
					grid-template-columns: 1fr;
				}

				.panel-tareas-kpis {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}

				.panel-tareas-stats,
				.panel-tareas-board {
					grid-template-columns: 1fr;
				}
			}
		`;

		document.head.appendChild(style);
	}

	render_shell() {
		const moveHint = this.canMoveCards
			? '<p class="pt-move-note">Arrastra tarjetas entre columnas para cambiar su estado.</p>'
			: "";

		this.wrapper.html(`
			<div class="panel-tareas-shell">
				<div class="panel-tareas-hero">
					<div class="panel-tareas-title">
						<div>
							<h2>Panel de Tareas</h2>
							<p>Seguimiento operativo por estado, vencimiento y responsable.</p>
							${moveHint}
						</div>
						<button class="pt-btn-nueva-tarea" type="button">+ Nueva Tarea</button>
					</div>
					<div class="panel-tareas-kpis">
						<div class="pt-kpi"><span class="v" data-kpi="total">0</span><span class="l">Total</span></div>
						<div class="pt-kpi" data-filter="vencidas" title="Click para filtrar"><span class="v" data-kpi="vencidas">0</span><span class="l">Vencidas</span></div>
						<div class="pt-kpi" data-filter="hoy" title="Click para filtrar"><span class="v" data-kpi="hoy">0</span><span class="l">Vencen Hoy</span></div>
						<div class="pt-kpi" data-filter="semana" title="Click para filtrar"><span class="v" data-kpi="semana">0</span><span class="l">Prox 7 Dias</span></div>
					</div>
				</div>
				<div class="panel-tareas-filters"></div>
				<div class="panel-tareas-stats"></div>
				<div class="panel-tareas-board"></div>
			</div>
		`);
	}

	setup_filters() {
		const filters = this.wrapper.find(".panel-tareas-filters");
		filters.html(`
			<div class="pt-field">
				<label>Cliente</label>
				<select class="filter-cliente"><option value="">Todos</option></select>
			</div>
			<div class="pt-field">
				<label>Periodo</label>
				<select class="filter-periodo"><option value="">Todos</option></select>
			</div>
			<div class="pt-field">
				<label>Tipo</label>
				<select class="filter-tipo"><option value="">Todos</option></select>
			</div>
			<div class="pt-field">
				<label>Estado</label>
				<select class="filter-estado">
					<option value="">Todos</option>
					<option value="Pendiente">Pendiente</option>
					<option value="En Proceso">En Proceso</option>
					<option value="En Revisión">En Revisión</option>
					<option value="Completada">Completada</option>
				</select>
			</div>
			<div class="pt-field">
				<label>Asignado</label>
				<select class="filter-asignado"><option value="">Todos</option></select>
			</div>
			<div class="pt-field">
				<label>Vencimiento</label>
				<select class="filter-vencimiento">
					<option value="">Todos</option>
					<option value="vencidas">Vencidas</option>
					<option value="hoy">Vencen Hoy</option>
					<option value="semana">Pr\u00f3x 7 D\u00edas</option>
				</select>
			</div>
			<div class="pt-field">
				<label>Buscar Titulo</label>
				<input type="text" class="filter-search" placeholder="Ej. IVA mayo" />
			</div>
			<div class="pt-field">
				<label>&nbsp;</label>
				<button class="pt-reset" type="button">Limpiar</button>
			</div>
		`);

		this.fill_select_options();

		filters.find("select").on("change", () => {
			this.sync_kpi_highlight();
			this.load_data();
		});
		filters.find(".filter-search").on("input", frappe.utils.debounce(() => this.load_data(), 240));
		filters.find(".pt-reset").on("click", () => {
			filters.find("select").val("");
			filters.find(".filter-search").val("");
			this.sync_kpi_highlight();
			this.load_data();
		});

		// KPI click → set vencimiento filter
		this.wrapper.find(".pt-kpi[data-filter]").on("click", (e) => {
			const filterVal = $(e.currentTarget).data("filter");
			const sel = this.wrapper.find(".filter-vencimiento");
			sel.val(sel.val() === filterVal ? "" : filterVal);
			this.sync_kpi_highlight();
			this.load_data();
		});
	}

	fill_select_options() {
		const filters = this.wrapper.find(".panel-tareas-filters");

		frappe.call({
			method: "frappe.client.get_list",
			args: { doctype: "Cliente Contable", fields: ["name"], limit_page_length: 0, order_by: "name asc" },
			callback: (r) => {
				(r.message || []).forEach((row) => {
					filters.find(".filter-cliente").append(`<option value="${row.name}">${row.name}</option>`);
				});
			},
		});

		frappe.call({
			method: "frappe.client.get_list",
			args: { doctype: "Periodo Contable", fields: ["name"], limit_page_length: 0, order_by: "name desc" },
			callback: (r) => {
				(r.message || []).forEach((row) => {
					filters.find(".filter-periodo").append(`<option value="${row.name}">${row.name}</option>`);
				});
			},
		});

		const tipos = [
			"Impuestos", "N\u00f3mina", "Cierre Contable", "Auditor\u00eda", "Conciliaci\u00f3n Bancaria",
			"Declaraci\u00f3n DGI", "Estados Financieros", "Facturaci\u00f3n",
			"Atenci\u00f3n a Requerimiento", "Tr\u00e1mite DGI", "Consultor\u00eda", "Otro",
		];
		tipos.forEach((tipo) => {
			filters.find(".filter-tipo").append(`<option value="${tipo}">${tipo}</option>`);
		});

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "User",
				fields: ["name", "full_name"],
				filters: { enabled: 1, user_type: "System User" },
				limit_page_length: 0,
				order_by: "full_name asc",
			},
			callback: (r) => {
				(r.message || []).forEach((row) => {
					const label = row.full_name || row.name;
					filters.find(".filter-asignado").append(`<option value="${row.name}">${label}</option>`);
				});
			},
		});
	}

	sync_kpi_highlight() {
		const activeVal = this.wrapper.find(".filter-vencimiento").val();
		this.wrapper.find(".pt-kpi[data-filter]").removeClass("pt-kpi-active");
		if (activeVal) {
			this.wrapper.find(`.pt-kpi[data-filter='${activeVal}']`).addClass("pt-kpi-active");
		}
	}

	get_filters() {
		const filters = {};
		const shell = this.wrapper;
		const cliente = shell.find(".filter-cliente").val();
		const periodo = shell.find(".filter-periodo").val();
		const tipo = shell.find(".filter-tipo").val();
		const estado = shell.find(".filter-estado").val();
		const asignado = shell.find(".filter-asignado").val();
		const vencimiento = shell.find(".filter-vencimiento").val();
		const search = (shell.find(".filter-search").val() || "").trim();

		if (cliente) filters.cliente = cliente;
		if (periodo) filters.periodo = periodo;
		if (tipo) filters.tipo_de_tarea = tipo;
		if (estado) filters.estado = estado;
		if (asignado) filters.asignado_a = asignado;

		return { filters, search, vencimiento };
	}

	load_data() {
		const { filters, search, vencimiento } = this.get_filters();
		this.currentVencimiento = vencimiento;
		this.fetch_tasks(filters, search);
	}

	fetch_tasks(filters, search) {
		const args = {
			doctype: "Tarea Contable",
			fields: ["name", "titulo", "cliente", "periodo", "tipo_de_tarea", "estado", "fecha_de_vencimiento", "asignado_a"],
			filters,
			limit_page_length: 0,
			order_by: "fecha_de_vencimiento asc",
		};

		if (search) {
			args.or_filters = [["Tarea Contable", "titulo", "like", `%${search}%`]];
		}

		frappe.call({
			method: "frappe.client.get_list",
			args,
			callback: (r) => {
				let tasks = r.message || [];
				if (this.currentVencimiento) {
					tasks = this.apply_due_filter(tasks, this.currentVencimiento);
				}
				this.render(tasks);
			},
		});
	}

	apply_due_filter(tasks, vencimiento) {
		const today = frappe.datetime.get_today();
		return tasks.filter((task) => {
			if (task.estado === "Completada" || !task.fecha_de_vencimiento) return false;
			const diff = frappe.datetime.get_diff(task.fecha_de_vencimiento, today);
			if (vencimiento === "vencidas") return diff < 0;
			if (vencimiento === "hoy") return diff === 0;
			if (vencimiento === "semana") return diff >= 0 && diff <= 7;
			return true;
		});
	}

	render(tasks) {
		this.render_kpis(tasks);
		this.render_stats(tasks);
		this.render_board(tasks);
	}

	render_kpis(tasks) {
		const today = frappe.datetime.get_today();
		let vencidas = 0;
		let hoy = 0;
		let semana = 0;

		tasks.forEach((task) => {
			if (!task.fecha_de_vencimiento || task.estado === "Completada") return;
			const diff = frappe.datetime.get_diff(task.fecha_de_vencimiento, today);
			if (diff < 0) vencidas += 1;
			if (diff === 0) hoy += 1;
			if (diff >= 0 && diff <= 7) semana += 1;
		});

		this.wrapper.find("[data-kpi='total']").text(tasks.length);
		this.wrapper.find("[data-kpi='vencidas']").text(vencidas);
		this.wrapper.find("[data-kpi='hoy']").text(hoy);
		this.wrapper.find("[data-kpi='semana']").text(semana);
	}

	render_stats(tasks) {
		const stats = this.wrapper.find(".panel-tareas-stats");
		const count = {};
		this.statuses.forEach((s) => { count[s] = 0; });

		tasks.forEach((task) => {
			if (count[task.estado] !== undefined) count[task.estado] += 1;
		});

		let html = "";
		this.statuses.forEach((status) => {
			const meta = this.statusMeta[status];
			html += `
				<div class="pt-stat" style="border-left-color:${meta.border};">
					<div class="n" style="color:${meta.text};">${count[status]}</div>
					<div class="t">${status}</div>
				</div>
			`;
		});

		stats.html(html);
	}

	render_board(tasks) {
		const board = this.wrapper.find(".panel-tareas-board");
		const grouped = {};
		this.statuses.forEach((s) => { grouped[s] = []; });

		tasks.forEach((task) => {
			if (grouped[task.estado]) grouped[task.estado].push(task);
		});

		let html = "";
		this.statuses.forEach((status) => {
			const meta = this.statusMeta[status];
			const rows = grouped[status];
			const dropzoneClass = this.canMoveCards ? " pt-dropzone" : "";

			html += `
				<div class="pt-col">
					<div class="pt-col-h" style="border-left:4px solid ${meta.border};">
						<span>${status}</span>
						<span class="pt-count" style="background:${meta.chip};color:${meta.text};">${rows.length}</span>
					</div>
					<div class="pt-col-b${dropzoneClass}" data-status="${status}">
			`;

			if (!rows.length) {
				html += '<div class="pt-empty">Sin tareas en esta etapa</div>';
			} else {
				rows.forEach((task) => { html += this.render_task_card(task); });
			}

			html += "</div></div>";
		});

		board.html(html);

		board.find(".pt-task-content").on("click", (event) => {
			if (Date.now() < this.blockCardClickUntil) return;
			const name = $(event.currentTarget).closest(".pt-task").data("name");
			this.open_task_modal(name);
		});

		if (this.canMoveCards) {
			this.bind_drag_and_drop();
		}
	}

	bind_drag_and_drop() {
		const board = this.wrapper.find(".panel-tareas-board");
		const handles = board.find(".pt-drag-handle");
		const cards = board.find(".pt-task");
		const zones = board.find(".pt-col-b.pt-dropzone");

		// Only allow drag from the handle
		cards.attr("draggable", "false");

		handles.on("mousedown", (event) => {
			const card = $(event.currentTarget).closest(".pt-task");
			card.attr("draggable", "true");
		});

		handles.on("mouseup", (event) => {
			const card = $(event.currentTarget).closest(".pt-task");
			card.attr("draggable", "false");
		});

		cards.on("dragstart", (event) => {
			const card = $(event.currentTarget);
			this.draggedTask = {
				name: card.data("name"),
				status: card.data("status"),
			};
			card.addClass("pt-dragging");

			if (event.originalEvent && event.originalEvent.dataTransfer) {
				event.originalEvent.dataTransfer.effectAllowed = "move";
				event.originalEvent.dataTransfer.setData("text/plain", this.draggedTask.name);
			}
		});

		cards.on("dragend", (event) => {
			$(event.currentTarget).removeClass("pt-dragging");
			zones.removeClass("pt-drop-active");
			this.draggedTask = null;
			this.blockCardClickUntil = Date.now() + 250;
		});

		zones.on("dragover", (event) => {
			event.preventDefault();
			if (!this.draggedTask) return;
			const zone = $(event.currentTarget);
			if (zone.data("status") !== this.draggedTask.status) {
				zone.addClass("pt-drop-active");
			}
		});

		zones.on("dragleave", (event) => {
			$(event.currentTarget).removeClass("pt-drop-active");
		});

		zones.on("drop", (event) => {
			event.preventDefault();
			const zone = $(event.currentTarget);
			zone.removeClass("pt-drop-active");

			if (!this.draggedTask) return;

			const targetStatus = zone.data("status");
			if (!targetStatus || targetStatus === this.draggedTask.status) return;

			this.blockCardClickUntil = Date.now() + 350;
			this.move_task_to_status(this.draggedTask.name, targetStatus);
		});
	}

	move_task_to_status(taskName, targetStatus) {
		frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "Tarea Contable",
				name: taskName,
				fieldname: "estado",
				value: targetStatus,
			},
			freeze: true,
			freeze_message: "Actualizando estado...",
			callback: (r) => {
				if (r.exc) {
					frappe.msgprint("No se pudo mover la tarea.");
					this.load_data();
					return;
				}

				frappe.show_alert({ message: `Tarea movida a ${targetStatus}`, indicator: "green" });
				this.load_data();
			},
			error: () => {
				frappe.msgprint("Ocurrio un error al mover la tarea.");
				this.load_data();
			},
		});
	}

	render_task_card(task) {
		const today = frappe.datetime.get_today();
		let dueClass = "";

		if (task.estado !== "Completada" && task.fecha_de_vencimiento) {
			const diff = frappe.datetime.get_diff(task.fecha_de_vencimiento, today);
			if (diff < 0) dueClass = "pt-due-danger";
			else if (diff <= 3) dueClass = "pt-due-warn";
		}

		const fecha = task.fecha_de_vencimiento
			? frappe.datetime.str_to_user(task.fecha_de_vencimiento)
			: "-";

		const asignado = task.asignado_a || "Sin asignar";
		const titulo = frappe.utils.escape_html(task.titulo || "Sin titulo");
		const cliente = frappe.utils.escape_html(task.cliente || "-");
		const periodo = frappe.utils.escape_html(task.periodo || "-");
		const tipo = task.tipo_de_tarea ? `<span class="pt-task-kind">${frappe.utils.escape_html(task.tipo_de_tarea)}</span>` : "";

		const dragHandle = this.canMoveCards
			? `<div class="pt-drag-handle" title="Arrastrar para cambiar estado">
				<div class="pt-drag-dots">
					<span></span><span></span>
					<span></span><span></span>
					<span></span><span></span>
				</div>
			   </div>`
			: "";

		return `
			<div class="pt-task" data-name="${task.name}" data-status="${task.estado || ""}">
				<div class="pt-task-content">
					${tipo}
					<div class="pt-task-title">${titulo}</div>
					<div class="pt-task-meta">
						<div class="pt-task-meta-row"><strong>Cliente:</strong> ${cliente}</div>
						<div class="pt-task-meta-row ${dueClass}"><strong>Vence:</strong> ${fecha}</div>
						<div class="pt-task-meta-row"><strong>Periodo:</strong> ${periodo}</div>
						<div class="pt-task-meta-row"><strong>Asignado:</strong> ${frappe.utils.escape_html(asignado)}</div>
					</div>
				</div>
				${dragHandle}
			</div>
		`;
	}

	open_task_modal(taskName) {
		frappe.call({
			method: "frappe.client.get",
			args: { doctype: "Tarea Contable", name: taskName },
			freeze: true,
			callback: (r) => {
				if (!r.message) return;
				this.show_task_dialog(r.message);
			}
		});
	}

	show_task_dialog(task) {
		const me = this;
		const isContador = this.has_any_role(["Contador del Despacho", "System Manager"]);
		const today = frappe.datetime.get_today();
		let dueClass = "";

		if (task.estado !== "Completada" && task.fecha_de_vencimiento) {
			const diff = frappe.datetime.get_diff(task.fecha_de_vencimiento, today);
			if (diff < 0) dueClass = "pt-due-danger";
			else if (diff <= 3) dueClass = "pt-due-warn";
		}

		const fecha_display = task.fecha_de_vencimiento
			? frappe.datetime.str_to_user(task.fecha_de_vencimiento)
			: "-";

		const statusMeta = this.statusMeta[task.estado] || { chip: "#f1f5f9", text: "#475569" };

		const readonly_html = `
			<div class="pt-modal-body">
				<div class="pt-modal-field">
					<div class="pt-modal-label">Cliente</div>
					<div class="pt-modal-value">${frappe.utils.escape_html(task.cliente || "-")}</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Periodo</div>
					<div class="pt-modal-value">${frappe.utils.escape_html(task.periodo || "-")}</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Tipo de Tarea</div>
					<div class="pt-modal-value">${frappe.utils.escape_html(task.tipo_de_tarea || "-")}</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Estado</div>
					<div class="pt-modal-value">
						<span style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:12px;font-weight:700;
							background:${statusMeta.chip};color:${statusMeta.text};">
							${frappe.utils.escape_html(task.estado || "-")}
						</span>
					</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Fecha de Vencimiento</div>
					<div class="pt-modal-value ${dueClass}">${fecha_display}</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Asignado a</div>
					<div class="pt-modal-value">${frappe.utils.escape_html(task.asignado_a || "Sin asignar")}</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Notas</div>
					<div class="pt-modal-notas">${frappe.utils.escape_html(task.notas || "Sin notas")}</div>
				</div>
			</div>
		`;

		const tipos = [
			"Impuestos", "N\u00f3mina", "Cierre Contable", "Auditor\u00eda", "Conciliaci\u00f3n Bancaria",
			"Declaraci\u00f3n DGI", "Estados Financieros", "Facturaci\u00f3n",
			"Atenci\u00f3n a Requerimiento", "Tr\u00e1mite DGI", "Consultor\u00eda", "Otro",
		];
		const estados = ["Pendiente", "En Proceso", "En Revisi\u00f3n", "Completada"];

		const tipo_options = tipos.map(t =>
			`<option value="${t}" ${t === task.tipo_de_tarea ? "selected" : ""}>${t}</option>`
		).join("");

		const estado_options = estados.map(e =>
			`<option value="${e}" ${e === task.estado ? "selected" : ""}>${e}</option>`
		).join("");

		const edit_html = `
			<div class="pt-modal-body">
				<div class="pt-modal-field pt-modal-edit-field">
					<div class="pt-modal-label">T\u00edtulo</div>
					<input type="text" class="pt-edit-titulo" value="${frappe.utils.escape_html(task.titulo || '')}" />
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Cliente</div>
					<div class="pt-modal-value">${frappe.utils.escape_html(task.cliente || "-")}</div>
				</div>
				<div class="pt-modal-field">
					<div class="pt-modal-label">Periodo</div>
					<div class="pt-modal-value">${frappe.utils.escape_html(task.periodo || "-")}</div>
				</div>
				<div class="pt-modal-field pt-modal-edit-field">
					<div class="pt-modal-label">Tipo de Tarea</div>
					<select class="pt-edit-tipo">${tipo_options}</select>
				</div>
				<div class="pt-modal-field pt-modal-edit-field">
					<div class="pt-modal-label">Estado</div>
					<select class="pt-edit-estado">${estado_options}</select>
				</div>
				<div class="pt-modal-field pt-modal-edit-field">
					<div class="pt-modal-label">Fecha de Vencimiento</div>
					<input type="date" class="pt-edit-fecha" value="${task.fecha_de_vencimiento || ''}" />
				</div>
				<div class="pt-modal-field pt-modal-edit-field">
					<div class="pt-modal-label">Notas</div>
					<textarea class="pt-edit-notas">${frappe.utils.escape_html(task.notas || '')}</textarea>
				</div>
			</div>
		`;

		const dialog = new frappe.ui.Dialog({
			title: task.titulo || "Detalle de Tarea",
			size: "large",
			primary_action_label: "Editar",
			primary_action: () => {
				// Switch to edit mode
				dialog.$body.html(edit_html);
				dialog.set_primary_action("Guardar", () => {
					const body = dialog.$body;
					const newTitulo = body.find(".pt-edit-titulo").val();
					const otherValues = {
						tipo_de_tarea: body.find(".pt-edit-tipo").val(),
						estado: body.find(".pt-edit-estado").val(),
						fecha_de_vencimiento: body.find(".pt-edit-fecha").val(),
						notas: body.find(".pt-edit-notas").val(),
					};

					const save_fields = (docName) => {
						frappe.call({
							method: "frappe.client.set_value",
							args: {
								doctype: "Tarea Contable",
								name: docName,
								fieldname: otherValues,
							},
							freeze: true,
							freeze_message: "Guardando...",
							callback: (r) => {
								if (!r.exc) {
									frappe.show_alert({ message: "Tarea actualizada", indicator: "green" });
									dialog.hide();
									me.load_data();
								}
							},
							error: () => {
								frappe.msgprint("Error al guardar la tarea.");
							}
						});
					};

					// Si cambió el titulo (que es el name), renombrar primero
					if (newTitulo && newTitulo !== task.name) {
						frappe.call({
							method: "frappe.client.rename_doc",
							args: {
								doctype: "Tarea Contable",
								old: task.name,
								new: newTitulo,
							},
							freeze: true,
							freeze_message: "Renombrando...",
							callback: (r) => {
								if (!r.exc) {
									save_fields(newTitulo);
								}
							},
							error: () => {
								frappe.msgprint("Error al renombrar la tarea.");
							}
						});
					} else {
						save_fields(task.name);
					}
				});

				// Change secondary to "Cancelar" that goes back to read-only
				dialog.set_secondary_action_label("Cancelar");
				dialog.set_secondary_action(() => {
					dialog.$body.html(readonly_html);
					dialog.set_primary_action("Editar", dialog.primary_action);
					dialog.set_secondary_action_label("Descartar");
					dialog.set_secondary_action(() => dialog.hide());
				});
			},
			secondary_action_label: "Descartar",
			secondary_action: () => dialog.hide(),
		});

		dialog.$body.html(readonly_html);
		dialog.show();
	}

	setup_actions() {
		this.wrapper.find(".pt-btn-nueva-tarea").on("click", () => this.open_new_task_modal());
	}

	open_new_task_modal() {
		const me = this;
		const tipos = [
			"Impuestos", "N\u00f3mina", "Cierre Contable", "Auditor\u00eda", "Conciliaci\u00f3n Bancaria",
			"Declaraci\u00f3n DGI", "Estados Financieros", "Facturaci\u00f3n",
			"Atenci\u00f3n a Requerimiento", "Tr\u00e1mite DGI", "Consultor\u00eda", "Otro",
		];

		const dialog = new frappe.ui.Dialog({
			title: "Nueva Tarea",
			size: "large",
			fields: [
				{ fieldtype: "Select", fieldname: "tipo_de_tarea", label: "Tipo de Tarea", options: tipos.join("\n"), reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Link", fieldname: "cliente", label: "Cliente", options: "Cliente Contable", reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Link", fieldname: "periodo", label: "Periodo", options: "Periodo Contable", reqd: 1 },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Date", fieldname: "fecha_de_vencimiento", label: "Fecha de Vencimiento", reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Link", fieldname: "asignado_a", label: "Asignado a", options: "User" },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Small Text", fieldname: "notas", label: "Notas" },
			],
			primary_action_label: "Crear Tarea",
			primary_action: (values) => {
				frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "Tarea Contable",
							cliente: values.cliente,
							periodo: values.periodo,
							tipo_de_tarea: values.tipo_de_tarea,
							estado: "Pendiente",
							fecha_de_vencimiento: values.fecha_de_vencimiento,
							asignado_a: values.asignado_a || null,
							notas: values.notas || "",
						}
					},
					freeze: true,
					freeze_message: "Creando tarea...",
					callback: (r) => {
						if (!r.exc) {
							frappe.show_alert({ message: "Tarea creada exitosamente", indicator: "green" });
							dialog.hide();
							me.load_data();
						}
					},
					error: () => {
						frappe.msgprint("Error al crear la tarea.");
					}
				});
			},
			secondary_action_label: "Cancelar",
			secondary_action: () => dialog.hide(),
		});

		dialog.show();
	}
}
