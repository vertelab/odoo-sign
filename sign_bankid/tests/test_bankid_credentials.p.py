import base64
import os

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.sign_bankid.models.bankid_credentials import BankIDCredentials


@tagged("post_install", "-at_install")
class TestBankIDCredentials(TransactionCase):
    """The credential handover to pybankid.

    BankIDClient needs file paths, so the provider materialises the uploaded
    Binary fields into a temporary directory. That directory must be private,
    removed afterwards, and never silently replaced by the bundled test
    certificate when a real one was uploaded.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["sign.provider"].search([("code", "=", "bankid")], limit=1)

    def test_bankid_provider_exists(self):
        """sign_bankid's data file adds the provider and names its module."""
        self.assertTrue(self.provider, "sign_bankid must define the bankid provider")
        self.assertEqual(self.provider.module_state, "installed")

    def test_test_server_unless_enabled(self):
        """A provider that is not enabled talks to the BankID test server."""
        self.provider.state = "test"
        self.assertTrue(self.provider._bankid_test_server())
        self.provider.state = "enabled"
        self.assertFalse(self.provider._bankid_test_server())

    def test_uploaded_certificates_become_private_files(self):
        """Uploaded PEM files are written 0600 in a directory that is removed on exit."""
        cert = base64.b64encode(b"-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")
        key = base64.b64encode(b"-----BEGIN PRIVATE KEY-----\nMIIB\n-----END PRIVATE KEY-----\n")

        with BankIDCredentials(cert_binary=cert, key_binary=key) as (cert_path, key_path):
            self.assertTrue(os.path.isfile(cert_path))
            self.assertTrue(os.path.isfile(key_path))
            self.assertEqual(os.stat(cert_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(key_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(os.path.dirname(cert_path)).st_mode & 0o777, 0o700)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))

    def test_corrupt_upload_fails_instead_of_falling_back(self):
        """A corrupt upload must not be silently replaced by test credentials."""
        with self.assertRaises(UserError):
            with BankIDCredentials(cert_binary=b"not base64!", key_binary=b"also not!"):
                pass

    def test_half_upload_fails(self):
        """Certificate without key is an error, not a test-certificate fallback."""
        cert = base64.b64encode(b"-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")
        with self.assertRaises(UserError):
            with BankIDCredentials(cert_binary=cert, key_binary=False):
                pass

    def test_enabled_provider_refuses_bundled_test_certificate(self):
        """A production provider with no upload cannot sign with test credentials."""
        with self.assertRaises(UserError):
            with BankIDCredentials(allow_test_fallback=False):
                pass

    def test_bundled_test_certificate_is_used_when_allowed(self):
        """Without an upload the bundled pybankid test certificate is used, flagged as such."""
        credentials = BankIDCredentials(allow_test_fallback=True)
        with credentials as (cert_path, key_path):
            self.assertTrue(os.path.isfile(cert_path))
            self.assertTrue(os.path.isfile(key_path))
        self.assertTrue(credentials.using_bundled_test_cert)
        self.assertIsNone(credentials._tmpdir)
