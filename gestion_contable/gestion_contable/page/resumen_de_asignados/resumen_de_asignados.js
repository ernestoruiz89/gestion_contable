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

			.ra-grid {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
				gap: 20px;
			}

			.ra-card {
				background: white;
				border-radius: 12px;
				padding: 20px;
				box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
				border: 1px solid #e2e8f0;
				transition: transform 0.2s, box-shadow 0.2s;
			}
			
			.ra-card:hover {
				transform: translateY(-2px);
				box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
			}

			.ra-card-header {
				display: flex;
				align-items: center;
				margin-bottom: 16px;
				padding-bottom: 16px;
				border-bottom: 1px solid #f1f5f9;
			}

			.ra-avatar {
				width: 48px;
				height: 48px;
				border-radius: 12px;
				background: #indigo-100;
				color: #4338ca;
				display: flex;
				align-items: center;
				justify-content: center;
				font-size: 20px;
				font-weight: bold;
				margin-right: 16px;
				background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
			}

			.ra-user-info h3 {
				margin: 0;
				font-size: 16px;
				font-weight: 700;
				color: #0f172a;
			}

			.ra-user-info p {
				margin: 2px 0 0 0;
				font-size: 12px;
				color: #64748b;
			}

			.ra-stats-grid {
				display: grid;
				grid-template-columns: repeat(3, 1fr);
				gap: 12px;
			}

			.ra-stat-item {
				background: #f8fafc;
				padding: 12px 8px;
				border-radius: 8px;
				text-align: center;
			}

			.ra-stat-value {
				font-size: 24px;
				font-weight: 800;
				color: #1e293b;
				line-height: 1;
				margin-bottom: 4px;
			}

			.ra-stat-label {
				font-size: 11px;
				font-weight: 600;
				text-transform: uppercase;
				color: #64748b;
				letter-spacing: 0.5px;
			}

			/* Specific stat colors */
			.ra-stat-item.ra-stat-totales .ra-stat-value { color: #3b82f6; }
			.ra-stat-item.ra-stat-pendientes .ra-stat-value { color: #f59e0b; }
			.ra-stat-item.ra-stat-proceso .ra-stat-value { color: #2563eb; }
			.ra-stat-item.ra-stat-revision .ra-stat-value { color: #8b5cf6; }
			.ra-stat-item.ra-stat-completadas { background: #ecfdf5; border: 1px solid #d1fae5; }
			.ra-stat-item.ra-stat-completadas .ra-stat-value { color: #10b981; }
			
			.ra-stat-item.ra-stat-atrasadas { background: #fef2f2; border: 1px solid #fee2e2; }
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
					<div>
						<button class="ra-btn-refresh">Actualizar Datos</button>
					</div>
				</div>
				<div class="ra-grid" id="ra-users-grid">
					<!-- Cards will be injected here -->
				</div>
			</div>
		`);
    }

    bind_events() {
        this.wrapper.find('.ra-btn-refresh').on('click', () => {
            this.load_data();
        });
    }

    get_initials(name) {
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    }

    load_data() {
        const grid = this.wrapper.find('#ra-users-grid');
        grid.html('<div class="ra-empty-state">Cargando métricas...</div>');

        frappe.call({
            method: 'gestion_contable.gestion_contable.page.resumen_de_asignados.resumen_de_asignados.get_user_stats',
            callback: (r) => {
                if (r.message) {
                    this.render_cards(r.message);
                } else {
                    grid.html('<div class="ra-empty-state">No se encontraron usuarios asignados.</div>');
                }
            }
        });
    }

    render_cards(users) {
        const grid = this.wrapper.find('#ra-users-grid');
        grid.empty();

        if (users.length === 0) {
            grid.html('<div class="ra-empty-state">No se encontraron usuarios activos con roles contables.</div>');
            return;
        }

        users.forEach(user => {
            const initials = this.get_initials(user.full_name);
            const email = user.name;

            // Si tiene atrasadas, agregamos un glow sutil
            const cardStyle = user.atrasadas > 0 ? "box-shadow: 0 0 0 1px #fecaca, 0 4px 6px -1px rgba(239, 68, 68, 0.1);" : "";

            const card = $(`
				<div class="ra-card" style="${cardStyle}">
					<div class="ra-card-header">
						<div class="ra-avatar">${initials}</div>
						<div class="ra-user-info">
							<h3>${frappe.utils.escape_html(user.full_name)}</h3>
							<p>${frappe.utils.escape_html(email)}</p>
						</div>
					</div>
					<div class="ra-stats-grid">
						<div class="ra-stat-item ra-stat-totales">
							<div class="ra-stat-value">${user.totales}</div>
							<div class="ra-stat-label">Totales</div>
						</div>
						<div class="ra-stat-item ra-stat-pendientes">
							<div class="ra-stat-value">${user.pendientes}</div>
							<div class="ra-stat-label">Pends.</div>
						</div>
						<div class="ra-stat-item ra-stat-proceso">
							<div class="ra-stat-value">${user.en_proceso}</div>
							<div class="ra-stat-label">Proceso</div>
						</div>
						<div class="ra-stat-item ra-stat-revision">
							<div class="ra-stat-value">${user.en_revision}</div>
							<div class="ra-stat-label">Revisión</div>
						</div>
						<div class="ra-stat-item ra-stat-completadas">
							<div class="ra-stat-value">${user.completadas}</div>
							<div class="ra-stat-label">Hechas</div>
						</div>
						<div class="ra-stat-item ra-stat-atrasadas">
							<div class="ra-stat-value">${user.atrasadas}</div>
							<div class="ra-stat-label">Atrasadas</div>
						</div>
					</div>
				</div>
			`);

            // Click en la tarjeta podría redirigir al panel de tareas filtrado por este usuario
            card.on('click', () => {
                frappe.set_route('panel-de-tareas', { asignado_a: user.name });
            });
            card.css('cursor', 'pointer');
            card.attr('title', 'Clic para ir al Panel de Tareas de este usuario');

            grid.append(card);
        });
    }
}
