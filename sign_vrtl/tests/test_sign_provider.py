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
        """prepare_signing_request calls prepare_<code>_request when it exists."""
        provider = self.provider

        def prepare_internal_request(sign_request):
            return {"document_name": "test.pdf"}

        self.patch(type(provider), "prepare_internal_request", prepare_internal_request)
        self.assertEqual(
            provider.prepare_signing_request(self.env["vrtl.sign.request"]),
            {"document_name": "test.pdf"},
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
        provider = self.env["sign.provider"].search(
            [("module_id", "=", self.env.ref("base.module_sign_vrtl").id)], limit=1
        )
        self.assertTrue(provider)
        self.assertEqual(provider.module_state, "installed")
