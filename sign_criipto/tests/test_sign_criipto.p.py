from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignCriipto(TransactionCase):
    """Criipto as a signing option on the sign template.

    sign_criipto adds the option to the template and the credentials to the
    company. Nothing here talks to Criipto — the client is patched.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["sign.oca.template"].create(
            {"name": "Criipto template", "model_id": cls.env.ref("sale.model_sale_order").id}
        )

    def test_criipto_is_a_signing_option_on_the_template(self):
        """sign_criipto extends the signing_option selection with criipto."""
        selection = dict(self.env["sign.oca.template"]._fields["signing_option"].selection)
        self.assertIn("criipto", selection)
        self.template.signing_option = "criipto"
        self.assertEqual(self.template.signing_option, "criipto")

    def test_company_client_requires_credentials(self):
        """Without client id and secret the client is refused, not half-built."""
        self.env.company.write(
            {"criipto_client_id": False, "criipto_client_secret": False}
        )
        with self.assertRaises(UserError):
            self.env.company.get_criipto_client()

    def test_company_client_uses_the_stored_credentials(self):
        """The client is built from the company's own credentials."""
        self.env.company.write(
            {"criipto_client_id": "client-id", "criipto_client_secret": "client-secret"}
        )
        with patch(
            "odoo.addons.sign_criipto.models.res_company.CriiptoSignatures"
        ) as client_class:
            client = self.env.company.get_criipto_client()
        client_class.assert_called_once_with(
            client_id="client-id", client_secret="client-secret"
        )
        self.assertEqual(client, client_class.return_value)

    def test_sale_order_has_the_signature_order_field(self):
        """The order records the Criipto signature order it created."""
        self.assertIn("criipto_signature_order_id", self.env["sale.order"]._fields)
