import frappe

from gestion_contable.gestion_contable.doctype.entregable_cliente.entregable_cliente import has_website_permission as entregable_has_website_permission
from gestion_contable.gestion_contable.doctype.requerimiento_cliente.requerimiento_cliente import has_website_permission as requerimiento_has_website_permission
from gestion_contable.gestion_contable.portal.cliente import (
    get_portal_cliente_for_user,
    get_portal_dashboard_context,
    get_portal_entregables_context,
    get_portal_requerimientos_context,
    portal_user_has_cliente_access,
    registrar_carga_entregable_portal,
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

    def test_carga_portal_crea_documento_y_actualiza_version_eeff(self):
        portal_user = self.create_user("portal_upload@test.local", "Portal", "Upload", role="Contador del Despacho")
        cliente = self.create_cliente(
            "TEST-PORTAL-UPLOAD",
            company_default=self.company,
            portal_habilitado=1,
            permite_carga_documentos=1,
            usuario_portal_principal=portal_user.name,
            correo_electronico=portal_user.name,
        )
        periodo = self.create_periodo(cliente.name, mes="Enero", anio=2027)

        requerimiento = frappe.get_doc(
            {
                "doctype": "Requerimiento Cliente",
                "nombre_del_requerimiento": "Revision EEFF Cliente",
                "cliente": cliente.name,
                "company": self.company,
                "periodo": periodo.name,
                "fecha_solicitud": "2027-01-05",
                "fecha_vencimiento": "2027-01-10",
                "canal_envio": "Portal",
                "fecha_envio": "2027-01-05 08:00:00",
                "estado_requerimiento": "Enviado",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Requerimiento Cliente", requerimiento.name)

        entregable = frappe.get_doc(
            {
                "doctype": "Entregable Cliente",
                "requerimiento_cliente": requerimiento.name,
                "tipo_entregable": "Word revisado",
                "descripcion": "Devolucion del documento con comentarios",
                "fecha_compromiso": "2027-01-10",
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Entregable Cliente", entregable.name)

        paquete = frappe.get_doc(
            {
                "doctype": "Paquete Estados Financieros Cliente",
                "cliente": cliente.name,
                "periodo_contable": periodo.name,
                "fecha_corte": "2027-01-31",
                "tipo_paquete": "Para Auditoria",
                "version": 1,
                "versiones_documento_eeff": [
                    {
                        "tipo_documento": "Word Revision Cliente",
                        "version_documento": 1,
                        "estado_documento": "Enviado a Cliente",
                        "es_version_vigente": 1,
                        "requerimiento_cliente": requerimiento.name,
                        "entregable_cliente": entregable.name,
                        "fecha_envio_cliente": "2027-01-06 09:00:00",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.track_doc("Paquete Estados Financieros Cliente", paquete.name)
        version_name = paquete.versiones_documento_eeff[0].name

        frappe.set_user(portal_user.name)
        result = registrar_carga_entregable_portal(
            entregable.name,
            file_name="revision-cliente.txt",
            content=b"comentarios del cliente",
            titulo_documento="Revision cliente EEFF",
            tipo_documental="Correspondencia",
            version_documento_name=version_name,
        )

        self.assertTrue(result["ok"])
        documento = frappe.get_doc("Documento Contable", result["documento_contable"])
        self.track_doc("Documento Contable", documento.name)
        file_name = frappe.db.get_value("File", {"attached_to_doctype": "Documento Contable", "attached_to_name": documento.name}, "name")
        if file_name:
            self.track_doc("File", file_name)

        entregable.reload()
        paquete.reload()
        version_row = next(row for row in paquete.versiones_documento_eeff if row.name == version_name)

        self.assertEqual(entregable.documento_contable, documento.name)
        self.assertEqual(entregable.estado_entregable, "Recibido")
        self.assertEqual(version_row.estado_documento, "Comentado por Cliente")
        self.assertEqual(version_row.documento_revision_cliente, documento.name)
