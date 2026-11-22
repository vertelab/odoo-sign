import requests
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)


class ScriveSignRequest(models.Model):
    _inherit = "vrtl.sign.request"

    scrive_document_id = fields.Char(string="Document ID", readonly=True)
    scrive_signatory_id = fields.Char(string="Signatory ID", readonly=True)
    scrive_is_document_signed = fields.Boolean(string="Signed and Sealed?", readonly=True)
    scrive_document_name = fields.Char(string="Document Name", readonly=True)
    scrive_document_data = fields.Binary(string="Datas", readonly=True)
    scrive_signed_date = fields.Datetime(string="Signed Date", readonly=True)
    scrive_last_updated = fields.Datetime(string="Signed Date", readonly=True)

    scrive_status = fields.Char(string="Status")

    email_delivery_status = fields.Selection(
        [
            ("delivered", "Delivered"),
            ("not_delivered", "Not Delivered"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(string="Rejection Reason", readonly=True)

    def download_scrive_document(self):
        """Download document from Scrive with proper filename"""
        if not self.scrive_document_id:
            return

        filename = f'{self.name}.pdf'
        provider = self.sign_provider_id
        url = f"{provider.scrive_api_url}/api/v2/documents/{self.scrive_document_id}/files/main/{filename}"
        headers = provider._build_request_headers()

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            pdf_base64 = base64.b64encode(response.content).decode('utf-8')
            self.write({
                'scrive_document_name': filename,
                'scrive_document_data': pdf_base64
            })

    def action_resend_invitation(self):
        provider = self.sign_provider_id
        url = f"{provider.scrive_api_url}/api/v2/documents/{self.scrive_document_id}/{self.signature_hash}/resend"
        headers = provider._build_request_headers()

        response = requests.post(url, headers=headers)

class ScriveSignRequestSinger(models.Model):
    _inherit = "vrtl.sign.request.signer"

    scrive_status = fields.Char(string="Status", readonly=True)

    email_delivery_status = fields.Selection(
        [
            ("delivered", "Delivered"),
            ("not_delivered", "Not Delivered"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        required=True,
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(string="Rejection Reason")