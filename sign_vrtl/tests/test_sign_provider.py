from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSignProvider(TransactionCase):
    """The provider framework: dispatch from a provider code to a method.

    Every provider module (sign_bankid, sign_scrive, sign_criipto) hangs on
    `sign.provider` and its dispatch, so the dispatch is what this test pins.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["sign.provider"].create(
            {"name": "Test Provider", "code": "internal"}
        )

    def test_dispatch_finds_provider_method(self):
        """prepare_signing_request calls prepare_<code>_request when it exists.

        sign_scrive implements prepare_scrive_request, so its provider is the
        real proof of the dispatch -- no patching needed.
        """
        provider = self.env["sign.provider"].search([("code", "=", "scrive")], limit=1)
        if not provider:
            self.skipTest("sign_scrive is not installed in this database")
        sign_request = self.env["vrtl.sign.request"].new({"name": "Avtal 1"})
        self.assertEqual(
            provider.prepare_signing_request(sign_request),
            {"document_name": "Avtal 1.pdf"},
        )

    def test_dispatch_without_provider_method_returns_empty(self):
        """A provider that implements nothing prepares an empty payload."""
        self.assertEqual(
            self.provider.prepare_signing_request(self.env["vrtl.sign.request"]),
            {},
        )

    def test_dispatch_without_initiate_raises(self):
        """initiate_signature names the missing method instead of failing silently."""
        with self.assertRaises(NotImplementedError) as caught:
            self.provider.initiate_signature(self.env["vrtl.sign.request"], {})
        self.assertIn("initiate_internal_signature", str(caught.exception))

    def test_dispatch_without_callback_raises(self):
        """process_callback names the missing method instead of failing silently."""
        with self.assertRaises(NotImplementedError) as caught:
            self.provider.process_callback(self.env["vrtl.sign.request"], {})
        self.assertIn("process_internal_callback", str(caught.exception))

    def test_provider_declares_its_module(self):
        """module_state follows module_id, which is how the UI knows what to install."""
        module = self.env["ir.module.module"].search([("name", "=", "sign_vrtl")])
        self.assertEqual(module.state, "installed")
        self.provider.module_id = module
        self.assertEqual(self.provider.module_state, "installed")
