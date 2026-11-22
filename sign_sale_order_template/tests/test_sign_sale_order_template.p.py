from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignSaleOrderTemplate(TransactionCase):
    """A quotation template that carries a sign template.

    Selecting the template on an order is what later lets the order build a
    sign request, so the copy from template to order is what this test pins.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sign_template = cls.env["sign.oca.template"].create(
            {"name": "Contract signature", "model_id": cls.env.ref("sale.model_sale_order").id}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Template Customer"})

    def test_sale_order_template_carries_a_sign_template(self):
        """The field sign_sale_order_template adds is present on sale.order.template."""
        self.assertIn("sign_template_id", self.env["sale.order.template"]._fields)
        quotation_template = self.env["sale.order.template"].create(
            {"name": "Standard", "sign_template_id": self.sign_template.id}
        )
        self.assertEqual(quotation_template.sign_template_id, self.sign_template)

    def test_order_reads_the_sign_template_through_its_quotation_template(self):
        """The order reaches the sign template via sale_order_template_id, not a copied field."""
        quotation_template = self.env["sale.order.template"].create(
            {"name": "Standard", "sign_template_id": self.sign_template.id}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "sale_order_template_id": quotation_template.id,
            }
        )
        self.assertEqual(order.sale_order_template_id.sign_template_id, self.sign_template)

    def test_generating_a_request_requires_a_quotation_template(self):
        """Without a quotation template there is no sign template to build from."""
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        with self.assertRaises(UserError):
            order.action_generate_sign_request()

    def test_sign_request_field_is_computed_from_record_ref(self):
        """sign_request_id finds the request whose record_ref points at the order."""
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertFalse(order.sign_request_id)
        request = self.env["sign.oca.request"].create(
            {
                "name": "Request for the order",
                "template_id": self.sign_template.id,
                "record_ref": f"sale.order,{order.id}",
                "data": b"JVBERi0xLjQK",
            }
        )
        order.invalidate_recordset(["sign_request_id"])
        self.assertEqual(order.sign_request_id, request)
        self.assertEqual(order.signed_doc, request.data)
