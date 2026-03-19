import frappe
from frappe.tests import IntegrationTestCase

from gestion_contable.gestion_contable.utils.finance import build_invoice_summary


class TestFinanceUtils(IntegrationTestCase):
    def test_build_invoice_summary_calcula_aging_y_cobranza(self):
        invoices = [
            frappe._dict(
                name="SINV-001",
                grand_total=1000,
                outstanding_amount=400,
                posting_date="2026-01-01",
                due_date="2026-01-15",
            ),
            frappe._dict(
                name="SINV-002",
                grand_total=500,
                outstanding_amount=0,
                posting_date="2026-02-01",
                due_date="2026-02-15",
            ),
            frappe._dict(
                name="SINV-003",
                grand_total=300,
                outstanding_amount=300,
                posting_date="2026-03-01",
                due_date="2026-03-25",
            ),
        ]

        summary = build_invoice_summary(invoices, today="2026-03-31")

        self.assertEqual(summary["facturas_emitidas"], 3)
        self.assertEqual(summary["facturas_abiertas"], 2)
        self.assertEqual(summary["facturas_vencidas"], 2)
        self.assertEqual(summary["ingreso_facturado"], 1800)
        self.assertEqual(summary["cobrado_total"], 1100)
        self.assertEqual(summary["saldo_por_cobrar"], 700)
        self.assertEqual(summary["cartera_vencida"], 700)
        self.assertEqual(summary["aging_31_60"], 400)
        self.assertEqual(summary["aging_0_30"], 300)
        self.assertEqual(summary["aging_current"], 0)
