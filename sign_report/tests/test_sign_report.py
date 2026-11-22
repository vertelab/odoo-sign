import base64

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignReport(TransactionCase):
    """A sign template that takes its document from a QWeb report.

    The point of sign_report is that `data` is regenerated from the report at
    request time, so the template itself does not carry the PDF.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["sign.oca.template"].create(
            {
                "name": "Order report template",
                "model_id": cls.env.ref("sale.model_sale_order").id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Report Customer"})
        cls.order = cls.env["sale.order"].create({"partner_id": cls.partner.id})

    def test_template_has_a_report_field(self):
        """The field sign_report adds is present on sign.oca.template."""
        self.assertIn("report_template", self.env["sign.oca.template"]._fields)

    def test_without_report_the_template_data_is_used(self):
        """No report configured: get_report_data returns the template's own data."""
        self.template.data = base64.b64encode(b"template payload")
        self.assertEqual(self.template.get_report_data(self.order), self.template.data)

    def _rendered(self):
        """The document get_report_data produces for the order.

        Without wkhtmltopdf Odoo falls back to returning the report HTML, so
        the test asserts the document comes from the report, not that it is a
        PDF -- the latter would test the machine, not the module.
        """
        return base64.b64decode(self.template.get_report_data(self.order))

    def test_with_report_the_document_is_rendered_from_the_record(self):
        """A configured report replaces the template data with the rendered report."""
        self.template.data = base64.b64encode(b"template payload")
        self.template.report_template = self.env.ref("sale.action_report_saleorder")
        rendered = self._rendered()
        self.assertTrue(rendered)
        self.assertNotEqual(rendered, b"template payload")
        self.assertIn(self.order.name.encode(), rendered)

    def test_request_vals_carry_the_rendered_document(self):
        """The request built from a record gets the rendered report, not the template data."""
        self.template.report_template = self.env.ref("sale.action_report_saleorder")
        vals = self.template._prepare_sign_oca_request_vals_from_record(self.order)
        self.assertEqual(vals["template_id"], self.template.id)
        self.assertEqual(vals["record_ref"], f"sale.order,{self.order.id}")
        self.assertEqual(base64.b64decode(vals["data"]), self._rendered())
