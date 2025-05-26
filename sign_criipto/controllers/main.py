import secrets
import base64
import urllib.parse
import requests
import werkzeug
import logging
from odoo import models, fields, api, _, http
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.fields import Command
from odoo.http import request

_logger = logging.getLogger(__name__)


class CriiptoController(http.Controller):

    @http.route('/criipto/callback', type='json', auth='public', csrf=False, methods=['POST'])
    def criipto_callback(self, **post):
        """Handle callbacks from Criipto Signatures"""
        _logger.info("Received Criipto callback")

        try:
            # Get the data from the request
            data = request.jsonrequest
            _logger.info(f"Callback data: {data}")

            # Extract the signature order ID and signatory ID
            signature_order_id = data.get('signatureOrderId')
            signatory_id = data.get('signatoryId')
            event_type = data.get('event')

            if not signature_order_id or not signatory_id or not event_type:
                _logger.error("Missing required fields in callback")
                return {'success': False, 'message': 'Missing required fields'}

            # Find the sale order with this signature order ID
            sale_order = request.env['sale.order'].sudo().search([
                ('criipto_signature_order_id', '=', signature_order_id)
            ], limit=1)

            if not sale_order:
                _logger.error(f"No sale order found with signature order ID: {signature_order_id}")
                return {'success': False, 'message': 'Sale order not found'}

            # Find the signatory
            signatory = request.env['criipto.signatory'].sudo().search([
                ('signatory_id', '=', signatory_id),
                ('sale_order_id', '=', sale_order.id)
            ], limit=1)

            if not signatory:
                _logger.error(f"No signatory found with ID: {signatory_id}")
                return {'success': False, 'message': 'Signatory not found'}

            # Update the signatory status based on the event
            if event_type == 'SIGNED':
                signatory.sudo().write({'status': 'signed'})
                _logger.info(f"Signatory {signatory.name} has signed the document")

                # Check if all signatories have signed
                all_signed = all(s.status == 'signed' for s in sale_order.signatory_ids)
                if all_signed:
                    # All signatories have signed, close the signature order
                    sale_order.sudo().action_close_signature_order()

            elif event_type == 'REJECTED':
                signatory.sudo().write({'status': 'rejected'})
                _logger.info(f"Signatory {signatory.name} has rejected the document")

            elif event_type == 'ERROR':
                signatory.sudo().write({'status': 'error'})
                _logger.error(f"Error with signatory {signatory.name}")

            return {'success': True}

        except Exception as e:
            _logger.exception(f"Error processing Criipto callback: {str(e)}")
            return {'success': False, 'message': str(e)}