import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.doctype.periodo_contable.periodo_contable import get_default_company


class GestionContableIntegrationTestCase(IntegrationTestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self._cleanup = []
        self.company = get_default_company() or frappe.db.get_value("Company", {}, "name")
        if not self.company:
            self.skipTest("No hay Company configurada para ejecutar pruebas de Gestion Contable")
        self.default_currency = frappe.db.get_value("Company", self.company, "default_currency") or frappe.db.get_single_value("Global Defaults", "default_currency")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._cleanup):
            self._safe_delete(doctype, name)
        frappe.set_user(self.previous_user)

    def track_doc(self, doctype, name):
        self._cleanup.append((doctype, name))
        return name

    def create_user(self, email, first_name="Test", last_name="User", role="Contador del Despacho"):
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            "roles": [{"role": role}],
        }).insert(ignore_permissions=True)
        self.track_doc("User", user.name)
        return user

    def create_customer(self, customer_name):
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
        territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_group": customer_group,
            "customer_type": "Company",
            "territory": territory,
        }).insert(ignore_permissions=True)
        self.track_doc("Customer", customer.name)
        return customer

    def create_cliente(self, customer_name, **extra_fields):
        customer = self.create_customer(customer_name)
        payload = {
            "doctype": "Cliente Contable",
            "customer": customer.name,
            "estado": "Activo",
            "frecuencia_de_cierre": "Mensual",
        }
        payload.update(extra_fields)
        cliente = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Cliente Contable", cliente.name)
        return cliente

    def create_periodo(self, cliente_name, anio=2026, mes="Mayo", estado="Abierto"):
        periodo = frappe.get_doc({
            "doctype": "Periodo Contable",
            "cliente": cliente_name,
            "company": self.company,
            "anio": anio,
            "mes": mes,
            "estado": estado,
        }).insert(ignore_permissions=True)
        self.track_doc("Periodo Contable", periodo.name)
        return periodo

    def create_item(self, item_code, item_name=None):
        item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
        stock_uom = frappe.db.get_value("UOM", {}, "name") or "Nos"
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name or item_code,
            "item_group": item_group,
            "stock_uom": stock_uom,
            "is_stock_item": 0,
        }).insert(ignore_permissions=True)
        self.track_doc("Item", item.name)
        return item

    def create_servicio(self, nombre, item_horas=None, tipo_de_servicio="Consultoria", tarifa_hora=100, honorario_fijo=0, costo_interno_hora=40):
        item = item_horas or self.create_item(f"ITEM-{nombre}")
        servicio = frappe.get_doc({
            "doctype": "Servicio Contable",
            "nombre_del_servicio": nombre,
            "tipo_de_servicio": tipo_de_servicio,
            "item_horas": item.name,
            "item_honorario_fijo": item.name,
            "company": self.company,
            "moneda": self.default_currency,
            "tarifa_hora": tarifa_hora,
            "honorario_fijo": honorario_fijo,
            "costo_interno_hora": costo_interno_hora,
        }).insert(ignore_permissions=True)
        self.track_doc("Servicio Contable", servicio.name)
        return servicio

    def create_encargo(self, cliente_name, **extra_fields):
        payload = {
            "doctype": "Encargo Contable",
            "nombre_del_encargo": extra_fields.pop("nombre_del_encargo", f"Encargo Test {frappe.generate_hash(length=6)}"),
            "cliente": cliente_name,
        }
        payload.update(extra_fields)
        encargo = frappe.get_doc(payload).insert(ignore_permissions=True)
        if encargo.project:
            self.track_doc("Project", encargo.project)
        self.track_doc("Encargo Contable", encargo.name)
        return encargo

    def create_contrato(self, cliente_name, servicio_name, **extra_fields):
        payload = {
            "doctype": "Contrato Comercial",
            "cliente": cliente_name,
            "fecha_inicio": extra_fields.pop("fecha_inicio", "2026-01-01"),
            "alcances": extra_fields.pop("alcances", [
                {
                    "servicio_contable": servicio_name,
                    "descripcion": "Alcance base",
                    "activa": 1,
                    "periodicidad": "Mensual",
                    "modalidad_tarifa": "Fijo",
                    "honorario_fijo": 500,
                }
            ]),
        }
        payload.update(extra_fields)
        contrato = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Contrato Comercial", contrato.name)
        return contrato

    def create_expediente(self, encargo_name, **extra_fields):
        payload = {
            "doctype": "Expediente Auditoria",
            "nombre_del_expediente": extra_fields.pop("nombre_del_expediente", f"Expediente Test {frappe.generate_hash(length=6)}"),
            "encargo_contable": encargo_name,
        }
        payload.update(extra_fields)
        expediente = frappe.get_doc(payload).insert(ignore_permissions=True)
        self.track_doc("Expediente Auditoria", expediente.name)
        return expediente

    def _safe_delete(self, doctype, name):
        if name and frappe.db.exists(doctype, name):
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
