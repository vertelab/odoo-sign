import secrets
import base64
import logging
import urllib.parse
import requests
import werkzeug
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError
from bankid import BankIDClient

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _bankid_provider(self):
        """Return the BankID sign provider whose certificates to use.

        Certificates live on the provider record (uploaded Binary fields), not
        on the company, so the company-level client delegates to it.
        """
        provider = self.env['sign.provider'].search(
            [('code', '=', 'bankid'), ('company_id', '=', self.id)], limit=1
        )
        if not provider:
            provider = self.env['sign.provider'].search(
                [('code', '=', 'bankid')], limit=1
            )
        return provider

    def bank_id_call(self, method_name, *args, **kwargs):
        """Call a BankIDClient method using the provider's certificates."""
        provider = self._bankid_provider()
        if not provider:
            from odoo.exceptions import UserError
            from odoo import _
            raise UserError(
                _("No BankID sign provider is configured. Create one under "
                  "Sign > Settings and upload the certificate.")
            )
        return provider.bank_id_call(method_name, *args, **kwargs)
