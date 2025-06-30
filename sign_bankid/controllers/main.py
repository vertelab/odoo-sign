import time
from datetime import datetime

from odoo import fields, http, _, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request
from odoo.tools import consteq

import logging

_logger = logging.getLogger(__name__)


class BankIDController(http.Controller):

    def _check_res_document_access(self, model_name, document_id, access_token=None):
        """Check if current user is allowed to access the specified record."""
        document = request.env[model_name].browse([document_id])
        document_sudo = document.with_user(SUPERUSER_ID).exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))
        try:
            document.check_access('read')
        except AccessError:
            if not access_token or not document_sudo.access_token or not consteq(document_sudo.access_token,
                                                                                 access_token):
                raise
        return document_sudo

    def _get_sign_request_from_record(self, res_model, res_id, access_token=None):
        """Get the sign request from any record that has sign.request.mixin"""
        try:
            # Get the original record
            rec_sudo = self._check_res_document_access(res_model, res_id, access_token=access_token)

            # Check if it has a sign request
            if hasattr(rec_sudo, 'sign_request_id') and rec_sudo.sign_request_id:
                return rec_sudo.sign_request_id
            elif res_model == 'vrtl.sign.request':
                return rec_sudo
            else:
                # Create sign request if needed
                if hasattr(rec_sudo, 'create_sign_request'):
                    sign_request = rec_sudo.create_sign_request()
                    return sign_request
                else:
                    raise ValidationError("Record does not support signing")

        except (AccessError, MissingError):
            raise ValidationError('Access denied or document not found')

    @http.route(['/bankid/initialize'], type='json', auth="public", website=True)
    def bankid_initialize(self, res_id, res_model, ssn=None, access_token=None, **kw):
        """Initialize a BankID signing process"""
        try:
            _logger.info(f"BankID Initialize called: res_id={res_id}, res_model={res_model}")

            # Get the sign request
            sign_request = self._get_sign_request_from_record(res_model, res_id, access_token)

            if not sign_request:
                return {'error': 'No sign request found'}

            # Check if it's BankID provider
            if sign_request.sign_provider_code != 'bankid':
                return {'error': 'Not configured for BankID signing'}

            # Start the signing process
            result = sign_request.sign()

            if isinstance(result, dict) and result.get('context'):
                context = result['context']
                return {
                    'success': True,
                    'order_ref': context.get('order_ref'),
                    'auto_start_token': context.get('auto_start_url', '').replace('bankid:///?autostarttoken=',
                                                                                  '').replace('&redirect=null', ''),
                    'qr_content': context.get('qr_code'),
                }
            else:
                return {'error': 'Failed to initialize BankID'}

        except Exception as e:
            _logger.error(f"Error in bankid_initialize: {e}", exc_info=True)
            return {'error': str(e)}

    @http.route(['/bankid/get_qr'], type='json', auth="public", website=True)
    def bankid_get_qr(self, res_id, res_model, ssn=None, access_token=None, **kw):
        """Get updated QR code content"""
        try:
            _logger.info(f"Getting QR code for: res_id={res_id}, res_model={res_model}")

            # Get the sign request
            sign_request = self._get_sign_request_from_record(res_model, res_id, access_token)

            if not sign_request or sign_request.sign_provider_code != 'bankid':
                return {'error': 'No BankID sign request found'}

            # Get current user's signer
            signer = sign_request.signer_id
            if not signer:
                user = request.env.user
                signer = sign_request.signer_ids.filtered(lambda s: s.partner_id == user.partner_id)
                if signer:
                    signer = signer[0]

            if not signer:
                return {'error': 'No signer found'}

            # Get updated QR code
            result = signer.get_updated_qr_code()

            if result.get('success'):
                return {'qr_content': result.get('qrCode')}
            else:
                return {'error': result.get('error', 'Failed to get QR code')}

        except Exception as e:
            _logger.error(f"Error in bankid_get_qr: {e}", exc_info=True)
            return {'error': str(e)}

    @http.route(['/bankid/collect'], type='json', auth="public", website=True)
    def bankid_collect(self, res_id, res_model, access_token=None, **kw):
        """Check the status of a BankID signing process"""
        try:
            _logger.info(f"Collecting BankID status for: res_id={res_id}, res_model={res_model}")

            # Get the sign request
            sign_request = self._get_sign_request_from_record(res_model, res_id, access_token)

            if not sign_request or sign_request.sign_provider_code != 'bankid':
                return {'status': 'error', 'message': 'No BankID sign request found'}

            # Get current user's signer
            signer = sign_request.signer_id
            if not signer:
                user = request.env.user
                signer = sign_request.signer_ids.filtered(lambda s: s.partner_id == user.partner_id)
                if signer:
                    signer = signer[0]

            if not signer:
                return {'status': 'error', 'message': 'No signer found'}

            # Check BankID status
            return signer.check_bankid_status()

        except Exception as e:
            _logger.error(f"Error in bankid_collect: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    @http.route('/bankid/cancel', type='json', auth='public')
    def bankid_cancel(self, order_ref, access_token=None, **kwargs):
        """Cancel the BankID signing process"""
        try:
            _logger.info(f"Cancelling BankID order: {order_ref}")

            # Find signer with this order ref
            signer = request.env['vrtl.sign.request.signer'].sudo().search([
                ('bankid_order_ref', '=', order_ref)
            ], limit=1)

            if not signer:
                return {'error': 'Invalid order reference'}

            # Cancel the signing
            result = signer.cancel_bankid_sign()
            return {'success': result}

        except Exception as e:
            _logger.error(f"Error in bankid_cancel: {e}", exc_info=True)
            return {'error': str(e)}