import frappe

from gestion_contable.gestion_contable.doctype.entregable_cliente.entregable_cliente import has_website_permission as entregable_has_website_permission
from gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente import has_website_permission as requerimiento_has_website_permission
from gestion_contable.gestion_contable.portal.cliente import (
    get_portal_cliente_for_user,
    get_portal_dashboard_context,
    get_portal_entregables_context,
    get_portal_requerimientos_context,
    portal_user_has_cliente_access,
)
from gestion_contable.gestion_contable.tests.base import GestionContableIntegrationTestCase


class TestPortalCliente(GestionContableIntegrationTestCase):
    def test_usuario_portal_resuelve_cliente_y_dashboard(self):
        portal_user = self.create_user("portal_cliente@test.local", "Portal", "Cliente", role="Contador del Despacho")
        cliente = self.create_cliente(
            "TEST-PORTAL-CLIENTE",
            company_default=self.company,
            portal_habilitado=1,
            usuario_portal_principal=portal_user.name,
            correo_electronico=portal_user.name,
        )
        self.create_periodo(cliente.name, mes="Octubre")

        frappe.set_user(portal_user.name)
        resolved = get_portal_cliente_for_user()
        dashboard = get_portal_dashboard_context()

        self.assertEqual(resolved.name, cliente.name)
        self.assertEqual(dashboard["cliente"].name, cliente.name)
        self.assertIn("summary", dashboard)
        self.assertEqual(dashboard["nav_items"][0]["route"], "/portal-cliente")

    def test_contextos_portal_publicados_coinciden_con_las_rutas_del_menu(self):
        portal_user = self.create_user("portal_rutas@test.local", "Portal", "Rutas", role="Contador del Despacho")
        cliente = self.create_cliente(
            "TEST-PORTAL-RUTAS",
            company_default=self.company,
            portal_habilitado=1,
            usuario_portal_principal=portal_user.name,
            correo_electronico=portal_user.name,
        )
        periodo = self.create_periodo(cliente.name, mes="Noviembre")

        requerimiento = frappe.get_doc(
            {
                "doctype": "Requerimiento Cliente",
                "nombre_del_requerimiento": "Req Portal Rutas",
                "cliente": cliente.name,
                "company": self.company,
                "periodo": periodo.name,
                "fecha_solicitud": "2026-11-05",
                "fecha_vencimiento": "2026-11-10",
                "canal_envio": "Portal",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Requerimiento Cliente", requerimiento.name)

        entregable = frappe.get_doc(
            {
                "doctype": "Entregable Cliente",
                "requerimiento_cliente": requerimiento.name,
                "tipo_entregable": "Estado de cuenta",
                "descripcion": "Carga de documento soporte",
                "fecha_compromiso": "2026-11-10",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Entregable Cliente", entregable.name)

        frappe.set_user(portal_user.name)
        req_context = get_portal_requerimientos_context()
        ent_context = get_portal_entregables_context()

        self.assertEqual(req_context["cliente"].name, cliente.name)
        self.assertEqual(ent_context["cliente"].name, cliente.name)
        self.assertTrue(any(row.name == requerimiento.name for row in req_context["requerimientos"]))
        self.assertTrue(any(row.name == entregable.name for row in ent_context["entregables"]))
        self.assertTrue(any(item["route"] == "/requerimientos-cliente" and item["active"] for item in req_context["nav_items"]))
        self.assertTrue(any(item["route"] == "/entregables-cliente" and item["active"] for item in ent_context["nav_items"]))

    def test_permisos_web_usan_el_mismo_resolvedor_que_el_portal(self):
        portal_user = self.create_user("portal_permiso@test.local", "Portal", "Permiso", role="Contador del Despacho")
        other_user = self.create_user("otro_permiso@test.local", "Otro", "Usuario", role="Contador del Despacho")
        cliente = self.create_cliente(
            "TEST-PORTAL-PERMISO",
            company_default=self.company,
            portal_habilitado=1,
            usuario_portal_principal=portal_user.name,
            correo_electronico=portal_user.name,
        )
        periodo = self.create_periodo(cliente.name, mes="Diciembre")

        requerimiento = frappe.get_doc(
            {
                "doctype": "Requerimiento Cliente",
                "nombre_del_requerimiento": "Req Portal Permiso",
                "cliente": cliente.name,
                "company": self.company,
                "periodo": periodo.name,
                "fecha_solicitud": "2026-12-05",
                "fecha_vencimiento": "2026-12-10",
                "canal_envio": "Portal",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Requerimiento Cliente", requerimiento.name)

        entregable = frappe.get_doc(
            {
                "doctype": "Entregable Cliente",
                "requerimiento_cliente": requerimiento.name,
                "tipo_entregable": "Confirmacion",
                "descripcion": "Respuesta del cliente",
                "fecha_compromiso": "2026-12-10",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Entregable Cliente", entregable.name)

        self.assertTrue(portal_user_has_cliente_access(cliente.name, portal_user.name))
        self.assertTrue(requerimiento_has_website_permission(requerimiento, "read", portal_user.name))
        self.assertTrue(entregable_has_website_permission(entregable, "read", portal_user.name))
        self.assertFalse(requerimiento_has_website_permission(requerimiento, "read", other_user.name))
        self.assertFalse(entregable_has_website_permission(entregable, "read", other_user.name))
