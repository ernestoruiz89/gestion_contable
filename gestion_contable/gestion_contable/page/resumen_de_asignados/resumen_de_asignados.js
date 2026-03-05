frappe.pages['resumen-de-asignados'].on_page_load = function (wrapper) {
    new ResumenAsignados(wrapper);
}

class ResumenAsignados {
    constructor(wrapper) {
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: 'Resumen de Asignados',
            single_column: true
        });
        this.wrapper = $(wrapper).find('.layout-main-section');
        this.setup_styles();
        this.render_shell();
        this.bind_events();
        this.load_data();
    }

    setup_styles() {
        if ($('#ra-styles').length) return;

        const css = `
			.ra-container {
				padding: 20px;
				background: #f8fafc;
				min-height: calc(100vh - 200px);
				border-radius: 12px;
			}
			
			.ra-hero {
				display: flex;
				justify-content: space-between;
				align-items: center;
				margin-bottom: 24px;
				padding: 24px;
				background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
				border-radius: 12px;
				color: white;
				box-shadow: 0 4px 15px rgba(15, 23, 42, 0.1);
			}
			
			.ra-hero h2 {
				margin: 0;
				font-size: 24px;
				font-weight: 700;
				color: #f8fafc;
			}
			
			.ra-hero p {
				margin: 5px 0 0 0;
				color: #94a3b8;
				font-size: 14px;
			}
			
			.ra-btn-refresh {
				background: rgba(255,255,255,0.1);
				border: 1px solid rgba(255,255,255,0.2);
				color: white;
				padding: 8px 16px;
				border-radius: 8px;
				cursor: pointer;
				font-weight: 600;
				transition: all 0.2s;
			}
			
			.ra-btn-refresh:hover {
				background: rgba(255,255,255,0.2);
			}

			.ra-search-wrapper {
				display: flex;
				align-items: center;
				gap: 12px;
			}
			
			.ra-search-input {
				padding: 8px 12px;
				border-radius: 8px;
				border: 1px solid rgba(255,255,255,0.3);
				background: rgba(255,255,255,0.1);
				color: white;
				width: 250px;
				outline: none;
				transition: border-color 0.2s, background 0.2s;
			}
			
			.ra-search-input::placeholder {
				color: rgba(255,255,255,0.6);
			}
			
			.ra-search-input:focus {
				border-color: rgba(255,255,255,0.8);
				background: rgba(255,255,255,0.15);
			}

			.ra-list {
				display: flex;
				flex-direction: column;
				gap: 12px;
			}

			.ra-list-item {
				background: white;
				border-radius: 12px;
				padding: 16px 20px;
				box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
				border: 1px solid #e2e8f0;
				display: flex;
				align-items: center;
				justify-content: space-between;
				transition: transform 0.2s, box-shadow 0.2s;
			}
			
			.ra-list-item:hover {
				transform: translateY(-1px);
				box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
			}

			.ra-user-section {
				display: flex;
				align-items: center;
				min-width: 280px;
			}

			.ra-avatar {
				width: 44px;
				height: 44px;
				border-radius: 10px;
				color: #4338ca;
				display: flex;
				align-items: center;
				justify-content: center;
				font-size: 18px;
				font-weight: bold;
				margin-right: 16px;
				flex-shrink: 0;
				background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
			}

			.ra-user-info h3 {
				margin: 0;
				font-size: 15px;
				font-weight: 700;
				color: #0f172a;
			}

			.ra-user-info p {
				margin: 2px 0 0 0;
				font-size: 12px;
				color: #64748b;
			}

			.ra-stats-list {
				display: flex;
				gap: 10px;
				flex: 1;
				justify-content: flex-end;
			}

			.ra-stat-item {
				background: #f8fafc;
				padding: 10px 16px;
				border-radius: 8px;
				text-align: center;
				min-width: 90px;
				cursor: pointer;
				border: 1px solid transparent;
				transition: all 0.2s;
			}
			
			.ra-stat-item:hover {
				background: #f1f5f9;
				transform: translateY(-2px);
				box-shadow: 0 2px 6px rgba(0,0,0,0.05);
			}

			.ra-stat-value {
				font-size: 20px;
				font-weight: 800;
				color: #1e293b;
				line-height: 1;
				margin-bottom: 4px;
			}

			.ra-stat-label {
				font-size: 10px;
				font-weight: 600;
				text-transform: uppercase;
				color: #64748b;
				letter-spacing: 0.5px;
			}

			/* Specific stat colors */
			.ra-stat-item.ra-stat-totales:hover { border-color: #93c5fd; }
			.ra-stat-item.ra-stat-totales .ra-stat-value { color: #3b82f6; }
			
			.ra-stat-item.ra-stat-pendientes:hover { border-color: #fbd38d; }
			.ra-stat-item.ra-stat-pendientes .ra-stat-value { color: #f59e0b; }
			
			.ra-stat-item.ra-stat-proceso:hover { border-color: #93c5fd; }
			.ra-stat-item.ra-stat-proceso .ra-stat-value { color: #2563eb; }
			
			.ra-stat-item.ra-stat-revision:hover { border-color: #c4b5fd; }
			.ra-stat-item.ra-stat-revision .ra-stat-value { color: #8b5cf6; }
			
			.ra-stat-item.ra-stat-completadas { background: #ecfdf5; border: 1px solid #d1fae5; }
			.ra-stat-item.ra-stat-completadas:hover { background: #d1fae5; border-color: #6ee7b7; }
			.ra-stat-item.ra-stat-completadas .ra-stat-value { color: #10b981; }
			
			.ra-stat-item.ra-stat-atrasadas { background: #fef2f2; border: 1px solid #fee2e2; }
			.ra-stat-item.ra-stat-atrasadas:hover { background: #fee2e2; border-color: #fca5a5; }
			.ra-stat-item.ra-stat-atrasadas .ra-stat-value { color: #ef4444; }
			
			.ra-empty-state {
				text-align: center;
				padding: 40px;
				color: #64748b;
				background: white;
				border-radius: 12px;
				border: 1px dashed #cbd5e1;
			}
		`;

        $('<style id="ra-styles">').prop('type', 'text/css').html(css).appendTo('head');
    }

    render_shell() {
        this.wrapper.html(`
			<div class="ra-container">
				<div class="ra-hero">
					<div>
						<h2>Dashboard de Asignados</h2>
						<p>Métricas y estado de tareas por miembro del equipo</p>
					</div>
					<div class="ra-search-wrapper">
						<input type="text" class="ra-search-input" placeholder="Buscar por nombre..." id="ra-search-input">
						<button class="ra-btn-refresh">Actualizar Datos</button>
					</div>
				</div>
				<div class="ra-list" id="ra-users-list">
					<!-- List items will be injected here -->
				</div>
			</div>
		`);
    }

    bind_events() {
        this.wrapper.find('.ra-btn-refresh').on('click', () => {
            this.load_data();
        });

        this.wrapper.find('#ra-search-input').on('input', (e) => {
            const searchTerm = $(e.currentTarget).val().toLowerCase();
            this.filter_list(searchTerm);
        });
    }

    get_initials(name) {
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    }

    load_data() {
        const list = this.wrapper.find('#ra-users-list');
        list.html('<div class="ra-empty-state">Cargando métricas...</div>');

        frappe.call({
            method: 'gestion_contable.gestion_contable.page.resumen_de_asignados.resumen_de_asignados.get_user_stats',
            callback: (r) => {
                if (r.message) {
                    this.users_data = r.message;
                    this.render_list(this.users_data);
                } else {
                    list.html('<div class="ra-empty-state">No se encontraron usuarios asignados.</div>');
                }
            }
        });
    }

    filter_list(term) {
        if (!this.users_data) return;
        if (!term) {
            this.render_list(this.users_data);
            return;
        }

        const filtered = this.users_data.filter(u => u.full_name.toLowerCase().includes(term));
        this.render_list(filtered);
    }

    render_list(users) {
        const list = this.wrapper.find('#ra-users-list');
        list.empty();

        if (users.length === 0) {
            list.html('<div class="ra-empty-state">No se encontraron usuarios activos con esos criterios.</div>');
            return;
        }

        users.forEach(user => {
            const initials = this.get_initials(user.full_name);
            const email = user.name;
            const rowStyle = user.atrasadas > 0 ? "box-shadow: 0 0 0 1px #fecaca, 0 2px 8px rgba(239, 68, 68, 0.05);" : "";

            const row = $(`
				<div class="ra-list-item" style="${rowStyle}">
					<div class="ra-user-section">
						<div class="ra-avatar">${initials}</div>
						<div class="ra-user-info">
							<h3>${frappe.utils.escape_html(user.full_name)}</h3>
							<p>${frappe.utils.escape_html(email)}</p>
						</div>
					</div>
					<div class="ra-stats-list">
						<div class="ra-stat-item ra-stat-totales" title="Ir a todas las tareas">
							<div class="ra-stat-value">${user.totales}</div>
							<div class="ra-stat-label">Totales</div>
						</div>
						<div class="ra-stat-item ra-stat-pendientes" title="Ir a Pendientes">
							<div class="ra-stat-value">${user.pendientes}</div>
							<div class="ra-stat-label">Pends.</div>
						</div>
						<div class="ra-stat-item ra-stat-proceso" title="Ir a En Proceso">
							<div class="ra-stat-value">${user.en_proceso}</div>
							<div class="ra-stat-label">Proceso</div>
						</div>
						<div class="ra-stat-item ra-stat-revision" title="Ir a En Revisión">
							<div class="ra-stat-value">${user.en_revision}</div>
							<div class="ra-stat-label">Revisión</div>
						</div>
						<div class="ra-stat-item ra-stat-completadas" title="Ir a Completadas">
							<div class="ra-stat-value">${user.completadas}</div>
							<div class="ra-stat-label">Hechas</div>
						</div>
						<div class="ra-stat-item ra-stat-atrasadas" title="Ir a Atrasadas">
							<div class="ra-stat-value">${user.atrasadas}</div>
							<div class="ra-stat-label">Atrasadas</div>
						</div>
					</div>
				</div>
			`);

            // Binding click events for each specific stat block to route to pre-filtered Panel de Tareas
            row.find('.ra-stat-totales').on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name });
            });
            row.find('.ra-stat-pendientes').on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name, estado: 'Pendiente' });
            });
            row.find('.ra-stat-proceso').on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name, estado: 'En Proceso' });
            });
            row.find('.ra-stat-revision').on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name, estado: 'En Revisión' });
            });
            row.find('.ra-stat-completadas').on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name, estado: 'Completada' });
            });
            row.find('.ra-stat-atrasadas').on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name, vencimiento: 'Vencidas' });
            });

            list.append(row);
        });
    }
}
