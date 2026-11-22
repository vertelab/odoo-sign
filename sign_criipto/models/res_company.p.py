import secrets
import base64
import logging
import urllib.parse
import requests
import werkzeug
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError
from ..criipto.main import CriiptoSignatures

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    criipto_domain = fields.Char(string="Criipto Domain")
    criipto_client_id = fields.Char(string="Criipto Client ID")
    criipto_client_secret = fields.Char(string="Criipto Client Secret")
    criipto_redirect_uri = fields.Char(string="Criipto Redirect URI")

    def get_criipto_client(self):
        """Get an authenticated Criipto client

        Returns:
            CriiptoSignatures: The authenticated client
        """
        self.ensure_one()

        if not self.criipto_client_id or not self.criipto_client_secret:
            raise UserError(_("Criipto Client ID and Client Secret must be configured."))

        try:
            client = CriiptoSignatures(
                client_id=self.criipto_client_id,
                client_secret=self.criipto_client_secret
            )
            return client
        except Exception as e:
            _logger.error("Failed to create Criipto client: %s", str(e))
            raise UserError(_("Failed to create Criipto client: %s") % str(e))

