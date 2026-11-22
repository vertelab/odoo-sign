from unittest.mock import MagicMock, patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestScriveProvider(TransactionCase):
    """The Scrive provider: its code, its auth header and its OAuth check.

    Nothing here calls Scrive — `requests` is patched, so the test proves the
    provider is wired into `sign.provider` and that the request it builds is
    the one Scrive expects.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["sign.provider"].search([("code", "=", "scrive")], limit=1)

    def test_scrive_provider_exists(self):
        """sign_scrive's data file adds the provider and names its module."""
        self.assertTrue(self.provider, "sign_scrive must define the scrive provider")
        self.assertEqual(self.provider.module_state, "installed")

    def test_auth_header_requires_all_four_secrets(self):
        """Without tokens the provider refuses to build a header."""
        self.provider.write(
            {
                "scrive_api_token": "token",
                "scrive_access_token": "access",
                "scrive_api_secret": False,
                "scrive_access_secret": "secret",
            }
        )
        self.assertFalse(self.provider._api_request_validation())
        with self.assertRaises(ValidationError):
            self.provider._build_request_headers()

    def test_auth_header_is_plaintext_oauth(self):
        """The header carries the four secrets URL-encoded, not concatenated raw."""
        self.provider.write(
            {
                "scrive_api_token": "token",
                "scrive_access_token": "access",
                "scrive_api_secret": "api secret",
                "scrive_access_secret": "access secret",
            }
        )
        self.assertTrue(self.provider._api_request_validation())
        header = self.provider._build_request_headers()["Authorization"]
        self.assertIn('oauth_signature_method="PLAINTEXT"', header)
        self.assertIn('oauth_consumer_key="token"', header)
        self.assertIn('oauth_token="access"', header)
        self.assertIn('oauth_signature="api%20secret&access%20secret"', header)

    def test_prepare_scrive_request_names_the_document(self):
        """The provider dispatches to prepare_scrive_request with the request name."""
        sign_request = self.env["vrtl.sign.request"].new({"name": "Avtal 42"})
        self.assertEqual(
            self.provider.prepare_signing_request(sign_request),
            {"document_name": "Avtal 42.pdf"},
        )

    def test_parties_are_built_per_signer(self):
        """Each signer becomes one Scrive party, in signer order."""
        partner_a = self.env["res.partner"].create({"name": "Anna", "email": "anna@example.com"})
        partner_b = self.env["res.partner"].create({"name": "Bert", "email": "bert@example.com"})
        sign_request = self.env["vrtl.sign.request"].create(
            {
                "name": "Avtal 43",
                "data": b"JVBERi0xLjQK",
                "signer_ids": [
                    (0, 0, {"partner_id": partner_a.id, "role": "customer"}),
                    (0, 0, {"partner_id": partner_b.id, "role": "witness"}),
                ],
            }
        )
        parties = self.provider._prepare_scrive_parties(sign_request)
        self.assertEqual([party["sign_order"] for party in parties], [1, 2])
        self.assertEqual(
            [field["value"] for field in parties[0]["fields"] if field["type"] == "name"],
            ["Anna"],
        )
        self.assertEqual(
            [field["value"] for field in parties[1]["fields"] if field["type"] == "email"],
            ["bert@example.com"],
        )

    def test_callback_url_joins_the_controller_route(self):
        """The callback URL is the controller's route on top of web.base.url."""
        self.env["ir.config_parameter"].sudo().set_param("web.base.url", "https://example.com")
        self.assertEqual(
            self.provider._get_scrive_callback_url(),
            "https://example.com/sign/scrive/callback",
        )

    def test_initiate_scrive_signature_creates_updates_and_starts(self):
        """initiate_scrive_signature drives create -> update -> start, in that order."""
        partner = self.env["res.partner"].create({"name": "Cissi", "email": "cissi@example.com"})
        sign_request = self.env["vrtl.sign.request"].create(
            {
                "name": "Avtal 44",
                "data": b"JVBERi0xLjQK",
                "signer_ids": [(0, 0, {"partner_id": partner.id, "role": "customer"})],
            }
        )
        self.provider.write(
            {
                "scrive_api_url": "https://api.scrive.example",
                "scrive_api_token": "token",
                "scrive_access_token": "access",
                "scrive_api_secret": "secret",
                "scrive_access_secret": "secret2",
            }
        )

        def response(json_payload):
            answer = MagicMock()
            answer.status_code = 200
            answer.json.return_value = json_payload
            answer.text = ""
            return answer

        with patch("odoo.addons.sign_scrive.models.scrive_sign_provider.requests") as requests:
            requests.post.side_effect = [
                response({"id": "doc-1"}),  # documents/new
                response({"parties": [{"id": "party-1"}]}),  # documents/update
                response({}),  # documents/start
            ]
            result = self.provider.initiate_scrive_signature(
                sign_request, self.provider.prepare_scrive_request(sign_request)
            )

        self.assertEqual(result, {"scrive_document_id": "doc-1", "status": "initiated"})
        self.assertEqual(sign_request.scrive_document_id, "doc-1")
        self.assertEqual(sign_request.scrive_signatory_id, "party-1")
        self.assertEqual(
            [call.args[0] for call in requests.post.call_args_list],
            [
                "https://api.scrive.example/api/v2/documents/new",
                "https://api.scrive.example/api/v2/documents/doc-1/update",
                "https://api.scrive.example/api/v2/documents/doc-1/start",
            ],
        )
