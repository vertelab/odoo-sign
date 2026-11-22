import json
import base64
import logging
import traceback
import binascii
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
import requests

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    criipto_signature_order_id = fields.Char(string="Criipto Signature Order ID", readonly=True)

    def action_create_signature(self):
        """Create a signature request and get the signing URL"""
        self.ensure_one()

        if not self.sign_request_id:
            raise UserError(_("Please initiate a signature request."))

        try:

            self.sign_request_id._action_initiate_signature()

        except Exception as e:
            _logger.error(f"Failed to create signature request: {str(e)}")
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return None


